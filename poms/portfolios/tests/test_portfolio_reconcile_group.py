from poms.common.common_base_test import BIG, BaseTestCase, SMALL
from poms.portfolios.models import PortfolioReconcileGroup, PortfolioType, PortfolioClass
from poms.configuration.utils import get_default_configuration_code


class PortfolioReconcileGroupViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-reconcile-group/"

        self.portfolio_1 = self.db_data.portfolios[BIG]
        self.general = PortfolioClass.objects.get(id=PortfolioClass.GENERAL)
        self.portfolio_1.portfolio_type = self.create_portfolio_type(self.general)
        self.portfolio_1.save()

        self.portfolio_2 = self.db_data.portfolios[SMALL]
        self.position = PortfolioClass.objects.get(id=PortfolioClass.POSITION)
        self.portfolio_2.portfolio_type = self.create_portfolio_type(self.position)
        self.portfolio_2.save()

    def create_portfolio_type(self, portfolio_class: PortfolioClass) -> PortfolioType:
        return PortfolioType.objects.create(
            master_user=self.master_user,
            owner=self.member,
            portfolio_class=portfolio_class,
            user_code=self.random_string(16),
        )

    def create_data(self) -> dict:
        user_code = get_default_configuration_code()
        name = self.random_string()
        return {
            "name": name,
            "user_code": user_code,
            "portfolios": [self.portfolio_1.id, self.portfolio_2.id],
            "params": {
                "precision": 1,
                "only_errors": False,
                "round_digits": 2,
                "emails": ["test@mail.com"],
            },
        }

    def test_check_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test_simple_create(self):
        create_data = self.create_data()
        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        group_data = response.json()
        self.assertEqual(group_data["name"], create_data["name"])
        self.assertEqual(group_data["user_code"], create_data["user_code"])
        self.assertIsNone(group_data["last_calculated_at"])
        params = group_data["params"]
        self.assertEqual(params["precision"], create_data["params"]["precision"])
        self.assertEqual(params["round_digits"], create_data["params"]["round_digits"])
        self.assertEqual(params["only_errors"], create_data["params"]["only_errors"])

        group = PortfolioReconcileGroup.objects.filter(id=group_data["id"]).first()
        self.assertIsNotNone(group)

    def test_update_by_patch(self):
        create_data = self.create_data()
        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        group_data = response.json()
        group_id = group_data["id"]

        patch_data = {"params": {"only_errors": True}}
        response = self.client.patch(f"{self.url}{group_id}/", data=patch_data, format="json")
        self.assertEqual(response.status_code, 200, response.content)

    def test_try_update_portfolios(self):
        create_data = self.create_data()
        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        group_data = response.json()
        group_id = group_data["id"]
        patch_data = {
            "portfolios": [self.portfolio_1.id, self.portfolio_2.id],
        }
        response = self.client.patch(f"{self.url}{group_id}/", data=patch_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)

    def test_delete(self):
        create_data = self.create_data()
        create_data.pop("portfolios")
        group = PortfolioReconcileGroup.objects.create(
            master_user=self.master_user,
            owner=self.member,
            **create_data,
        )
        response = self.client.delete(f"{self.url}{group.id}/")
        self.assertEqual(response.status_code, 204, response.content)

        group = PortfolioReconcileGroup.objects.filter(id=group.id).first()
        self.assertIsNotNone(group)
        self.assertTrue(group.is_deleted)

    def test_precision_validation_error(self):
        create_data = self.create_data()
        create_data["params"]["precision"] = -1

        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)

    def test_only_errors_validation_error(self):
        create_data = self.create_data()
        create_data["params"]["only_errors"] = -1

        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)

    @BaseTestCase.cases(
        ("int", 11111),
        ("url", "test/api/v1/portfolios/portfolio-reconcile-group/"),
        ("str", "dicembre"),
    )
    def test_create_with_invalid_emails(self, invalid_email):
        create_data = self.create_data()
        create_data["params"]["emails"] = [invalid_email]
        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)

    @BaseTestCase.cases(
        ("int", 11111),
        ("str", "dicembre"),
    )
    def test_create_with_invalid_notification(self, invalid_notification):
        create_data = self.create_data()
        create_data["params"]["notifications"] = [invalid_notification]
        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)

    def test_create_with_1_portfolio(self):
        create_data = self.create_data()
        create_data["portfolios"] = [self.portfolio_1.id]
        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)

    def test_create_with_duplicate_portfolio(self):
        create_data = self.create_data()
        create_data["portfolios"] += [self.portfolio_1.id]
        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)
