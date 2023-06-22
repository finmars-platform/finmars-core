from unittest import mock
from datetime import date

from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.integrations.monad import Monad, MonadStatus
from poms.integrations.database_client import BACKEND_CALLBACK_URLS
from poms.celery_tasks.models import CeleryTask
from poms.instruments.models import Instrument


class ImportInstrumentDatabaseViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = (
            f"/{settings.BASE_API_URL}/api/v1/import/finmars-database/instrument/"
        )
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
            type="import_from_database",
            status=CeleryTask.STATUS_PENDING,
            result="{}",
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
            "user_code": "user_code",
            "name": "name",
            "instrument_type_user_code": type_code,
        }
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 400, response.content)

    @BaseTestCase.cases(
        ("bond_111", "bond"),
        ("bond_777", "bond"),
        ("stock_333", "stock"),
        ("stock_999", "stock"),
    )
    @mock.patch("poms.integrations.database_client.DatabaseService.get_monad")
    def test__task_ready(self, type_code, mock_get_task):
        remote_task_id = self.random_int()
        mock_get_task.return_value = Monad(
            status=MonadStatus.TASK_CREATED,
            task_id=remote_task_id,
        )
        user_code = self.random_string()
        name = self.random_string()
        request_data = {
            "user_code": user_code,
            "name": name,
            "instrument_type_code": type_code,
        }
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        print("task_ready", response_json)

        self.assertIn("result_id", response_json)
        self.assertIn("errors", response_json)
        self.assertIsNone(response_json["errors"])

        self.assertIn("task", response_json)
        self.assertIn("name", response_json)
        self.assertIn("short_name", response_json)
        self.assertIn("user_code", response_json)

        self.assertIn("remote_task_id", response_json)
        self.assertEqual(response_json["remote_task_id"], remote_task_id)

        simple_instrument = Instrument.objects.get(pk=response_json["result_id"])
        self.assertFalse(simple_instrument.is_active)

        celery_task = CeleryTask.objects.get(pk=response_json["task"])
        options = celery_task.options_object
        self.assertEqual(options["callback_url"], BACKEND_CALLBACK_URLS["instrument"])

    @BaseTestCase.cases(
        ("bond", "bond"),
        ("stock", "stock"),
    )
    @mock.patch("poms.integrations.database_client.DatabaseService.get_monad")
    def test__data_ready(self, type_code, mock_get_monad):
        user_code = self.random_string(10)
        currency_code = self.random_string(3)
        mock_get_monad.return_value = Monad(
            status=MonadStatus.DATA_READY,
            data={
                "instruments": [
                    {
                        "instrument_type": {
                            "user_code": type_code,
                        },
                        "user_code": user_code,
                        "short_name": "test_short_name",
                        "name": "test_name",
                        "pricing_currency": {
                            "code": currency_code,
                        },
                        "maturity_price": 100.0,
                        "maturity": date.today(),
                        "country": {
                            "code": "USA",
                        },
                    },
                ],
                "currencies": [
                    {
                        "user_code": currency_code,
                        "short_name": f"short_{currency_code}",
                        "name": f"name_{currency_code}",
                        "public_name": f"public_{currency_code}",
                    }
                ],
            },
        )
        reference = self.random_string()
        name = self.random_string()
        request_data = {
            "user_code": reference,
            "name": name,
            "instrument_type_user_code": type_code,
        }
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        mock_get_monad.assert_called_once()

        response_json = response.json()

        self.assertIn("task", response_json)
        self.assertIn("result_id", response_json)
        self.assertIn("name", response_json)
        self.assertIn("short_name", response_json)
        self.assertIn("user_code", response_json)

        self.assertIn("errors", response_json)
        self.assertIsNone(response_json["errors"])

        self.assertIsNotNone(CeleryTask.objects.get(pk=response_json["task"]))
        self.assertIsNotNone(Instrument.objects.get(pk=response_json["result_id"]))

    @mock.patch("poms.integrations.database_client.DatabaseService.get_monad")
    def test__error(self, mock_get_task):
        message = self.random_string()
        mock_get_task.return_value = Monad(
            status=MonadStatus.ERROR,
            message=message,
        )
        request_data = {
            "user_code": "code",
            "name": "name",
            "instrument_type_user_code": "bonds",
        }
        response = self.client.post(path=self.url, format="json", data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        print("error", response_json)

        self.assertNotIn("result_id", response_json)

        self.assertIn("errors", response_json)
        self.assertIn(message, response_json["errors"])
