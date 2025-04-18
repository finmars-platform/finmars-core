from poms.common.common_base_test import BaseTestCase
from poms.common.utils import db_class_check_data
from poms.instruments.models import AccrualCalculationModel

EXPECTED_RESPONSE = {
    "count": 21,
    "next": None,
    "previous": None,
    "results": [
        {"id": 1, "user_code": "NONE", "name": "none"},
        {
            "id": 2,
            "user_code": "DAY_COUNT_ACT_ACT_ICMA",
            "name": "Actual/Actual (ICMA)",
        },
        {
            "id": 3,
            "user_code": "DAY_COUNT_ACT_ACT_ISDA",
            "name": "Actual/Actual (ISDA)",
        },
        {"id": 4, "user_code": "DAY_COUNT_ACT_360", "name": "Actual/360"},
        {"id": 5, "user_code": "DAY_COUNT_ACT_365", "name": "Actual/365"},
        {"id": 7, "user_code": "DAY_COUNT_ACT_365L", "name": "Actual/365L"},
        {
            "id": 11,
            "user_code": "DAY_COUNT_30_360_ISDA",
            "name": "30/360 (30/360 ISDA)",
        },
        {"id": 14, "user_code": "DAY_COUNT_NL_365", "name": "NL/365"},
        {
            "id": 16,
            "user_code": "DAY_COUNT_30_360_ISMA",
            "name": "30/360 (30/360 ISMA)",
        },
        {"id": 18, "user_code": "DAY_COUNT_30_360_US", "name": "30/360 US"},
        {"id": 20, "user_code": "DAY_COUNT_BD_252", "name": "BD/252"},
        {"id": 21, "user_code": "DAY_COUNT_30_360_GERMAN", "name": "30/360 German"},
        {"id": 24, "user_code": "DAY_COUNT_30E_PLUS_360", "name": "30E+/360"},
        {"id": 26, "user_code": "DAY_COUNT_ACT_ACT_AFB", "name": "Actual/Actual (AFB)"},
        {
            "id": 27,
            "user_code": "DAY_COUNT_ACT_365_FIXED",
            "name": "Actual/365 (Actual/365F)",
        },
        {"id": 28, "user_code": "DAY_COUNT_30E_360", "name": "30E/360"},
        {"id": 29, "user_code": "DAY_COUNT_ACT_365A", "name": "Actual/365A"},
        {"id": 30, "user_code": "DAY_COUNT_ACT_366", "name": "Actual/366"},
        {"id": 31, "user_code": "DAY_COUNT_ACT_364", "name": "Actual/364"},
        {"id": 32, "user_code": "DAY_COUNT_30_365", "name": "30/365"},
        {"id": 100, "user_code": "DAY_COUNT_SIMPLE", "name": "Simple"},
    ],
    "meta": {
        "execution_time": 21,
        "request_id": "c608093a-510a-4fb9-9415-2fbac65a45ad",
    },
}


class DayTimeConventionTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/instruments/day-time-convention/"

        db_class_check_data(AccrualCalculationModel, 2, "default")

    def test__test_list(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        results = response_json["results"]
        self.assertEqual(len(results), 21, results)

    @BaseTestCase.cases(
        ("2", 2),
        ("3", 3),
        ("4", 4),
        ("5", 5),
        ("7", 7),
        ("21", 21),
        ("30", 30),
        ("100", 100),
    )
    def test__test_retrieve(self, item_id):
        response = self.client.get(path=f"{self.url}{item_id}/")
        self.assertEqual(response.status_code, 200, response.content)
