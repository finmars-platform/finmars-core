from django.conf import settings
from django.contrib.auth.models import User

from poms.common.common_base_test import BaseTestCase


class TransactionTypeViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        user = User.objects.first()
        self.client.force_authenticate(user)
        self.pk = 1
        self.url = (
            f"/{settings.BASE_API_URL}/api/v1"
            f"/transactions/transaction-type/{self.pk}/recalculate-user-fields/"
        )

    def test_ok(self):
        response = self.client.post(path=self.url, format="json", data={})

        self.assertEqual(response.status_code, 200, response.content)
