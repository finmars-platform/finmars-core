from __future__ import unicode_literals, print_function

import json
import uuid
from datetime import date, datetime, timedelta
from logging import getLogger

from croniter import croniter
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy

from poms.common.models import TimeStampedModel, AbstractClassModel, EXPRESSION_FIELD_LENGTH, DataTimeStampedModel, \
    NamedModel
from poms.configuration.models import ConfigurationModel
from poms.integrations.storage import import_config_storage
from poms.obj_attrs.models import GenericClassifier, GenericAttributeType

_l = getLogger('poms.integrations')

from poms.common.storage import get_storage

storage = get_storage()


class ProviderClass(AbstractClassModel):
    BLOOMBERG = 1
    CLASSES = (
        (BLOOMBERG, 'BLOOMBERG', gettext_lazy("Bloomberg")),
    )

    class Meta(AbstractClassModel.Meta):
        pass


class FactorScheduleDownloadMethod(AbstractClassModel):
    IGNORE = 1
    DEFAULT = 2
    CLASSES = (
        (IGNORE, 'IGNORE', gettext_lazy("Ignore")),
        (DEFAULT, 'DEFAULT', gettext_lazy("Default")),
    )

    class Meta(AbstractClassModel.Meta):
        pass


class AccrualScheduleDownloadMethod(AbstractClassModel):
    IGNORE = 1
    DEFAULT = 2
    CLASSES = (
        (IGNORE, 'IGNORE', gettext_lazy("Ignore")),
        (DEFAULT, 'DEFAULT', gettext_lazy("Default")),
    )

    class Meta(AbstractClassModel.Meta):
        pass


def import_cert_upload_to(instance, filename):
    # return '%s/%s' % (instance.master_user_id, filename)
    return '%s/%s-%s' % (instance.master_user_id, instance.provider_id, uuid.uuid4().hex)


def bloomberg_cert_upload_to(instance, filename):
    hex = uuid.uuid4().hex[:6]

    return '%s/data_providers/bloomberg/cert_%s.p12' % (instance.master_user.token, hex)


class BloombergDataProviderCredential(TimeStampedModel):
    master_user = models.ForeignKey('users.MasterUser', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    is_valid = models.BooleanField(default=False, verbose_name=gettext_lazy('is valid'))

    p12cert = models.TextField(blank=True, default='', verbose_name=gettext_lazy('File URL'))

    # p12cert = models.FileField(null=True, blank=True, upload_to=bloomberg_cert_upload_to, storage=storage,
    #                            verbose_name=gettext_lazy('p12cert'))

    password = models.CharField(max_length=64, null=True, blank=True, verbose_name=gettext_lazy('password'))

    def save(self, *args, **kwargs):

        qs = BloombergDataProviderCredential.objects.filter(master_user=self.master_user)

        _l.debug('self.master_user.pk %s ' % self.master_user.pk)
        _l.debug('qs len %s' % len(qs))
        if self.pk:
            qs = qs.exclude(pk=self.pk)
            qs.delete()

        _l.debug('qs len after %s' % len(qs))

        super(BloombergDataProviderCredential, self).save(*args, **kwargs)

    def __str__(self):
        return 'BloombergDataProviderCredential'

    @property
    def has_p12cert(self):
        return bool(self.p12cert)

    @property
    def has_password(self):
        return bool(self.password)

    @property
    def pair(self):
        if self.p12cert:
            try:
                from poms.integrations.providers.bloomberg import get_certs

                with storage.open(self.p12cert, 'rb') as f:

                    file_data = f.read()

                    return get_certs(file_data, self.password, is_base64=False)
            except FileNotFoundError:
                raise ValueError(gettext_lazy("Can't read cert file"))
        return None, None


class ImportConfig(models.Model):
    master_user = models.ForeignKey('users.MasterUser', related_name='import_configs',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    provider = models.ForeignKey(ProviderClass, verbose_name=gettext_lazy('provider'), on_delete=models.CASCADE)

    # p12cert = models.FileField(null=True, blank=True, upload_to=import_cert_upload_to, storage=import_config_storage,
    #                            verbose_name=gettext_lazy('p12cert'))
    p12cert = models.TextField(blank=True, default='', verbose_name=gettext_lazy('p12cert'))
    password = models.CharField(max_length=64, null=True, blank=True, verbose_name=gettext_lazy('password'))

    cert = models.TextField(blank=True, default='', verbose_name=gettext_lazy('cert'))
    key = models.TextField(blank=True, default='', verbose_name=gettext_lazy('key'))

    # cert = models.FileField(null=True, blank=True, upload_to=import_cert_upload_to, storage=import_config_storage,
    #                         verbose_name=gettext_lazy('cert'))
    # key = models.FileField(null=True, blank=True, upload_to=import_cert_upload_to, storage=import_config_storage,
    #                        verbose_name=gettext_lazy('key'))

    is_valid = models.BooleanField(default=False, verbose_name=gettext_lazy('is valid'))

    class Meta:
        verbose_name = gettext_lazy('import config')
        verbose_name_plural = gettext_lazy('import configs')
        unique_together = [
            ['master_user', 'provider']
        ]

    def __str__(self):
        return '%s' % self.provider.name

    # def delete(self, using=None, keep_parents=False):
    #     if self.p12cert:
    #         self.p12cert.delete(save=False)
    #     if self.cert:
    #         self.cert.delete(save=False)
    #     if self.key:
    #         self.key.delete(save=False)
    #     super(BloombergConfig, self).delete(using=using, keep_parents=keep_parents)

    @property
    def pair(self):
        if self.cert and self.key:
            return self.cert, self.key
        elif self.p12cert:
            try:
                from poms.integrations.providers.bloomberg import get_certs
                return get_certs(self.p12cert.read(), self.password, is_base64=False)
            except FileNotFoundError:
                raise ValueError(gettext_lazy("Can't read cert file"))
        return None, None

    @property
    def has_p12cert(self):
        return bool(self.p12cert)

    @property
    def has_password(self):
        return bool(self.password)

    @property
    def has_cert(self):
        return bool(self.cert)

    @property
    def has_key(self):
        return bool(self.key)

    @property
    def is_ready(self):
        return (self.has_p12cert and self.has_password) or (self.has_cert and self.has_key)


class InstrumentDownloadScheme(NamedModel, DataTimeStampedModel):
    MODE_CHOICES = [
        ['skip', 'Skip if exists'],
        ['overwrite_empty_values', 'Overwrite only empty values'],
        ['overwrite', 'Overwrite'],
    ]

    BASIC_FIELDS = [
        'reference_for_pricing', 'instrument_user_code', 'instrument_name', 'instrument_short_name',
        'instrument_public_name', 'instrument_notes', 'instrument_type',
        'pricing_currency', 'price_multiplier', 'accrued_currency', 'accrued_multiplier', 'maturity_date',
        'user_text_1', 'user_text_2', 'user_text_3',
    ]

    mode = models.CharField(max_length=255, choices=MODE_CHOICES, default='skip')

    user_code = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('user code'))

    master_user = models.ForeignKey('users.MasterUser', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    provider = models.ForeignKey(ProviderClass, verbose_name=gettext_lazy('provider'), on_delete=models.PROTECT)

    reference_for_pricing = models.CharField(max_length=255, blank=True, default='',
                                             verbose_name=gettext_lazy('reference for pricing'))
    instrument_user_code = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                            verbose_name=gettext_lazy('user code'))
    instrument_name = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=gettext_lazy('name'))
    instrument_short_name = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                             verbose_name=gettext_lazy('short name'))
    instrument_public_name = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                              verbose_name=gettext_lazy('public name'))
    instrument_notes = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                        verbose_name=gettext_lazy('notes'))
    instrument_type = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                       verbose_name=gettext_lazy('instrument type'))
    pricing_currency = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                        verbose_name=gettext_lazy('pricing currency'))
    price_multiplier = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='1.0',
                                        verbose_name=gettext_lazy('price multiplier'))
    accrued_currency = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                        verbose_name=gettext_lazy('accrued currency'))
    accrued_multiplier = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='1.0',
                                          verbose_name=gettext_lazy('accrued multiplier'))
    maturity_date = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=gettext_lazy('maturity date'))
    maturity_price = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                      verbose_name=gettext_lazy('maturity price'))
    user_text_1 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=gettext_lazy('user text 1'))
    user_text_2 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=gettext_lazy('user text 2'))
    user_text_3 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=gettext_lazy('user text 3'))

    payment_size_detail = models.ForeignKey('instruments.PaymentSizeDetail', on_delete=models.PROTECT,
                                            null=True, blank=True, verbose_name=gettext_lazy('payment size detail'))
    daily_pricing_model = models.ForeignKey('instruments.DailyPricingModel', null=True, blank=True,
                                            verbose_name=gettext_lazy('daily pricing model'), on_delete=models.SET_NULL)
    default_price = models.FloatField(default=0.0, verbose_name=gettext_lazy('default price'))
    default_accrued = models.FloatField(default=0.0, verbose_name=gettext_lazy('default accrued'))

    factor_schedule_method = models.ForeignKey(FactorScheduleDownloadMethod, null=True, blank=True,
                                               verbose_name=gettext_lazy('factor schedule method'),
                                               on_delete=models.SET_NULL)
    accrual_calculation_schedule_method = models.ForeignKey(AccrualScheduleDownloadMethod, null=True, blank=True,
                                                            verbose_name=gettext_lazy(
                                                                'accrual calculation schedule method'),
                                                            on_delete=models.SET_NULL)

    class Meta:
        verbose_name = gettext_lazy('instrument download scheme')
        verbose_name_plural = gettext_lazy('instrument download schemes')

    def __str__(self):
        return self.user_code

    @property
    def fields(self):
        return [f.field for f in self.inputs.all() if f.field]


class InstrumentDownloadSchemeInput(models.Model):
    scheme = models.ForeignKey(InstrumentDownloadScheme, related_name='inputs', verbose_name=gettext_lazy('scheme'),
                               on_delete=models.CASCADE)
    name = models.CharField(max_length=32, blank=True, default='', verbose_name=gettext_lazy('name'))
    field = models.CharField(max_length=32, blank=True, default='', verbose_name=gettext_lazy('field'))
    name_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                 verbose_name=gettext_lazy('name expression'))

    class Meta:
        verbose_name = gettext_lazy('instrument download scheme input')
        verbose_name_plural = gettext_lazy('instrument download scheme inputs')
        unique_together = (
            ('scheme', 'name')
        )
        ordering = ['name', ]

    def __str__(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.field:
            self.field = self.name
        return super(InstrumentDownloadSchemeInput, self).save(
            force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class InstrumentDownloadSchemeAttribute(models.Model):
    scheme = models.ForeignKey(InstrumentDownloadScheme, related_name='attributes',
                               verbose_name=gettext_lazy('scheme'), on_delete=models.CASCADE)
    attribute_type = models.ForeignKey('obj_attrs.GenericAttributeType', null=True, blank=True,
                                       verbose_name=gettext_lazy('attribute_ type'), on_delete=models.SET_NULL)
    value = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                             verbose_name=gettext_lazy('value'))

    class Meta:
        verbose_name = gettext_lazy('instrument download scheme attribute')
        verbose_name_plural = gettext_lazy('instrument download schemes attribute')
        unique_together = (
            ('scheme', 'attribute_type')
        )
        ordering = ['attribute_type']

    def __str__(self):
        # return '%s -> %s' % (self.name, self.attribute_type)
        return '%s' % (self.attribute_type,)


# DEPRECATED
class PriceDownloadScheme(models.Model):
    master_user = models.ForeignKey('users.MasterUser', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    scheme_name = models.CharField(max_length=255, verbose_name=gettext_lazy('scheme name'))
    provider = models.ForeignKey(ProviderClass, verbose_name=gettext_lazy('provider'), on_delete=models.PROTECT)

    bid0 = models.CharField(max_length=50, blank=True, verbose_name=gettext_lazy('bid0'))
    bid1 = models.CharField(max_length=50, blank=True, verbose_name=gettext_lazy('bid1'))
    bid2 = models.CharField(max_length=50, blank=True, verbose_name=gettext_lazy('bid2'))
    bid_multiplier = models.FloatField(default=1.0, verbose_name=gettext_lazy('bid multiplier'))
    ask0 = models.CharField(max_length=50, blank=True, verbose_name=gettext_lazy('ask0'))
    ask1 = models.CharField(max_length=50, blank=True, verbose_name=gettext_lazy('ask1'))
    ask2 = models.CharField(max_length=50, blank=True, verbose_name=gettext_lazy('ask2'))
    ask_multiplier = models.FloatField(default=1.0, verbose_name=gettext_lazy('ask multiplier'))
    last = models.CharField(max_length=50, blank=True, verbose_name=gettext_lazy('last'))
    last_multiplier = models.FloatField(default=1.0, verbose_name=gettext_lazy('last multiplier'))
    mid = models.CharField(max_length=50, blank=True, verbose_name=gettext_lazy('mid'))
    mid_multiplier = models.FloatField(default=1.0, verbose_name=gettext_lazy('mid multiplier'))

    bid_history = models.CharField(max_length=50, blank=True, verbose_name=gettext_lazy('bid history'))
    bid_history_multiplier = models.FloatField(default=1.0, verbose_name=gettext_lazy('bid history multiplier'))
    ask_history = models.CharField(max_length=50, blank=True, verbose_name=gettext_lazy('ask history'))
    ask_history_multiplier = models.FloatField(default=1.0, verbose_name=gettext_lazy('ask history multiplier'))
    mid_history = models.CharField(max_length=50, blank=True, verbose_name=gettext_lazy('mid history'))
    mid_history_multiplier = models.FloatField(default=1.0, verbose_name=gettext_lazy('mid history multiplier'))
    last_history = models.CharField(max_length=50, blank=True, verbose_name=gettext_lazy('last history'))
    last_history_multiplier = models.FloatField(default=1.0, verbose_name=gettext_lazy('last history multiplier'))

    currency_fxrate = models.CharField(max_length=50, blank=True, verbose_name=gettext_lazy('currency FX-rate'))
    currency_fxrate_multiplier = models.FloatField(default=1.0,
                                                   verbose_name=gettext_lazy('currency FX-rate multiplier'))

    class Meta:
        verbose_name = gettext_lazy('price download scheme')
        verbose_name_plural = gettext_lazy('price download schemes')
        unique_together = [
            ['master_user', 'scheme_name']
        ]
        ordering = ['scheme_name', ]

    def __str__(self):
        return self.scheme_name

    def _get_fields(self, *args):
        ret = set()
        for attr_name in args:
            field_name = getattr(self, attr_name)
            if field_name:
                ret.add(field_name)
        return sorted(ret)

    def _get_value(self, values, *args):
        for attr_name in args:
            field_name = getattr(self, attr_name)
            if field_name and field_name in values:
                value = values[field_name]
                return float(value) if value is not None else 0.0
        return 0.0

    @property
    def instrument_yesterday_fields(self):
        return self._get_fields('bid0', 'bid1', 'bid2', 'ask0', 'ask1', 'ask2', 'last', 'mid')

    @property
    def instrument_history_fields(self):
        return self._get_fields('bid_history', 'ask_history', 'mid_history', 'last_history')

    @property
    def currency_history_fields(self):
        return self._get_fields('currency_fxrate')


# -------


class AbstractMapping(models.Model):
    master_user = models.ForeignKey('users.MasterUser', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    provider = models.ForeignKey(ProviderClass, verbose_name=gettext_lazy('provider'), on_delete=models.CASCADE)
    value = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('value'))

    class Meta:
        abstract = True
        ordering = ['value']

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class CurrencyMapping(AbstractMapping):
    content_object = models.ForeignKey('currencies.Currency', verbose_name=gettext_lazy('currency'),
                                       on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('currency mapping')
        verbose_name_plural = gettext_lazy('currency mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class PricingPolicyMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.PricingPolicy', verbose_name=gettext_lazy('pricing policy'),
                                       on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('pricing policy mapping')
        verbose_name_plural = gettext_lazy('pricing policy mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class InstrumentTypeMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.InstrumentType', verbose_name=gettext_lazy('instrument type'),
                                       on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('instrument type mapping')
        verbose_name_plural = gettext_lazy('instrument type mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class AccountTypeMapping(AbstractMapping):
    content_object = models.ForeignKey('accounts.AccountType', verbose_name=gettext_lazy('account type'),
                                       on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('account type mapping')
        verbose_name_plural = gettext_lazy('account type mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class InstrumentAttributeValueMapping(AbstractMapping):
    content_object = models.ForeignKey('obj_attrs.GenericAttributeType', on_delete=models.PROTECT,
                                       verbose_name=gettext_lazy('attribute type'))
    value_string = models.CharField(max_length=255, default='', blank=True,
                                    verbose_name=gettext_lazy('value (String)'))
    value_float = models.FloatField(default=0.0, verbose_name=gettext_lazy('value (Float)'))
    value_date = models.DateField(default=date.min, verbose_name=gettext_lazy('value (Date)'))
    classifier = models.ForeignKey('obj_attrs.GenericClassifier', on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name=gettext_lazy('classifier'))

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('instrument attribute value mapping')
        verbose_name_plural = gettext_lazy('instrument attribute value mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        value = self.content_object.get_value(self)
        return '%s / %s -> %s / %s' % (self.provider, self.value, self.content_object, value)


class AccrualCalculationModelMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.AccrualCalculationModel',
                                       verbose_name=gettext_lazy('accrual calculation model'), on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('accrual calculation model mapping')
        verbose_name_plural = gettext_lazy('accrual calculation model  mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class PeriodicityMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.Periodicity', verbose_name=gettext_lazy('periodicity'),
                                       on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('periodicity mapping')
        verbose_name_plural = gettext_lazy('periodicity  mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
            # ['master_user', 'provider', 'periodicity'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class AccountMapping(AbstractMapping):
    content_object = models.ForeignKey('accounts.Account', verbose_name=gettext_lazy('account'),
                                       on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('account mapping')
        verbose_name_plural = gettext_lazy('account mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class AccountClassifierMapping(AbstractMapping):
    attribute_type = models.ForeignKey(GenericAttributeType, on_delete=models.CASCADE)
    content_object = models.ForeignKey(GenericClassifier, on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('account classifier mapping')
        verbose_name_plural = gettext_lazy('account classifier mappings')
        unique_together = [
            ['master_user', 'provider', 'value', 'attribute_type'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class InstrumentMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.Instrument', verbose_name=gettext_lazy('instrument'),
                                       on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('instrument mapping')
        verbose_name_plural = gettext_lazy('instrument mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class InstrumentClassifierMapping(AbstractMapping):
    attribute_type = models.ForeignKey(GenericAttributeType, on_delete=models.CASCADE)
    content_object = models.ForeignKey(GenericClassifier, on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('instrument classifier mapping')
        verbose_name_plural = gettext_lazy('instrument classifier mappings')
        unique_together = [
            ['master_user', 'provider', 'value', 'attribute_type'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class CounterpartyMapping(AbstractMapping):
    content_object = models.ForeignKey('counterparties.Counterparty', verbose_name=gettext_lazy('counterparty'),
                                       on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('counterparty mapping')
        verbose_name_plural = gettext_lazy('counterparty mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class CounterpartyClassifierMapping(AbstractMapping):
    attribute_type = models.ForeignKey(GenericAttributeType, on_delete=models.CASCADE)
    content_object = models.ForeignKey(GenericClassifier, on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('responsible classifier mapping')
        verbose_name_plural = gettext_lazy('responsible classifier mappings')
        unique_together = [
            ['master_user', 'provider', 'value', 'attribute_type'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class ResponsibleMapping(AbstractMapping):
    content_object = models.ForeignKey('counterparties.Responsible', verbose_name=gettext_lazy('responsible'),
                                       on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('responsible mapping')
        verbose_name_plural = gettext_lazy('responsible mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class ResponsibleClassifierMapping(AbstractMapping):
    attribute_type = models.ForeignKey(GenericAttributeType, on_delete=models.CASCADE)
    content_object = models.ForeignKey(GenericClassifier, on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('responsible classifier mapping')
        verbose_name_plural = gettext_lazy('responsible classifier mappings')
        unique_together = [
            ['master_user', 'provider', 'value', 'attribute_type'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class PortfolioMapping(AbstractMapping):
    content_object = models.ForeignKey('portfolios.Portfolio', verbose_name=gettext_lazy('portfolio'),
                                       on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('portfolio mapping')
        verbose_name_plural = gettext_lazy('portfolio mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class PortfolioClassifierMapping(AbstractMapping):
    attribute_type = models.ForeignKey(GenericAttributeType, on_delete=models.CASCADE)
    content_object = models.ForeignKey(GenericClassifier, on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('portfolio classifier mapping')
        verbose_name_plural = gettext_lazy('portfolio classifier mappings')
        unique_together = [
            ['master_user', 'provider', 'value', 'attribute_type'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class Strategy1Mapping(AbstractMapping):
    content_object = models.ForeignKey('strategies.Strategy1', verbose_name=gettext_lazy('strategy1'),
                                       on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('strategy1 mapping')
        verbose_name_plural = gettext_lazy('strategy1 mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class Strategy2Mapping(AbstractMapping):
    content_object = models.ForeignKey('strategies.Strategy2', verbose_name=gettext_lazy('strategy2'),
                                       on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('strategy2 mapping')
        verbose_name_plural = gettext_lazy('strategy2 mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class Strategy3Mapping(AbstractMapping):
    content_object = models.ForeignKey('strategies.Strategy3', verbose_name=gettext_lazy('strategy3'),
                                       on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('strategy3 mapping')
        verbose_name_plural = gettext_lazy('strategy3 mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class DailyPricingModelMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.DailyPricingModel',
                                       verbose_name=gettext_lazy('daily pricing model'), on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('daily pricing model mapping')
        verbose_name_plural = gettext_lazy('daily pricing model mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class PaymentSizeDetailMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.PaymentSizeDetail',
                                       verbose_name=gettext_lazy('payment size detail'), on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('payment size detail mapping')
        verbose_name_plural = gettext_lazy('payment size detail model mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class PriceDownloadSchemeMapping(AbstractMapping):
    content_object = models.ForeignKey('integrations.PriceDownloadScheme',
                                       verbose_name=gettext_lazy('price download scheme'), on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('price download scheme mapping')
        verbose_name_plural = gettext_lazy('price download scheme mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class PricingConditionMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.PricingCondition',
                                       verbose_name=gettext_lazy('pricing condition'), on_delete=models.CASCADE)

    class Meta(AbstractMapping.Meta):
        verbose_name = gettext_lazy('pricing condition mapping')
        verbose_name_plural = gettext_lazy('pricing condition model mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)

# ----------------------------------------


ERROR_HANDLER_CHOICES = [
    ['break', 'Break'],
    ['continue', 'Continue'],
]

DELIMITER_CHOICES = [
    [',', 'Comma'],
    [';', 'Semicolon'],
    ['\t', 'Tab'],
]

MISSING_DATA_CHOICES = [
    ['throw_error', 'Treat as Error'],
    ['set_defaults', 'Replace with Default Value'],
]

COLUMN_MATCHER_CHOICES = [
    ['index', 'Index'],
    ['name', 'Name']
]


class ComplexTransactionImportScheme(NamedModel, DataTimeStampedModel, ConfigurationModel):
    SKIP = 1
    BOOK_WITHOUT_UNIQUE_CODE = 2
    OVERWRITE = 3
    TREAT_AS_ERROR = 4
    USE_TRANSACTION_TYPE_SETTING = 5

    BOOK_UNIQUENESS_CHOICES = (
        (SKIP, gettext_lazy('Skip')),
        (BOOK_WITHOUT_UNIQUE_CODE, gettext_lazy('Book without Unique Code ')),
        (OVERWRITE, gettext_lazy('Overwrite')),
        (TREAT_AS_ERROR, gettext_lazy('Treat as error')),
        (USE_TRANSACTION_TYPE_SETTING, gettext_lazy('Use Transaction Type Setting')),
    )

    user_code = models.CharField(max_length=1024, null=True, blank=True, verbose_name=gettext_lazy('user code'))

    book_uniqueness_settings = models.PositiveSmallIntegerField(default=SKIP, choices=BOOK_UNIQUENESS_CHOICES,
                                                                verbose_name=gettext_lazy('book uniqueness settings'))

    master_user = models.ForeignKey('users.MasterUser', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    rule_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=gettext_lazy('rule expressions'))

    recon_layout_json = models.TextField(null=True, blank=True,
                                         verbose_name=gettext_lazy('recon layout json'))

    delimiter = models.CharField(max_length=255, choices=DELIMITER_CHOICES, default=',')
    error_handler = models.CharField(max_length=255, choices=ERROR_HANDLER_CHOICES, default='break')
    missing_data_handler = models.CharField(max_length=255, choices=MISSING_DATA_CHOICES, default='throw_error')

    spreadsheet_start_cell = models.CharField(max_length=255, default='A1')
    spreadsheet_active_tab_name = models.CharField(max_length=255, default='', blank=True, null=True)

    column_matcher = models.CharField(max_length=255, choices=COLUMN_MATCHER_CHOICES, default='index')

    filter_expression = models.CharField(max_length=255, null=True, blank=True,
                                         verbose_name=gettext_lazy('filter expression'))
    has_header_row = models.BooleanField(default=True, verbose_name=gettext_lazy("has header row"))

    data_preprocess_expression = models.CharField(null=True, max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                                  verbose_name=gettext_lazy('data preprocess expression'))

    expression_iterations_count = models.SmallIntegerField(default=1) # min 1

    @property
    def recon_layout(self):
        try:
            return json.loads(self.recon_layout_json) if self.recon_layout_json else None
        except (ValueError, TypeError):
            return None

    @recon_layout.setter
    def recon_layout(self, data):
        self.recon_layout_json = json.dumps(data, cls=DjangoJSONEncoder, sort_keys=True) if data else None

    class Meta:
        verbose_name = gettext_lazy('complex transaction import scheme')
        verbose_name_plural = gettext_lazy('complex transaction import schemes')
        unique_together = [
            ['master_user', 'user_code'],
        ]

    def __str__(self):
        return self.user_code


class ComplexTransactionImportSchemeInput(models.Model):
    scheme = models.ForeignKey(ComplexTransactionImportScheme, related_name='inputs',
                               verbose_name=gettext_lazy('scheme'), on_delete=models.CASCADE)
    # order = models.SmallIntegerField(default=0)
    name = models.CharField(max_length=255)
    column = models.SmallIntegerField()
    column_name = models.CharField(max_length=255, blank=True, null=True)

    name_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='',
                                 verbose_name=gettext_lazy('name expression'))

    class Meta:
        verbose_name = gettext_lazy('complex transaction import scheme input')
        verbose_name_plural = gettext_lazy('complex transaction import scheme inputs')
        # ordering = ['order']
        order_with_respect_to = 'scheme'

    def __str__(self):
        return self.name


class ComplexTransactionImportSchemeCalculatedInput(models.Model):
    scheme = models.ForeignKey(ComplexTransactionImportScheme, related_name='calculated_inputs',
                               verbose_name=gettext_lazy('scheme'), on_delete=models.CASCADE)
    # order = models.SmallIntegerField(default=0)
    name = models.CharField(max_length=255)
    column = models.SmallIntegerField()

    name_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='',
                                 verbose_name=gettext_lazy('name expression'))

    class Meta:
        verbose_name = gettext_lazy('complex transaction import scheme calculated input')
        verbose_name_plural = gettext_lazy('complex transaction import scheme calculated inputs')
        # ordering = ['order']
        order_with_respect_to = 'scheme'

    def __str__(self):
        return self.name


class ComplexTransactionImportSchemeSelectorValue(models.Model):
    scheme = models.ForeignKey(ComplexTransactionImportScheme, related_name='selector_values',
                               verbose_name=gettext_lazy('scheme'), on_delete=models.CASCADE)

    value = models.CharField(max_length=1000, verbose_name=gettext_lazy('value '))
    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'))

    order = models.IntegerField(default=0, verbose_name=gettext_lazy('order'))


class ComplexTransactionImportSchemeRuleScenario(models.Model):

    MODE_CHOICES = [
        ['active', 'active'],
        ['skip', 'skip'],
    ]

    is_default_rule_scenario = models.BooleanField(default=False, verbose_name=gettext_lazy('is default rule scenario'))
    is_error_rule_scenario = models.BooleanField(default=False, verbose_name=gettext_lazy('is error rule scenario'))

    scheme = models.ForeignKey(ComplexTransactionImportScheme, related_name='rule_scenarios',
                               verbose_name=gettext_lazy('scheme'), on_delete=models.CASCADE)
    # order = models.SmallIntegerField(default=0)

    name = models.CharField(max_length=255, verbose_name=gettext_lazy('name'), null=True, blank=True, )

    status = models.CharField(max_length=255, choices=MODE_CHOICES, default='active')

    # value = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('mapping value'))
    transaction_type = models.ForeignKey('transactions.TransactionType', on_delete=models.CASCADE,
                                         verbose_name=gettext_lazy('transaction type'))

    selector_values = models.ManyToManyField('ComplexTransactionImportSchemeSelectorValue', blank=True,
                                             related_name='rule_selector_values',
                                             verbose_name=gettext_lazy('selector values'))

    class Meta:
        verbose_name = gettext_lazy('complex transaction import scheme rule scenario')
        verbose_name_plural = gettext_lazy('complex transaction import scheme rules scenarios')
        # ordering = ['order']
        order_with_respect_to = 'scheme'

    def __str__(self):
        if self.name:
            return self.name
        return ''


class ComplexTransactionImportSchemeField(models.Model):
    # for simpler admin
    # scheme = models.ForeignKey(ComplexTransactionImportScheme, verbose_name=gettext_lazy('scheme'))
    rule_scenario = models.ForeignKey(ComplexTransactionImportSchemeRuleScenario, related_name='fields',
                                      null=True,
                                      verbose_name=gettext_lazy('rule scenario'), on_delete=models.CASCADE)
    # order = models.SmallIntegerField(default=0)
    # name = models.CharField(max_length=255, verbose_name=gettext_lazy('name'))
    transaction_type_input = models.ForeignKey('transactions.TransactionTypeInput', on_delete=models.CASCADE,
                                               verbose_name=gettext_lazy('transaction type input'))
    value_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=gettext_lazy('value expression'))

    class Meta:
        verbose_name = gettext_lazy('complex transaction import scheme field')
        verbose_name_plural = gettext_lazy('complex transaction import scheme fields')
        # ordering = ['order']
        # order_with_respect_to = 'rule_scenario'

    def __str__(self):
        return '%s - %s' % (self.rule_scenario, self.transaction_type_input,)


class ComplexTransactionImportSchemeReconScenario(models.Model):
    scheme = models.ForeignKey(ComplexTransactionImportScheme, related_name='recon_scenarios',
                               verbose_name=gettext_lazy('scheme'), on_delete=models.CASCADE)

    name = models.CharField(max_length=255, verbose_name=gettext_lazy('name'), null=True, blank=True, )
    line_reference_id = models.CharField(max_length=EXPRESSION_FIELD_LENGTH,
                                         verbose_name=gettext_lazy('line reference id'))
    reference_date = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=gettext_lazy('reference_date'))

    selector_values = models.ManyToManyField('ComplexTransactionImportSchemeSelectorValue', blank=True,
                                             related_name='recon_selector_values',
                                             verbose_name=gettext_lazy('selector values'))

    class Meta:
        verbose_name = gettext_lazy('complex transaction import scheme recon scenario')
        verbose_name_plural = gettext_lazy('complex transaction import scheme recon scenarios')

    def __str__(self):
        if self.name:
            return self.name
        return ''


class ComplexTransactionImportSchemeReconField(models.Model):
    recon_scenario = models.ForeignKey(ComplexTransactionImportSchemeReconScenario, related_name='fields',
                                       verbose_name=gettext_lazy('recon scenario'), on_delete=models.CASCADE)

    reference_name = models.CharField(max_length=255, verbose_name=gettext_lazy('reference name '))
    description = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('description'))

    value_string = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=gettext_lazy('value string'))
    value_float = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=gettext_lazy('value float'))
    value_date = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=gettext_lazy('value date'))


class DataProvider(models.Model):
    name = models.CharField(max_length=255)
    user_code = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('user code'))
    notes = models.TextField(blank=True, default='', verbose_name=gettext_lazy('notes'))

    def __str__(self):
        return self.name


class TransactionFileResult(DataTimeStampedModel):
    procedure_instance = models.ForeignKey('procedures.RequestDataFileProcedureInstance', on_delete=models.CASCADE,
                                           verbose_name=gettext_lazy('procedure'))

    master_user = models.ForeignKey('users.MasterUser', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    provider = models.ForeignKey(DataProvider, verbose_name=gettext_lazy('provider'), on_delete=models.CASCADE)

    scheme_user_code = models.CharField(max_length=255)

    file_path = models.TextField(blank=True, default='', verbose_name=gettext_lazy('File Path'))
    file_name = models.CharField(max_length=255, blank=True, default='')
