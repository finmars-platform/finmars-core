from poms.common.common_base_test import BIG, BaseTestCase, SMALL
from poms.portfolios.models import Portfolio, PortfolioReconcileGroup, PortfolioReconcileHistory


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
            }
        )

    def create_reconcile_history(self, group: PortfolioReconcileGroup) -> PortfolioReconcileHistory:
        return PortfolioReconcileHistory.objects.create(
            master_user=self.master_user,
            user_code=self.random_string(),
            date=self.random_future_date(),
            portfolio_reconcile_group=group,
        )


    def test_check_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)
