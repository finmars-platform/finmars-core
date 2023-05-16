from copy import deepcopy
from unittest import mock

from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.common.monad import Monad, MonadStatus

CURRENCY_DATA = {
    "count": 3,
    "next": "https://database.finmars.com/api/v1/currency/?page=2",
    "previous": None,
    "results": [
        {
            "id": 1,
            "name": "Afghani",
            "user_code": "AFN",
            "code": "AFN",
            "numeric_code": "971"
        },
        {
            "id": 3,
            "name": "Lek",
            "user_code": "ALL",
            "code": "ALL",
            "numeric_code": "008"
        },
        {
            "id": 6,
            "name": "Kwanza",
            "user_code": "AOA",
            "code": "AOA",
            "numeric_code": "973"
        },
    ]
}


class CurrencyDatabaseSearchViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = (
            f"/{settings.BASE_API_URL}/api/v1/currencies/currency-database-search"
        )

    @BaseTestCase.cases(
        ("no_name", {"page_size": 100}),
        ("empty_name", {"page_size": 500, "name": ""}),
    )
    def test__empty_name_200_with_empty_response(self, params):
        response = self.client.get(self.url, data=params)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertIsNone(data["next"])
        self.assertIsNone(data["previous"])
        self.assertEqual(data["count"], 0)
        self.assertEqual(len(data["results"]), 0)

    @BaseTestCase.cases(
        ("1", {"page_size": 1, "name": "name_2"}),
        ("2", {"page_size": 1, "user_code": "name_2"}),
        ("3", {"page_size": 1, "short_name": "name_2"}),
        ("4", {"page_size": 1, "public_name": "name_2"}),
    )
    @mock.patch("poms.common.database_client.DatabaseService.get_results")
    def test__data_ready(self, params, mock_get_results):
        test_data = deepcopy(CURRENCY_DATA)
        mock_get_results.return_value = Monad(
            status=MonadStatus.DATA_READY,
            data=test_data,
        )
        response = self.client.get(path=self.url, data=params)
        self.assertEqual(response.status_code, 200, response.content)

        response_data = response.json()
        self.assertEqual(response_data["count"], 3)
        self.assertEqual(len(response_data["results"]), 3)

    @BaseTestCase.cases(
        ("1", {"name": "name_2"}),
        ("2", {"user_code": "name_2"}),
        ("3", {"short_name": "name_2"}),
        ("4", {"public_name": "name_2"}),
    )
    @mock.patch("poms.common.database_client.DatabaseService.get_results")
    def test__error(self, params, mock_get_results):
        message = self.random_string()
        mock_get_results.return_value = Monad(
            status=MonadStatus.ERROR,
            message=message,
        )

        response = self.client.get(path=self.url, data=params)
        self.assertEqual(response.status_code, 200, response.content)

        data = response.json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(len(data["results"]), 0)
