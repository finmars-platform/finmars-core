from poms.common.common_base_test import BIG, BaseTestCase, SMALL
from poms.portfolios.models import PortfolioReconcileGroup, PortfolioReconcileHistory


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

    def test__delete_no_file_report(self):
        group = self.create_reconcile_group()
        group.portfolios.add(self.portfolio_1)
        group.portfolios.add(self.portfolio_2)
        history = self.create_reconcile_history(group)

        self.assertIsNotNone(PortfolioReconcileHistory.objects.filter(pk=history.pk).first())

        self.portfolio_1.destroy_reconcile_histories()

        self.assertIsNone(PortfolioReconcileHistory.objects.filter(pk=history.pk).first())
