from django.conf import settings

from poms.common.common_base_test import BIG, BaseTestCase
from poms.portfolios.models import PortfolioRegister

PORTFOLIO_API = f"/{settings.BASE_API_URL}/api/v1/portfolios/portfolio-register"

EXPECTED_RESPONSE_PRICES = {
    "task_id": 1,
    "task_status": "P",
    "task_type": "calculate_portfolio_register_price_history",
    "task_options": {"date_to": "2023-09-13", "portfolios": ["x1", "y2", "z3"]},
}

EXPECTED_RESPONSE_RECORD = {
    "task_id": 2,
    "task_status": "P",
    "task_type": "calculate_portfolio_register_record",
    "task_options": {"portfolios": ["x1", "y2", "z3"]},
}


class PortfolioRegisterRecordViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"{PORTFOLIO_API}/"
        self.portfolio = self.db_data.portfolios[BIG]
        self.instrument = self.db_data.instruments["Apple"]
        self.pr_data = None
        self.pr_data = {
            "portfolio": self.portfolio.id,
            "linked_instrument": self.instrument.id,
            "valuation_currency": self.db_data.usd.id,
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


class PortfolioRegisterCalculateRecordsActionTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"{PORTFOLIO_API}/calculate-records/"

    def test_check_url(self):
        response = self.client.post(path=self.url, data={})
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(set(response_json), set(EXPECTED_RESPONSE_RECORD))
        self.assertEqual(
            response_json["task_type"], EXPECTED_RESPONSE_RECORD["task_type"]
        )

    def test__validate_portfolios(self):
        request_data = dict(portfolios=["a1", "b2", "c3"])

        response = self.client.post(path=self.url, data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json["task_options"], request_data)


class PortfolioRegisterCalculatePriceHistoryActionTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"{PORTFOLIO_API}/calculate-price-history/"

    def test_check_url(self):
        response = self.client.post(path=self.url, data={})
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(set(response_json), set(EXPECTED_RESPONSE_PRICES))
        self.assertEqual(
            response_json["task_type"], EXPECTED_RESPONSE_PRICES["task_type"]
        )

    def test__validate_portfolios(self):
        request_data = dict(portfolios=["x1", "y2", "z3"])

        response = self.client.post(path=self.url, data=request_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(
            response_json["task_options"]["portfolios"], request_data["portfolios"]
        )
