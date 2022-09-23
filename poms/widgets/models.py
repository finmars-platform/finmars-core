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


# "nav": stats_handler.get_balance_nav(),  # done
# "total": stats_handler.get_pl_total(),  # done
# "cumulative_return": stats_handler.get_cumulative_return(),  # done
# "annualized_return": stats_handler.get_annualized_return(),  # done
# "portfolio_volatility": stats_handler.get_portfolio_volatility(), # done
# "annualized_portfolio_volatility": stats_handler.get_annualized_portfolio_volatility(), # done
# "sharpe_ratio": stats_handler.get_sharpe_ratio(), # done
# "max_annualized_drawdown": stats_handler.get_max_annualized_drawdown(),
# "betta": stats_handler.get_betta(),
# "alpha": stats_handler.get_alpha(),
# "correlation": stats_handler.get_correlation()

class WidgetStats(models.Model):

    master_user = models.ForeignKey(MasterUser,
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    date = models.DateField(db_index=True, default=date_now, verbose_name=gettext_lazy('date'))

    portfolio = models.ForeignKey('portfolios.Portfolio', blank=True, on_delete=models.CASCADE,
                                  verbose_name=gettext_lazy('portfolio'))
    benchmark = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('benchmark'))

    nav = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('nav'))
    total = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('total'))
    cumulative_return = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('cumulative return'))
    annualized_return = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('annualized return'))
    portfolio_volatility = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('portfolio volatility'))
    annualized_portfolio_volatility = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('annualized portfolio volatility'))
    sharpe_ratio = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('sharpe_ratio'))
    max_annualized_drawdown = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('max_annualized_drawdown'))
    betta = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('betta'))
    alpha = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('alpha'))
    correlation = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('correlation'))