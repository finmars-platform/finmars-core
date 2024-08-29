from copy import deepcopy

from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import AccrualCalculationSchedule, Instrument
from poms.instruments.tests.common_test_data import (
    EXPECTED_INSTRUMENT,
    INSTRUMENT_CREATE_DATA,
)


class InstrumentViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = (
            f"/{self.realm_code}/{self.space_code}/api/v1/instruments/instrument/"
        )
        self.pricing_policy = None
        self.instrument = Instrument.objects.first()

    def prepare_data_for_create(self) -> dict:
        create_data = deepcopy(INSTRUMENT_CREATE_DATA)
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
        create_data["identifier"] = {}

        return create_data

    def test__check_api_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    @BaseTestCase.cases(
        ("bond", "bond"),
        ("stock", "stock"),
    )
    def test__retrieve(self, instrument_type):
        instrument = self.create_instrument(instrument_type)
        response = self.client.get(path=f"{self.url}{instrument.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        # check fields
        self.assertEqual(response_json.keys(), EXPECTED_INSTRUMENT.keys())

        # check values
        self.assertEqual(response_json["short_name"], instrument.short_name)
        self.assertEqual(
            response_json["instrument_type"],
            instrument.instrument_type.id,
        )
        self.assertEqual(
            response_json["pricing_currency"],
            instrument.pricing_currency.id,
        )
        self.assertEqual(
            response_json["accrued_currency"],
            instrument.accrued_currency.id,
        )
        self.assertEqual(response_json["user_text_1"], instrument.user_text_1)
        self.assertEqual(response_json["user_text_2"], instrument.user_text_2)
        self.assertEqual(response_json["user_text_3"], instrument.user_text_3)

        self.assertIn("files", response_json)

    def test__list_attributes(self):
        response = self.client.get(path=f"{self.url}attributes/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 34)

    def test__list_light(self):
        self.create_instrument()
        response = self.client.get(path=f"{self.url}light/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 4)  # default + 2 test + new

    def test__get_filters(self):  # sourcery skip: extract-duplicate-method
        instrument = self.create_instrument()
        response = self.client.get(path=f"{self.url}?user_code={instrument.user_code}")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["user_code"],
            instrument.user_code,
        )

        response = self.client.get(
            path=f"{self.url}?user_text_1={instrument.user_text_1}"
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["user_text_1"],
            instrument.user_text_1,
        )

    def test__create(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)

        response_json = response.json()

        instrument_id = response_json["id"]
        instrument = Instrument.objects.get(id=instrument_id)
        self.assertEqual(
            instrument.accrued_currency.id,
            create_data["accrued_currency"],
        )
        self.assertEqual(
            instrument.long_underlying_exposure.id,
            create_data["long_underlying_exposure"],
        )
        self.assertEqual(
            instrument.daily_pricing_model.id,
            create_data["daily_pricing_model"],
        )
        self.assertEqual(
            instrument.pricing_condition.id,
            create_data["pricing_condition"],
        )
        self.assertEqual(
            instrument.exposure_calculation_model.id,
            create_data["exposure_calculation_model"],
        )
        self.assertEqual(
            instrument.payment_size_detail.id,
            create_data["payment_size_detail"],
        )
        self.assertEqual(
            instrument.short_underlying_exposure.id,
            create_data["short_underlying_exposure"],
        )
        self.assertEqual(
            instrument.country.id,
            create_data["country"],
        )
        self.assertFalse(response_json["is_deleted"])

    def test__update_patch(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        instrument_id = response_json["id"]
        new_user_text_1 = self.random_string()
        update_data = {"user_text_1": new_user_text_1}
        response = self.client.patch(
            path=f"{self.url}{instrument_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}{instrument_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["user_text_1"], new_user_text_1)

    def test__delete(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        instrument_id = response_json["id"]

        response = self.client.delete(path=f"{self.url}{instrument_id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(path=f"{self.url}{instrument_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertTrue(response_json["is_deleted"])

    def test__retrieve_bond_with_accrual_schedule(self):
        instrument = self.create_instrument("bond")
        start_date = "2021-01-10"
        payment_date = "2022-01-31"
        AccrualCalculationSchedule.objects.create(
            instrument=instrument,
            accrual_calculation_model_id=1,
            accrual_start_date=start_date,
            first_payment_date=payment_date,
        )

        response = self.client.get(path=f"{self.url}{instrument.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        accrual_data = response_json["accrual_calculation_schedules"][0]
        self.assertEqual(accrual_data["accrual_start_date"], start_date)
        self.assertEqual(accrual_data["first_payment_date"], payment_date)

    def test__retrieve_with_file(self):
        from poms.explorer.models import StorageObject

        instrument = self.create_instrument("bond")
        file = StorageObject.objects.create(
            path="/root/etc/system/name.pdf",
            size=1234567890,
            is_file=True,
        )
        instrument.files.add(file, through_defaults=None)

        response = self.client.get(path=f"{self.url}{instrument.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        file_data = response_json["files"][0]
        self.assertEqual(file_data["name"], file.name)
        self.assertEqual(file_data["path"], file.path)
        self.assertEqual(file_data["size"], file.size)
        self.assertEqual(file_data["extension"], ".pdf")
