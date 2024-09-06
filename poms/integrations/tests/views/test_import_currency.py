from unittest import mock

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.integrations.database_client import get_backend_callback_url
from poms.integrations.monad import Monad, MonadStatus
from poms.currencies.models import Currency


class ImportCurrencyDatabaseViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = 'realm00000'
        self.space_code = 'space00000'
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/import/finmars-database/currency/"
        # self.url = urls.reverse("import_currency_database")

    def test__400(self):
        response = self.client.post(path=self.url, format="json", data={})
        self.assertEqual(response.status_code, 400, response.content)

    @BaseTestCase.cases(
        ("USD", "USD", 111),
        ("EUR", "EUR", 222),
    )
    @mock.patch("poms.integrations.database_client.DatabaseService.get_monad")
    def test__task_ready(self, user_code, task_id, mock_get_task):
        mock_get_task.return_value = Monad(
            status=MonadStatus.TASK_CREATED,
            task_id=task_id,
        )
        request_data = {"user_code": user_code}
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        print("task_ready", response_json)

        self.assertNotIn("result_id", response_json)
        self.assertIn("errors", response_json)
        self.assertIsNone(response_json["errors"])

        self.assertIn("task", response_json)
        celery_task = CeleryTask.objects.filter(pk=response_json["task"]).first()
        self.assertIsNotNone(celery_task)

        self.assertIn("remote_task_id", response_json)
        self.assertEqual(response_json["remote_task_id"], task_id)

        options = celery_task.options_object

        BACKEND_CALLBACK_URLS = get_backend_callback_url()
        self.assertEqual(options["callback_url"], BACKEND_CALLBACK_URLS["currency"])
        results = celery_task.result_object
        self.assertEqual(results["remote_task_id"], task_id)

    @BaseTestCase.cases(
        ("USD", "USD"),
        ("EUR", "EUR"),
    )
    @mock.patch("poms.integrations.database_client.DatabaseService.get_monad")
    def test__data_ready(self, user_code, mock_get_monad):
        mock_get_monad.return_value = Monad(
            status=MonadStatus.DATA_READY,
            data={
                "id": self.random_int(),
                "name": self.random_string(),
                "short_name": self.random_string(),
                "user_code": self.random_string(),
                "public_name": self.random_string(),
                "notes": self.random_string(),
            },
        )
        request_data = {"user_code": user_code}
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        mock_get_monad.assert_called_once()

        response_json = response.json()

        self.assertIn("task", response_json)
        self.assertIn("result_id", response_json)
        self.assertIn("errors", response_json)
        self.assertIsNone(response_json["errors"])

        self.assertIsNotNone(CeleryTask.objects.get(pk=response_json["task"]))
        self.assertIsNotNone(Currency.objects.get(pk=response_json["result_id"]))

    @mock.patch("poms.integrations.database_client.DatabaseService.get_monad")
    def test__error(self, mock_get_task):
        message = self.random_string()
        mock_get_task.return_value = Monad(
            status=MonadStatus.ERROR,
            message=message,
        )

        request_data = {"user_code": "USD"}
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        print("error", response_json)

        self.assertNotIn("result_id", response_json)

        self.assertIn("errors", response_json)
        self.assertIn(message, response_json["errors"])
