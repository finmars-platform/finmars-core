from poms.common.common_base_test import BaseTestCase
from poms.currencies.constants import DASH, MAIN_CURRENCIES
from poms.currencies.models import Currency


class CurrencyDeleteViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = 'realm00000'
        self.space_code = 'space00000'
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/currencies/currency"

    def test_detail_delete_main_currencies(self):
        for currency in Currency.objects.filter(user_code__in=MAIN_CURRENCIES):
            response = self.client.delete(path=f"{self.url}/{currency.id}/")
            self.assertEqual(response.status_code, 409)

    def test_detail_delete_custom_currencies(self):
        currency = Currency.objects.last()
        currency = Currency.objects.create(
            user_code="test",
            name="test",
            owner=currency.owner,
            master_user=currency.master_user,
        )

        self.assertNotIn(currency.user_code, MAIN_CURRENCIES)

        response = self.client.delete(path=f"{self.url}/{currency.id}/")
        self.assertEqual(response.status_code, 204)

    def test_bulk_delete(self):
        currencies = Currency.objects.all()
        ids_tuples = currencies.values_list('id', flat=True)
        ids_list = list(ids_tuples)

        data = {"ids": ids_list}
        response = self.client.post(path=f"{self.url}/bulk-delete/", data=data)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIsInstance(response_data["task_id"], int)

    def test_invalid_ids(self):
        response = self.client.delete(path=f"{self.url}/33454353453/")
        self.assertEqual(response.status_code, 404)

        response = self.client.delete(path=f"{self.url}/EUR/")
        self.assertEqual(response.status_code, 404)

    def test_bulk_delete_with_dash(self):
        currency = Currency.objects.first()
        currency.user_code = DASH
        currency.save()
        currency.fake_delete()
        self.assertEqual(currency.is_deleted, False)
