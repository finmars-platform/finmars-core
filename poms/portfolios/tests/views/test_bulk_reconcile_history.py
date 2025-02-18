from unittest import mock

from poms.common.common_base_test import BIG, BaseTestCase, SMALL
from poms.portfolios.models import PortfolioReconcileGroup


class BulkReconcileHistoryViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-reconcile-history/"
        self.portfolio_1 = self.db_data.portfolios[BIG]
        self.portfolio_2 = self.db_data.portfolios[SMALL]
        self.group = self.create_reconcile_group()

    def create_reconcile_group(self) -> PortfolioReconcileGroup:
        return PortfolioReconcileGroup.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            name=self.random_string(),
            params={
                "precision": 1,
                "only_errors": False,
                "report_ttl": 45,
                "round_digits": 2,
            }
        )

    def test_check_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test_calculate_invalid_group(self):
        calculate_data = {
            "reconcile_groups": [self.random_string()],
            "dates": [self.yesterday().strftime("%Y-%m-%d"), self.today().strftime("%Y-%m-%d")],
        }
        response = self.client.post(f"{self.url}bulk-calculate/", data=calculate_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)

    def test_no_groups(self):
        calculate_data = {
            "dates": [self.yesterday().strftime("%Y-%m-%d"), self.today().strftime("%Y-%m-%d")],
        }
        response = self.client.post(f"{self.url}bulk-calculate/", data=calculate_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)

    def test_empty_groups(self):
        calculate_data = {
            "reconcile_groups": [],
            "dates": [self.yesterday().strftime("%Y-%m-%d"), self.today().strftime("%Y-%m-%d")],
        }
        response = self.client.post(f"{self.url}bulk-calculate/", data=calculate_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)

    def test_calculate_empty_dates(self):
        calculate_data = {
            "reconcile_groups": [self.group.user_code],
            "dates": [],
        }
        response = self.client.post(f"{self.url}bulk-calculate/", data=calculate_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)

    def test_calculate_no_dates(self):
        calculate_data = {
            "reconcile_groups": [self.group.user_code],
        }
        response = self.client.post(f"{self.url}bulk-calculate/", data=calculate_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)

    @BaseTestCase.cases(
        ["0", "YYYY-MM-XX"],
        ["1", "2025-43-17"],
        ["2", "1234-12-37"],
        ["3", "12-12-12"],
    )
    def test_calculate_invalid_dates(self, invalid_date):
        calculate_data = {
            "reconcile_groups": [self.group.user_code],
            "dates": [invalid_date, self.today().strftime("%Y-%m-%d")],
        }
        response = self.client.post(f"{self.url}bulk-calculate/", data=calculate_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)

    @mock.patch("poms.portfolios.tasks.bulk_calculate_reconcile_history.apply_async")
    def test_bulk_calculate(self, apply_async):
        calculate_data = {
            "reconcile_groups": [self.group.user_code],
            "dates": [self.yesterday().strftime("%Y-%m-%d"), self.today().strftime("%Y-%m-%d")],
        }
        response = self.client.post(f"{self.url}bulk-calculate/", data=calculate_data, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        response_data = response.json()

        apply_async.assert_called()
        self.group.refresh_from_db()
        self.assertEqual(response_data["task_options"]["reconcile_groups"], [self.group.user_code])
        self.assertEqual(response_data["task_status"], "I")
