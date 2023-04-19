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

    @mock.patch("poms.common.database_client.DatabaseService.get_info")
    def test__task_ready(self, mock_get_info):
        mock_get_info.return_value = Monad(
            status=MonadStatus.TASK_READY, data={"task_id": 777}
        )
        reference = self.random_string()
        name = self.random_string()
        request_data = {
            "instrument_code": reference,
            "instrument_name": name,
            "instrument_type_code": "bonds",
        }
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        data = response.json()
        self.assertEqual(data["instrument_code"], reference)
        self.assertEqual(data["instrument_name"], name)
        self.assertEqual(data["instrument_type_code"], "bonds")
        self.assertIsNone(data["errors"])

        celery_task = CeleryTask.objects.get(pk=data["task"])
        print(celery_task.options_object)
        print(celery_task.result_object)

        simple_instrument = Instrument.objects.get(pk=data["result_id"])
        print(
            simple_instrument.is_active,
            simple_instrument.instrument_type_id,
            simple_instrument.pricing_currency,
            simple_instrument.default_price,
        )

        # {
        #     'instrument_code': 'XXVJRNNMTE', 'instrument_name': 'NVJXVHMVGH',
        #     'instrument_type_code': 'bonds', 'task': 1, 'result_id': 13, 'errors': None
        # }

        print(response.json())
