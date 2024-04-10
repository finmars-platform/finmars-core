from datetime import date, timedelta

from poms.common.common_base_test import BIG, BaseTestCase
from poms.portfolios.models import PortfolioRegisterRecord
from poms.transactions.models import Transaction, TransactionClass

EXPECTED_RESPONSE = [
    {
        "portfolio": {
            "id": 1,
            "user_code": "-",
            "name": "-",
            "short_name": "-",
            "public_name": None,
            "notes": None,
            "is_deleted": False,
            "is_enabled": True,
        },
        "first_transaction": {"date_field": "transaction_date", "date": None},
    },
    {
        "portfolio": {
            "id": 2,
            "user_code": "Big",
            "name": "Big",
            "short_name": "Big",
            "public_name": None,
            "notes": None,
            "is_deleted": False,
            "is_enabled": True,
        },
        "first_transaction": {"date_field": "transaction_date", "date": "2023-09-05"},
    },
]


class PortfolioFirstTransactionViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/first-transaction-date/"
        self.portfolio = self.db_data.portfolios[BIG]

    def create_3_prr(self):
        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)
        self.days_ago = self.today - timedelta(days=10)
        for day in (self.today, self.yesterday, self.days_ago):
            self.create_prr_data(day)

    def create_prr_data(self, transaction_date: date):
        complex_transaction, transaction = self.db_data.cash_in_transaction(
            self.portfolio,
            day=transaction_date,
        )
        transaction.trade_price = self.random_float()
        transaction.save()

        trans_class = self.db_data.transaction_classes[TransactionClass.CASH_INFLOW]
        instrument = self.db_data.instruments["Apple"]
        portfolio_register = self.db_data.create_portfolio_register(
            self.portfolio,
            instrument,
            user_code=self.random_string(),
        )
        prr_data = {
            "master_user": self.master_user,
            "portfolio": self.portfolio,
            "instrument": instrument,
            "transaction_class": trans_class,
            "transaction_code": self.random_int(1_000, 10_000),
            "transaction_date": transaction_date,
            "cash_amount": self.random_int(100_000, 500_000),
            "cash_currency": self.db_data.usd,
            "fx_rate": self.db_data.usd.default_fx_rate,
            "valuation_currency": self.db_data.usd,
            "transaction": transaction,
            "complex_transaction": complex_transaction,
            "portfolio_register": portfolio_register,
        }
        return PortfolioRegisterRecord.objects.create(**prr_data)

    def get_portfolio_by_id(self):
        response = self.client.get(path=f"{self.url}?portfolio={self.portfolio.id}")
        self.assertEqual(response.status_code, 200, response.content)

        return response.json()

    def test__no_portfolio_id(self):
        self.create_3_prr()

        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(len(response_json), 2)

    def test__with_portfolio_id_as_int(self):
        self.create_3_prr()

        response_json = self.get_portfolio_by_id()

        self.assertEqual(len(response_json), 1)

        portfolio_id = response_json[0]["portfolio"]["id"]
        self.assertEqual(portfolio_id, self.portfolio.id)

        transaction_date = response_json[0]["first_transaction"]["date"]
        self.assertEqual(transaction_date, self.days_ago.strftime("%Y-%m-%d"))

    def test__with_portfolio_user_code_as_str(self):
        self.create_3_prr()

        response = self.client.get(
            path=f"{self.url}?portfolio={self.portfolio.user_code}"
        )
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(len(response_json), 1)
        portfolio_user_code = response_json[0]["portfolio"]["user_code"]
        self.assertEqual(portfolio_user_code, self.portfolio.user_code)

        transaction_date = response_json[0]["first_transaction"]["date"]
        self.assertEqual(transaction_date, self.days_ago.strftime("%Y-%m-%d"))

    @BaseTestCase.cases(
        ("cash_date", "cash_date"),
        ("accounting_date", "accounting_date"),
        ("transaction_date", "transaction_date"),
    )
    def test__different_date_field_values(self, date_field: str):
        self.create_3_prr()

        response = self.client.get(
            path=f"{self.url}?portfolio={self.portfolio.user_code}&date_field={date_field}"
        )
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(len(response_json), 1)
        portfolio_user_code = response_json[0]["portfolio"]["user_code"]
        self.assertEqual(portfolio_user_code, self.portfolio.user_code)

        transaction_date = response_json[0]["first_transaction"]["date"]
        self.assertEqual(transaction_date, self.days_ago.strftime("%Y-%m-%d"))

        field_name = response_json[0]["first_transaction"]["date_field"]
        self.assertEqual(field_name, date_field)

    @BaseTestCase.cases(
        ("settlement_date", "settlement_date"),
        ("is_canceled", "is_canceled"),
        ("jqhwgqjhge", "transaction_date_x"),
    )
    def test__different_invalid_date_field_values(self, date_field: str):
        response = self.client.get(
            path=f"{self.url}?portfolio={self.portfolio.user_code}&date_field={date_field}"
        )
        self.assertEqual(response.status_code, 400, response.content)

    @BaseTestCase.cases(
        ("not_exists", 1827368113),
        ("wrong_value", "8278372o9"),
    )
    def test__different_invalid_portfolio_values(self, date_field: str):
        response = self.client.get(
            path=f"{self.url}?portfolio={self.portfolio.user_code}&date_field={date_field}"
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test__method_not_allowed(self):
        response = self.client.get(
            path=f"{self.url}{self.portfolio.id}/?portfolio={self.portfolio.user_code}"
        )
        self.assertEqual(response.status_code, 405, response.content)

    def test__delete_transaction(self):
        self.create_3_prr()

        response_json = self.get_portfolio_by_id()

        first_date = response_json[0]["first_transaction"]["date"]
        self.assertEqual(first_date, self.days_ago.strftime("%Y-%m-%d"))

        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.first_transaction_date, self.days_ago)
        self.assertEqual(self.portfolio.first_cash_flow_date, self.days_ago)

        # delete earliest transaction
        first_transaction = Transaction.objects.get(transaction_date=self.days_ago)
        first_transaction.delete()

        response_json = self.get_portfolio_by_id()

        first_date = response_json[0]["first_transaction"]["date"]
        self.assertEqual(first_date, self.yesterday.strftime("%Y-%m-%d"))

        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.first_transaction_date, self.yesterday)
        self.assertEqual(self.portfolio.first_cash_flow_date, self.yesterday)

        # delete yesterday transaction
        first_transaction = Transaction.objects.get(transaction_date=self.yesterday)
        first_transaction.delete()

        response_json = self.get_portfolio_by_id()

        first_date = response_json[0]["first_transaction"]["date"]
        self.assertEqual(first_date, self.today.strftime("%Y-%m-%d"))

        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.first_transaction_date, self.today)
        self.assertEqual(self.portfolio.first_cash_flow_date, self.today)

        # delete today transaction
        first_transaction = Transaction.objects.get(transaction_date=self.today)
        first_transaction.delete()

        response_json = self.get_portfolio_by_id()

        first_date = response_json[0]["first_transaction"]["date"]
        self.assertIsNone(first_date)

        self.portfolio.refresh_from_db()
        self.assertIsNone(self.portfolio.first_transaction_date)
        self.assertIsNone(self.portfolio.first_cash_flow_date)
