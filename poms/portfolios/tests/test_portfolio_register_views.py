from datetime import date
from django.conf import settings
from django.contrib.auth.models import User

from poms.common.common_base_test import BaseTestCase, BIG
from poms.transactions.models import (
    TransactionClass,
    TransactionType,
    TransactionTypeGroup,
)


class PortfolioRegisterRecordViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        user = User.objects.first()
        self.client.force_authenticate(user)
        self.url = (
            f"/{settings.BASE_API_URL}/api/v1"
            f"/portfolios/portfolio-register-record/"
        )

    def test_check_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)
        print(response.json())

    def test_created_prr(self):
        prr_data = {
            "master_user": self.db_data.master_user.id,
            "portfolio": self.db_data.portfolios[BIG].id,
            "instrument": self.db_data.instruments["Apple"].id,
            "transaction_class": self.db_data.transaction_classes[TransactionClass.CASH_INFLOW].id,
            "transaction_code": self.random_int(1_000, 10_000),
            "transaction_date": date.today(),
            "cash_amount": self.random_int(100_000, 500_000),
            "cash_currency": self.db_data.usd.id,
            "fx_rate": self.db_data.usd.default_fx_rate,
            "valuation_currency": self.db_data.usd.id,
        }
        response = self.client.post(path=self.url, format="json", data=prr_data)
        self.assertEqual(response.status_code, 201, response.content)


# class PortfolioRegisterRecordEvViewSetTest(BaseTestCase):
#     def setUp(self):
#         super().setUp()
#         self.init_test_case()
#         user = User.objects.first()
#         self.client.force_authenticate(user)
#         self.url = (
#             f"/{settings.BASE_API_URL}/api/v1"
#             f"/portfolios/portfolio-register-record-ev/"
#         )
#
#     def test_ok(self):
#         response = self.client.get(path=self.url, format="json")
#         self.assertEqual(response.status_code, 200, response.content)
#         print(response.json())


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
