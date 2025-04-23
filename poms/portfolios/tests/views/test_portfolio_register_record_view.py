from datetime import date
import random

from django.conf import settings

from poms.common.common_base_test import BIG, SMALL, BaseTestCase
from poms.portfolios.models import PortfolioRegisterRecord
from poms.transactions.models import TransactionClass


class PortfolioRegisterRecordViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-register-record/"
        self.portfolio = self.db_data.portfolios[BIG]
        self.prr_data = None

    def create_prr_data(
        self, trade_price=1.0, t_class=0, use_default_portfolio=True, current_date=True
    ):
        complex_transaction, transaction = self.db_data.cash_in_transaction(
            self.portfolio
        )
        if trade_price > 0:
            transaction.trade_price = trade_price
            transaction.save()
        if t_class == 0:
            trans_class = self.db_data.transaction_classes[TransactionClass.CASH_INFLOW]
        else:
            trans_class = self.db_data.transaction_classes[t_class]
        instrument = self.db_data.instruments["Apple"]
        portfolio_register = self.db_data.create_portfolio_register(
            self.portfolio,
            instrument,
            user_code=self.random_string(),
        )
        self.prr_data = {
            "portfolio": self.portfolio.id
            if use_default_portfolio
            else self.db_data.portfolios[SMALL].id,
            "instrument": instrument.id,
            "transaction_class": trans_class.id,
            "transaction_code": self.random_int(1_000, 10_000),
            "transaction_date": str(date.today()) if current_date else "2024-01-01",
            "cash_amount": self.random_int(100_000, 500_000),
            "cash_currency": self.db_data.usd.id,
            "fx_rate": self.db_data.usd.default_fx_rate,
            "valuation_currency": self.db_data.usd.id,
            "transaction": transaction.id,
            "complex_transaction": complex_transaction.id,
            "portfolio_register": portfolio_register.id,
        }

    def create_portfolio_register_record(
        self,
        trade_price: float = 0,
        t_class: int = 0,
        use_default_portfolio=True,
        current_date=True,
    ):
        self.create_prr_data(trade_price, t_class, use_default_portfolio, current_date)

        response = self.client.post(self.url, data=self.prr_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        return response.json()

    def test_created_prr_has_new_field_automatic(self):
        resp_data = self.create_portfolio_register_record(trade_price=0)
        self.assertIn("share_price_calculation_type", resp_data)
        self.assertEqual(
            resp_data["share_price_calculation_type"],
            PortfolioRegisterRecord.AUTOMATIC,
        )

    def test_created_prr_has_new_field_manual(self):
        resp_data = self.create_portfolio_register_record(trade_price=0.1)
        self.assertIn("share_price_calculation_type", resp_data)
        self.assertEqual(
            resp_data["share_price_calculation_type"],
            PortfolioRegisterRecord.MANUAL,
        )

    def test_created_prr_has_new_field_automatic_if_not_cash_in_out(self):
        resp_data = self.create_portfolio_register_record(trade_price=0.1, t_class=3)
        self.assertIn("share_price_calculation_type", resp_data)
        self.assertEqual(
            resp_data["share_price_calculation_type"],
            PortfolioRegisterRecord.AUTOMATIC,
        )

    def test_get_list(self):
        self.create_portfolio_register_record()
        self.create_portfolio_register_record()
        self.create_portfolio_register_record(
            use_default_portfolio=False, current_date=False
        )

        response = self.client.get(path=f"{self.url}")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json().get("count"), 3)

        response = self.client.get(
            path=f"{self.url}?portfolio__user_code={self.portfolio.user_code}"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json().get("count"), 2)

        response = self.client.get(
            path=f"{self.url}?transaction_date_before=2024-01-02"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json().get("count"), 1)

        response = self.client.get(path=f"{self.url}?transaction_date_after=2024-01-02")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json().get("count"), 2)
