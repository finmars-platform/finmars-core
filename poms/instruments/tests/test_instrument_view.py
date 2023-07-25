from copy import deepcopy
from datetime import date

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from poms.common.common_base_test import BaseTestCase
from poms.common.constants import SystemValueType
from poms.currencies.models import Currency
from poms.instruments.models import (
    AccrualCalculationModel,
    AccrualCalculationSchedule,
    Country,
    DailyPricingModel,
    ExposureCalculationModel,
    Instrument,
    InstrumentFactorSchedule,
    InstrumentType,
    LongUnderlyingExposure,
    PaymentSizeDetail,
    Periodicity,
    PricingCondition,
    ShortUnderlyingExposure,
)
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType

EXPECTED_INSTRUMENT = {
    "id": 22,
    "instrument_type": 17,
    "instrument_type_object": {
        "id": 17,
        "instrument_class": 1,
        "instrument_class_object": {
            "id": 1,
            "user_code": "GENERAL",
            "name": "General Class",
            "description": "General Class",
        },
        "user_code": "local.poms.space00000:stock",
        "name": "stock",
        "short_name": "stock",
        "public_name": "stock",
        "instrument_form_layouts": None,
        "deleted_user_code": None,
        "meta": {
            "content_type": "instruments.instrumenttype",
            "app_label": "instruments",
            "model_name": "instrumenttype",
            "space_code": "space00000",
        },
    },
    "user_code": "CSVJGHVZFC",
    "name": "BOXUGKLYWOR",
    "short_name": "BSH",
    "public_name": None,
    "notes": None,
    "is_active": True,
    "is_deleted": False,
    "has_linked_with_portfolio": False,
    "pricing_currency": 28,
    "pricing_currency_object": {
        "id": 28,
        "user_code": "EUR",
        "name": "EUR - Euro",
        "short_name": "EUR",
        "deleted_user_code": None,
        "meta": {
            "content_type": "currencies.currency",
            "app_label": "currencies",
            "model_name": "currency",
            "space_code": "space00000",
        },
    },
    "price_multiplier": 1.0,
    "accrued_currency": 28,
    "accrued_currency_object": {
        "id": 28,
        "user_code": "EUR",
        "name": "EUR - Euro",
        "short_name": "EUR",
        "deleted_user_code": None,
        "meta": {
            "content_type": "currencies.currency",
            "app_label": "currencies",
            "model_name": "currency",
            "space_code": "space00000",
        },
    },
    "accrued_multiplier": 1.0,
    "payment_size_detail": 1,
    "payment_size_detail_object": {
        "id": 1,
        "user_code": "PERCENT",
        "name": "% per annum",
        "description": "% per annum",
    },
    "default_price": 0.0,
    "default_accrued": 0.0,
    "user_text_1": "JBYWDPLZLI",
    "user_text_2": "FHHMHMVRER",
    "user_text_3": "SHASFYKQLJ",
    "reference_for_pricing": "",
    "daily_pricing_model": 6,
    "daily_pricing_model_object": {
        "id": 6,
        "user_code": "-",
        "name": "Use Default Price (no Price History)",
        "description": "Use Default Price (no Price History)",
    },
    "pricing_condition": 1,
    "pricing_condition_object": {
        "id": 1,
        "user_code": "NO_VALUATION",
        "name": "Don't Run Valuation",
        "description": "Don't Run Valuation",
    },
    "maturity_date": None,
    "maturity_price": 0.0,
    "manual_pricing_formulas": [],
    "accrual_calculation_schedules": [
        {
            "id": 4,
            "accrual_start_date": None,
            "accrual_start_date_value_type": 40,
            "first_payment_date": None,
            "first_payment_date_value_type": 40,
            "accrual_size": "0.598345055004762",
            "accrual_size_value_type": 20,
            "periodicity_n": "30",
            "periodicity_n_value_type": 20,
            "accrual_calculation_model": 2,
            "accrual_calculation_model_object": {
                "id": 2,
                "user_code": "ACT_ACT",
                "name": "ACT/ACT",
                "description": "ACT/ACT",
            },
            "periodicity": 1,
            "periodicity_object": {
                "id": 1,
                "user_code": "N_DAY",
                "name": "N Days",
                "description": "N Days",
            },
            "notes": "",
        }
    ],
    "factor_schedules": [
        {
            "effective_date": "2024-05-21",
            "factor_value": 0.2278459186631061,
        }
    ],
    "event_schedules": [],
    "is_enabled": True,
    "pricing_policies": [],
    "exposure_calculation_model": 1,
    "exposure_calculation_model_object": {
        "id": 1,
        "user_code": "MARKET_VALUE",
        "name": "Market value",
        "description": "Market value",
    },
    "co_directional_exposure_currency": 28,
    "counter_directional_exposure_currency": None,
    "co_directional_exposure_currency_object": {
        "id": 28,
        "user_code": "EUR",
        "name": "EUR - Euro",
        "short_name": "EUR",
        "deleted_user_code": None,
        "meta": {
            "content_type": "currencies.currency",
            "app_label": "currencies",
            "model_name": "currency",
            "space_code": "space00000",
        },
    },
    "counter_directional_exposure_currency_object": {
        "id": 28,
        "user_code": "EUR",
        "name": "EUR - Euro",
        "short_name": "EUR",
        "deleted_user_code": None,
        "meta": {
            "content_type": "currencies.currency",
            "app_label": "currencies",
            "model_name": "currency",
            "space_code": "space00000",
        },
    },
    "long_underlying_instrument": None,
    "short_underlying_instrument": None,
    "long_underlying_instrument_object": None,
    "short_underlying_instrument_object": None,
    "underlying_long_multiplier": 1.0,
    "underlying_short_multiplier": 1.0,
    "long_underlying_exposure": 1,
    "short_underlying_exposure": 1,
    "position_reporting": 1,
    "country": 112,
    "country_object": {
        "id": 112,
        "name": "Italy",
        "user_code": "Italy",
        "country_code": "380",
        "region": "Europe",
        "region_code": "150",
        "alpha_2": "IT",
        "alpha_3": "ITA",
        "sub_region": "Southern Europe",
        "sub_region_code": "039",
    },
    "deleted_user_code": None,
    "attributes": [
        {
            "id": 4,
            "attribute_type": 4,
            "value_string": "PGBZBAEROP",
            "value_float": 6897.0,
            "value_date": "2023-07-21",
            "classifier": None,
            "attribute_type_object": {
                "id": 4,
                "user_code": "local.poms.space00000:auth.permission:tbylo",
                "name": "",
                "short_name": "PC",
                "public_name": None,
                "notes": None,
                "can_recalculate": False,
                "value_type": 20,
                "order": 0,
                "is_hidden": False,
                "kind": 1,
            },
            "classifier_object": None,
        }
    ],
    "meta": {
        "content_type": "instruments.instrument",
        "app_label": "instruments",
        "model_name": "instrument",
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


class InstrumentViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/instruments/instrument/"
        self.pricing_policy = None
        self.instrument = Instrument.objects.first()

    def create_attribute_type(self) -> GenericAttributeType:
        self.attribute_type = GenericAttributeType.objects.create(
            master_user=self.master_user,
            content_type=ContentType.objects.first(),
            user_code=self.random_string(5),
            short_name=self.random_string(2),
            value_type=GenericAttributeType.NUMBER,
            kind=GenericAttributeType.USER,
            tooltip=self.random_string(),
            favorites=self.random_string(),
            prefix=self.random_string(3),
            expr=self.random_string(),
        )
        return self.attribute_type

    def create_attribute(self) -> GenericAttribute:
        self.attribute = GenericAttribute.objects.create(
            attribute_type=self.create_attribute_type(),
            content_type=ContentType.objects.last(),
            object_id=self.random_int(),
            value_string=self.random_string(),
            value_float=self.random_int(),
            value_date=date.today(),
        )
        return self.attribute

    @staticmethod
    def get_instrument_type(instrument_type: str = "bond") -> InstrumentType:
        return InstrumentType.objects.get(user_code__contains=instrument_type)

    @staticmethod
    def get_currency(user_code: str = "EUR") -> InstrumentType:
        return Currency.objects.get(user_code=user_code)

    @staticmethod
    def get_pricing_condition(model_id=PricingCondition.NO_VALUATION):
        return PricingCondition.objects.get(id=model_id)

    @staticmethod
    def get_exposure_calculation(model_id=ExposureCalculationModel.MARKET_VALUE):
        return ExposureCalculationModel.objects.get(id=model_id)

    @staticmethod
    def get_payment_size(model_id=PaymentSizeDetail.PERCENT):
        return PaymentSizeDetail.objects.get(id=model_id)

    @staticmethod
    def get_daily_pricing(model_id=DailyPricingModel.DEFAULT):
        return DailyPricingModel.objects.get(id=model_id)

    @staticmethod
    def get_long_under_exp(model_id=LongUnderlyingExposure.ZERO):
        return LongUnderlyingExposure.objects.get(id=model_id)

    @staticmethod
    def get_short_under_exp(model_id=ShortUnderlyingExposure.ZERO):
        return ShortUnderlyingExposure.objects.get(id=model_id)

    @staticmethod
    def get_country(name="Italy"):
        return Country.objects.get(name=name)

    @staticmethod
    def get_accrual_calculation_model(model_id=AccrualCalculationModel.ACT_ACT):
        return AccrualCalculationModel.objects.get(id=model_id)

    @staticmethod
    def get_periodicity(model_id=Periodicity.N_DAY):
        return Periodicity.objects.get(id=model_id)

    def create_accrual(self, instrument: Instrument) -> AccrualCalculationSchedule:
        return AccrualCalculationSchedule.objects.create(
            instrument=instrument,
            accrual_start_date=date.today(),
            accrual_start_date_value_type=SystemValueType.DATE,
            first_payment_date=self.random_future_date(),
            first_payment_date_value_type=SystemValueType.DATE,
            accrual_size=self.random_percent(),
            accrual_calculation_model=self.get_accrual_calculation_model(),
            periodicity=self.get_periodicity(),
            periodicity_n="30",
            periodicity_n_value_type=SystemValueType.NUMBER,
        )

    def create_factor(self, instrument: Instrument) -> InstrumentFactorSchedule:
        return InstrumentFactorSchedule.objects.create(
            instrument=instrument,
            effective_date=self.random_future_date(),
            factor_value=self.random_percent(),
        )

    def create_instrument(
        self,
        instrument_type: str = "bond",
        currency_code: str = "EUR",
    ) -> Instrument:
        currency = self.get_currency(user_code=currency_code)
        self.instrument = Instrument.objects.create(
            # mandatory fields
            master_user=self.master_user,
            instrument_type=self.get_instrument_type(instrument_type),
            pricing_currency=currency,
            accrued_currency=currency,
            name=self.random_string(11),
            # optional fields
            short_name=self.random_string(3),
            user_code=self.random_string(),
            user_text_1=self.random_string(),
            user_text_2=self.random_string(),
            user_text_3=self.random_string(),
            daily_pricing_model=self.get_daily_pricing(),
            pricing_condition=self.get_pricing_condition(),
            exposure_calculation_model=self.get_exposure_calculation(),
            payment_size_detail=self.get_payment_size(),
            long_underlying_exposure=self.get_long_under_exp(),
            short_underlying_exposure=self.get_short_under_exp(),
            co_directional_exposure_currency=currency,
            country=self.get_country(),
        )
        self.instrument.attributes.set([self.create_attribute()])
        self.instrument.save()
        self.create_accrual(self.instrument)
        self.create_factor(self.instrument)

        return self.instrument

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
