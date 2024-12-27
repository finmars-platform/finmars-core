from poms.common.common_base_test import BIG, BaseTestCase, SMALL
from poms.portfolios.models import PortfolioReconcileGroup, PortfolioReconcileHistory
from poms.configuration.utils import get_default_configuration_code


class PortfolioReconcileHistoryViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-reconcile-history/"
        self.portfolio_1 = self.db_data.portfolios[BIG]
        self.portfolio_2 = self.db_data.portfolios[SMALL]

    def create_reconcile_group(self) -> PortfolioReconcileGroup:
        return PortfolioReconcileGroup.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=get_default_configuration_code(),
            name=self.random_string(),
            report_params={
                "precision": 1,
                "only_errors": False,
            }
        )

    def create_data(self) -> dict:
        user_code = get_default_configuration_code()
        name = self.random_string()
        return {
            "name": name,
            "user_code": user_code,
            "date": self.today().strftime("%Y-%m-%d"),
            "portfolio_reconcile_group": self.create_reconcile_group().id,
        }

    def test_check_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test_simple_create(self):
        create_data = self.create_data()
        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        history_data = response.json()
        self.assertEqual(history_data["user_code"], create_data["user_code"])
        self.assertEqual(history_data["portfolio_reconcile_group"], create_data["portfolio_reconcile_group"])
        self.assertEqual(history_data["date"], create_data["date"])

        history = PortfolioReconcileHistory.objects.filter(user_code=create_data["user_code"]).first()
        self.assertIsNotNone(history)
        self.assertIsNotNone(history.id, history_data["id"])

    def test_update_patch(self):
        create_data = self.create_data()
        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        history_data = response.json()
        patch_data = {
            "date": self.yesterday().strftime("%Y-%m-%d"),
        }
        response = self.client.patch(f"{self.url}{history_data['id']}/", data=patch_data, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        new_history_data = response.json()

        self.assertEqual(new_history_data["date"], self.yesterday().strftime("%Y-%m-%d"))

    def test_delete(self):
        create_data = self.create_data()
        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        history_data = response.json()

        response = self.client.delete(f"{self.url}{history_data['id']}/")
        self.assertEqual(response.status_code, 204, response.content)

        history = PortfolioReconcileHistory.objects.filter(id=history_data["id"]).first()
        self.assertIsNone(history)

    def test_validation_error(self):
        create_data = self.create_data()
        create_data["portfolio_reconcile_group"] = self.random_int(100000, 3000000)
        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)
