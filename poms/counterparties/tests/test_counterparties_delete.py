from django.conf import settings
from poms.currencies.constants import DASH
from poms.common.common_base_test import BaseTestCase
from poms.counterparties.models import Counterparty

class CounterpartyDeleteViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = 'realm00000'
        self.space_code = 'space00000'

        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/counterparties/counterparty"

    def test_detail_delete_main_counterparties(self):
        for counterparty in Counterparty.objects.filter(user_code__in=DASH):
            response = self.client.delete(path=f"{self.url}/{counterparty.id}/")
            self.assertEqual(response.status_code, 409)
            
    def test_detail_delete_custom_counterparties(self):
        counterparty = Counterparty.objects.last()
        counterparty = Counterparty.objects.create(
            user_code="test",
            name="test",
            owner=counterparty.owner,
            master_user=counterparty.master_user,
        )

        self.assertNotIn(counterparty.user_code, DASH)

        response = self.client.delete(path=f"{self.url}/{counterparty.id}/")
        self.assertEqual(response.status_code, 204)