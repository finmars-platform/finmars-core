from copy import deepcopy

from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import Instrument, PriceHistory, PricingPolicy
from poms.pricing.models import CurrencyPricingScheme, InstrumentPricingScheme

EXPECTED_PRICE_HISTORY = {
    "id": 1,
    "instrument": 4,
    "instrument_object": {
        "id": 4,
        "instrument_type": 4,
        "instrument_type_object": {
            "id": 4,
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
        "user_code": "-",
        "name": "-",
        "short_name": "-",
        "public_name": None,
        "notes": None,
        "is_active": True,
        "is_deleted": False,
        "has_linked_with_portfolio": False,
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
    "pricing_policy": 5,
    "pricing_policy_object": {
        "id": 5,
        "user_code": "local.poms.space00000:hosor",
        "configuration_code": "local.poms.space00000",
        "name": "CCSDLHNCDKE",
        "short_name": "VM",
        "notes": None,
        "expr": "",
        "default_instrument_pricing_scheme": 2,
        "default_currency_pricing_scheme": 2,
        "deleted_user_code": None,
        "default_instrument_pricing_scheme_object": {
            "id": 2,
            "name": "-",
            "user_code": "local.poms.space00000:_",
            "configuration_code": "local.poms.space00000",
            "notes": "",
            "notes_for_users": "",
            "notes_for_parameter": "",
            "error_handler": 1,
            "type": 1,
            "type_settings": {},
            "type_object": {"id": 1, "name": "Skip", "notes": "", "input_type": 1},
            "meta": {
                "content_type": "pricing.instrumentpricingscheme",
                "app_label": "pricing",
                "model_name": "instrumentpricingscheme",
                "space_code": "space00000",
            },
        },
        "default_currency_pricing_scheme_object": {
            "id": 2,
            "name": "-",
            "user_code": "local.poms.space00000:_",
            "configuration_code": "local.poms.space00000",
            "notes": "",
            "notes_for_users": "",
            "notes_for_parameter": "",
            "error_handler": 1,
            "type": 1,
            "type_settings": {},
            "type_object": {"id": 1, "name": "Skip", "notes": "", "input_type": 1},
            "meta": {
                "content_type": "pricing.currencypricingscheme",
                "app_label": "pricing",
                "model_name": "currencypricingscheme",
                "space_code": "space00000",
            },
        },
        "meta": {
            "content_type": "instruments.pricingpolicy",
            "app_label": "instruments",
            "model_name": "pricingpolicy",
            "space_code": "space00000",
        },
    },
    "date": "2023-07-19",
    "principal_price": 1302.0,
    "accrued_price": 4037.0,
    "procedure_modified_datetime": "2023-07-19T00:00:00Z",
    "nav": 1.0,
    "cash_flow": 2.0,
    "factor": 1.0,
    "long_delta": 1558.0,
    "short_delta": 2968.0,
    "is_temporary_price": False,
    "ytm": 3.0,
    "modified_duration": 3.0,
    "meta": {
        "content_type": "instruments.pricehistory",
        "app_label": "instruments",
        "model_name": "pricehistory",
        "space_code": "space00000",
    },
}

CREATE_DATA = {
    "instrument": 4,
    "pricing_policy": 5,
    "principal_price": 1302.0,
    "accrued_price": 4037.0,
    "nav": 12.0,
    "cash_flow": 11.0,
    "factor": 1.0,
    "long_delta": 1558.0,
    "short_delta": 2968.0,
    "is_temporary_price": False,
    # "ytm": 0 - calculated value
}


class PriceHistoryViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/instruments/price-history/"
        self.pricing_policy = None
        self.pricing_history = None
        self.instrument = Instrument.objects.first()
        self.instrument_pricing_schema = InstrumentPricingScheme.objects.first()
        self.instrument_currency_schema = CurrencyPricingScheme.objects.first()

    def create_pricing_policy(self) -> PricingPolicy:
        self.pricing_policy = PricingPolicy.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(5),
            short_name=self.random_string(2),
            name=self.random_string(11),
            default_instrument_pricing_scheme=self.instrument_pricing_schema,
            default_currency_pricing_scheme=self.instrument_currency_schema,
        )
        return self.pricing_policy

    def create_pricing_history(self) -> PriceHistory:
        self.pricing_history = PriceHistory.objects.create(
            instrument=self.instrument,
            pricing_policy=self.create_pricing_policy(),
            principal_price=self.random_int(),
            accrued_price=self.random_int(),
            long_delta=self.random_int(),
            short_delta=self.random_int(),
        )
        return self.pricing_history

    def prepare_data_for_create(self) -> dict:
        create_data = deepcopy(CREATE_DATA)
        create_data["instrument"] = self.instrument.id
        pricing_policy = self.create_pricing_policy()
        create_data["pricing_policy"] = pricing_policy.id

        return create_data

    def test__check_api_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test__create_and_retrieve(self):
        pricing_history = self.create_pricing_history()
        response = self.client.get(path=f"{self.url}{pricing_history.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        # check fields
        self.assertEqual(response_json.keys(), EXPECTED_PRICE_HISTORY.keys())

        # check values
        self.assertEqual(
            response_json["principal_price"], pricing_history.principal_price
        )
        self.assertEqual(response_json["accrued_price"], pricing_history.accrued_price)

    def test__list_attributes(self):
        response = self.client.get(path=f"{self.url}attributes/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 12)

    def test__get_filters(self):  # sourcery skip: extract-duplicate-method
        pricing_history = self.create_pricing_history()
        response = self.client.get(
            path=f"{self.url}?instrument={pricing_history.instrument.id}"
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["instrument"],
            pricing_history.instrument.id,
        )

        response = self.client.get(
            path=f"{self.url}?principal_price={pricing_history.principal_price}"
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["principal_price"],
            pricing_history.principal_price,
        )

    def test__create(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)

        response_json = response.json()

        price_history_id = response_json["id"]
        price_history = PriceHistory.objects.get(id=price_history_id)
        self.assertEqual(price_history.principal_price, create_data["principal_price"])

    def test__bulk_create(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(
            path=f"{self.url}bulk-create/",
            format="json",
            data=[create_data],
        )
        self.assertEqual(response.status_code, 201, response.content)

        price_history = PriceHistory.objects.filter(
            instrument=create_data["instrument"]
        )
        self.assertIsNotNone(price_history)

    def test__update_put(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        price_history_id = response_json["id"]
        new_principal = self.random_int()
        update_data = deepcopy(create_data)
        update_data["principal_price"] = new_principal
        response = self.client.put(
            path=f"{self.url}{price_history_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}{price_history_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["principal_price"], new_principal)

    def test__update_patch(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        price_history_id = response_json["id"]
        new_principal = self.random_int()
        update_data = {"principal_price": new_principal}
        response = self.client.patch(
            path=f"{self.url}{price_history_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}{price_history_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["principal_price"], new_principal)

    def test__delete(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        price_history_id = response_json["id"]

        response = self.client.delete(path=f"{self.url}{price_history_id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(path=f"{self.url}{price_history_id}/")
        self.assertEqual(response.status_code, 404, response.content)

    def test__create_with_null_accrued_price(self):
        create_data = self.prepare_data_for_create()
        create_data["accrued_price"] = None

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)

        response_json = response.json()
        self.assertIsNotNone(response_json["accrued_price"])

    def test__create_with_0_accrued_price(self):
        create_data = self.prepare_data_for_create()
        create_data["accrued_price"] = 0

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)

        response_json = response.json()
        self.assertEqual(response_json["accrued_price"], 0)

    def test__create_without_date_error(self):
        create_data = self.prepare_data_for_create()
        create_data["accrued_price"] = None
        create_data["date"] = None

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 400, response.content)
