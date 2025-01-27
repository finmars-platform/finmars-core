from poms.common.common_base_test import BIG, BaseTestCase, SMALL
from poms.portfolios.models import PortfolioReconcileGroup, PortfolioReconcileHistory
from poms.configuration.utils import get_default_configuration_code


class PortfolioReconcileHistoryViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-reconcile-history/status/"
        self.portfolio_1 = self.db_data.portfolios[BIG]
        self.portfolio_2 = self.db_data.portfolios[SMALL]
        self.group = self.create_reconcile_group()

    def create_reconcile_group(self) -> PortfolioReconcileGroup:
        return PortfolioReconcileGroup.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=get_default_configuration_code(),
            name=self.random_string(),
            params={
                "precision": 1,
                "only_errors": False,
            }
        )


    def test_check_url(self):
        portfolios = {"portfolios": [self.portfolio_1.id, self.portfolio_2.id]}
        response = self.client.get(path=self.url, data=portfolios)
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        print(response_json)
