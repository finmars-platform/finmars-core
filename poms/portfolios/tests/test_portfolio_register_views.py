from django.conf import settings
from django.contrib.auth.models import User

from poms.common.common_base_test import BaseTestCase


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
        response = self.client.get(path=self.url, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        print(response.json())

    # def test_created_prr(self):
    #     prr_data = {
    #
    #     }


class PortfolioRegisterRecordEvViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        user = User.objects.first()
        self.client.force_authenticate(user)
        self.url = (
            f"/{settings.BASE_API_URL}/api/v1"
            f"/portfolios/portfolio-register-record-ev/"
        )

    def test_ok(self):
        response = self.client.get(path=self.url, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        print(response.json())


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
