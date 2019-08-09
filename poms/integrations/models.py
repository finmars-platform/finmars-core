from __future__ import unicode_literals, print_function

import json
import uuid
from datetime import date, datetime, timedelta
from logging import getLogger

from croniter import croniter
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext, ugettext_lazy

from poms.common.models import TimeStampedModel, AbstractClassModel, EXPRESSION_FIELD_LENGTH
from poms.integrations.storage import import_config_storage
from poms.obj_attrs.models import GenericClassifier, GenericAttributeType

_l = getLogger('poms.integrations')


class ProviderClass(AbstractClassModel):
    BLOOMBERG = 1
    CLASSES = (
        (BLOOMBERG, 'BLOOMBERG', ugettext_lazy("Bloomberg")),
    )

    class Meta(AbstractClassModel.Meta):
        pass


class FactorScheduleDownloadMethod(AbstractClassModel):
    IGNORE = 1
    DEFAULT = 2
    CLASSES = (
        (IGNORE, 'IGNORE', ugettext_lazy("Ignore")),
        (DEFAULT, 'DEFAULT', ugettext_lazy("Default")),
    )

    class Meta(AbstractClassModel.Meta):
        pass


class AccrualScheduleDownloadMethod(AbstractClassModel):
    IGNORE = 1
    DEFAULT = 2
    CLASSES = (
        (IGNORE, 'IGNORE', ugettext_lazy("Ignore")),
        (DEFAULT, 'DEFAULT', ugettext_lazy("Default")),
    )

    class Meta(AbstractClassModel.Meta):
        pass


def import_cert_upload_to(instance, filename):
    # return '%s/%s' % (instance.master_user_id, filename)
    return '%s/%s-%s' % (instance.master_user_id, instance.provider_id, uuid.uuid4().hex)


class ImportConfig(models.Model):
    master_user = models.ForeignKey('users.MasterUser', related_name='import_configs',
                                    verbose_name=ugettext_lazy('master user'))
    provider = models.ForeignKey(ProviderClass, verbose_name=ugettext_lazy('provider'))
    p12cert = models.FileField(null=True, blank=True, upload_to=import_cert_upload_to, storage=import_config_storage,
                               verbose_name=ugettext_lazy('p12cert'))
    password = models.CharField(max_length=64, null=True, blank=True, verbose_name=ugettext_lazy('password'))
    cert = models.FileField(null=True, blank=True, upload_to=import_cert_upload_to, storage=import_config_storage,
                            verbose_name=ugettext_lazy('cert'))
    key = models.FileField(null=True, blank=True, upload_to=import_cert_upload_to, storage=import_config_storage,
                           verbose_name=ugettext_lazy('key'))

    is_valid = models.BooleanField(default=False, verbose_name=ugettext_lazy('is valid'))

    class Meta:
        verbose_name = ugettext_lazy('import config')
        verbose_name_plural = ugettext_lazy('import configs')
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
                raise ValueError(ugettext("Can't read cert file"))
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


class InstrumentDownloadScheme(models.Model):
    BASIC_FIELDS = [
        'reference_for_pricing', 'user_code', 'name', 'short_name', 'public_name', 'notes', 'instrument_type',
        'pricing_currency', 'price_multiplier', 'accrued_currency', 'accrued_multiplier', 'maturity_date',
        'user_text_1', 'user_text_2', 'user_text_3',
    ]

    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'))
    scheme_name = models.CharField(max_length=255, verbose_name=ugettext_lazy('scheme name'))
    provider = models.ForeignKey(ProviderClass, verbose_name=ugettext_lazy('provider'))

    reference_for_pricing = models.CharField(max_length=255, blank=True, default='',
                                             verbose_name=ugettext_lazy('reference for pricing'))
    user_code = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                 verbose_name=ugettext_lazy('user code'))
    name = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=ugettext_lazy('name'))
    short_name = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                  verbose_name=ugettext_lazy('short name'))
    public_name = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('public name'))
    notes = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                             verbose_name=ugettext_lazy('notes'))
    instrument_type = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                       verbose_name=ugettext_lazy('instrument type'))
    pricing_currency = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                        verbose_name=ugettext_lazy('pricing currency'))
    price_multiplier = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='1.0',
                                        verbose_name=ugettext_lazy('price multiplier'))
    accrued_currency = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                        verbose_name=ugettext_lazy('accrued currency'))
    accrued_multiplier = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='1.0',
                                          verbose_name=ugettext_lazy('accrued multiplier'))
    maturity_date = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('maturity date'))
    maturity_price = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                      verbose_name=ugettext_lazy('maturity price'))
    user_text_1 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 1'))
    user_text_2 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 2'))
    user_text_3 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 3'))

    payment_size_detail = models.ForeignKey('instruments.PaymentSizeDetail', on_delete=models.PROTECT,
                                            null=True, blank=True, verbose_name=ugettext_lazy('payment size detail'))
    daily_pricing_model = models.ForeignKey('instruments.DailyPricingModel', null=True, blank=True,
                                            verbose_name=ugettext_lazy('daily pricing model'))
    price_download_scheme = models.ForeignKey('integrations.PriceDownloadScheme', on_delete=models.PROTECT, null=True,
                                              blank=True, verbose_name=ugettext_lazy('price download scheme'))
    default_price = models.FloatField(default=0.0, verbose_name=ugettext_lazy('default price'))
    default_accrued = models.FloatField(default=0.0, verbose_name=ugettext_lazy('default accrued'))

    factor_schedule_method = models.ForeignKey(FactorScheduleDownloadMethod, null=True, blank=True,
                                               verbose_name=ugettext_lazy('factor schedule method'))
    accrual_calculation_schedule_method = models.ForeignKey(AccrualScheduleDownloadMethod, null=True, blank=True,
                                                            verbose_name=ugettext_lazy(
                                                                'accrual calculation schedule method'))

    class Meta:
        verbose_name = ugettext_lazy('instrument download scheme')
        verbose_name_plural = ugettext_lazy('instrument download schemes')
        index_together = (
            ('master_user', 'scheme_name')
        )
        unique_together = (
            ('master_user', 'scheme_name')
        )
        ordering = ['scheme_name', ]
        # permissions = [
        #     ('view_instrumentdownloadscheme', 'Can view instrument download scheme'),
        #     ('manage_instrumentdownloadscheme', 'Can manage instrument download scheme'),
        # ]

    def __str__(self):
        return self.scheme_name

    @property
    def fields(self):
        return [f.field for f in self.inputs.all() if f.field]


class InstrumentDownloadSchemeInput(models.Model):
    scheme = models.ForeignKey(InstrumentDownloadScheme, related_name='inputs', verbose_name=ugettext_lazy('scheme'))
    name = models.CharField(max_length=32, blank=True, default='', verbose_name=ugettext_lazy('name'))
    field = models.CharField(max_length=32, blank=True, default='', verbose_name=ugettext_lazy('field'))
    name_expr = models.CharField(max_length=1000, blank=True, default='', verbose_name=ugettext_lazy('name expression'))

    class Meta:
        verbose_name = ugettext_lazy('instrument download scheme input')
        verbose_name_plural = ugettext_lazy('instrument download scheme inputs')
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
                               verbose_name=ugettext_lazy('scheme'))
    attribute_type = models.ForeignKey('obj_attrs.GenericAttributeType', null=True, blank=True,
                                       verbose_name=ugettext_lazy('attribute_ type'))
    value = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                             verbose_name=ugettext_lazy('value'))

    class Meta:
        verbose_name = ugettext_lazy('instrument download scheme attribute')
        verbose_name_plural = ugettext_lazy('instrument download schemes attribute')
        unique_together = (
            ('scheme', 'attribute_type')
        )
        ordering = ['attribute_type']

    def __str__(self):
        # return '%s -> %s' % (self.name, self.attribute_type)
        return '%s' % (self.attribute_type,)


class PriceDownloadScheme(models.Model):
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'))
    scheme_name = models.CharField(max_length=255, verbose_name=ugettext_lazy('scheme name'))
    provider = models.ForeignKey(ProviderClass, verbose_name=ugettext_lazy('provider'))

    bid0 = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('bid0'))
    bid1 = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('bid1'))
    bid2 = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('bid2'))
    bid_multiplier = models.FloatField(default=1.0, verbose_name=ugettext_lazy('bid multiplier'))
    ask0 = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('ask0'))
    ask1 = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('ask1'))
    ask2 = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('ask2'))
    ask_multiplier = models.FloatField(default=1.0, verbose_name=ugettext_lazy('ask multiplier'))
    last = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('last'))
    last_multiplier = models.FloatField(default=1.0, verbose_name=ugettext_lazy('last multiplier'))
    mid = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('mid'))
    mid_multiplier = models.FloatField(default=1.0, verbose_name=ugettext_lazy('mid multiplier'))

    bid_history = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('bid history'))
    bid_history_multiplier = models.FloatField(default=1.0, verbose_name=ugettext_lazy('bid history multiplier'))
    ask_history = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('ask history'))
    ask_history_multiplier = models.FloatField(default=1.0, verbose_name=ugettext_lazy('ask history multiplier'))
    mid_history = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('mid history'))
    mid_history_multiplier = models.FloatField(default=1.0, verbose_name=ugettext_lazy('mid history multiplier'))
    last_history = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('last history'))
    last_history_multiplier = models.FloatField(default=1.0, verbose_name=ugettext_lazy('last history multiplier'))

    currency_fxrate = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('currency FX-rate'))
    currency_fxrate_multiplier = models.FloatField(default=1.0,
                                                   verbose_name=ugettext_lazy('currency FX-rate multiplier'))

    class Meta:
        verbose_name = ugettext_lazy('price download scheme')
        verbose_name_plural = ugettext_lazy('price download schemes')
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
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'))
    provider = models.ForeignKey(ProviderClass, verbose_name=ugettext_lazy('provider'))
    value = models.CharField(max_length=255, blank=True, default='', verbose_name=ugettext_lazy('value'))

    class Meta:
        abstract = True
        ordering = ['value']

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class CurrencyMapping(AbstractMapping):
    content_object = models.ForeignKey('currencies.Currency', verbose_name=ugettext_lazy('currency'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('currency mapping')
        verbose_name_plural = ugettext_lazy('currency mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class PricingPolicyMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.PricingPolicy', verbose_name=ugettext_lazy('pricing policy'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('pricing policy mapping')
        verbose_name_plural = ugettext_lazy('pricing policy mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class InstrumentTypeMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.InstrumentType', verbose_name=ugettext_lazy('instrument type'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('instrument type mapping')
        verbose_name_plural = ugettext_lazy('instrument type mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class AccountTypeMapping(AbstractMapping):
    content_object = models.ForeignKey('accounts.AccountType', verbose_name=ugettext_lazy('account type'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('account type mapping')
        verbose_name_plural = ugettext_lazy('account type mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class InstrumentAttributeValueMapping(AbstractMapping):
    content_object = models.ForeignKey('obj_attrs.GenericAttributeType', on_delete=models.PROTECT,
                                       verbose_name=ugettext_lazy('attribute type'))
    value_string = models.CharField(max_length=255, default='', blank=True,
                                    verbose_name=ugettext_lazy('value (String)'))
    value_float = models.FloatField(default=0.0, verbose_name=ugettext_lazy('value (Float)'))
    value_date = models.DateField(default=date.min, verbose_name=ugettext_lazy('value (Date)'))
    classifier = models.ForeignKey('obj_attrs.GenericClassifier', on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name=ugettext_lazy('classifier'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('instrument attribute value mapping')
        verbose_name_plural = ugettext_lazy('instrument attribute value mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        value = self.content_object.get_value(self)
        return '%s / %s -> %s / %s' % (self.provider, self.value, self.content_object, value)


class AccrualCalculationModelMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.AccrualCalculationModel',
                                       verbose_name=ugettext_lazy('accrual calculation model'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('accrual calculation model mapping')
        verbose_name_plural = ugettext_lazy('accrual calculation model  mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class PeriodicityMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.Periodicity', verbose_name=ugettext_lazy('periodicity'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('periodicity mapping')
        verbose_name_plural = ugettext_lazy('periodicity  mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
            # ['master_user', 'provider', 'periodicity'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class AccountMapping(AbstractMapping):
    content_object = models.ForeignKey('accounts.Account', verbose_name=ugettext_lazy('account'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('account mapping')
        verbose_name_plural = ugettext_lazy('account mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class AccountClassifierMapping(AbstractMapping):
    attribute_type = models.ForeignKey(GenericAttributeType)
    content_object = models.ForeignKey(GenericClassifier)

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('account classifier mapping')
        verbose_name_plural = ugettext_lazy('account classifier mappings')
        unique_together = [
            ['master_user', 'provider', 'value', 'attribute_type'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class InstrumentMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.Instrument', verbose_name=ugettext_lazy('instrument'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('instrument mapping')
        verbose_name_plural = ugettext_lazy('instrument mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class InstrumentClassifierMapping(AbstractMapping):
    attribute_type = models.ForeignKey(GenericAttributeType)
    content_object = models.ForeignKey(GenericClassifier)

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('instrument classifier mapping')
        verbose_name_plural = ugettext_lazy('instrument classifier mappings')
        unique_together = [
            ['master_user', 'provider', 'value', 'attribute_type'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class CounterpartyMapping(AbstractMapping):
    content_object = models.ForeignKey('counterparties.Counterparty', verbose_name=ugettext_lazy('counterparty'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('counterparty mapping')
        verbose_name_plural = ugettext_lazy('counterparty mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class CounterpartyClassifierMapping(AbstractMapping):
    attribute_type = models.ForeignKey(GenericAttributeType)
    content_object = models.ForeignKey(GenericClassifier)

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('responsible classifier mapping')
        verbose_name_plural = ugettext_lazy('responsible classifier mappings')
        unique_together = [
            ['master_user', 'provider', 'value', 'attribute_type'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class ResponsibleMapping(AbstractMapping):
    content_object = models.ForeignKey('counterparties.Responsible', verbose_name=ugettext_lazy('responsible'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('responsible mapping')
        verbose_name_plural = ugettext_lazy('responsible mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class ResponsibleClassifierMapping(AbstractMapping):
    attribute_type = models.ForeignKey(GenericAttributeType)
    content_object = models.ForeignKey(GenericClassifier)

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('responsible classifier mapping')
        verbose_name_plural = ugettext_lazy('responsible classifier mappings')
        unique_together = [
            ['master_user', 'provider', 'value', 'attribute_type'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class PortfolioMapping(AbstractMapping):
    content_object = models.ForeignKey('portfolios.Portfolio', verbose_name=ugettext_lazy('portfolio'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('portfolio mapping')
        verbose_name_plural = ugettext_lazy('portfolio mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class PortfolioClassifierMapping(AbstractMapping):
    attribute_type = models.ForeignKey(GenericAttributeType)
    content_object = models.ForeignKey(GenericClassifier)

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('portfolio classifier mapping')
        verbose_name_plural = ugettext_lazy('portfolio classifier mappings')
        unique_together = [
            ['master_user', 'provider', 'value', 'attribute_type'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class Strategy1Mapping(AbstractMapping):
    content_object = models.ForeignKey('strategies.Strategy1', verbose_name=ugettext_lazy('strategy1'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('strategy1 mapping')
        verbose_name_plural = ugettext_lazy('strategy1 mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class Strategy2Mapping(AbstractMapping):
    content_object = models.ForeignKey('strategies.Strategy2', verbose_name=ugettext_lazy('strategy2'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('strategy2 mapping')
        verbose_name_plural = ugettext_lazy('strategy2 mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class Strategy3Mapping(AbstractMapping):
    content_object = models.ForeignKey('strategies.Strategy3', verbose_name=ugettext_lazy('strategy3'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('strategy3 mapping')
        verbose_name_plural = ugettext_lazy('strategy3 mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class DailyPricingModelMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.DailyPricingModel',
                                       verbose_name=ugettext_lazy('daily pricing model'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('daily pricing model mapping')
        verbose_name_plural = ugettext_lazy('daily pricing model mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class PaymentSizeDetailMapping(AbstractMapping):
    content_object = models.ForeignKey('instruments.PaymentSizeDetail',
                                       verbose_name=ugettext_lazy('payment size detail'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('payment size detail mapping')
        verbose_name_plural = ugettext_lazy('payment size detail model mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


class PriceDownloadSchemeMapping(AbstractMapping):
    content_object = models.ForeignKey('integrations.PriceDownloadScheme',
                                       verbose_name=ugettext_lazy('price download scheme'))

    class Meta(AbstractMapping.Meta):
        verbose_name = ugettext_lazy('price download scheme mapping')
        verbose_name_plural = ugettext_lazy('price download scheme mappings')
        unique_together = [
            ['master_user', 'provider', 'value'],
        ]

    def __str__(self):
        return '%s / %s -> %s' % (self.provider, self.value, self.content_object)


# -------


class Task(TimeStampedModel):
    ACTION_INSTRUMENT = 'instrument'
    ACTION_PRICING = 'pricing'

    STATUS_PENDING = 'P'
    STATUS_REQUEST_SENT = 'S'
    STATUS_WAIT_RESPONSE = 'W'
    STATUS_DONE = 'D'
    STATUS_ERROR = 'E'
    STATUS_TIMEOUT = 'T'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'PENDING'),
        (STATUS_REQUEST_SENT, 'REQUEST_SENT'),
        (STATUS_WAIT_RESPONSE, 'WAIT_RESPONSE'),
        (STATUS_DONE, 'DONE'),
        (STATUS_ERROR, 'ERROR'),
        (STATUS_TIMEOUT, 'TIMEOUT'),
    )

    master_user = models.ForeignKey('users.MasterUser', related_name='tasks', verbose_name=ugettext_lazy('master user'))
    member = models.ForeignKey('users.Member', related_name='tasks', null=True, blank=True,
                               verbose_name=ugettext_lazy('member'))

    provider = models.ForeignKey(ProviderClass, null=True, blank=True, db_index=True,
                                 verbose_name=ugettext_lazy('provider'))
    action = models.CharField(max_length=20, db_index=True, verbose_name=ugettext_lazy('action'))
    status = models.CharField(max_length=1, default=STATUS_PENDING, choices=STATUS_CHOICES,
                              verbose_name=ugettext_lazy('status'))

    celery_tasks_id = models.CharField(max_length=255, blank=True, default='',
                                       verbose_name=ugettext_lazy('celery tasks id'))
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children',
                               verbose_name=ugettext_lazy('parent'))

    options = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('options'))
    result = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('result'))
    request_id = models.CharField(max_length=50, null=True, db_index=True, verbose_name=ugettext_lazy('request id'))
    response_id = models.CharField(max_length=50, null=True, db_index=True, verbose_name=ugettext_lazy('response id'))

    class Meta:
        verbose_name = ugettext_lazy('task')
        verbose_name_plural = ugettext_lazy('tasks')
        index_together = (
            ('master_user', 'created')
        )
        ordering = ('-created',)

    def __str__(self):
        return '%s' % (self.id,)

    @property
    def info(self):
        return '%s/%s' % (self.id, self.get_status_display())

    @property
    def is_running(self):
        return self.status in [self.STATUS_PENDING, self.STATUS_REQUEST_SENT, self.STATUS_WAIT_RESPONSE]

    @property
    def is_finished(self):
        return self.status in [self.STATUS_DONE, self.STATUS_ERROR, self.STATUS_TIMEOUT]

    def add_celery_task_id(self, celery_task_id):
        if not celery_task_id:
            return
        if self.celery_tasks_id is None:
            self.celery_tasks_id = ''
        if celery_task_id in self.celery_tasks_id:
            return
        if self.celery_tasks_id:
            self.celery_tasks_id = '%s %s' % (self.celery_tasks_id, celery_task_id)
        else:
            self.celery_tasks_id = celery_task_id

    @property
    def options_object(self):
        if self.options is None:
            return None
        return json.loads(self.options)

    @options_object.setter
    def options_object(self, value):
        if value is None:
            self.options = None
        else:
            self.options = json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, indent=1)

    @property
    def result_object(self):
        if self.result is None:
            return None
        return json.loads(self.result)

    @result_object.setter
    def result_object(self, value):
        if value is None:
            self.result = None
        else:
            self.result = json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, indent=1)


# def to_crontab(value):
#     from celery.schedules import crontab
#
#     if value:
#         elmts = value.split()
#         if len(elmts) != 5:
#             raise ValueError('Invalid crontab expression')
#
#         minute = elmts[0]
#         hour = elmts[1]
#         day_of_week = elmts[2]
#         day_of_month = elmts[3]
#         month_of_year = elmts[4]
#         try:
#             return crontab(
#                 minute=minute,
#                 hour=hour,
#                 day_of_week=day_of_week,
#                 day_of_month=day_of_month,
#                 month_of_year=month_of_year
#             )
#         except (TypeError, ValueError):
#             raise ValueError('Invalid crontab expression')


def validate_crontab(value):
    try:
        # to_crontab(value)
        croniter(value, timezone.now())
    except (ValueError, KeyError, TypeError):
        raise ValidationError(ugettext_lazy('A valid cron string is required.'))


class PricingAutomatedSchedule(models.Model):
    master_user = models.OneToOneField('users.MasterUser', related_name='pricing_automated_schedule',
                                       verbose_name=ugettext_lazy('master user'))

    is_enabled = models.BooleanField(default=True, verbose_name=ugettext_lazy('is enabled'))
    cron_expr = models.CharField(max_length=255, blank=True, default='', validators=[validate_crontab],
                                 verbose_name=ugettext_lazy('cron expr'),
                                 help_text=ugettext_lazy(
                                     'Format is "* * * * *" (minute / hour / day_month / month / day_week)'))
    balance_day = models.PositiveSmallIntegerField(default=0, verbose_name=ugettext_lazy('balance day'))
    load_days = models.PositiveSmallIntegerField(default=1, verbose_name=ugettext_lazy('load days'))
    fill_days = models.PositiveSmallIntegerField(default=0, verbose_name=ugettext_lazy('tagfill dayss'))
    override_existed = models.BooleanField(default=True, verbose_name=ugettext_lazy('override existed'))

    # latest_running = models.DateTimeField(null=True, blank=True, editable=False)
    # latest_task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL, editable=False)

    last_run_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True,
                                       verbose_name=ugettext_lazy('last run at'))
    next_run_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True,
                                       verbose_name=ugettext_lazy('next run at'))
    last_run_task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL, editable=False,
                                      db_index=True, verbose_name=ugettext_lazy('last run task'))

    class Meta:
        verbose_name = ugettext_lazy('pricing automated schedule')
        verbose_name_plural = ugettext_lazy('pricing automated schedules')
        index_together = (
            ('is_enabled', 'next_run_at'),
        )
        ordering = ['is_enabled']

    def __str__(self):
        return ugettext('pricing automated schedule')

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.is_enabled:
            self.schedule(save=False)
        super(PricingAutomatedSchedule, self).save(force_insert=force_insert, force_update=force_update, using=using,
                                                   update_fields=update_fields)

    # def to_crontab(self):
    #     if self.is_enabled and self.cron_expr:
    #         return to_crontab(self.cron_expr)
    #     return None

    def can_schedule(self):
        return self.latest_task is None or self.latest_task.is_finished

    def schedule(self, save=False):
        start_time = timezone.localtime(timezone.now())
        cron = croniter(self.cron_expr, start_time)

        next_run_at = cron.get_next(datetime)

        min_timedelta = settings.PRICING_AUTO_DOWNLOAD_MIN_TIMEDELTA
        if min_timedelta is not None:
            if not isinstance(min_timedelta, timedelta):
                min_timedelta = timedelta(minutes=min_timedelta)
            for i in range(100):
                if (next_run_at - start_time) >= min_timedelta:
                    break
                next_run_at = cron.get_next(datetime)

        self.next_run_at = next_run_at

        if save:
            self.save(update_fields=['last_run_at', 'next_run_at', ])


# ----------------------------------------


class ComplexTransactionImportScheme(models.Model):
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'))
    scheme_name = models.CharField(max_length=255, verbose_name=ugettext_lazy('scheme name'))
    rule_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=ugettext_lazy('rule expressions'))

    class Meta:
        verbose_name = ugettext_lazy('complex transaction import scheme')
        verbose_name_plural = ugettext_lazy('complex transaction import schemes')

    def __str__(self):
        return self.scheme_name


class ComplexTransactionImportSchemeInput(models.Model):
    scheme = models.ForeignKey(ComplexTransactionImportScheme, related_name='inputs',
                               verbose_name=ugettext_lazy('scheme'))
    # order = models.SmallIntegerField(default=0)
    name = models.CharField(max_length=255)
    column = models.SmallIntegerField()

    name_expr = models.CharField(max_length=1000, default='', verbose_name=ugettext_lazy('name expression'))

    class Meta:
        verbose_name = ugettext_lazy('complex transaction import scheme input')
        verbose_name_plural = ugettext_lazy('complex transaction import scheme inputs')
        # ordering = ['order']
        order_with_respect_to = 'scheme'

    def __str__(self):
        return self.name


class ComplexTransactionImportSchemeRule(models.Model):
    scheme = models.ForeignKey(ComplexTransactionImportScheme, related_name='rules',
                               verbose_name=ugettext_lazy('scheme'))
    # order = models.SmallIntegerField(default=0)
    value = models.CharField(max_length=255, blank=True, default='', verbose_name=ugettext_lazy('mapping value'))
    transaction_type = models.ForeignKey('transactions.TransactionType', on_delete=models.CASCADE,
                                         verbose_name=ugettext_lazy('transaction type'))

    class Meta:
        verbose_name = ugettext_lazy('complex transaction import scheme rule')
        verbose_name_plural = ugettext_lazy('complex transaction import scheme rules')
        # ordering = ['order']
        order_with_respect_to = 'scheme'

    def __str__(self):
        return self.value


class ComplexTransactionImportSchemeField(models.Model):
    # for simpler admin
    # scheme = models.ForeignKey(ComplexTransactionImportScheme, verbose_name=ugettext_lazy('scheme'))
    rule = models.ForeignKey(ComplexTransactionImportSchemeRule, related_name='fields',
                             verbose_name=ugettext_lazy('rule'))
    # order = models.SmallIntegerField(default=0)
    # name = models.CharField(max_length=255, verbose_name=ugettext_lazy('name'))
    transaction_type_input = models.ForeignKey('transactions.TransactionTypeInput', on_delete=models.CASCADE,
                                               verbose_name=ugettext_lazy('transaction type input'))
    value_expr = models.CharField(max_length=1000, verbose_name=ugettext_lazy('value expression'))

    class Meta:
        verbose_name = ugettext_lazy('complex transaction import scheme field')
        verbose_name_plural = ugettext_lazy('complex transaction import scheme fields')
        # ordering = ['order']
        order_with_respect_to = 'rule'

    def __str__(self):
        return '%s - %s' % (self.rule, self.transaction_type_input,)
