from poms.common.common_base_test import BaseTestCase
from poms.expressions_engine import formula
from poms.iam.models import ResourceGroup
from poms.portfolios.models import Portfolio

PORTFOLIO_DATA_SHORT = {
    "id": 3,
    "user_code": "Small",
    "name": "Small",
    "short_name": "Small",
    "public_name": None,
    "notes": None,
    "is_deleted": False,
    "is_enabled": True,
    "registers": [],
    "deleted_user_code": None,
    "attributes": [],
    "accounts_object": [
        {
            "id": 3,
            "type": None,
            "type_object": None,
            "user_code": "Small",
            "name": "Small",
            "short_name": "Small",
            "public_name": None,
            "deleted_user_code": None,
            "meta": {
                "content_type": "accounts.account",
                "app_label": "accounts",
                "model_name": "account",
                "space_code": "space00000",
            },
        }
    ],
    "responsibles_object": [],
    "counterparties_object": [],
    "transaction_types_object": [],
    "meta": {
        "content_type": "portfolios.portfolio",
        "app_label": "portfolios",
        "model_name": "portfolio",
        "space_code": "space00000",
    },
}


PORTFOLIO_DATA_FULL = {
    "id": 4,
    "user_code": "Small",
    "name": "Small",
    "short_name": "Small",
    "public_name": None,
    "notes": None,
    "is_deleted": False,
    "is_enabled": True,
    "registers": [
        {
            "id": 1,
            "user_code": "Small",
            "name": "Small",
            "short_name": "Small",
            "public_name": None,
            "notes": None,
            "is_deleted": False,
            "is_enabled": True,
            "linked_instrument": 4,
            "linked_instrument_object": {
                "id": 4,
                "instrument_type": 1,
                "instrument_type_object": {
                    "id": 1,
                    "instrument_class": 1,
                    "instrument_class_object": {
                        "id": 1,
                        "user_code": "GENERAL",
                        "name": "General Class",
                        "description": "General Class",
                    },
                    "user_code": "local.poms.space00000:_",
                    "name": "-",
                    "short_name": "-",
                    "public_name": None,
                    "instrument_form_layouts": None,
                    "deleted_user_code": None,
                    "meta": {
                        "content_type": "instruments.instrumenttype",
                        "app_label": "instruments",
                        "model_name": "instrumenttype",
                        "space_code": "space00000",
                    },
                },
                "user_code": "QVNFLWQKSF",
                "name": "Small",
                "short_name": "Small",
                "public_name": None,
                "notes": None,
                "is_active": True,
                "is_deleted": False,
                "has_linked_with_portfolio": True,
                "user_text_1": None,
                "user_text_2": None,
                "user_text_3": None,
                "maturity_date": None,
                "deleted_user_code": None,
                "meta": {
                    "content_type": "instruments.instrument",
                    "app_label": "instruments",
                    "model_name": "instrument",
                    "space_code": "space00000",
                },
            },
            "valuation_currency": 1,
            "valuation_currency_object": {
                "id": 1,
                "user_code": "-",
                "name": "-",
                "short_name": "-",
                "deleted_user_code": None,
                "meta": {
                    "content_type": "currencies.currency",
                    "app_label": "currencies",
                    "model_name": "currency",
                    "space_code": "space00000",
                },
            },
            "valuation_pricing_policy": 1,
            "valuation_pricing_policy_object": {
                "id": 1,
                "user_code": "local.poms.space00000:_",
                "configuration_code": "local.poms.space00000",
                "name": "-",
                "short_name": "-",
                "notes": None,
                "expr": "(ask+bid)/2",
                "default_instrument_pricing_scheme": None,
                "default_currency_pricing_scheme": None,
                "deleted_user_code": None,
                "default_instrument_pricing_scheme_object": None,
                "default_currency_pricing_scheme_object": None,
                "meta": {
                    "content_type": "instruments.pricingpolicy",
                    "app_label": "instruments",
                    "model_name": "pricingpolicy",
                    "space_code": "space00000",
                },
            },
            "default_price": 1.0,
            "deleted_user_code": None,
            "attributes": [],
            "meta": {
                "content_type": "portfolios.portfolioregister",
                "app_label": "portfolios",
                "model_name": "portfolioregister",
                "space_code": "space00000",
            },
        }
    ],
    "deleted_user_code": None,
    "attributes": [],
    "accounts_object": [],
    "responsibles_object": [],
    "counterparties_object": [],
    "transaction_types_object": [],
    "meta": {
        "content_type": "portfolios.portfolio",
        "app_label": "portfolios",
        "model_name": "portfolio",
        "space_code": "space00000",
    },
}


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

    def test_formula(self):
        # test user_code generated
        n1 = formula.safe_eval(
            'generate_user_code("del", "", 0)',
            context={"master_user": self.master_user},
        )
        n2 = formula.safe_eval(
            'generate_user_code("del", "", 0)',
            context={"master_user": self.master_user},
        )
        n3 = formula.safe_eval(
            'generate_user_code("del", "", 0)',
            context={"master_user": self.master_user},
        )
        self.assertEqual(n1, "del00000000000000001")
        self.assertEqual(n2, "del00000000000000002")
        self.assertEqual(n3, "del00000000000000003")

    def test_retrieve(self):
        response = self.client.get(f"{self.url}{self.portfolio.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json["user_code"], self.user_code)
        self.assertFalse(response_json["is_deleted"])
        self.assertIn("resource_groups", response_json)
        self.assertEqual(response_json["resource_groups"], [])
        self.assertEqual(response_json["resource_groups_object"], [])

    def test_destroy(self):
        response = self.client.delete(f"{self.url}{self.portfolio.id}/", format="json")
        self.assertEqual(response.status_code, 204, response.content)

        # test that Portfolio object is not deleted

        self.portfolio.refresh_from_db()
        self.assertTrue(self.portfolio.is_deleted)
        self.assertEqual(self.portfolio.user_code, "del00000000000000001")

    def test_retrieve_destroy(self):
        response = self.client.get(f"{self.url}{self.portfolio.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        portfolio_data = response.json()

        id_0 = portfolio_data.pop("id")
        portfolio_data.pop("meta")

        response = self.client.delete(f"{self.url}{id_0}/", format="json")
        self.assertEqual(response.status_code, 204, response.content)

    def create_group(self, name: str = "test") -> ResourceGroup:
        return ResourceGroup.objects.create(
            name=name,
            user_code=name,
            description=name,
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
