from unittest import mock

from django.conf import settings

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.common.database_client import BACKEND_CALLBACK_URLS
from poms.common.monad import Monad, MonadStatus
# from poms.counterparties.models import Counterparty


class ImportCompanyDatabaseViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/import/finmars-database/company/"

    def test__400(self):
        response = self.client.post(path=self.url, format="json", data={})
        self.assertEqual(response.status_code, 400, response.content)

    @BaseTestCase.cases(
        ("Raiffiesen", "12345", 111),
        ("IntesaSanPaolo", "67890", 222),
    )
    @mock.patch("poms.common.database_client.DatabaseService.get_task")
    def test__task_ready(self, company_id, task_id, mock_get_task):
        mock_get_task.return_value = Monad(
            status=MonadStatus.TASK_READY,
            task_id=task_id,
        )
        request_data = {"company_id": company_id}
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        print("task_ready", response_json)

        self.assertEqual(response_json["company_id"], company_id)
        self.assertIsNone(response_json["result_id"])
        self.assertIsNone(response_json["errors"])
        celery_task = CeleryTask.objects.get(pk=response_json["task"])
        options = celery_task.options_object
        self.assertEqual(options["callback_url"], BACKEND_CALLBACK_URLS["company"])
        results = celery_task.result_object
        self.assertEqual(results["task_id"], task_id)

    @BaseTestCase.cases(
        ("Raiffiesen", "12345"),
        ("IntesaSanPaolo", "67890"),
    )
    @mock.patch("poms.common.database_client.DatabaseService.get_task")
    @mock.patch("poms.integrations.tasks.update_task_with_company_data")
    def test__data_ready(self, code, mock_update_data, mock_get_task):
        mock_get_task.return_value = Monad(
            status=MonadStatus.DATA_READY,
            data={},
        )
        request_data = {"company_id": code}
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        mock_update_data.assert_called_once()

        response_json = response.json()
        celery_task = CeleryTask.objects.get(pk=response_json["task"])

        print("company_data_ready", response_json)
        # TODO extend test with creation of the company
        self.assertEqual(response_json["company_id"], code)

    @mock.patch("poms.common.database_client.DatabaseService.get_task")
    def test__error(self, mock_get_task):
        message = self.random_string()
        mock_get_task.return_value = Monad(
            status=MonadStatus.ERROR,
            message=message,
        )

        request_data = {"company_id": "12345"}
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertIsNone(response_json["result_id"])
        self.assertIn(message, response_json["errors"])
