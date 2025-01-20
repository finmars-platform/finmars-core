from unittest import mock
from django.conf import settings
from poms.common.common_base_test import BaseTestCase
from poms.currencies.models import Currency


class CurrencyRestoreViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/currencies/currency"
        self.currency = self.create_currency()
        
    def create_currency(self, user_code=None):
        user_code = user_code if user_code else "TEST01" 
        return Currency.objects.using(settings.DB_DEFAULT).create(
            master_user=self.master_user,
            owner=self.member,
            user_code=user_code,
        )

    @mock.patch("poms.common.models.get_request")
    def test__bulk_restore(self, get_request):
        get_request.return_value.user.member = self.member
        self.currency.fake_delete()

        data = {"ids": [self.currency.id,]}
        response = self.client.post(path=f"{self.url}/bulk-restore/", data=data)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIsInstance(response_data["task"], int)

    def test__invalid_ids(self):
        cur_ids = [c.id for c in Currency.objects.all()]
        ids = [id for id in range(999, 1999, 155) if id not in cur_ids]
        data = {"ids": ids}

        response = self.client.post(
            path=f"{self.url}/bulk-restore/", data=data
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.json()

        self.assertEqual(
            response_data["error"],
            f"IDs '{', '.join([str(id) for id in ids])}' don`t exist"
        )

    @mock.patch("poms.common.models.get_request")
    def test__bulk_restore_existing_user_code(self, get_request):
        get_request.return_value.user.member = self.member

        user_code = self.currency.user_code
        self.currency.fake_delete()
        self.create_currency(user_code)
        data = {"ids": [self.currency.id,]}

        response = self.client.post(
            path=f"{self.url}/bulk-restore/", data=data
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.json()

        self.assertEqual(response_data["error"], "Codes 'TEST01' already exist")