from __future__ import unicode_literals

import csv
import os

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import SimpleLazyObject
from django.utils.translation import gettext_lazy

from poms.common.models import NamedModel, FakeDeletableModel, DataTimeStampedModel
from poms.common.utils import date_now
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.obj_attrs.models import GenericAttribute
from poms.users.models import MasterUser

# Probably Deprecated
def _load_currencies_data():
    ccy_path = os.path.join(settings.BASE_DIR, 'data', 'currencies.csv')
    ret = {}
    with open(ccy_path) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            ret[row['user_code']] = row
    return ret


currencies_data = SimpleLazyObject(_load_currencies_data)


class Currency(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):
    '''
    Entity for Currency itself, e.g. USD, EUR, CHF
    Used in Transactions, in Reports, in Pricing,
    Very core Entity and very important
    '''
    master_user = models.ForeignKey(MasterUser, related_name='currencies', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    reference_for_pricing = models.CharField(max_length=100, blank=True, default='',
                                             verbose_name=gettext_lazy('reference for pricing'))

    # daily_pricing_model = models.ForeignKey('instruments.DailyPricingModel', null=True, blank=True,
    #                                         verbose_name=gettext_lazy('daily pricing model'), on_delete=models.CASCADE)
    # price_download_scheme = models.ForeignKey('integrations.PriceDownloadScheme', on_delete=models.PROTECT, null=True,
    #                                           blank=True, verbose_name=gettext_lazy('price download scheme'))

    pricing_condition = models.ForeignKey('instruments.PricingCondition', null=True, blank=True,
                                          verbose_name=gettext_lazy('pricing condition'), on_delete=models.CASCADE)

    attributes = GenericRelation(GenericAttribute, verbose_name=gettext_lazy('attributes'))

    default_fx_rate = models.FloatField(default=1, verbose_name=gettext_lazy('default fx rate'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('currency')
        verbose_name_plural = gettext_lazy('currencies')
        permissions = [
            # ('view_currency', 'Can view currency'),
            ('manage_currency', 'Can manage currency'),
        ]

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10
            },
            {
                "key": "reference_for_pricing",
                "name": "Reference for pricing",
                "value_type": 10
            },
            {
                "key": "default_fx_rate",
                "name": "Default FX rate",
                "value_type": 20
            },
            {
                "key": "pricing_condition",
                "name": "Pricing Condition",
                "value_content_type": "instruments.pricingcondition",
                "value_entity": "pricing-condition",
                "code": "user_code",
                "value_type": "field"
            }
        ]


class CurrencyHistory(DataTimeStampedModel):
    '''
    FX rate of Currencies for specific date
    Finmars is not bound to USD as base currency (Base Currency could be set in poms.users.EcosystemDefault)

    Example of currency history (ecosystem_default.currency = USD)
    EUR 2023-01-01 1.07

    '''
    currency = models.ForeignKey(Currency, related_name='histories', verbose_name=gettext_lazy('currency'),
                                 on_delete=models.CASCADE)
    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE, null=True, blank=True,
                                       verbose_name=gettext_lazy('pricing policy'))
    date = models.DateField(db_index=True, default=date_now, verbose_name=gettext_lazy('date'))
    fx_rate = models.FloatField(default=1, verbose_name=gettext_lazy('fx rate'))

    procedure_modified_datetime = models.DateTimeField(null=True, blank=True,
                                                       verbose_name=gettext_lazy('procedure_modified_datetime'))

    class Meta:
        verbose_name = gettext_lazy('currency history')
        verbose_name_plural = gettext_lazy('currency histories')
        unique_together = (
            ('currency', 'pricing_policy', 'date',)
        )
        index_together = [
            ['currency', 'pricing_policy', 'date']
        ]
        ordering = ['date']

    def save(self, *args, **kwargs):

        cache.clear()

        if self.fx_rate == 0:
            raise ValidationError('FX rate must not be zero')

        if not self.procedure_modified_datetime:
            self.procedure_modified_datetime = date_now()

        if not self.created:
            self.created = date_now()

        super(CurrencyHistory, self).save(*args, **kwargs)

    def __str__(self):
        # return '%s:%s:%s:%s' % (self.currency_id, self.pricing_policy_id, self.date, self.fx_rate)
        return '%s @%s' % (self.fx_rate, self.date)
