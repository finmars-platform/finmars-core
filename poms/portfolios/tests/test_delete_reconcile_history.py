from poms.common.common_base_test import BIG, BaseTestCase, SMALL
from poms.portfolios.models import PortfolioReconcileGroup, PortfolioReconcileHistory
from poms.file_reports.models import FileReport


class DeleteReconcileHistoryTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
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
            },
        )

    def create_reconcile_history(self, group: PortfolioReconcileGroup) -> PortfolioReconcileHistory:
        return PortfolioReconcileHistory.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            date=self.random_future_date(),
            portfolio_reconcile_group=group,
        )

    def create_file_report(self) -> FileReport:
        return FileReport.objects.create(
            master_user=self.master_user,
            file_name=self.random_string(),
        )

    def test__delete_no_file_report(self):
        group = self.create_reconcile_group()
        group.portfolios.add(self.portfolio_1)
        group.portfolios.add(self.portfolio_2)
        history = self.create_reconcile_history(group)

        self.assertIsNotNone(PortfolioReconcileHistory.objects.filter(pk=history.pk).first())

        self.portfolio_1.destroy_reconcile_histories()

        self.assertIsNone(PortfolioReconcileHistory.objects.filter(pk=history.pk).first())

    def test__delete_with_file_report(self):
        group = self.create_reconcile_group()
        group.portfolios.add(self.portfolio_1)
        group.portfolios.add(self.portfolio_2)
        history = self.create_reconcile_history(group)
        file_report = self.create_file_report()
        history.file_report = file_report
        history.save()

        self.assertIsNotNone(PortfolioReconcileHistory.objects.filter(pk=history.pk).first())
        self.assertEqual(file_report.pk, history.file_report.pk)

        self.portfolio_1.destroy_reconcile_histories()

        self.assertIsNone(PortfolioReconcileHistory.objects.filter(pk=history.pk).first())
        self.assertIsNone(FileReport.objects.filter(pk=history.pk).first())
