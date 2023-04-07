from datetime import date
from django.conf import settings
from django.contrib.auth.models import User

from poms.common.common_base_test import BaseTestCase, BIG
from poms.portfolios.models import PortfolioRegisterRecord
from poms.transactions.models import TransactionClass
from poms.users.models import Member

JSON_TYPE = "application/json"


class PortfolioRegisterRecordViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.user = User.objects.create(username="view_tester")
        self.user.master_user = self.db_data.master_user
        self.user.save()
        self.member = Member.objects.create(
            user=self.user,
            master_user=self.user.master_user,
            is_admin=True,
        )
        self.client.force_authenticate(self.user)
        self.url = (
            f"/{settings.BASE_API_URL}/api/v1/portfolios/portfolio-register-record/"
        )

    def create_portfolio_register_record(self):
        portfolio = self.db_data.portfolios[BIG]
        complex_transaction, transaction = self.db_data.cash_in_transaction(portfolio)
        trans_class = self.db_data.transaction_classes[TransactionClass.CASH_INFLOW]
        instrument = self.db_data.instruments["Apple"]
        portfolio_register = self.db_data.create_portfolio_register(
            portfolio, instrument
        )
        prr_data = {
            "portfolio": portfolio.id,
            "instrument": instrument.id,
            "transaction_class": trans_class.id,
            "transaction_code": self.random_int(1_000, 10_000),
            "transaction_date": str(date.today()),
            "cash_amount": self.random_int(100_000, 500_000),
            "cash_currency": self.db_data.usd.id,
            "fx_rate": self.db_data.usd.default_fx_rate,
            "valuation_currency": self.db_data.usd.id,
            "transaction": transaction.id,
            "complex_transaction": complex_transaction.id,
            "portfolio_register": portfolio_register.id,
        }
        response = self.client.post(self.url, data=prr_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def test_check_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test_created_prr_has_new_field(self):
        resp_data = self.create_portfolio_register_record()
        self.assertIn("share_price_calculation_type", resp_data)
        self.assertEqual(
            resp_data["share_price_calculation_type"],
            PortfolioRegisterRecord.AUTOMATIC,
        )

    def test_check_updated_prr_became_manual(self):
        resp_data = self.create_portfolio_register_record()
        resp_data["dealing_price_valuation_currency"] += self.random_int()
        response = self.client.put(
            f"{self.url}{resp_data['id']}/",
            data=resp_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        updated_data = response.json()
        self.assertEqual(
            updated_data["share_price_calculation_type"],
            PortfolioRegisterRecord.MANUAL,
        )


class PortfolioRegisterRecordEvViewSetTest(PortfolioRegisterRecordViewSetTest):
    def setUp(self):
        super().setUp()
        self.url = (
            f"/{settings.BASE_API_URL}/api/v1"
            f"/portfolios/portfolio-register-record-ev/"
        )



# class PortfolioRegisterRecordEvGroupViewSetTest(BaseTestCase):
#     def setUp(self):
#         super().setUp()
#         self.init_test_case()
#         user = User.objects.first()
#         self.client.force_authenticate(user)
#         self.pk = 1
#         self.url = (
#             f"/{settings.BASE_API_URL}/api/v1"
#             f"/portfolios/portfolio-register-record-ev-group/"
#         )
#
#     def test_ok(self):
#         response = self.client.get(path=self.url, format="json")
#         self.assertEqual(response.status_code, 200, response.content)
#         print(response.json())
