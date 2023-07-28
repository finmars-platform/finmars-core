from copy import deepcopy

from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import InstrumentType

EXPECTED_INSTRUMENT_TYPE = {
    "id": 9,
    "user_code": "local.poms.space00000:bond",
    "name": "bond",
    "short_name": "bond",
    "public_name": "bond",
    "notes": None,
    "is_deleted": False,
    "instrument_form_layouts": None,
    "instrument_class": 1,
    "instrument_class_object": {
        "id": 1,
        "user_code": "GENERAL",
        "name": "General Class",
        "description": "General Class",
    },
    "one_off_event": None,
    "one_off_event_object": None,
    "regular_event": None,
    "regular_event_object": None,
    "factor_same": None,
    "factor_same_object": None,
    "factor_up": None,
    "factor_up_object": None,
    "factor_down": None,
    "factor_down_object": None,
    "is_enabled": True,
    "pricing_policies": [],
    "has_second_exposure_currency": False,
    "accruals": [],
    "events": [],
    "instrument_attributes": [],
    "instrument_factor_schedules": [],
    "payment_size_detail": None,
    "payment_size_detail_object": None,
    "accrued_currency": None,
    "accrued_currency_object": None,
    "accrued_multiplier": 1.0,
    "default_accrued": 0.0,
    "exposure_calculation_model": None,
    "co_directional_exposure_currency": None,
    "counter_directional_exposure_currency": None,
    "co_directional_exposure_currency_value_type": 100,
    "counter_directional_exposure_currency_value_type": 100,
    "long_underlying_instrument": None,
    "short_underlying_instrument": None,
    "underlying_long_multiplier": 1.0,
    "underlying_short_multiplier": 1.0,
    "long_underlying_exposure": None,
    "short_underlying_exposure": None,
    "position_reporting": 1,
    "instrument_factor_schedule_data": None,
    "pricing_currency": None,
    "pricing_currency_object": None,
    "price_multiplier": 1.0,
    "pricing_condition": None,
    "pricing_condition_object": None,
    "default_price": 0.0,
    "maturity_date": None,
    "maturity_price": 0.0,
    "reference_for_pricing": "",
    "configuration_code": "local.poms.space00000",
    "attributes": [],
    "deleted_user_code": None,
    "meta": {
        "content_type": "instruments.instrumenttype",
        "app_label": "instruments",
        "model_name": "instrumenttype",
        "space_code": "space00000",
    },
}

CREATE_DATA = {
    "user_code": "Apple",
    "name": "Apple",
    "short_name": "Apple",
    "public_name": "",
    "notes": "",
    "user_text_1": "",
    "user_text_2": "",
    "user_text_3": "",
}


class InstrumentTypeViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/instruments/instrument-type/"

    def prepare_data_for_create(self) -> dict:
        create_data = deepcopy(CREATE_DATA)
        create_data["name"] = self.random_string(11)
        instrument_type = self.get_instrument_type()
        create_data["instrument_type"] = instrument_type.id
        currency = self.get_currency()
        create_data["pricing_currency"] = currency.id
        create_data["accrued_currency"] = currency.id
        create_data["co_directional_exposure_currency"] = currency.id
        create_data["counter_directional_exposure_currency"] = currency.id
        # optional fields
        create_data["user_code"] = self.random_string()
        create_data["short_name"] = self.random_string(3)
        create_data["user_text_1"] = self.random_string()
        create_data["daily_pricing_model"] = self.get_daily_pricing().id
        create_data["pricing_condition"] = self.get_pricing_condition().id
        create_data["exposure_calculation_model"] = self.get_exposure_calculation().id
        create_data["payment_size_detail"] = self.get_payment_size().id
        create_data["long_underlying_exposure"] = self.get_long_under_exp().id
        create_data["short_underlying_exposure"] = self.get_short_under_exp().id
        create_data["country"] = self.get_country().id

        return create_data

    def test__check_api_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test__list_defaults(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(len(response_json["results"]), 3)

    def test__retrieve(self):
        instrument_type = self.get_instrument_type("bond")
        response = self.client.get(path=f"{self.url}{instrument_type.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        # check fields
        self.assertEqual(response_json.keys(), EXPECTED_INSTRUMENT_TYPE.keys())

        # check values
        self.assertEqual(response_json["short_name"], instrument_type.short_name)

    def test__list_attributes(self):
        response = self.client.get(path=f"{self.url}attributes/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 30)

    def test__list_light(self):
        self.create_instrument()
        response = self.client.get(path=f"{self.url}light/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 3)  # defaults

    # def test__get_filters(self):  # sourcery skip: extract-duplicate-method
    #     instrument = self.create_instrument()
    #     response = self.client.get(path=f"{self.url}?user_code={instrument.user_code}")
    #     self.assertEqual(response.status_code, 200, response.content)
    #     response_json = response.json()
    #     self.assertEqual(response_json["count"], 1)
    #     self.assertEqual(
    #         response_json["results"][0]["user_code"],
    #         instrument.user_code,
    #     )
    #
    #     response = self.client.get(
    #         path=f"{self.url}?user_text_1={instrument.user_text_1}"
    #     )
    #     self.assertEqual(response.status_code, 200, response.content)
    #     response_json = response.json()
    #     self.assertEqual(response_json["count"], 1)
    #     self.assertEqual(
    #         response_json["results"][0]["user_text_1"],
    #         instrument.user_text_1,
    #     )
    #
    # def test__create(self):
    #     create_data = self.prepare_data_for_create()
    #
    #     response = self.client.post(path=self.url, format="json", data=create_data)
    #     self.assertEqual(response.status_code, 201, response.content)
    #
    #     response_json = response.json()
    #
    #     instrument_id = response_json["id"]
    #     instrument = Instrument.objects.get(id=instrument_id)
    #     self.assertEqual(
    #         instrument.accrued_currency.id,
    #         create_data["accrued_currency"],
    #     )
    #     self.assertEqual(
    #         instrument.long_underlying_exposure.id,
    #         create_data["long_underlying_exposure"],
    #     )
    #     self.assertEqual(
    #         instrument.daily_pricing_model.id,
    #         create_data["daily_pricing_model"],
    #     )
    #     self.assertEqual(
    #         instrument.pricing_condition.id,
    #         create_data["pricing_condition"],
    #     )
    #     self.assertEqual(
    #         instrument.exposure_calculation_model.id,
    #         create_data["exposure_calculation_model"],
    #     )
    #     self.assertEqual(
    #         instrument.payment_size_detail.id,
    #         create_data["payment_size_detail"],
    #     )
    #     self.assertEqual(
    #         instrument.short_underlying_exposure.id,
    #         create_data["short_underlying_exposure"],
    #     )
    #     self.assertEqual(
    #         instrument.country.id,
    #         create_data["country"],
    #     )
    #     self.assertFalse(response_json["is_deleted"])
    #
    # def test__update_patch(self):
    #     create_data = self.prepare_data_for_create()
    #
    #     response = self.client.post(path=self.url, format="json", data=create_data)
    #     self.assertEqual(response.status_code, 201, response.content)
    #     response_json = response.json()
    #
    #     instrument_id = response_json["id"]
    #     new_user_text_1 = self.random_string()
    #     update_data = {"user_text_1": new_user_text_1}
    #     response = self.client.patch(
    #         path=f"{self.url}{instrument_id}/", format="json", data=update_data
    #     )
    #     self.assertEqual(response.status_code, 200, response.content)
    #
    #     response = self.client.get(path=f"{self.url}{instrument_id}/")
    #     self.assertEqual(response.status_code, 200, response.content)
    #     response_json = response.json()
    #     self.assertEqual(response_json["user_text_1"], new_user_text_1)
    #
    # def test__delete(self):
    #     create_data = self.prepare_data_for_create()
    #
    #     response = self.client.post(path=self.url, format="json", data=create_data)
    #     self.assertEqual(response.status_code, 201, response.content)
    #     response_json = response.json()
    #
    #     instrument_id = response_json["id"]
    #
    #     response = self.client.delete(path=f"{self.url}{instrument_id}/")
    #     self.assertEqual(response.status_code, 204, response.content)
    #
    #     response = self.client.get(path=f"{self.url}{instrument_id}/")
    #     self.assertEqual(response.status_code, 200, response.content)
    #     response_json = response.json()
    #
    #     self.assertTrue(response_json["is_deleted"])
