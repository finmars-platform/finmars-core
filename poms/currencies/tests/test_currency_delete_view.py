from django.conf import settings
from poms.currencies.constants import MAIN_CURRENCIES
from poms.common.common_base_test import BaseTestCase
from poms.currencies.models import Currency


class CurrencyDeleteViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/currencies/currency"

    def test_detail_delete(self):
        currency = Currency.objects.last()
        self.assertIn(currency.user_code, MAIN_CURRENCIES)

        response = self.client.delete(path=f"{self.url}/{currency.id}/")
        self.assertEqual(response.status_code, 409)
        currency = Currency.objects.create(
            user_code="test",
            name="test",
            owner=currency.owner,
            master_user=currency.master_user,
        )

        self.assertNotIn(currency.user_code, MAIN_CURRENCIES)

        response = self.client.delete(path=f"{self.url}/{currency.id}/")
        self.assertEqual(response.status_code, 204)