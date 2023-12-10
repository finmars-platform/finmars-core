from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import InstrumentType, InstrumentClass
from poms.instruments.tests.common_test_data import EXPECTED_INSTRUMENT_TYPE


class InstrumentTypeViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/instruments/instrument-type/"

    @staticmethod
    def get_instrument_class(class_id: int = InstrumentClass.DEFAULT):
        return InstrumentClass.objects.get(id=class_id)

    def prepare_data_for_create(self) -> dict:
        currency_id = self.get_currency().id
        attribute = self.create_attribute()
        return {
            "user_code": self.random_string(11),
            "name": self.random_string(11),
            "short_name": self.random_string(3),
            "instrument_class": self.get_instrument_class().id,
            "configuration_code": str(self.random_int(1, 100000)),
            "attributes": [
                {
                    "id": attribute.id,
                    "attribute_type": attribute.attribute_type.id,
                    "value_float": attribute.value_float,
                }
            ],
            "accrued_currency": currency_id,
            "pricing_currency": currency_id,
            "default_price": 111.0,
            "instrument_factor_schedule_data": [],
        }

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

    @BaseTestCase.cases(
        ("user_code", "user_code"),
        ("name", "name"),
        ("short_name", "short_name"),
    )
    def test__get_filters(self, field):
        instrument_type = self.get_instrument_type("stock")
        response = self.client.get(
            path=f"{self.url}?{field}={getattr(instrument_type, field)}",
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0][field],
            getattr(instrument_type, field),
        )

    @BaseTestCase.cases(
        ("0", 0),
        ("1", 1),
        ("2", 2),
    )
    def test__get_instrument_class_filter_(self, index):
        response = self.client.get(
            path=f"{self.url}?instrument_class__id={InstrumentClass.GENERAL}",
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertEqual(
            response_json["results"][index]["instrument_class"],
            InstrumentClass.GENERAL,
        )

    def test__create(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)

        response_json = response.json()

        self.assertEqual(response_json.keys(), EXPECTED_INSTRUMENT_TYPE.keys())

        instrument_type_id = response_json["id"]
        instrument_type = InstrumentType.objects.get(id=instrument_type_id)
        self.assertEqual(
            instrument_type.accrued_currency.id,
            create_data["accrued_currency"],
        )
        self.assertEqual(
            instrument_type.pricing_currency.id,
            create_data["pricing_currency"],
        )
        self.assertEqual(
            instrument_type.short_name,
            create_data["short_name"],
        )
        self.assertEqual(
            instrument_type.configuration_code,
            create_data["configuration_code"],
        )
        self.assertEqual(
            instrument_type.instrument_class.id,
            create_data["instrument_class"],
        )
        self.assertFalse(response_json["is_deleted"])

    def test__update_patch(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        instrument_type_id = response_json["id"]

        new_user_code = self.random_string()
        update_data = {"user_code": new_user_code}
        response = self.client.patch(
            path=f"{self.url}{instrument_type_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}{instrument_type_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        config_code, user_code = response_json["user_code"].split(":")
        self.assertEqual(response_json["configuration_code"], config_code)
        self.assertEqual(user_code.upper(), new_user_code)

    def test__delete(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        instrument_type_id = response_json["id"]

        response = self.client.delete(path=f"{self.url}{instrument_type_id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(path=f"{self.url}{instrument_type_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertTrue(response_json["is_deleted"])

    def test__get_update_pricing(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        instrument_type_id = response_json["id"]

        response = self.client.get(
            path=f"{self.url}{instrument_type_id}/update-pricing/"
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertEqual(response_json["status"], "ok")
        self.assertEqual(response_json["data"], {"instruments_affected": 0})

    def test__patch_bulk_update(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        instrument_type_id = response_json["id"]
        new_name = self.random_string()
        update_data = [{"id": instrument_type_id, "short_name": new_name}]
        response = self.client.patch(
            path=f"{self.url}bulk-update/",
            format="json",
            data=update_data,
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertEqual(len(response_json), 1)
        instrument_type_data = response_json[0]
        self.assertEqual(instrument_type_data["id"], instrument_type_id)
        self.assertEqual(instrument_type_data["short_name"], new_name)
