from poms.common.common_base_test import BaseTestCase
from poms.configuration.utils import get_default_configuration_code
from poms.instruments.models import PriceHistory, PricingPolicy
from poms.portfolios import utils


class UpdatePriceHistoriesTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.instrument = self.db_data.instruments["Apple"]
        self.pricing_policy = PricingPolicy.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            configuration_code=get_default_configuration_code(),
            # default_instrument_pricing_scheme=None,
            # default_currency_pricing_scheme=None,
        )
        self.err_msg = self.random_string()

    def create_price_history(self, n: int):
        while n > 0:
            _, created = PriceHistory.objects.get_or_create(
                instrument=self.instrument,
                pricing_policy=self.pricing_policy,
                date=self.random_future_date(),
                defaults=dict(
                    principal_price=self.random_float(),
                    cash_flow=self.random_float(),
                    nav=self.random_float(),
                ),
            )
            if created:
                n -= 1

    @BaseTestCase.cases(
        ["0", 0],
        ["4", 1],
        ["7", 7],
        ["21", 21],
    )
    def test__fields_updated_error_reset(self, amount):
        self.create_price_history(amount)
        prices = PriceHistory.objects.all()

        utils.update_price_histories(prices, error_message=self.err_msg)

        count = PriceHistory.objects.filter(
            error_message__icontains=self.err_msg
        ).count()
        self.assertEqual(count, amount)

        value = self.random_int()
        utils.update_price_histories(
            prices,
            error_message="",
            nav=value,
            cash_flow=value,
            principal_price=value,
        )

        count = PriceHistory.objects.filter(
            error_message="",
            nav=value,
            cash_flow=value,
            principal_price=value,
        ).count()
        self.assertEqual(count, amount)
