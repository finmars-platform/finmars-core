# import logging
# from datetime import timedelta
#
# from django.db.models import Q
#
# from poms.currencies.models import CurrencyHistory
# from poms.instruments.models import PriceHistory
#
# _l = logging.getLogger('poms.reports')
#
#
# class AbstractProvider:
#     def __init__(self, master_user, pricing_policy, report_date):
#         self._cache = {}
#         self._master_user = master_user
#         self._pricing_policy = pricing_policy
#         self._report_date = report_date
#         self._lazy = True
#
#     def get(self, item, d=None):
#         d = d or self._report_date
#         key = (item.id, d)
#         try:
#             return self._cache[key]
#         except KeyError:
#             h = self._on_missed(item, d)
#             self._cache[key] = h
#             return h
#
#     def __getitem__(self, item):
#         if isinstance(item, (tuple, list)):
#             return self.get(*item)
#         else:
#             return self.get(item)
#
#     def _on_missed(self, item, d):
#         raise NotImplementedError('`_on_missed()` must be implemented.')
#
#
# # Instrument
#
#
# class FakeInstrumentPricingProvider(AbstractProvider):
#     def fill_using_transactions(self, transaction_queryset, lazy=True):
#         pass
#
#     def _on_missed(self, item, d):
#         h = PriceHistory(pricing_policy=self._pricing_policy, instrument=item, date=d)
#         return h
#
#
# class InstrumentPricingProvider(AbstractProvider):
#     def fill_using_transactions(self, transaction_queryset, lazy=True):
#         self._lazy = lazy
#         self._cache = {}
#
#         dates = [
#             self._report_date,
#             self._report_date - timedelta(days=1),
#             self._report_date - timedelta(days=self._report_date.day),
#         ]
#
#         qs = PriceHistory.objects.filter(
#             instrument__master_user=self._master_user,
#             pricing_policy=self._pricing_policy
#         ).filter(
#             Q(date__in=dates) | Q(date__in=transaction_queryset.values_list('accounting_date', flat=True))
#         ).filter(
#             Q(instrument__in=transaction_queryset.values_list('instrument', flat=True))
#         )
#
#         for h in qs:
#             self._cache[(h.instrument_id, h.date)] = h
#
#         _l.debug('instrument pricing: len=%s', len(self._cache))
#
#     def _on_missed(self, item, d):
#         if self._lazy:
#             try:
#                 return PriceHistory.objects.get(pricing_policy=self._pricing_policy, instrument=item, date=d)
#             except PriceHistory.DoesNotExist:
#                 pass
#         h = PriceHistory(pricing_policy=self._pricing_policy, instrument=item, date=d)
#         return h
#
#
# # Currency
#
#
# class FakeCurrencyFxRateProvider(AbstractProvider):
#     def fill_using_transactions(self, transaction_queryset, lazy=True, currencies=None):
#         pass
#
#     def _on_missed(self, item, d):
#         h = CurrencyHistory(pricing_policy=self._pricing_policy, currency=item, date=d)
#         if self._master_user.system_currency_id == item.id:
#             h.fx_rate = 1.0
#         return h
#
#
# class CurrencyFxRateProvider(AbstractProvider):
#     def fill_using_transactions(self, transaction_queryset, lazy=True, currencies=None):
#         self._lazy = lazy
#         self._cache = {}
#         currencies = currencies or []
#
#         dates = [
#             self._report_date,
#             self._report_date - timedelta(days=1),
#             self._report_date - timedelta(days=self._report_date.day)
#         ]
#
#         qs = CurrencyHistory.objects.filter(
#             currency__master_user=self._master_user,
#             pricing_policy=self._pricing_policy
#         ).filter(
#             Q(date__in=dates) |
#             Q(date__in=transaction_queryset.values_list('cash_date', flat=True)) |
#             Q(date__in=transaction_queryset.values_list('accounting_date', flat=True))
#         ).filter(
#             Q(currency__in=currencies) |
#             Q(currency__in=transaction_queryset.values_list('transaction_currency', flat=True)) |
#             Q(currency__in=transaction_queryset.values_list('settlement_currency', flat=True)) |
#             Q(currency__in=transaction_queryset.values_list('instrument__pricing_currency', flat=True)) |
#             Q(currency__in=transaction_queryset.values_list('instrument__accrued_currency', flat=True))
#         )
#
#         for h in qs:
#             self._cache[(h.currency_id, h.date)] = h
#
#         _l.debug('currency fx rates: len=%s', len(self._cache))
#
#     def _on_missed(self, item, d):
#         if self._lazy:
#             try:
#                 return CurrencyHistory.objects.get(pricing_policy=self._pricing_policy, currency=item, date=d)
#             except CurrencyHistory.DoesNotExist:
#                 pass
#         h = CurrencyHistory(pricing_policy=self._pricing_policy, currency=item, date=d)
#         if self._master_user.system_currency_id == item.id:
#             h.fx_rate = 1.0
#         return h
