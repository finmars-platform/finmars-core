from __future__ import unicode_literals

import csv
import os

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.functional import SimpleLazyObject
from django.utils.translation import ugettext_lazy

from poms.common.models import NamedModel, FakeDeletableModel
from poms.common.utils import date_now
from poms.obj_attrs.models import GenericAttribute
from poms.tags.models import TagLink
from poms.users.models import MasterUser


def _load_currencies_data():
    ccy_path = os.path.join(settings.BASE_DIR, 'data', 'currencies.csv')
    ret = {}
    with open(ccy_path) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            ret[row['user_code']] = row
    return ret


currencies_data = SimpleLazyObject(_load_currencies_data)


class Currency(NamedModel, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='currencies', verbose_name=ugettext_lazy('master user'))
    reference_for_pricing = models.CharField(max_length=100, blank=True, default='',
                                             verbose_name=ugettext_lazy('reference for pricing'))
    daily_pricing_model = models.ForeignKey('instruments.DailyPricingModel', null=True, blank=True,
                                            verbose_name=ugettext_lazy('daily pricing model'))
    price_download_scheme = models.ForeignKey('integrations.PriceDownloadScheme', on_delete=models.PROTECT, null=True,
                                              blank=True, verbose_name=ugettext_lazy('price download scheme'))

    attributes = GenericRelation(GenericAttribute, verbose_name=ugettext_lazy('attributes'))
    tags = GenericRelation(TagLink, verbose_name=ugettext_lazy('tags'))

    default_fx_rate = models.FloatField(default=1, verbose_name=ugettext_lazy('default fx rate'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('currency')
        verbose_name_plural = ugettext_lazy('currencies')
        permissions = [
            ('view_currency', 'Can view currency'),
            ('manage_currency', 'Can manage currency'),
        ]

    @property
    def is_system(self):
        return self.master_user.system_currency_id == self.id if self.master_user_id else False

    @property
    def is_default(self):
        return self.master_user.currency_id == self.id if self.master_user_id else False


# class CurrencyUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(Currency, related_name='user_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('currencies - user permission')
#         verbose_name_plural = ugettext_lazy('currencies - user permissions')
#
#
# class CurrencyGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(Currency, related_name='group_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('currencies - group permission')
#         verbose_name_plural = ugettext_lazy('currencies - group permissions')


# EUR -> USD
# RUB -> USD
# ...
class CurrencyHistory(models.Model):
    currency = models.ForeignKey(Currency, related_name='histories', verbose_name=ugettext_lazy('currency'))
    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.PROTECT, null=True, blank=True,
                                       verbose_name=ugettext_lazy('pricing policy'))
    date = models.DateField(db_index=True, default=date_now, verbose_name=ugettext_lazy('date'))
    fx_rate = models.FloatField(default=0., verbose_name=ugettext_lazy('fx rate'))

    class Meta:
        verbose_name = ugettext_lazy('currency history')
        verbose_name_plural = ugettext_lazy('currency histories')
        unique_together = (
            ('currency', 'pricing_policy', 'date',)
        )
        ordering = ['date']

    def __str__(self):
        # return '%s:%s:%s:%s' % (self.currency_id, self.pricing_policy_id, self.date, self.fx_rate)
        from datetime import date
        return '%s @%s' % (self.fx_rate, self.date)
