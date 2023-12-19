from django.conf import settings

from poms.common.common_base_test import BIG, BaseTestCase
from poms.configuration.utils import get_default_configuration_code
from poms.instruments.models import PricingPolicy, InstrumentType, Instrument
from poms.portfolios.models import PortfolioRegister

PORTFOLIO_API = f"/{settings.BASE_API_URL}/api/v1/portfolios/portfolio-register"

EXPECTED_RESPONSE = {
    "id": 1,
    "user_code": "YOSDJXXNXR",
    "name": "name",
    "short_name": "short_name",
    "public_name": "public_name",
    "notes": None,
    "is_deleted": False,
    "is_enabled": True,
    "portfolio": 2,
    "portfolio_object": {
        "id": 2,
        "user_code": "Big",
        "name": "Big",
        "short_name": "Big",
        "public_name": None,
        "deleted_user_code": None,
        "owner": {
            "id": 1,
            "username": "finmars_bot",
            "first_name": "",
            "last_name": "",
            "display_name": "finmars_bot",
            "is_owner": False,
            "is_admin": True,
            "user": 1,
        },
        "meta": {
            "content_type": "portfolios.portfolio",
            "app_label": "portfolios",
            "model_name": "portfolio",
            "space_code": "space00000",
        },
    },
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
            "owner": {
                "id": 1,
                "username": "finmars_bot",
                "first_name": "",
                "last_name": "",
                "display_name": "finmars_bot",
                "is_owner": False,
                "is_admin": True,
                "user": 1,
            },
            "meta": {
                "content_type": "instruments.instrumenttype",
                "app_label": "instruments",
                "model_name": "instrumenttype",
                "space_code": "space00000",
            },
        },
        "user_code": "YOSDJXXNXR",
        "name": "RQCDWRWGFT",
        "short_name": "BDN",
        "public_name": "HOZGAXADKEAKRTLEQZUM",
        "notes": None,
        "is_active": True,
        "is_deleted": False,
        "has_linked_with_portfolio": True,
        "user_text_1": None,
        "user_text_2": None,
        "user_text_3": None,
        "maturity_date": None,
        "deleted_user_code": None,
        "owner": {
            "id": 2,
            "username": "",
            "first_name": "",
            "last_name": "",
            "display_name": "",
            "is_owner": True,
            "is_admin": True,
            "user": 2,
        },
        "meta": {
            "content_type": "instruments.instrument",
            "app_label": "instruments",
            "model_name": "instrument",
            "space_code": "space00000",
        },
    },
    "valuation_currency": 2,
    "valuation_currency_object": {
        "id": 2,
        "user_code": "USD",
        "name": "US Dollar (USD)",
        "short_name": "USD",
        "deleted_user_code": None,
        "owner": {
            "id": 1,
            "username": "finmars_bot",
            "first_name": "",
            "last_name": "",
            "display_name": "finmars_bot",
            "is_owner": False,
            "is_admin": True,
            "user": 1,
        },
        "meta": {
            "content_type": "currencies.currency",
            "app_label": "currencies",
            "model_name": "currency",
            "space_code": "space00000",
        },
    },
    "valuation_pricing_policy": 2,
    "valuation_pricing_policy_object": {
        "id": 2,
        "user_code": "local.poms.space00000:qktnkeomku",
        "configuration_code": "local.poms.space00000",
        "name": "",
        "short_name": "",
        "notes": None,
        "expr": "",
        "default_instrument_pricing_scheme": None,
        "default_currency_pricing_scheme": None,
        "deleted_user_code": None,
        "default_instrument_pricing_scheme_object": None,
        "default_currency_pricing_scheme_object": None,
        "owner": {
            "id": 1,
            "username": "finmars_bot",
            "first_name": "",
            "last_name": "",
            "display_name": "finmars_bot",
            "is_owner": False,
            "is_admin": True,
            "user": 1,
        },
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
    "owner": {
        "id": 2,
        "username": "",
        "first_name": "",
        "last_name": "",
        "display_name": "",
        "is_owner": True,
        "is_admin": True,
        "user": 2,
    },
    "meta": {
        "content_type": "portfolios.portfolioregister",
        "app_label": "portfolios",
        "model_name": "portfolioregister",
        "space_code": "space00000",
    },
}


class PortfolioRegisterCreateTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"{PORTFOLIO_API}/"
        self.portfolio = self.db_data.portfolios[BIG]
        self.instrument = self.db_data.instruments["Apple"]
        self.instrument_type = InstrumentType.objects.first()
        self.pricing_policy = PricingPolicy.objects.create(
            master_user=self.master_user,
            owner=self.finmars_bot,
            user_code=self.random_string(),
            configuration_code=get_default_configuration_code(),
            default_instrument_pricing_scheme=None,
            default_currency_pricing_scheme=None,
        )
        self.pr_user_code = self.random_string()
        self.pr_data = {
            "portfolio": self.portfolio.id,
            "linked_instrument": self.instrument.id,
            "valuation_currency": self.db_data.usd.id,
            "valuation_pricing_policy": self.pricing_policy.id,
            "user_code": self.pr_user_code,
            "name": "name",
            "short_name": "short_name",
            "public_name": "public_name",
        }

    def test_create_with_new_linked_instrument(self):
        new_pr_data = {
            **self.pr_data,
            "new_linked_instrument": {
                "name": self.random_string(),
                "short_name": self.random_string(3),
                "user_code": self.pr_user_code,
                "public_name": self.random_string(20),
                "instrument_type": self.instrument_type.id,
            },
        }
        new_pr_data.pop("linked_instrument")

        response = self.client.post(self.url, data=new_pr_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        created_pr = PortfolioRegister.objects.filter(
            user_code=self.pr_user_code
        ).first()
        self.assertIsNotNone(created_pr)

        created_in = Instrument.objects.filter(user_code=self.pr_user_code).first()
        self.assertIsNotNone(created_in)

        self.assertEqual(response_json["user_code"], self.pr_user_code)
        self.assertEqual(
            response_json["linked_instrument_object"]["user_code"],
            self.pr_user_code,
        )
        self.assertEqual(response_json["linked_instrument"], created_in.id)
