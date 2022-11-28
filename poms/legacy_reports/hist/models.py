from __future__ import unicode_literals

from django.db import models
from django.utils.translation import gettext_lazy

from poms.users.models import MasterUser


# class ReportClass(AbstractClassModel):
#     # TODO: add "values"
#     BALANCE = 1
#     P_L = 2
#     COST = 3
#     YTM = 4
#     CLASSES = (
#         (BALANCE, 'BALANCE', gettext_lazy('BALANCE')),
#         (P_L, 'P_L', gettext_lazy('P&L')),
#         (COST, 'COST', gettext_lazy('COST')),
#         (YTM, 'YTM', gettext_lazy('YTM')),
#     )
#
#     class Meta(AbstractClassModel.Meta):
#         verbose_name = gettext_lazy('report class')
#         verbose_name_plural = gettext_lazy('report classes')


class CustomField(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='custom_fields')
    # report_class = models.ForeignKey(ReportClass, null=True, blank=True)
    name = models.CharField(max_length=255)
    expr = models.CharField(max_length=255)

    class Meta:
        verbose_name = gettext_lazy('custom field')
        verbose_name_plural = gettext_lazy('custom fields')
        unique_together = [
            ['master_user', 'name']
        ]

    def __str__(self):
        return self.name


class BalanceReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='balance_reports')

    class Meta:
        verbose_name = gettext_lazy('balance report')
        verbose_name_plural = gettext_lazy('balance reports')


class PLReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='pl_reports')

    class Meta:
        verbose_name = gettext_lazy('p&l report')
        verbose_name_plural = gettext_lazy('p&l report')


class PerformanceReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='performance_reports')

    class Meta:
        verbose_name = gettext_lazy('performance report')
        verbose_name_plural = gettext_lazy('performance reports')


class CashFlowReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='cashflow_reports')

    class Meta:
        verbose_name = gettext_lazy('cash flow report')
        verbose_name_plural = gettext_lazy('cash flow reports')


class TransactionReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='transaction_reports')

    class Meta:
        verbose_name = gettext_lazy('transaction report')
        verbose_name_plural = gettext_lazy('transaction reports')

# # ----------------------------------------------------------------------------------------------------------------------
#
#
# class VirtualTransaction(object):
#     def __init__(self, transaction, pk, override_values):
#         self.transaction = transaction
#         self.pk = pk
#         self.override_values = override_values or {}
#
#     def __getattr__(self, item):
#         if item == 'pk' or item == 'id':
#             return self.pk
#         if item in self.override_values:
#             return self.override_values[item]
#         return getattr(self.transaction, item)
#
#
# class BaseReportItem(object):
#     def __init__(self, pk=None, portfolio=None, account=None, strategy1=None, strategy2=None, strategy3=None,
#                  instrument=None, currency=None, position=0.0, transaction=None, custom_fields=None):
#         self.pk = pk
#         self.portfolio = portfolio  # -> Portfolio if use_portfolio
#         self.account = account  # -> Account if use_account
#         self.strategy1 = strategy1  # -> Strategy1 if use_strategy1
#         self.strategy2 = strategy2  # -> Strategy2 if use_strategy2
#         self.strategy3 = strategy3  # -> Strategy3 if use_strategy3
#         self.instrument = instrument  # -> Instrument
#         self.currency = currency  # -> Currency
#         self.transaction = transaction  # -> Transaction if show_transaction_details
#
#         self.position = position
#
#         self.custom_fields = custom_fields or {}
#
#     def __str__(self):
#         return "%s #%s" % (self.__class__.__name__, self.pk,)
#
#
# class BaseReportSummary(object):
#     def __init__(self):
#         pass
#
#     def __str__(self):
#         return "summary"
#
#
# class BaseReport(object):
#     def __init__(self, id=None, master_user=None, task_id=None, task_status=None,
#                  report_date=None, report_currency=None, pricing_policy=None, cost_method=None,
#                  detail_by_portfolio=False, detail_by_account=False, detail_by_strategy1=False,
#                  detail_by_strategy2=False, detail_by_strategy3=False,
#                  show_transaction_details=False,
#                  portfolios=None, accounts=None, strategies1=None, strategies2=None, strategies3=None,
#                  custom_fields=None, items=None, summary=None, transactions=None):
#         self.id = id
#         self.task_id = task_id
#         self.task_status = task_status
#
#         self.master_user = master_user
#         self.report_date = report_date
#         self.report_currency = report_currency
#         self.pricing_policy = pricing_policy
#         self.cost_method = cost_method
#
#         self.detail_by_portfolio = detail_by_portfolio
#         self.detail_by_account = detail_by_account
#         self.detail_by_strategy1 = detail_by_strategy1
#         self.detail_by_strategy2 = detail_by_strategy2
#         self.detail_by_strategy3 = detail_by_strategy3
#         self.show_transaction_details = show_transaction_details
#
#         self.portfolios = portfolios or []
#         self.accounts = accounts or []
#         self.strategies1 = strategies1 or []
#         self.strategies2 = strategies2 or []
#         self.strategies3 = strategies3 or []
#
#         self.custom_fields = custom_fields or []
#
#         self.items = items or []
#         self.summary = summary or BaseReportSummary()
#         self.transactions = transactions or []
#
#     def __str__(self):
#         return "%s for %s @ %s" % (self.__class__.__name__, self.master_user, self.report_date)
#
#
# # ----------------------------------------------------------------------------------------------------------------------
#
#
# class BalanceReportItem(BaseReportItem):
#     def __init__(self, position=0.0, market_value_system_ccy=0.0, market_value_report_ccy=0.0, transaction=None, *args,
#                  **kwargs):
#         super(BalanceReportItem, self).__init__(*args, **kwargs)
#
#         self.position = position
#
#         # self.currency_history = None  # -> CurrencyHistory
#         # self.currency_name = None
#         # self.currency_fx_rate = 0.
#
#         # self.price_history = None  # -> PriceHistory
#         # self.instrument_principal_currency_history = None  # -> CurrencyHistory
#         # self.instrument_accrued_currency_history = None  # -> CurrencyHistory
#
#         # self.instrument_name = None
#         # self.instrument_principal_pricing_ccy = 0.
#         # self.instrument_price_multiplier = 0.
#         # self.instrument_accrued_pricing_ccy = 0.
#         # self.instrument_accrued_multiplier = 0.
#         # self.instrument_principal_price = 0.
#         # self.instrument_accrued_price = 0.
#         # self.principal_value_instrument_principal_ccy = None
#         # self.accrued_value_instrument_accrued_ccy = None
#         # self.instrument_principal_fx_rate = 0.
#         # self.instrument_accrued_fx_rate = 0.
#
#         self.principal_value_system_ccy = 0.0
#         self.accrued_value_system_ccy = 0.0
#         self.market_value_system_ccy = market_value_system_ccy
#
#         self.principal_value_report_ccy = 0.0
#         self.accrued_value_report_ccy = 0.0
#         self.market_value_report_ccy = market_value_report_ccy
#
#         self.transaction = transaction  # -> Transaction for case 1 and case 2
#
#     def __str__(self):
#         if self.instrument:
#             return "%s - %s" % (self.instrument, self.position)
#         else:
#             return "%s - %s" % (self.currency, self.position)
#
#
# class BalanceReportSummary(object):
#     def __init__(self,
#                  invested_value_system_ccy=0.0, current_value_system_ccy=0.0, p_l_system_ccy=0.0,
#                  invested_value_report_ccy=0.0, current_value_report_ccy=0.0, p_l_report_ccy=0.0):
#         self.invested_value_system_ccy = invested_value_system_ccy
#         self.current_value_system_ccy = current_value_system_ccy
#         self.p_l_system_ccy = p_l_system_ccy
#
#         self.invested_value_report_ccy = invested_value_report_ccy
#         self.current_value_report_ccy = current_value_report_ccy
#         self.p_l_report_ccy = p_l_report_ccy
#
#     def __str__(self):
#         return "invested_value_system_ccy=%s, current_value_system_ccy=%s, p_l_system_ccy=%s" % \
#                (self.invested_value_system_ccy, self.current_value_system_ccy, self.p_l_system_ccy)
#
#
# class BalanceReport(BaseReport):
#     def __init__(self, show_transaction_details=True, summary=None, *args, **kwargs):
#         super(BalanceReport, self).__init__(*args, **kwargs)
#         self.show_transaction_details = show_transaction_details
#         self.invested_items = []
#         self.summary = summary or BalanceReportSummary()
#
#
# # ----------------------------------------------------------------------------------------------------------------------
#
#
# class PLReportItem(BaseReportItem):
#     def __init__(self, principal_with_sign_system_ccy=0.0, carry_with_sign_system_ccy=0.0,
#                  overheads_with_sign_system_ccy=0.0, total_system_ccy=0.0,
#                  principal_with_sign_report_ccy=0.0, carry_with_sign_report_ccy=0.0,
#                  overheads_with_sign_report_ccy=0.0, total_report_ccy=0.0,
#                  *args, **kwargs):
#         super(PLReportItem, self).__init__(*args, **kwargs)
#
#         self.principal_with_sign_system_ccy = principal_with_sign_system_ccy
#         self.carry_with_sign_system_ccy = carry_with_sign_system_ccy
#         self.overheads_with_sign_system_ccy = overheads_with_sign_system_ccy
#         self.total_system_ccy = total_system_ccy
#
#         self.principal_with_sign_report_ccy = principal_with_sign_report_ccy
#         self.carry_with_sign_report_ccy = carry_with_sign_report_ccy
#         self.overheads_with_sign_report_ccy = overheads_with_sign_report_ccy
#         self.total_report_ccy = total_report_ccy
#
#     def __str__(self):
#         return 'PLReportItem'
#
#
# class PLReportSummary(object):
#     def __init__(self, principal_with_sign_system_ccy=0.0, carry_with_sign_system_ccy=0.0,
#                  overheads_with_sign_system_ccy=0.0, total_system_ccy=0.0,
#                  principal_with_sign_report_ccy=0.0, carry_with_sign_report_ccy=0.0,
#                  overheads_with_sign_report_ccy=0.0, total_report_ccy=0.0):
#         self.principal_with_sign_system_ccy = principal_with_sign_system_ccy
#         self.carry_with_sign_system_ccy = carry_with_sign_system_ccy
#         self.overheads_with_sign_system_ccy = overheads_with_sign_system_ccy
#         self.total_system_ccy = total_system_ccy
#
#         self.principal_with_sign_report_ccy = principal_with_sign_report_ccy
#         self.carry_with_sign_report_ccy = carry_with_sign_report_ccy
#         self.overheads_with_sign_report_ccy = overheads_with_sign_report_ccy
#         self.total_report_ccy = total_report_ccy
#
#
# class PLReport(BaseReport):
#     def __init__(self, summary=None, *args, **kwargs):
#         super(PLReport, self).__init__(*args, **kwargs)
#         self.summary = summary or PLReportSummary()
#
#
# # ----------------------------------------------------------------------------------------------------------------------
#
#
# class CostReportItem(BaseReportItem):
#     def __init__(self, position=0., cost_price=0., cost_price_adjusted=0., cost_system_ccy=0., cost_instrument_ccy=0.,
#                  *args, **kwargs):
#         super(CostReportItem, self).__init__(*args, **kwargs)
#         self.position = position
#         self.cost_price = cost_price,
#         self.cost_price_adjusted = cost_price_adjusted
#         self.cost_instrument_ccy = cost_instrument_ccy
#         self.cost_system_ccy = cost_system_ccy
#
#
# class CostReport(BaseReport):
#     def __init__(self, *args, **kwargs):
#         super(CostReport, self).__init__(*args, **kwargs)
#
#
# # ----------------------------------------------------------------------------------------------------------------------
#
#
# class YTMReportItem(BaseReportItem):
#     def __init__(self, position=0., ytm=0., time_invested=0., *args, **kwargs):
#         super(YTMReportItem, self).__init__(*args, **kwargs)
#         self.position = position
#         self.ytm = ytm
#         self.time_invested = time_invested
#
#
# class YTMReport(BaseReport):
#     def __init__(self, *args, **kwargs):
#         super(YTMReport, self).__init__(*args, **kwargs)
