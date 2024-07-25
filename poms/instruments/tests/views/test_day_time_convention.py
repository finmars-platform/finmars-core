from poms.common.common_base_test import BaseTestCase
from poms.common.utils import db_class_check_data
from poms.instruments.models import AccrualCalculationModel


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
        print(response_json)

    @BaseTestCase.cases(
        ("1", 1),
        ("2", 2),
        ("3", 3),
        ("4", 4),
        ("5", 5),
        ("7", 7),
        ("30", 30),
        ("100", 100),
    )
    def test__test_retrieve(self, item_id):
        response = self.client.get(path=f"{self.url}{item_id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        print(response_json)
