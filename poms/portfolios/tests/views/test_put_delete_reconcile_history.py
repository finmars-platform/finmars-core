from datetime import date

from poms.common.common_base_test import BaseTestCase
from poms.file_reports.models import FileReport
from poms.portfolios.models import PortfolioReconcileGroup, PortfolioReconcileHistory


class DummyUpdateAndDeleteReconcileHistoryTest(BaseTestCase):
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

    def test__put(self):
        response = self.client.put(path=f"{self.url}{self.history.id}/", data={}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertEqual(response_json["id"], self.history.id)
        self.assertEqual(response_json["user_code"], self.history.user_code)

    def test__destroy(self):
        file_report_id = self.history.file_report_id
        response = self.client.delete(path=f"{self.url}{self.history.id}/")
        self.assertEqual(response.status_code, 204, response.content)

        history = PortfolioReconcileHistory.objects.filter(id=self.history.id).first()
        self.assertIsNone(history)
        file_report = FileReport.objects.filter(id=file_report_id).first()
        self.assertIsNone(file_report)
