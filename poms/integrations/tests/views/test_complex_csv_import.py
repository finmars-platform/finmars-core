from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.celery_tasks.models import CeleryTask

BASE_URL = f"/{settings.BASE_API_URL}/api/v1/import"


class ComplexTransactionCsvFileImportViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"{BASE_URL}/complex-transaction-csv-file-import/"
        self.task = self.create_task(
            name="Test",
            func="test",
        )

    def create_task(self, name: str, func: str):
        return CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            verbose_name=name,
            function_name=func,
            type="transaction_import",
            status=CeleryTask.STATUS_PENDING,
            result="{}",
        )

    def test__405(self):
        response = self.client.get(path=self.url, format="json", data={})
        self.assertEqual(response.status_code, 405, response.content)

    def test__create(self):
        response = self.client.post(path=self.url, data={})
        self.assertEqual(response.status_code, 400, response.content)
