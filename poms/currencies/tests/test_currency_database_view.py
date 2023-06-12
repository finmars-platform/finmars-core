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
            "numeric_code": "971",
        },
        {
            "id": 2,
            "name": "Lek",
            "user_code": "ALL",
            "code": "ALL",
            "numeric_code": "008",
        },
        {
            "id": 3,
            "name": "Kwanza",
            "user_code": "AOA",
            "code": "AOA",
            "numeric_code": "973",
        },
    ],
}


class CurrencyDatabaseSearchViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = (
            f"/{settings.BASE_API_URL}/api/v1/currencies/currency-database-search"
        )

    @BaseTestCase.cases(
        ("no_name", {"page_size": 200}),
        ("empty_name", {"page_size": 500, "name": ""}),
    )
    @mock.patch("poms.common.database_client.DatabaseService.get_results")
    def test__empty_name_results_in_full_list(self, params, mock_get_results):
        test_data = deepcopy(CURRENCY_DATA)
        test_data["results"] = CURRENCY_DATA["results"] * 100
        expected_len = len(test_data["results"])
        mock_get_results.return_value = Monad(
            status=MonadStatus.DATA_READY,
            data=test_data,
        )

        response = self.client.get(self.url, data=params)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertIsNone(data["next"])
        self.assertIsNone(data["previous"])
        self.assertEqual(data["count"], expected_len)
        self.assertEqual(len(data["results"]), expected_len)

    @BaseTestCase.cases(
        ("1", {"name": "Afgh"}),
        ("2", {"code": "AFN"}),
        ("3", {"user_code": "ALL"}),
        ("4", {"numeric_code": "973"}),
        ("5", {"name": "AFN"}),
        ("6", {"name": "ALL"}),
        ("7", {"name": "973"}),
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
        self.assertEqual(response_data["count"], 1)
        self.assertEqual(len(response_data["results"]), 1)

    @BaseTestCase.cases(
        ("1", {"name": "Afgh"}),
        ("2", {"code": "AFN"}),
        ("3", {"user_code": "ALL"}),
        ("4", {"numeric_code": "973"}),
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
