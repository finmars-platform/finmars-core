from copy import deepcopy

from poms.common.common_base_test import BaseTestCase
from poms.currencies.models import Currency, CurrencyHistory
from poms.currencies.tests.common_test_data import (
    CREATE_DATA,
    EXPECTED_CURRENCY_HISTORY,
)
from poms.instruments.models import PricingPolicy
from poms.pricing.models import CurrencyPricingScheme, InstrumentPricingScheme


class CurrencyHistoryViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = (
            f"/{self.realm_code}/{self.space_code}/api/v1/currencies/currency-history/"
        )
        self.currency = Currency.objects.last()
        self.instrument_pricing_schema = InstrumentPricingScheme.objects.first()
        self.instrument_currency_schema = CurrencyPricingScheme.objects.first()
        self.currency_history = None

    def create_pricing_policy(self) -> PricingPolicy:
        return PricingPolicy.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(5),
            short_name=self.random_string(2),
            name=self.random_string(11),
            default_instrument_pricing_scheme=self.instrument_pricing_schema,
            default_currency_pricing_scheme=self.instrument_currency_schema,
        )

    def create_currency_history(self) -> CurrencyHistory:
        self.currency_history = CurrencyHistory.objects.create(
            currency=self.currency,
            pricing_policy=self.create_pricing_policy(),
            fx_rate=self.random_int(),
        )
        return self.currency_history

    def prepare_data_for_create(self) -> dict:
        create_data = deepcopy(CREATE_DATA)
        pricing_policy = self.create_pricing_policy()
        create_data["fx_rate"] = self.random_int()
        create_data["currency"] = self.currency.id
        create_data["pricing_policy"] = pricing_policy.id
        return create_data

    def test__check_api_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test__create_and_retrieve(self):
        currency_history = self.create_currency_history()

        response = self.client.get(path=f"{self.url}{currency_history.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        # check fields
        self.assertEqual(response_json.keys(), EXPECTED_CURRENCY_HISTORY.keys())

        # check values
        self.assertEqual(response_json["fx_rate"], currency_history.fx_rate)
        self.assertEqual(
            response_json["pricing_policy"],
            currency_history.pricing_policy.id,
        )

    def test__list_attributes(self):
        response = self.client.get(path=f"{self.url}attributes/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 5)

    def test__get_filters(self):  # sourcery skip: extract-duplicate-method
        currency_history = self.create_currency_history()
        response = self.client.get(
            path=f"{self.url}?currency={currency_history.currency.id}"
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["currency"],
            currency_history.currency.id,
        )

        response = self.client.get(
            path=f"{self.url}?fx_rate={currency_history.fx_rate}"
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["fx_rate"],
            currency_history.fx_rate,
        )

    def test__create(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)

        response_json = response.json()

        currency_history_id = response_json["id"]
        currency_history = CurrencyHistory.objects.get(id=currency_history_id)
        self.assertEqual(currency_history.fx_rate, create_data["fx_rate"])

    def test__bulk_create(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(
            path=f"{self.url}bulk-create/",
            format="json",
            data=[create_data],
        )
        self.assertEqual(response.status_code, 201, response.content)

        currency_history = CurrencyHistory.objects.filter(
            fx_rate=create_data["fx_rate"]
        )
        self.assertIsNotNone(currency_history)

    def test__update_put(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        currency_history_id = response_json["id"]
        new_fx_rate = self.random_int()
        update_data = deepcopy(create_data)
        update_data["fx_rate"] = new_fx_rate
        response = self.client.put(
            path=f"{self.url}{currency_history_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}{currency_history_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["fx_rate"], new_fx_rate)

    def test__update_patch(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        currency_history_id = response_json["id"]
        new_fx_rate = self.random_int()
        update_data = {"fx_rate": new_fx_rate}

        response = self.client.patch(
            path=f"{self.url}{currency_history_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}{currency_history_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["fx_rate"], new_fx_rate)

    def test__delete(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        currency_history_id = response_json["id"]

        response = self.client.delete(path=f"{self.url}{currency_history_id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(path=f"{self.url}{currency_history_id}/")
        self.assertEqual(response.status_code, 404, response.content)
