from unittest import mock

from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.common.monad import Monad, MonadStatus
from poms.celery_tasks.models import CeleryTask
from poms.instruments.models import Instrument


class ImportInstrumentDatabaseViewSetTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = (
            f"/{settings.BASE_API_URL}/api/v1" f"/import/finmars-database/instrument/"
        )

    def test__400(self):
        response = self.client.post(path=self.url, format="json", data={})
        self.assertEqual(response.status_code, 400, response.content)

    @BaseTestCase.cases(
        ("bonds_777", "bonds", 777),
        ("bonds_111", "bonds", 111),
        ("stocks_333", "stocks", 333),
        ("stocks_999", "stocks", 999),
    )
    @mock.patch("poms.common.database_client.DatabaseService.get_info")
    def test__task_ready(self, type_code, task_id, mock_get_info):
        mock_get_info.return_value = Monad(
            status=MonadStatus.TASK_READY,
            task_id=task_id,
        )
        reference = self.random_string()
        name = self.random_string()
        request_data = {
            "instrument_code": reference,
            "instrument_name": name,
            "instrument_type_code": type_code,
        }
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        data = response.json()
        self.assertEqual(data["instrument_code"], reference)
        self.assertEqual(data["instrument_name"], name)
        self.assertEqual(data["instrument_type_code"], type_code)
        self.assertIsNone(data["errors"])

        simple_instrument = Instrument.objects.get(pk=data["result_id"])
        self.assertFalse(simple_instrument.is_active)
        celery_task = CeleryTask.objects.get(pk=data["task"])
        options = celery_task.options_object
        callback_url = (
            f"https://{settings.DOMAIN_NAME}/{settings.BASE_API_URL}"
            f"/api/instruments/fdb-create-from-callback/"
        )
        self.assertEqual(options["callback_url"], callback_url)
        results = celery_task.result_object
        self.assertEqual(results["instrument_id"], simple_instrument.id)
        self.assertEqual(results["task_id"], task_id)

    # @mock.patch("poms.common.database_client.DatabaseService.get_info")
    # def test__data_ready(self, type_code, mock_get_info):
    #     mock_get_info.return_value = Monad(
    #         status=MonadStatus.DATA_READY,
    #         data={
    #
    #         },
    #     )
    #     reference = self.random_string()
    #     name = self.random_string()
    #     request_data = {
    #         "instrument_code": reference,
    #         "instrument_name": name,
    #         "instrument_type_code": type_code,
    #     }
    #     response = self.client.post(path=self.url, format="json", data=request_data)
    #     self.assertEqual(response.status_code, 200, response.content)
    #
    #     data = response.json()

    @mock.patch("poms.common.database_client.DatabaseService.get_info")
    def test__error(self, mock_get_info):
        message = self.random_string()
        mock_get_info.return_value = Monad(
            status=MonadStatus.ERROR,
            message=message,
        )

        request_data = {
            "instrument_code": "reference",
            "instrument_name": "name",
            "instrument_type_code": "any",
        }
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        data = response.json()
        self.assertIsNone(data["result_id"])
        self.assertIn(message, data["errors"])
