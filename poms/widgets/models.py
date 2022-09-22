from django.utils.translation import gettext_lazy
from django.db import models

from poms.common.models import DataTimeStampedModel
from poms.common.utils import date_now
from poms.currencies.models import Currency
from poms.instruments.models import PricingPolicy, CostMethod
from poms.users.models import MasterUser


class BalanceReportHistory(DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser, related_name='balance_report_histories',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    date = models.DateField(db_index=True, default=date_now, verbose_name=gettext_lazy('date'))

    report_currency = models.ForeignKey(Currency, null=True, blank=True,
                                        on_delete=models.PROTECT, verbose_name=gettext_lazy('report currency'))

    pricing_policy = models.ForeignKey(PricingPolicy, on_delete=models.CASCADE,
                                       verbose_name=gettext_lazy('pricing policy'))

    cost_method = models.ForeignKey(CostMethod, on_delete=models.CASCADE, null=True, blank=True,
                                    verbose_name=gettext_lazy('cost method'))

    portfolio = models.ForeignKey('portfolios.Portfolio', blank=True, on_delete=models.CASCADE,
                                   verbose_name=gettext_lazy('portfolio'))

    report_settings_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('report settings data'))

    nav = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('nav'))


class BalanceReportHistoryItem(models.Model):
    balance_report_history = models.ForeignKey(BalanceReportHistory, related_name='items',
                                               verbose_name=gettext_lazy('balance report history'),
                                               on_delete=models.CASCADE)

    category = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('category'))
    name = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('name'))
    key = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('key'))
    value = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('value'))


class PLReportHistory(DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser,
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    date = models.DateField(db_index=True, default=date_now, verbose_name=gettext_lazy('date'))

    pl_first_date = models.DateField(db_index=True, default=date_now, verbose_name=gettext_lazy('pl first date'))

    report_currency = models.ForeignKey(Currency, null=True, blank=True,
                                        on_delete=models.PROTECT, verbose_name=gettext_lazy('report currency'))

    pricing_policy = models.ForeignKey(PricingPolicy, on_delete=models.CASCADE,
                                       verbose_name=gettext_lazy('pricing policy'))

    cost_method = models.ForeignKey(CostMethod, on_delete=models.CASCADE, null=True, blank=True,
                                    verbose_name=gettext_lazy('cost method'))

    portfolio = models.ForeignKey('portfolios.Portfolio', blank=True, on_delete=models.CASCADE,
                                  verbose_name=gettext_lazy('portfolio'))

    report_settings_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('report settings data'))

    total = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('total'))


class PLReportHistoryItem(models.Model):
    pl_report_history = models.ForeignKey(PLReportHistory, related_name='items',
                                          verbose_name=gettext_lazy('pl report history'), on_delete=models.CASCADE)

    category = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('category'))
    name = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('name'))
    key = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('key'))
    value = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('value'))
