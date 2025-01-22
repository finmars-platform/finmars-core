from unittest import mock

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

    def create_data(self) -> dict:
        user_code = get_default_configuration_code()
        name = self.random_string()
        return {
            "name": name,
            "user_code": user_code,
            "date": self.today().strftime("%Y-%m-%d"),
            "portfolio_reconcile_group": self.group.id,
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
        self.assertEqual(history_data["report_ttl"], 90)  # default value

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

    @mock.patch("poms.portfolios.tasks.calculate_portfolio_reconcile_history.apply_async")
    def test_calculate(self, apply_async):
        create_data = self.create_data()
        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        self.assertIsNone(self.group.last_calculated_at)
        history_data = response.json()

        calculate_data = {
            "portfolio_reconcile_group": history_data["user_code"],
            "date_from": self.yesterday().strftime("%Y-%m-%d"),
            "date_to": self.today().strftime("%Y-%m-%d"),
        }
        response = self.client.post(f"{self.url}calculate/", data=calculate_data, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        response_data = response.json()

        apply_async.assert_called()
        self.group.refresh_from_db()
        self.assertIsNotNone(self.group.last_calculated_at)
        self.assertEqual(response_data["task_options"]["portfolio_reconcile_group"], self.group.user_code)
        self.assertEqual(response_data["task_status"], "I")
