from typing import Optional
from unittest import mock  # , skip

from django.conf import settings

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BIG, BaseTestCase
from poms.common.exceptions import FinmarsBaseException
from poms.configuration.utils import get_default_configuration_code
from poms.instruments.models import PricingPolicy
from poms.portfolios.models import PortfolioRegister
from poms.portfolios.tasks import calculate_portfolio_register_price_history


class CalculatePortfolioRegisterPriceHistoryTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.portfolio = self.db_data.portfolios[BIG]
        self.instrument = self.db_data.instruments["Apple"]
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-register/"
        self.user_code = self.random_string(5)
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
            "user_code": self.user_code,
            "public_name": "public_name",
        }

    def create_celery_task(self, options: Optional[dict] = None) -> CeleryTask:
        self.celery_task = CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            verbose_name="Calculate Portfolio Register Prices",
            type="calculate_portfolio_register_price_history",
            status=CeleryTask.STATUS_PENDING,
        )
        self.celery_task.options_object = options
        self.celery_task.save()

        return self.celery_task

    def create_portfolio_register(self) -> PortfolioRegister:
        response = self.client.post(self.url, data=self.pr_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        return PortfolioRegister.objects.filter(name="name").first()

    # @skip("temporally")
    def test__invalid_celery_task(self):
        with self.assertRaises(FinmarsBaseException):
            calculate_portfolio_register_price_history(task_id=self.random_int())

    # @skip("temporally")
    @mock.patch("poms.portfolios.tasks.send_system_message")
    def test__no_options_in_celery_task(self, system_message):
        celery_task = self.create_celery_task()

        with self.assertRaises(RuntimeError):
            calculate_portfolio_register_price_history(task_id=celery_task.id)

        celery_task.refresh_from_db()
        self.assertEqual(celery_task.status, CeleryTask.STATUS_ERROR)
        system_message.assert_called_once()

    # @skip("temporally")
    @mock.patch("poms.portfolios.tasks.send_system_message")
    def test__invalid_portfolio_user_code(self, system_message):
        options = {
            "date_from": self.yesterday().strftime(settings.API_DATE_FORMAT),
            "date_to": self.today().strftime(settings.API_DATE_FORMAT),
            "portfolios": [self.random_string(5)]
        }
        celery_task = self.create_celery_task(options=options)

        calculate_portfolio_register_price_history(task_id=celery_task.id)

        celery_task.refresh_from_db()
        self.assertEqual(celery_task.status, CeleryTask.STATUS_DONE)
        self.assertEqual(system_message.call_count, 2)

    @mock.patch("poms.portfolios.tasks.send_system_message")
    def test__valid_portfolio_user_code(self, system_message):
        self.create_portfolio_register()
        options = {
            "date_from": self.yesterday().strftime(settings.API_DATE_FORMAT),
            "date_to": self.today().strftime(settings.API_DATE_FORMAT),
            "portfolios": [self.user_code]
        }
        celery_task = self.create_celery_task(options=options)

        calculate_portfolio_register_price_history(task_id=celery_task.id)

        celery_task.refresh_from_db()
        self.assertEqual(celery_task.status, CeleryTask.STATUS_DONE)
        self.assertEqual(system_message.call_count, 2)
