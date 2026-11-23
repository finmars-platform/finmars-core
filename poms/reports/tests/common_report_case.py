from datetime import date

from poms.common.common_base_test import BIG, BUY_SELL, SMALL, BaseTestCase
from poms.instruments.models import CostMethod, PriceHistory
from poms.transactions.models import ComplexTransaction, Transaction, TransactionClass

REPORT_DATE = date(2026, 9, 30)
PL_FIRST_DATE = date(2025, 12, 31)  # last business day of 2025, i.e. what "ytd" resolves to

BACKEND_OPTIONS = {
    "filter_settings": [],
    "groups_types": [],
    "groups_values": [],
    "columns": [],
}


class ReportsTestCase(BaseTestCase):
    """
    Two portfolios with their own accounts and registers (created by DbInitializer):

        Big:   cash in 10000, buy 10 Apple @ 100
        Small: cash in  5000, buy  5 Apple @ 110, buy 20 Tesla @ 50

    Prices: Apple 90 -> 120, Tesla 40 -> 60 (PL_FIRST_DATE -> REPORT_DATE).
    """

    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.pricing_policy = self.create_pricing_policy()

        self.big = self.db_data.portfolios[BIG]
        self.small = self.db_data.portfolios[SMALL]
        self.apple = self.db_data.instruments["Apple"]
        self.tesla = self.db_data.instruments["Tesla B."]

        for instrument, prices in (
            (self.apple, {PL_FIRST_DATE: 90, REPORT_DATE: 120}),
            (self.tesla, {PL_FIRST_DATE: 40, REPORT_DATE: 60}),
        ):
            for day, price in prices.items():
                PriceHistory.objects.create(
                    instrument=instrument,
                    pricing_policy=self.pricing_policy,
                    date=day,
                    principal_price=price,
                    accrued_price=0,
                )

        self.book(self.big, None, TransactionClass.CASH_INFLOW, 0, 0, 10000, date(2025, 11, 3))
        self.book(self.big, self.apple, TransactionClass.BUY, 10, -1000, -1000, date(2026, 1, 15))
        self.book(self.small, None, TransactionClass.CASH_INFLOW, 0, 0, 5000, date(2025, 11, 3))
        self.book(self.small, self.apple, TransactionClass.BUY, 5, -550, -550, date(2026, 2, 10))
        self.book(self.small, self.tesla, TransactionClass.BUY, 20, -1000, -1000, date(2026, 2, 10))

    def book(self, portfolio, instrument, transaction_class_id, position, principal, cash, day):
        complex_transaction = ComplexTransaction.objects.create(
            master_user=self.master_user,
            owner=self.member,
            date=day,
            transaction_type=self.db_data.transaction_types[BUY_SELL],
        )
        account = portfolio.accounts.first()
        instrument = instrument or self.db_data.default_instrument
        strategies = self.db_data.strategies
        return Transaction.objects.create(
            master_user=self.master_user,
            owner=self.member,
            complex_transaction=complex_transaction,
            portfolio=portfolio,
            transaction_class_id=transaction_class_id,
            instrument=instrument,
            linked_instrument=instrument,
            allocation_balance=instrument,
            allocation_pl=instrument,
            transaction_currency=self.usd,
            settlement_currency=self.usd,
            position_size_with_sign=position,
            principal_with_sign=principal,
            cash_consideration=cash,
            carry_with_sign=0,
            overheads_with_sign=0,
            reference_fx_rate=1,
            factor=1,
            account_position=account,
            account_cash=account,
            account_interim=account,
            strategy1_position=strategies[1],
            strategy1_cash=strategies[1],
            strategy2_position=strategies[2],
            strategy2_cash=strategies[2],
            strategy3_position=strategies[3],
            strategy3_cash=strategies[3],
            transaction_date=day,
            accounting_date=day,
            cash_date=day,
        )

    def report_payload(self, **kwargs):
        return {
            "report_date": str(REPORT_DATE),
            "report_currency": self.usd.user_code,
            "pricing_policy": self.pricing_policy.id,
            "cost_method": CostMethod.AVCO,
            **kwargs,
        }

    def post_report(self, url_path, **kwargs):
        url = f"/{self.realm_code}/{self.space_code}/api/v1/reports/{url_path}/"
        return self.client.post(path=url, format="json", data=self.report_payload(**kwargs))

    @staticmethod
    def positions(items):
        """(portfolio, account, user_code) -> (position_size, market_value, total) of report items"""
        result = {}
        for item in items:
            key = (
                item.get("portfolio.user_code"),
                item.get("account.user_code"),
                item["user_code"],
            )
            assert key not in result, f"duplicate report item {key}"
            result[key] = tuple(round(item[name], 6) for name in ("position_size", "market_value", "total"))
        return result
