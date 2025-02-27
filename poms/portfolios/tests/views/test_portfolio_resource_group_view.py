from poms.common.common_base_test import BaseTestCase
from poms.iam.models import ResourceGroup
from poms.portfolios.models import Portfolio
from poms.users.models import Member


class PortfolioViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio/"
        self.portfolio = Portfolio.objects.last()
        self.user_code = self.random_string()
        self.portfolio.user_code = self.user_code
        self.portfolio.save()
        self.db_data.create_portfolio_register(
            self.portfolio,
            self.db_data.default_instrument,
            self.user_code,
        )

    def create_group(self, name: str = "test") -> ResourceGroup:
        return ResourceGroup.objects.create(
            name=name,
            user_code=name,
            description=name,
            configuration_code=name,
            owner=Member.objects.all().first(),
        )

    def test_add_resource_group(self):
        rg_name = self.random_string()
        rg = self.create_group(name=rg_name)
        response = self.client.patch(
            f"{self.url}{self.portfolio.id}/",
            data={"resource_groups": [rg_name]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        portfolio_data = response.json()
        self.assertIn("resource_groups", portfolio_data)
        self.assertEqual(portfolio_data["resource_groups"], [rg_name])

        self.assertIn("resource_groups_object", portfolio_data)
        resource_group = portfolio_data["resource_groups_object"][0]
        self.assertEqual(resource_group["name"], rg.name)
        self.assertEqual(resource_group["id"], rg.id)
        self.assertEqual(resource_group["user_code"], rg.user_code)
        self.assertEqual(resource_group["description"], rg.description)
        self.assertNotIn("assignments", resource_group)

    def test_update_resource_groups(self):
        name_1 = self.random_string()
        self.create_group(name=name_1)
        name_2 = self.random_string()
        self.create_group(name=name_2)
        name_3 = self.random_string()
        self.create_group(name=name_3)

        response = self.client.patch(
            f"{self.url}{self.portfolio.id}/",
            data={"resource_groups": [name_1, name_2, name_3]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        portfolio_data = response.json()
        self.assertEqual(len(portfolio_data["resource_groups"]), 3)
        self.assertEqual(len(portfolio_data["resource_groups_object"]), 3)

        response = self.client.patch(
            f"{self.url}{self.portfolio.id}/",
            data={"resource_groups": [name_2]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        portfolio_data = response.json()
        self.assertEqual(len(portfolio_data["resource_groups"]), 1)
        self.assertEqual(portfolio_data["resource_groups"], [name_2])

        self.assertEqual(len(portfolio_data["resource_groups_object"]), 1)

    def test_remove_resource_groups(self):
        name_1 = self.random_string()
        self.create_group(name=name_1)
        name_3 = self.random_string()
        self.create_group(name=name_3)

        response = self.client.patch(
            f"{self.url}{self.portfolio.id}/",
            data={"resource_groups": [name_1, name_3]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        portfolio_data = response.json()
        self.assertEqual(len(portfolio_data["resource_groups"]), 2)
        self.assertEqual(len(portfolio_data["resource_groups_object"]), 2)

        response = self.client.patch(
            f"{self.url}{self.portfolio.id}/",
            data={"resource_groups": []},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        portfolio_data = response.json()
        self.assertEqual(len(portfolio_data["resource_groups"]), 0)
        self.assertEqual(portfolio_data["resource_groups"], [])

        self.assertEqual(len(portfolio_data["resource_groups_object"]), 0)
        self.assertEqual(portfolio_data["resource_groups_object"], [])

    def test_destroy_assignments(self):
        name_1 = self.random_string()
        rg_1 = self.create_group(name=name_1)
        name_3 = self.random_string()
        rg_3 = self.create_group(name=name_3)

        response = self.client.patch(
            f"{self.url}{self.portfolio.id}/",
            data={"resource_groups": [name_1, name_3]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        portfolio_data = response.json()
        self.assertEqual(len(portfolio_data["resource_groups"]), 2)
        self.assertEqual(len(portfolio_data["resource_groups_object"]), 2)

        url = f"/{self.realm_code}/{self.space_code}/api/v1/iam/resource-group/"
        response = self.client.delete(f"{url}{rg_1.id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.delete(f"{url}{rg_3.id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(f"{self.url}{self.portfolio.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        portfolio_data = response.json()
        self.assertEqual(len(portfolio_data["resource_groups"]), 0)
        self.assertEqual(portfolio_data["resource_groups"], [])

    def test_update_client(self):
        client = self.create_client_obj()

        response = self.client.patch(
            f"{self.url}{self.portfolio.id}/",
            data={"client": client.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        portfolio_data = response.json()
        self.assertEqual(portfolio_data["client"], client.pk)
        self.assertEqual(portfolio_data["client_object"]["user_code"], client.user_code)
