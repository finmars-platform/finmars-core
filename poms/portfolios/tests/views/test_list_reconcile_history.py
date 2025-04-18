from datetime import date

from poms.common.common_base_test import BaseTestCase
from poms.file_reports.models import FileReport
from poms.portfolios.models import PortfolioReconcileGroup, PortfolioReconcileHistory


class ListFilterReconcileHistoryTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-reconcile-history/"
        self.group = self.create_reconcile_group()
        self.history = self.create_reconcile_history(self.group, day=self.today())

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
            },
        )

    def create_file_report(self) -> FileReport:
        return FileReport.objects.create(
            master_user=self.master_user,
            file_name=self.random_string(),
        )

    def create_reconcile_history(self, group: PortfolioReconcileGroup, day: date) -> PortfolioReconcileHistory:
        return PortfolioReconcileHistory.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            portfolio_reconcile_group=group,
            date=day,
            file_report=self.create_file_report(),
        )

    def test__list(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertEqual(response_json["count"], 1)
        self.assertEqual(len(response_json["results"]), 1)

        history_data = response_json["results"][0]
        self.assertEqual(history_data["id"], self.history.id)
        self.assertIsInstance(history_data["portfolio_reconcile_group_object"], dict)
        self.assertIsInstance(history_data["file_report"], dict)

        print(history_data)

    def test__retrieve(self):
        response = self.client.get(path=f"{self.url}{self.history.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertEqual(response_json["id"], self.history.id)

    def test__filter_out_date_range_2(self):
        response = self.client.get(
            path=self.url, data={"date_after": str(self.yesterday()), "date_before": str(self.yesterday())}
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)

    def test__filter_out_date_range_1(self):
        response = self.client.get(path=self.url, data={"date_before": str(self.yesterday())})
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)

    def test__filter_out_date_range_0(self):
        response = self.client.get(path=self.url, data={"date_after": str(self.random_future_date())})
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)

    def test__filter_in_date_range(self):
        response = self.client.get(path=self.url, data={"date_after": str(self.yesterday())})
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)

    def test__filter_status_ok(self):
        response = self.client.get(path=self.url, data={"status": PortfolioReconcileHistory.STATUS_OK})
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)

    def test__filter_status_error(self):
        response = self.client.get(path=self.url, data={"status": PortfolioReconcileHistory.STATUS_ERROR})
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)

    def test__filter_wrong_user_code(self):
        response = self.client.get(path=self.url, data={"reconcile_group": "invalid_user_code"})
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)

    def test__filter_user_code(self):
        response = self.client.get(
            path=self.url, data={"reconcile_group": self.history.portfolio_reconcile_group.user_code}
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)

    def test__complex_filter_future(self):
        response = self.client.get(
            path=self.url,
            data={
                "reconcile_group": self.history.portfolio_reconcile_group.user_code,
                "date_after": str(self.random_future_date()),
            },
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)

    def test__complex_filter_past(self):
        response = self.client.get(
            path=self.url,
            data={
                "reconcile_group": self.history.portfolio_reconcile_group.user_code,
                "date_before": str(self.yesterday()),
            },
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)

    def test__complex_filter_now(self):
        response = self.client.get(
            path=self.url,
            data={
                "reconcile_group": self.history.portfolio_reconcile_group.user_code,
                "date_after": str(self.yesterday()),
                "date_before": str(self.random_future_date()),
            },
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
