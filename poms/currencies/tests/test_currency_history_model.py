from datetime import timedelta

from poms.common.common_base_test import BaseTestCase
from poms.common.exceptions import FinmarsBaseException
from poms.currencies.models import Currency, CurrencyHistory
from poms.instruments.models import PricingPolicy
from poms.pricing.models import CurrencyPricingScheme, InstrumentPricingScheme


class CurrencyHistoryModelTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
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

    def create_currency_history(self, policy, date) -> CurrencyHistory:
        self.currency_history = CurrencyHistory.objects.create(
            currency=self.currency,
            pricing_policy=policy,
            fx_rate=self.random_int(),
            date=date,
        )
        return self.currency_history

    def test__get_fx_rate_method_ok(self):
        policy = self.create_pricing_policy()
        date = self.random_future_date()
        currency_history = self.create_currency_history(policy, date)

        fx_rate = CurrencyHistory.objects.get_fx_rate(
            currency_id=self.currency.id,
            pricing_policy=policy,
            date=date,
        )

        self.assertEqual(currency_history.fx_rate, fx_rate)

    def test__get_fx_rate_method_raises_error(self):
        policy = self.create_pricing_policy()
        date = self.random_future_date()
        self.create_currency_history(policy, date)

        with self.assertRaises(FinmarsBaseException):
            CurrencyHistory.objects.get_fx_rate(
                currency_id=self.currency.id,
                pricing_policy=policy,
                date=date - timedelta(days=1),
            )
