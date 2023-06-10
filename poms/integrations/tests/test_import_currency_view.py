from unittest import mock

from django.conf import settings

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.common.database_client import BACKEND_CALLBACK_URLS
from poms.common.monad import Monad, MonadStatus
from poms.currencies.models import Currency


class ImportCurrencyDatabaseViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/import/finmars-database/currency/"

    def test__400(self):
        response = self.client.post(path=self.url, format="json", data={})
        self.assertEqual(response.status_code, 400, response.content)

    @BaseTestCase.cases(
        ("USD", "USD", 111),
        ("EUR", "EUR", 222),
    )
    @mock.patch("poms.common.database_client.DatabaseService.get_task")
    def test__task_ready(self, currency_code, task_id, mock_get_task):
        mock_get_task.return_value = Monad(
            status=MonadStatus.TASK_READY,
            task_id=task_id,
        )
        request_data = {"currency_code": currency_code}
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        data = response.json()
        print("task_ready", data)

        self.assertEqual(data["code"], currency_code)
        self.assertIsNone(data["result_id"])
        self.assertIsNone(data["errors"])
        celery_task = CeleryTask.objects.get(pk=data["task"])
        options = celery_task.options_object
        callback_url = BACKEND_CALLBACK_URLS["currency"]
        self.assertEqual(options["callback_url"], callback_url)
        results = celery_task.result_object
        self.assertEqual(results["task_id"], task_id)

    # @BaseTestCase.cases(
    #     ("USD", "USD"),
    #     ("EUR", "EUR"),
    # )
    # @mock.patch("poms.common.database_client.DatabaseService.get_task")
    # @mock.patch("poms.integrations.tasks.update_task_with_database_data")
    # def test__data_ready(self, type_code, mock_update_data, mock_get_task):
    #     mock_get_task.return_value = Monad(
    #         status=MonadStatus.DATA_READY,
    #         data={
    #
    #         },
    #     )
    #     currency_code = self.random_string()
    #     request_data = {"currency_code": currency_code}
    #     response = self.client.post(path=self.url, format="json", data=request_data)
    #     self.assertEqual(response.status_code, 200, response.content)
    #
    #     mock_update_data.assert_called_once()
    #
    #     data = response.json()
    #     print("data_ready", data)
    #     self.assertEqual(data["code"], type_code)

    # @mock.patch("poms.common.database_client.DatabaseService.get_task")
    # def test__error(self, mock_get_task):
    #     message = self.random_string()
    #     mock_get_task.return_value = Monad(
    #         status=MonadStatus.ERROR,
    #         message=message,
    #     )
    #
    #     request_data = {"currency_code": "USD"}
    #     response = self.client.post(path=self.url, format="json", data=request_data)
    #     self.assertEqual(response.status_code, 200, response.content)
    #
    #     data = response.json()
    #     self.assertIsNone(data["result_id"])
    #     self.assertIn(message, data["errors"])
