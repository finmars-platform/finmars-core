from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.database_client import DatabaseService
from poms.common.http_client import HttpClientError

from poms.common.monad import Monad, MonadStatus


class DatabaseClientGetTaskTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.service = DatabaseService()

    @BaseTestCase.cases(
        ("task_id_111",  {"task_id": 111}),
        ("task_id_777",  {"task_id": 777}),
    )
    @mock.patch("poms.common.http_client.HttpClient.post")
    def test__task_id(self, data, mock_post):
        mock_post.return_value = data

        monad : Monad = self.service.get_task("instrument", data)

        self.assertEqual(monad.status, MonadStatus.TASK_READY)
        self.assertEqual(monad.task_id, data["task_id"])

    @BaseTestCase.cases(
        ("data_111",  {"data": {"test": 333}}),
        ("data_777",  {"data": {"test": 999}}),
    )
    @mock.patch("poms.common.http_client.HttpClient.post")
    def test__data(self, data, mock_post):
        mock_post.return_value = data

        monad : Monad = self.service.get_task("instrument", data)

        self.assertEqual(monad.status, MonadStatus.DATA_READY)
        self.assertEqual(monad.task_id, 0)
        self.assertEqual(monad.data, data)

    @mock.patch("poms.common.http_client.HttpClient.post")
    def test__http_error(self, mock_post):
        data = {"items": []}
        mock_post.side_effect = HttpClientError("test")

        monad : Monad = self.service.get_task("instrument", data)

        self.assertEqual(monad.status, MonadStatus.ERROR)
        self.assertEqual(monad.task_id, 0)
        self.assertIsNone(monad.data)
        self.assertEqual(monad.message, repr(HttpClientError("test")))

    @BaseTestCase.cases(
        ("wrong_service",  "xxx_service"),
        ("empty_service",  ""),
        ("no_service",  None),
    )
    def test__wrong_service(self, service):
        data = {"items": []}

        with self.assertRaises(RuntimeError):
            self.service.get_task(service, data)

    @BaseTestCase.cases(
        ("none_data",  None),
        ("empty_data",  {}),
    )
    def test__get_task_no_data(self, data):
        with self.assertRaises(RuntimeError):
            self.service.get_task("instrument", data)


# DEPRECATED task: FN-1736
# class DatabaseClientGetResultsTest(BaseTestCase):
#     def setUp(self):
#         super().setUp()
#         self.service = DatabaseService()
#
#     @BaseTestCase.cases(
#         ("results_1",  {"results": [1, 2]}),
#         ("results_2",  {"results": [3, 4]}),
#     )
#     @mock.patch("poms.common.http_client.HttpClient.get")
#     def test__get_results_with_data(self, data, mock_get):
#         mock_get.return_value = data
#
#         monad : Monad = self.service.get_results("instrument-narrow", data)
#
#         self.assertEqual(monad.status, MonadStatus.DATA_READY)
#         self.assertEqual(monad.data, data)
#
#     @mock.patch("poms.common.http_client.HttpClient.get")
#     def test__get_results_http_error(self, mock_get):
#         data = {"items": []}
#         mock_get.side_effect = HttpClientError("test")
#
#         monad : Monad = self.service.get_results("instrument-narrow", data)
#
#         self.assertEqual(monad.status, MonadStatus.ERROR)
#         self.assertIsNone(monad.data)
#         self.assertEqual(monad.message, repr(HttpClientError("test")))
#
#     @BaseTestCase.cases(
#         ("wrong_service",  "xxx_service"),
#         ("empty_service",  ""),
#         ("no_service",  None),
#     )
#     def test__get_results_wrong_service(self, service):
#         with self.assertRaises(RuntimeError):
#             self.service.get_results(service, {})
