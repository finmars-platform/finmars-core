from poms.common.common_base_test import BaseTestCase
from poms.portfolios.models import Portfolio

# Portfolio JSON format:
# {
#     "accounts_object": [
#         {
#             "deleted_user_code": None,
#             "id": 6,
#             "meta": {
#                 "app_label": "accounts",
#                 "content_type": "accounts.account",
#                 "model_name": "account",
#                 "realm_code": "realm0000",
#                 "space_code": "space0000",
#             },
#             "name": "Small",
#             "owner": {"id": 2, "username": "finmars_bot"},
#             "public_name": None,
#             "short_name": "Small",
#             "type": None,
#             "type_object": None,
#             "user_code": "Small",
#         }
#     ],
#     "actual_at": None,
#     "attributes": [],
#     "client": None,
#     "client_object": None,
#     "counterparties_object": [],
#     "created_at": "2025-02-27T18:27:54.832696Z",
#     "deleted_at": None,
#     "deleted_user_code": None,
#     "external_id": None,
#     "first_cash_flow_date": None,
#     "first_transaction": {"date": None, "date_field": "accounting_date"},
#     "first_transaction_date": None,
#     "id": 4,
#     "is_active": True,
#     "is_deleted": False,
#     "is_enabled": True,
#     "is_locked": True,
#     "is_manual_locked": False,
#     "meta": {
#         "app_label": "portfolios",
#         "content_type": "portfolios.portfolio",
#         "model_name": "portfolio",
#         "realm_code": "realm0000",
#         "space_code": "space0000",
#     },
#     "modified_at": "2025-02-27T18:27:54.887412Z",
#     "name": "Small",
#     "notes": None,
#     "owner": {"id": 2, "username": "finmars_bot"},
#     "portfolio_type": None,
#     "portfolio_type_object": None,
#     "public_name": None,
#     "registers": [
#         {
#             "actual_at": None,
#             "attributes": [],
#             "created_at": "2025-02-27T18:27:54.889170Z",
#             "default_price": 1.0,
#             "deleted_at": None,
#             "deleted_user_code": None,
#             "external_id": None,
#             "id": 6,
#             "is_active": True,
#             "is_deleted": False,
#             "is_enabled": True,
#             "is_locked": True,
#             "is_manual_locked": False,
#             "linked_instrument": 4,
#             "linked_instrument_object": {
#                 "deleted_user_code": None,
#                 "has_linked_with_portfolio": True,
#                 "id": 4,
#                 "identifier": {},
#                 "instrument_type": 6,
#                 "instrument_type_object": {
#                     "deleted_user_code": None,
#                     "id": 6,
#                     "instrument_class": 1,
#                     "instrument_class_object": {
#                         "description": "General " "Class",
#                         "id": 1,
#                         "name": "General " "Class",
#                         "user_code": "GENERAL",
#                     },
#                     "instrument_form_layouts": None,
#                     "meta": {
#                         "app_label": "instruments",
#                         "content_type": "instruments.instrumenttype",
#                         "model_name": "instrumenttype",
#                         "realm_code": "realm0000",
#                         "space_code": "space0000",
#                     },
#                     "name": "-",
#                     "owner": {"id": 2, "username": "finmars_bot"},
#                     "public_name": "-",
#                     "short_name": "-",
#                     "user_code": "local.poms.space00000",
#                 },
#                 "is_active": True,
#                 "is_deleted": False,
#                 "maturity_date": "2046-09-25",
#                 "meta": {
#                     "app_label": "instruments",
#                     "content_type": "instruments.instrument",
#                     "model_name": "instrument",
#                     "realm_code": "realm0000",
#                     "space_code": "space0000",
#                 },
#                 "name": "-",
#                 "notes": None,
#                 "owner": {"id": 2, "username": "finmars_bot"},
#                 "public_name": "-",
#                 "short_name": "-",
#                 "user_code": "-",
#                 "user_text_1": None,
#                 "user_text_2": None,
#                 "user_text_3": None,
#             },
#             "meta": {
#                 "app_label": "portfolios",
#                 "content_type": "portfolios.portfolioregister",
#                 "model_name": "portfolioregister",
#                 "realm_code": "realm0000",
#                 "space_code": "space0000",
#             },
#             "modified_at": "2025-02-27T18:27:54.889174Z",
#             "name": "AEUHAMEJZZ",
#             "notes": None,
#             "owner": {"id": 2, "username": "finmars_bot"},
#             "public_name": None,
#             "short_name": "AEUHAMEJZZ",
#             "source_origin": "manual",
#             "source_type": "manual",
#             "user_code": "AEUHAMEJZZ",
#             "valuation_currency": 3,
#             "valuation_currency_object": {
#                 "deleted_user_code": None,
#                 "id": 3,
#                 "meta": {
#                     "app_label": "currencies",
#                     "content_type": "currencies.currency",
#                     "model_name": "currency",
#                     "realm_code": "realm0000",
#                     "space_code": "space0000",
#                 },
#                 "name": "USD",
#                 "owner": {"id": 2, "username": "finmars_bot"},
#                 "public_name": "USD",
#                 "short_name": "USD",
#                 "user_code": "USD",
#             },
#             "valuation_pricing_policy": None,
#             "valuation_pricing_policy_object": None,
#         },
#         {
#             "actual_at": None,
#             "attributes": [],
#             "created_at": "2025-02-27T18:27:54.839111Z",
#             "default_price": 1.0,
#             "deleted_at": None,
#             "deleted_user_code": None,
#             "external_id": None,
#             "id": 5,
#             "is_active": True,
#             "is_deleted": False,
#             "is_enabled": True,
#             "is_locked": True,
#             "is_manual_locked": False,
#             "linked_instrument": 4,
#             "linked_instrument_object": {
#                 "deleted_user_code": None,
#                 "has_linked_with_portfolio": True,
#                 "id": 4,
#                 "identifier": {},
#                 "instrument_type": 6,
#                 "instrument_type_object": {
#                     "deleted_user_code": None,
#                     "id": 6,
#                     "instrument_class": 1,
#                     "instrument_class_object": {
#                         "description": "General " "Class",
#                         "id": 1,
#                         "name": "General " "Class",
#                         "user_code": "GENERAL",
#                     },
#                     "instrument_form_layouts": None,
#                     "meta": {
#                         "app_label": "instruments",
#                         "content_type": "instruments.instrumenttype",
#                         "model_name": "instrumenttype",
#                         "realm_code": "realm0000",
#                         "space_code": "space0000",
#                     },
#                     "name": "-",
#                     "owner": {"id": 2, "username": "finmars_bot"},
#                     "public_name": "-",
#                     "short_name": "-",
#                     "user_code": "local.poms.space00000",
#                 },
#                 "is_active": True,
#                 "is_deleted": False,
#                 "maturity_date": "2046-09-25",
#                 "meta": {
#                     "app_label": "instruments",
#                     "content_type": "instruments.instrument",
#                     "model_name": "instrument",
#                     "realm_code": "realm0000",
#                     "space_code": "space0000",
#                 },
#                 "name": "-",
#                 "notes": None,
#                 "owner": {"id": 2, "username": "finmars_bot"},
#                 "public_name": "-",
#                 "short_name": "-",
#                 "user_code": "-",
#                 "user_text_1": None,
#                 "user_text_2": None,
#                 "user_text_3": None,
#             },
#             "meta": {
#                 "app_label": "portfolios",
#                 "content_type": "portfolios.portfolioregister",
#                 "model_name": "portfolioregister",
#                 "realm_code": "realm0000",
#                 "space_code": "space0000",
#             },
#             "modified_at": "2025-02-27T18:27:54.839115Z",
#             "name": "Small",
#             "notes": None,
#             "owner": {"id": 2, "username": "finmars_bot"},
#             "public_name": None,
#             "short_name": "Small",
#             "source_origin": "manual",
#             "source_type": "manual",
#             "user_code": "Small",
#             "valuation_currency": 3,
#             "valuation_currency_object": {
#                 "deleted_user_code": None,
#                 "id": 3,
#                 "meta": {
#                     "app_label": "currencies",
#                     "content_type": "currencies.currency",
#                     "model_name": "currency",
#                     "realm_code": "realm0000",
#                     "space_code": "space0000",
#                 },
#                 "name": "USD",
#                 "owner": {"id": 2, "username": "finmars_bot"},
#                 "public_name": "USD",
#                 "short_name": "USD",
#                 "user_code": "USD",
#             },
#             "valuation_pricing_policy": None,
#             "valuation_pricing_policy_object": None,
#         },
#     ],
#     "resource_groups": [],
#     "resource_groups_object": [],
#     "responsibles_object": [],
#     "short_name": "Small",
#     "source_origin": "manual",
#     "source_type": "manual",
#     "transaction_types_object": [],
#     "user_code": "AEUHAMEJZZ",
# }


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

    def test_update(self):
        data={}
        response = self.client.patch(f"{self.url}{self.portfolio.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json["user_code"], self.user_code)
        self.assertFalse(response_json["is_deleted"])
        self.assertIn("resource_groups", response_json)
        self.assertEqual(response_json["resource_groups"], [])
        self.assertEqual(response_json["resource_groups_object"], [])
