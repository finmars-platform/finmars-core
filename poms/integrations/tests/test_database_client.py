from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.integrations.database_client import DatabaseService
from poms.common.http_client import HttpClientError
from poms.integrations.monad import Monad, MonadStatus
from poms.celery_tasks.models import CeleryTask


class DatabaseClientTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.task = self.create_task(
            name="Test",
            func="test",
        )
        self.service = DatabaseService()

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

    @BaseTestCase.cases(
        ("task_id_111", {"task_id": 111, "data": None, "request_id": None}),
        ("task_id_777", {"task_id": 777, "data": None, "request_id": None}),
    )
    @mock.patch("poms.common.http_client.HttpClient.post")
    def test__task_id(self, request_data, mock_post):
        request_data["request_id"] = self.task.id
        mock_post.return_value = request_data

        monad: Monad = self.service.get_monad("instrument", request_data)

        self.assertEqual(monad.status, MonadStatus.TASK_CREATED)
        self.assertEqual(monad.task_id, request_data["task_id"])

    @BaseTestCase.cases(
        ("data_111", {"data": {"test": 333}, "request_id": None, "task_id": None}),
        ("data_777", {"data": {"test": 999}, "request_id": None, "task_id": None}),
    )
    @mock.patch("poms.common.http_client.HttpClient.post")
    def test__data(self, request_data: dict, mock_post):
        request_data["request_id"] = self.task.id
        mock_post.return_value = request_data

        monad: Monad = self.service.get_monad("instrument", request_data)

        self.assertEqual(monad.status, MonadStatus.DATA_READY)
        self.assertEqual(monad.task_id, None)
        self.assertEqual(monad.data, request_data["data"])

    @mock.patch("poms.common.http_client.HttpClient.post")
    def test__http_error(self, mock_post):
        data = {"items": []}
        mock_post.side_effect = HttpClientError("test")

        monad: Monad = self.service.get_monad("instrument", data)

        self.assertEqual(monad.status, MonadStatus.ERROR)
        self.assertEqual(monad.message, repr(HttpClientError("test")))

    @BaseTestCase.cases(
        ("wrong_service", "xxx_service"),
        ("empty_service", ""),
        ("no_service", None),
    )
    def test__wrong_service(self, service):
        data = {"items": []}

        with self.assertRaises(RuntimeError):
            self.service.get_monad(service, data)

    @BaseTestCase.cases(
        ("no_data", {"task_id": None, "request_id": None, }),
        ("no_task_id", {"data": {"test": 333}, "request_id": None,}),
        ("no_both", {"data": None, "task_id": None, "request_id": None,}),
    )
    @mock.patch("poms.common.http_client.HttpClient.post")
    def test__missing_param(self, request_data: dict, mock_post):
        request_data["request_id"] = self.task.id
        mock_post.return_value = request_data
        monad: Monad = self.service.get_monad("instrument", request_data)
        self.assertEqual(monad.status, MonadStatus.ERROR)
        print(f"\nmonad.message={monad.message}\n")

    @BaseTestCase.cases(
        ("no_req_id", {"data": {"test": 1}, "task_id": 2, }),
        ("wrong_reg_id", {"data": {"test": 1}, "task_id": 2, "request_id": 777,}),
    )
    @mock.patch("poms.common.http_client.HttpClient.post")
    def test__invalid(self, request_data: dict, mock_post):
        mock_post.return_value = request_data
        monad: Monad = self.service.get_monad("instrument", request_data)
        self.assertEqual(monad.status, MonadStatus.ERROR)
        print(f"\nmonad.message={monad.message}\n")
