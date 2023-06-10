from unittest import mock

from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.common.monad import Monad, MonadStatus
from poms.common.database_client import BACKEND_CALLBACK_URLS
from poms.celery_tasks.models import CeleryTask
from poms.instruments.models import Instrument


class ImportInstrumentDatabaseViewSetTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = (
            f"/{settings.BASE_API_URL}/api/v1/import/finmars-database/instrument/"
        )

    def test__400(self):
        response = self.client.post(path=self.url, format="json", data={})
        self.assertEqual(response.status_code, 400, response.content)

    @BaseTestCase.cases(
        ("bsy", "bsy"),
        ("bon", "bon"),
        ("stsy", "stsy"),
        ("sto", "sto"),
    )
    def test__check_instrument_type(self, type_code):
        request_data = {
            "instrument_code": "reference",
            "instrument_name": "name",
            "instrument_type_code": type_code,
        }
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 400, response.content)

    @BaseTestCase.cases(
        ("bonds_111", "bond", 111),
        ("bonds_777", "bond", 777),
        ("stocks_333", "stock", 333),
        ("stocks_999", "stock", 999),
    )
    @mock.patch("poms.common.database_client.DatabaseService.get_task")
    def test__task_ready(self, type_code, remote_task_id, mock_get_task):
        mock_get_task.return_value = Monad(
            status=MonadStatus.TASK_READY,
            task_id=remote_task_id,
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

        response_json = response.json()
        self.assertEqual(response_json["instrument_code"], reference)
        self.assertEqual(response_json["instrument_type_code"], type_code)
        self.assertIsNone(response_json["errors"])

        simple_instrument = Instrument.objects.get(pk=response_json["result_id"])
        self.assertFalse(simple_instrument.is_active)

        celery_task = CeleryTask.objects.get(pk=response_json["task"])
        options = celery_task.options_object
        callback_url = BACKEND_CALLBACK_URLS["instrument"]
        self.assertEqual(options["callback_url"], callback_url)
        results = celery_task.result_object
        self.assertEqual(results["instrument_id"], simple_instrument.id)
        self.assertEqual(results["task_id"], remote_task_id)

    @BaseTestCase.cases(
        ("bonds", "bonds"),
        ("stocks", "stocks"),
    )
    @mock.patch("poms.common.database_client.DatabaseService.get_task")
    @mock.patch("poms.integrations.tasks.update_task_with_instrument_data")
    def test__data_ready(self, type_code, mock_update_data, mock_get_task):
        mock_get_task.return_value = Monad(
            status=MonadStatus.DATA_READY,
            data={},
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

        mock_update_data.assert_called_once()

        response_json = response.json()

        # TODO extend test with creation of the full instrument
        self.assertEqual(response_json["instrument_type_code"], type_code)

    @mock.patch("poms.common.database_client.DatabaseService.get_task")
    def test__error(self, mock_get_task):
        message = self.random_string()
        mock_get_task.return_value = Monad(
            status=MonadStatus.ERROR,
            message=message,
        )
        request_data = {
            "instrument_code": "reference",
            "instrument_name": "name",
            "instrument_type_code": "bond",
        }
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertIsNone(response_json["result_id"])
        self.assertIn(message, response_json["errors"])
