from django.conf import settings
from django.test import override_settings

from poms.common.common_base_test import BIG, BaseTestCase
from poms.configuration.utils import get_default_configuration_code
from poms.instruments.models import PricingPolicy
from poms.portfolios.models import PortfolioRegister

EXPECTED_RESPONSE_PRICES = {
    "task_id": 1,
    "task_status": "P",
    "task_type": "calculate_portfolio_register_price_history",
    "task_options": {"date_to": "2023-09-13", "portfolio_registers": ["x1", "y2", "z3"]},
}

EXPECTED_RESPONSE_RECORD = {
    "task_id": 2,
    "task_status": "P",
    "task_type": "calculate_portfolio_register_record",
    "task_options": {"portfolio_registers": ["x1", "y2", "z3"]},
}


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class PortfolioRegisterViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-register/"
        self.portfolio = self.db_data.portfolios[BIG]
        self.instrument = self.db_data.instruments["Apple"]
        self.pricing_policy = PricingPolicy.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            configuration_code=get_default_configuration_code(),
            # default_instrument_pricing_scheme=None,
            # default_currency_pricing_scheme=None,
        )
        self.pr_data = {
            "portfolio": self.portfolio.id,
            "linked_instrument": self.instrument.id,
            "valuation_currency": self.db_data.usd.id,
            "valuation_pricing_policy": self.pricing_policy.id,
            "name": "name",
            "short_name": "short_name",
            "user_code": "user_code",
            "public_name": "public_name",
        }

    def test_check_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test_create_simple(self):
        response = self.client.post(self.url, data=self.pr_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        pr = PortfolioRegister.objects.filter(name="name").first()
        self.assertIsNotNone(pr)

    def test_no_create_with_invalid_new_instrument(self):
        new_instrument = self.db_data.instruments["Tesla B."]
        new_pr_data = {
            **self.pr_data,
            "new_linked_instrument": {
                "name": new_instrument.name,
                "short_name": new_instrument.short_name,
                "user_code": new_instrument.user_code,
                "public_name": new_instrument.public_name,
                "instrument_type": self.random_int(),
            },
        }

        response = self.client.post(self.url, data=new_pr_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class PortfolioRegisterCalculateRecordsActionTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-register/calculate-records/"

    def test_check_url(self):
        response = self.client.post(path=self.url, data={})
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertTrue(set(EXPECTED_RESPONSE_PRICES).issubset(set(response_json)))
        self.assertEqual(
            response_json["task_type"], EXPECTED_RESPONSE_RECORD["task_type"]
        )

    def test__validate_portfolios(self):
        request_data = dict(portfolio_registers=["a1", "b2", "c3"])

        response = self.client.post(path=self.url, data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json["task_options"]['portfolio_registers'], request_data['portfolio_registers'])


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class PortfolioRegisterCalculatePriceHistoryActionTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-register/calculate-price-history/"

    def test_check_url(self):
        response = self.client.post(path=self.url, data={})
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertTrue(set(EXPECTED_RESPONSE_PRICES).issubset(set(response_json)))
        self.assertEqual(
            response_json["task_type"], EXPECTED_RESPONSE_PRICES["task_type"]
        )

    def test__validate_portfolios(self):
        request_data = dict(portfolio_registers=["x1", "y2", "z3"])

        response = self.client.post(path=self.url, data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(
            response_json["task_options"]["portfolio_registers"], request_data["portfolio_registers"]
        )

    @BaseTestCase.cases(
        ("1", "2023-08-01", "2023-09-06"),
        ("2", "2020-01-27", "2023-10-13"),
        ("3", "2022-11-14", "2025-03-30"),
        ("4", "2022-12-31", None),
        ("5", "2022-11-14", "2022-11-14"),
    )
    def test__validate_dates(self, date_from, date_to):
        request_data = (
            dict(date_from=date_from, date_to=date_to)
            if date_to
            else dict(date_from=date_from)
        )

        response = self.client.post(path=self.url, data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json["task_options"]["date_from"], date_from)
        self.assertEqual(
            response_json["task_options"]["date_to"],
            date_to or self.yesterday().strftime(settings.API_DATE_FORMAT),
        )

    @BaseTestCase.cases(
        ("invalid_date", "2023-09-01", "2023-07-01"),
    )
    def test__validate_invalid_dates(self, date_from, date_to):
        request_data = dict(date_from=date_from, date_to=date_to)

        response = self.client.post(path=self.url, data=request_data)
        self.assertEqual(response.status_code, 400, response.content)
