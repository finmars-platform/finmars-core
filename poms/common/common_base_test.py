import random
import string
from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.test import TestCase  # TransactionTestCase
from rest_framework.test import APIClient

import dateutil.utils

from poms.accounts.models import Account, AccountType
from poms.common.constants import SystemValueType
from poms.counterparties.models import (
    Counterparty,
    CounterpartyGroup,
    Responsible,
    ResponsibleGroup,
)
from poms.currencies.models import Currency
from poms.instruments.models import (
    AccrualCalculationModel,
    AccrualCalculationSchedule,
    Country,
    DailyPricingModel,
    ExposureCalculationModel,
    Instrument,
    InstrumentClass,
    InstrumentFactorSchedule,
    InstrumentType,
    LongUnderlyingExposure,
    PaymentSizeDetail,
    Periodicity,
    PricingCondition,
    PricingPolicy,
    ShortUnderlyingExposure,
)
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.portfolios.models import Portfolio, PortfolioRegister
from poms.strategies.models import (
    Strategy1,
    Strategy2,
    Strategy3,
    Strategy1Group,
    Strategy2Group,
    Strategy3Group,
    Strategy1Subgroup,
    Strategy2Subgroup,
    Strategy3Subgroup,
)

from poms.transactions.models import (
    ComplexTransaction,
    Transaction,
    TransactionClass,
    TransactionType,
    TransactionTypeGroup,
)
from poms.users.models import EcosystemDefault, MasterUser, Member

# TEST_CASE = TransactionTestCase  # if settings.USE_DB_REPLICA == True
TEST_CASE = TestCase

MASTER_USER = "test_master"
FINMARS_BOT = "finmars_bot"
FINMARS_USER = "test_user"
BUY_SELL = "Buy/Sell_unified"
DEPOSIT = "Deposits/Withdraw_unified"
FX = "FX/Forwards_unified"
INSTRUMENT_EXP = "Expense/Income (Instrument)_unified"
NON_INSTRUMENT_EXP = "Expense/Income (Non-Instrument)_unified"

TRANSACTIONS_TYPES = [
    BUY_SELL,
    DEPOSIT,
    FX,
    INSTRUMENT_EXP,
    NON_INSTRUMENT_EXP,
]
INITIAL_TYPE_PREFIX = "local.poms.space00000"
INITIAL_INSTRUMENTS_TYPES = [
    f"{INITIAL_TYPE_PREFIX}:bond",
    f"{INITIAL_TYPE_PREFIX}:stock",
]
STANDARD_TYPE_BOND = f"{settings.INSTRUMENT_TYPE_PREFIX}:bond"
STANDARD_TYPE_STOCK = f"{settings.INSTRUMENT_TYPE_PREFIX}:stock"

IDENTIFIERS = [
    {
        "cbonds_id": "id",
        "isin": "isin",
        "state_reg_number": "state_reg_number",
        "bbgid": "bbgid",
        "figi": "bbgid",
        "isin_code_144a": "isin_code_144a",
        "sedol": "sedol",
        "database_id": "",
    },
    {
        "cbonds_id": None,
        "isin": "isin",
        "state_reg_number": "state_reg_number",
        "bbgid": "bbgid",
        "figi": "bbgid",
        "isin_code_144a": "isin_code_144a",
        "sedol": "sedol",
        "database_id": "",
    },
]


INSTRUMENTS = [
    ("Apple", INITIAL_INSTRUMENTS_TYPES[0], InstrumentClass.GENERAL, IDENTIFIERS[0]),
    ("Tesla B.", INITIAL_INSTRUMENTS_TYPES[1], InstrumentClass.GENERAL, IDENTIFIERS[1]),
]
TRANSACTIONS_CLASSES = [
    TransactionClass.CASH_INFLOW,
    TransactionClass.CASH_OUTFLOW,
    TransactionClass.BUY,  # must include instrument
    TransactionClass.SELL,  # must include instrument
    TransactionClass.FX_TRADE,
    TransactionClass.TRANSACTION_PL,
    TransactionClass.INSTRUMENT_PL,  # must include instrument
]
BIG = "Big"
SMALL = "Small"
PORTFOLIOS = [BIG, SMALL]
UNIFIED = "Unified"

USD = "USD"
EUR = "EUR"
CURRENCIES = [
    (USD, 1),
    (EUR, 1.1),
]


def show_all_urls():
    """
    Print all urls in the project
    """
    from django.urls import get_resolver

    def print_urls(resolver, prefix="/"):
        for url_pattern in resolver.url_patterns:
            if hasattr(url_pattern, "url_patterns"):
                print_urls(
                    url_pattern,
                    prefix=f"{prefix}{url_pattern.pattern.regex.pattern}",
                )
            else:
                print(f"{prefix}{url_pattern.pattern.regex.pattern}")

    print("------------------------------------------------")
    django_resolver = get_resolver(None)
    print_urls(django_resolver)
    print("------------------------------------------------")


def print_namespace():
    from django import urls

    url_resolver = urls.get_resolver(urls.get_urlconf())
    print("namespaces=", url_resolver.namespace_dict.keys())


def print_patterns(patterns, namespace="rest_framework"):
    # # Get the URL resolver for the current Django app
    # from django.urls import get_resolver
    # resolver = get_resolver()
    #
    # # Get all URL patterns
    # url_patterns = resolver.url_patterns
    #
    # # Print all patterns and namespaces
    # print_patterns(url_patterns)

    for pattern in patterns:
        if hasattr(pattern, "url_patterns"):
            # It's a URL pattern group, so recurse
            new_namespace = (
                namespace + pattern.namespace + ":" if pattern.namespace else ""
            )
            print_patterns(pattern.url_patterns, new_namespace)
        elif hasattr(pattern, "callback") and hasattr(pattern.callback, "__name__"):
            # It's a URL patter
            print(
                f"pattern: {pattern.pattern} name: {pattern.name}  namespace: "
                f"{namespace}  view.name: {pattern.callback.__name__}"
            )


# noinspection SqlNoDataSourceInspection
def change_created_time(instance: models.Model, new_time: datetime):
    if not isinstance(new_time, datetime):
        raise ValueError(f"value {new_time} must be a datetime object!")

    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {instance._meta.db_table} SET created_at='{new_time.isoformat()}' "
            f"WHERE id={instance.id}",
        )


def print_all_users(title: str):
    print(f"=================={title}=======================")

    print("user - default")
    for user in User.objects.using(settings.DB_DEFAULT).all():
        print(
            user.id,
            user.username,
        )
    print("+")
    print("user - replica")
    for user in User.objects.using(settings.DB_REPLICA).all():
        print(
            user.id,
            user.username,
        )

    print("-" * 40)

    print("member - default")
    for member in Member.objects.using(settings.DB_DEFAULT).all():
        print(member.id, member.username)
    print("+")
    print("member - replica")
    for member in Member.objects.using(settings.DB_REPLICA).all():
        print(member.id, member.username)

    print("-" * 40)

    print("master - default")
    for master in MasterUser.objects.using(settings.DB_DEFAULT).all():
        print(master.id, master.name)
    print("+")
    print("master - replica")
    for master in MasterUser.objects.using(settings.DB_REPLICA).all():
        print(master.id, master.name)


def clear_users_tables(db_name: str = settings.DB_REPLICA):
    from django.db import connections

    with connections[db_name].cursor() as cursor:
        # for table_name in connection.introspection.table_names():
        for table_name in ["auth_user", "users_member", "users_masteruser"]:
            cursor.execute(f"TRUNCATE TABLE {table_name} CASCADE;")


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code
        self.content = str(json_data)

    def json(self):
        return self.json_data


class TestMetaClass(type):
    def __new__(mcs, name, bases, dct):
        # sourcery skip: class-method-first-arg-name
        for attr_name in list(dct.keys()):
            if hasattr(dct[attr_name], "test_cases"):
                cases = dct[attr_name].test_cases
                del dct[attr_name].test_cases
                hidden_name = f"__{attr_name}"
                mcs._move_method(dct, attr_name, hidden_name)

                for case in cases:
                    mcs._add_test_method(dct, attr_name, hidden_name, case[0], case[1:])

        return super(TestMetaClass, mcs).__new__(mcs, name, bases, dct)

    @classmethod
    def _move_method(mcs, dct, from_name, to_name):
        # sourcery skip: class-method-first-arg-name
        dct[to_name] = dct[from_name]
        dct[to_name].__name__ = str(to_name)
        del dct[from_name]

    @classmethod
    def _add_test_method(mcs, dct, orig_name, hidden_name, postfix, params):
        test_method_name = "{}__{}".format(orig_name, postfix)

        def test_method(self):
            return getattr(self, hidden_name)(*params)

        test_method.__name__ = test_method_name
        dct[test_method_name] = test_method


class BaseTestCase(TEST_CASE, metaclass=TestMetaClass):
    client: APIClient = None

    @classmethod
    def cases(cls, *cases):
        """
        Create a bunch of test methods using the case table and test code.
        Example. The following two pieces of code would behave identically:

        @BaseTestCase.cases(['name1', 1], ['name2', 2])
        def test_example(self, number):
            self.assertGreater(number, 0)

        def __test_example(self, number):
            self.assertGreater(number, 0)
        def test_example__name1(self):
            return self.__test_example(1)
        def test_example__name2(self):
            return self.__test_example(2)
        """

        def decorator(test_method):
            test_method.test_cases = cases
            return test_method

        return decorator

    @classmethod
    def random_percent(cls) -> float:
        return random.random()

    @classmethod
    def random_float(cls, _min: int = 1, _max: int = 10000) -> float:
        return random.random() * random.randint(_min, _max)

    @classmethod
    def random_int(cls, _min: int = 1, _max: int = 10000) -> int:
        return random.randint(_min, _max)

    @classmethod
    def random_string(cls, length: int = 10) -> str:
        return "".join(
            random.SystemRandom().choice(string.ascii_uppercase) for _ in range(length)
        )

    @classmethod
    def random_email(cls) -> str:
        return f"{cls.random_string(5)}@{cls.random_string(3)}.{cls.random_string(2)}"

    @classmethod
    def today(cls) -> date:
        return dateutil.utils.today().date()

    @classmethod
    def yesterday(cls) -> date:
        return cls.today() - timedelta(days=1)

    @classmethod
    def random_future_date(cls, interval: int = 365 * 50) -> date:
        days = cls.random_int(_max=interval)
        return cls.today() + timedelta(days=days)

    @classmethod
    def random_choice(cls, choices: list):
        return random.choice(choices)

    @staticmethod
    def get_instrument_type(
        instrument_type: str = INITIAL_INSTRUMENTS_TYPES[0],
    ) -> InstrumentType:
        return InstrumentType.objects.using(settings.DB_DEFAULT).get(
            user_code__contains=instrument_type
        )

    @staticmethod
    def get_currency(user_code: str = "EUR") -> Currency:
        return Currency.objects.using(settings.DB_DEFAULT).get(user_code=user_code)

    @staticmethod
    def get_pricing_condition(model_id=PricingCondition.NO_VALUATION):
        return PricingCondition.objects.using(settings.DB_DEFAULT).get(id=model_id)

    @staticmethod
    def get_exposure_calculation(model_id=ExposureCalculationModel.MARKET_VALUE):
        return ExposureCalculationModel.objects.using(settings.DB_DEFAULT).get(
            id=model_id
        )

    @staticmethod
    def get_payment_size(model_id=PaymentSizeDetail.PERCENT):
        return PaymentSizeDetail.objects.using(settings.DB_DEFAULT).get(id=model_id)

    @staticmethod
    def get_daily_pricing(model_id=DailyPricingModel.DEFAULT):
        return DailyPricingModel.objects.using(settings.DB_DEFAULT).get(id=model_id)

    @staticmethod
    def get_long_under_exp(model_id=LongUnderlyingExposure.ZERO):
        return LongUnderlyingExposure.objects.using(settings.DB_DEFAULT).get(
            id=model_id
        )

    @staticmethod
    def get_short_under_exp(model_id=ShortUnderlyingExposure.ZERO):
        return ShortUnderlyingExposure.objects.using(settings.DB_DEFAULT).get(
            id=model_id
        )

    @staticmethod
    def get_country(name="Italy"):
        return Country.objects.using(settings.DB_DEFAULT).get(name=name)

    @staticmethod
    def get_accrual_calculation_model(
        model_id=AccrualCalculationModel.DAY_COUNT_ACT_ACT_ISDA,
    ):
        return AccrualCalculationModel.objects.using(settings.DB_DEFAULT).get(
            id=model_id
        )

    @staticmethod
    def get_periodicity(model_id=Periodicity.N_DAY):
        return Periodicity.objects.using(settings.DB_DEFAULT).get(id=model_id)

    def create_accrual(self, instrument: Instrument) -> AccrualCalculationSchedule:
        return AccrualCalculationSchedule.objects.using(settings.DB_DEFAULT).create(
            instrument=instrument,
            accrual_start_date=self.random_future_date().strftime("%Y-%m-%d"),
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
        return InstrumentFactorSchedule.objects.using(settings.DB_DEFAULT).create(
            instrument=instrument,
            effective_date=self.random_future_date(),
            factor_value=self.random_percent(),
        )

    def create_instrument(
        self,
        instrument_type: str = INITIAL_INSTRUMENTS_TYPES[0],
        currency_code: str = "EUR",
    ) -> Instrument:
        currency = self.get_currency(user_code=currency_code)
        instrument = Instrument.objects.using(settings.DB_DEFAULT).create(
            # mandatory fields
            master_user=self.master_user,
            owner=self.member,
            instrument_type=self.get_instrument_type(instrument_type),
            pricing_currency=currency,
            accrued_currency=currency,
            name=self.random_string(11),
            maturity_date=self.random_future_date(),
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
        instrument.attributes.set([self.create_attribute()])
        instrument.save()
        if instrument_type == INITIAL_INSTRUMENTS_TYPES[0]:
            self.create_accrual(instrument)
            self.create_factor(instrument)

        return instrument

    def create_attribute_type(
        self, content_type=None, value_type=GenericAttributeType.NUMBER
    ) -> GenericAttributeType:
        return GenericAttributeType.objects.using(settings.DB_DEFAULT).create(
            master_user=self.master_user,
            owner=self.member,
            content_type=content_type
            or ContentType.objects.using(settings.DB_DEFAULT).first(),
            user_code=self.random_string(5),
            short_name=self.random_string(2),
            value_type=value_type,
            kind=GenericAttributeType.USER,
            tooltip=self.random_string(),
            favorites=self.random_string(),
            prefix=self.random_string(3),
            expr=self.random_string(),
        )

    def create_attribute(
        self, attribute_type=None, object_id=None, content_type=None
    ) -> GenericAttribute:
        return GenericAttribute.objects.using(settings.DB_DEFAULT).create(
            attribute_type=attribute_type or self.create_attribute_type(),
            content_type=content_type
            or ContentType.objects.using(settings.DB_DEFAULT).first(),
            object_id=object_id or self.random_int(),
            value_string=self.random_string(),
            value_float=self.random_int(),
            value_date=self.random_future_date(),
        )

    def create_account_type(self) -> AccountType:
        account_type = AccountType.objects.using(settings.DB_DEFAULT).create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            short_name=self.random_string(3),
            transaction_details_expr=self.random_string(),
        )
        return self._add_attributes(account_type)

    def create_account(self) -> Account:
        self.account = Account.objects.using(settings.DB_DEFAULT).create(
            master_user=self.master_user,
            owner=self.member,
            type=self.create_account_type(),
            user_code=self.random_string(),
            short_name=self.random_string(3),
        )
        return self._add_attributes(self.account)

    def _add_attributes(self, model):
        model.attributes.set([self.create_attribute()])
        model.save()
        return model

    def create_instruments_types(self):
        for type_ in INITIAL_INSTRUMENTS_TYPES:
            InstrumentType.objects.using(settings.DB_DEFAULT).get_or_create(
                master_user=self.master_user,
                user_code=type_,
                defaults=dict(
                    owner=self.member,
                    instrument_class_id=InstrumentClass.GENERAL,
                    name=type_,
                    short_name=type_,
                    public_name=type_,
                ),
            )

    def create_currencies(self):
        for currency in CURRENCIES:
            Currency.objects.using(settings.DB_DEFAULT).get_or_create(
                master_user=self.master_user,
                owner=self.member,
                user_code=currency[0],
                defaults=dict(
                    name=currency[0],
                    default_fx_rate=currency[1],
                ),
            )

    def get_or_create_default_instrument(self):
        self.instrument_type, _ = InstrumentType.objects.using(
            settings.DB_DEFAULT
        ).get_or_create(
            master_user=self.master_user,
            user_code=INITIAL_TYPE_PREFIX,
            defaults=dict(
                master_user=self.master_user,
                owner=self.member,
                instrument_class_id=InstrumentClass.GENERAL,
                name="-",
                short_name="-",
                public_name="-",
            ),
        )

        instrument, _ = Instrument.objects.using(settings.DB_DEFAULT).get_or_create(
            master_user=self.master_user,
            user_code="-",
            defaults=dict(
                owner=self.member,
                instrument_type=self.instrument_type,
                name="-",
                short_name="-",
                public_name="-",
                accrued_currency=self.usd,
                pricing_currency=self.usd,
                maturity_date=self.random_future_date(),
            ),
        )
        return instrument

    def create_pricing_policy(self) -> GenericAttributeType:
        name = "pricing_policy"
        return PricingPolicy.objects.using(settings.DB_DEFAULT).create(
            master_user=self.master_user,
            owner=self.member,
            user_code=name,
            name=name,
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.ecosystem = None
        self.default_instrument = None
        self.master_user = None
        self.member = None
        self.usd = None
        self.eur = None
        self.user = None
        self.account_type = None
        self.account = None
        self.instrument_type = None
        self.db_data = None
        self.realm_code = "realm0000"
        self.space_code = "space0000"

    def init_test_case(self):
        self.client = APIClient()

        self.master_user, _ = MasterUser.objects.using(
            settings.DB_DEFAULT
        ).get_or_create(
            space_code="space00000",
            defaults=dict(
                name=MASTER_USER,
                journal_status="disabled",
            ),
        )
        self.user, _ = User.objects.using(settings.DB_DEFAULT).get_or_create(
            username=FINMARS_USER,
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(self.user)

        self.member, _ = Member.objects.using(settings.DB_DEFAULT).get_or_create(
            user=self.user,
            master_user=self.master_user,
            username=FINMARS_BOT,
            defaults=dict(
                is_admin=True,
                is_owner=True,
            ),
        )

        self.create_currencies()
        self.usd = Currency.objects.using(settings.DB_DEFAULT).get(user_code=USD)
        self.eur = Currency.objects.using(settings.DB_DEFAULT).get(user_code=EUR)
        self.create_instruments_types()
        self.default_instrument = self.get_or_create_default_instrument()
        self.ecosystem, _ = EcosystemDefault.objects.using(
            settings.DB_DEFAULT
        ).get_or_create(
            master_user=self.master_user,
            currency=self.usd,
            instrument=self.default_instrument,
        )
        self.account_type = self.create_account_type()
        self.account = self.create_account()
        self.db_data = DbInitializer(
            master_user=self.master_user,
            member=self.member,
            ecosystem=self.ecosystem,
        )


class DbInitializer:
    def __init__(self, master_user, member, ecosystem):
        self.master_user = master_user
        self.member = member
        self.default_ecosystem = ecosystem

        if settings.USE_DB_REPLICA:
            print_all_users("DbInitializer")

        self.usd = Currency.objects.using(settings.DB_DEFAULT).get(user_code=USD)
        self.default_instrument = Instrument.objects.using(settings.DB_DEFAULT).get(
            user_code="-"
        )

        self.portfolios = self.create_accounts_and_portfolios()
        self.counter_party = self.create_counter_party()
        self.transaction_types = self.get_or_create_transaction_types()
        self.transaction_classes = self.get_or_create_classes()
        self.instruments = self.get_or_create_instruments()
        self.strategies = self.create_strategies()
        self.strategy_groups = self.create_strategy_groups()
        self.strategy_subgroups = self.create_strategy_subgroups()

        print(
            f"\n{'-'*30} db initialized, master_user={self.master_user.id} {'-'*30}\n"
        )

    def get_or_create_instruments(self) -> dict:
        instruments = {}
        for name, type_, class_id, identifier in INSTRUMENTS:
            instrument_type, _ = InstrumentType.objects.using(
                settings.DB_DEFAULT
            ).get_or_create(
                master_user=self.master_user,
                user_code=type_,
                defaults=dict(
                    owner=self.member,
                    instrument_class_id=class_id,
                    name=type_,
                    short_name=type_,
                    public_name=type_,
                ),
            )
            instrument, _ = Instrument.objects.using(settings.DB_DEFAULT).get_or_create(
                master_user=self.master_user,
                user_code=name,
                defaults=dict(
                    owner=self.member,
                    instrument_type=instrument_type,
                    name=name,
                    short_name=name,
                    identifier=identifier,
                    public_name=name,
                    accrued_currency=self.usd,
                    pricing_currency=self.usd,
                    maturity_date=BaseTestCase().random_future_date(),
                ),
            )
            instruments[name] = instrument
        return instruments

    def create_portfolio_register(
        self, portfolio: Portfolio, instrument: Instrument, user_code: str
    ) -> PortfolioRegister:
        pr, _ = PortfolioRegister.objects.using(settings.DB_DEFAULT).get_or_create(
            master_user=self.master_user,
            user_code=user_code,
            portfolio=portfolio,
            owner=self.member,
            linked_instrument=instrument,
            defaults=dict(
                valuation_currency=self.usd,
                name=user_code,
                short_name=user_code,
            ),
        )
        return pr

    def create_accounts_and_portfolios(self) -> dict:
        portfolios = {}
        for name in PORTFOLIOS:
            account, _ = Account.objects.using(settings.DB_DEFAULT).get_or_create(
                master_user=self.master_user,
                owner=self.member,
                user_code=name,
                defaults=dict(
                    name=name,
                    short_name=name,
                ),
            )
            portfolio, _ = Portfolio.objects.using(settings.DB_DEFAULT).get_or_create(
                master_user=self.master_user,
                owner=self.member,
                user_code=name,
                defaults=dict(
                    name=name,
                    short_name=name,
                ),
            )
            portfolio.accounts.clear()
            portfolio.accounts.add(account)
            portfolio.save()
            portfolios[name] = portfolio
            self.create_portfolio_register(
                portfolio=portfolio,
                instrument=self.default_instrument,
                user_code=name,
            )

        return portfolios

    def create_unified_transaction_group(self):
        group, _ = TransactionTypeGroup.objects.using(
            settings.DB_DEFAULT
        ).get_or_create(
            master_user=self.master_user,
            owner=self.member,
            name=UNIFIED,
            defaults=dict(
                user_code=UNIFIED,
                short_name=UNIFIED,
            ),
        )
        return group

    def get_or_create_transaction_types(self) -> dict:
        tr_group = self.create_unified_transaction_group()
        types = {}
        for name in TRANSACTIONS_TYPES:
            types[name], _ = TransactionType.objects.using(
                settings.DB_DEFAULT
            ).get_or_create(
                master_user=self.master_user,
                owner=self.member,
                user_code=name,
                defaults=dict(
                    group=tr_group.user_code,
                    name=name,
                    short_name=name,
                ),
            )

        return types

    @staticmethod
    def get_or_create_classes() -> dict:
        classes = {}
        for class_id in TRANSACTIONS_CLASSES:
            name = f"transaction_class_{class_id}"
            classes[class_id], _ = TransactionClass.objects.using(
                settings.DB_DEFAULT
            ).get_or_create(
                id=class_id,
                defaults=dict(
                    user_code=name,
                    name=name,
                    short_name=name,
                ),
            )
        return classes

    def create_strategy_groups(self):
        groups = {}
        for i, model in enumerate([Strategy1Group, Strategy2Group, Strategy3Group]):
            group, _ = model.objects.using(settings.DB_DEFAULT).get_or_create(
                master_user=self.master_user,
                owner=self.member,
                defaults={
                    "name": f"strategy_group_{i+1}",
                },
            )
            groups[i + 1] = group

        return groups

    def create_strategy_subgroups(self):
        sub_groups = {}
        for i, model in enumerate(
            [Strategy1Subgroup, Strategy2Subgroup, Strategy3Subgroup], start=1
        ):
            sub_group, _ = model.objects.using(settings.DB_DEFAULT).get_or_create(
                master_user=self.master_user,
                owner=self.member,
                defaults={
                    "name": f"sub_strategy_group_{i}",
                },
            )
            sub_groups[i] = sub_group

        return sub_groups

    def create_strategies(self):
        strategies = {}
        for i, model in enumerate([Strategy1, Strategy2, Strategy3]):
            if not (strategy := model.objects.using(settings.DB_DEFAULT).first()):
                strategy = model.objects.using(settings.DB_DEFAULT).create(
                    master_user=self.master_user,
                    owner=self.member,
                    name=f"strategy_{i+1}",
                )
            strategies[i + 1] = strategy
        return strategies

    def create_counterparty_group(self) -> CounterpartyGroup:
        group_name = "test_counterparty_group"
        cp_group, _ = CounterpartyGroup.objects.using(
            settings.DB_DEFAULT
        ).get_or_create(
            master_user=self.master_user,
            user_code=group_name,
            owner=self.member,
            defaults=dict(
                name=group_name,
                short_name=group_name,
            ),
        )
        return cp_group

    def create_counter_party(self) -> Counterparty:
        name = "test_company"
        company, _ = Counterparty.objects.using(settings.DB_DEFAULT).get_or_create(
            master_user=self.master_user,
            owner=self.member,
            group=self.create_counterparty_group(),
            user_code=name,
            defaults=dict(
                name=name,
                short_name=name,
            ),
        )
        return company

    def create_responsible_group(self) -> ResponsibleGroup:
        name = "test_responsible_group"
        group, _ = ResponsibleGroup.objects.using(settings.DB_DEFAULT).get_or_create(
            master_user=self.master_user,
            owner=self.member,
            user_code=name,
            defaults=dict(
                name=name,
                short_name=name,
            ),
        )
        return group

    def create_responsible(self) -> Responsible:
        name = "test_responsible"
        responsible, _ = Responsible.objects.using(settings.DB_DEFAULT).get_or_create(
            master_user=self.master_user,
            owner=self.member,
            user_code=name,
            group=self.create_responsible_group(),
            defaults=dict(
                name=name,
                short_name=name,
            ),
        )
        return responsible

    def cash_in_transaction(
        self, portfolio: Portfolio, amount: int = 1000, day: date = None
    ) -> tuple:
        notes = f"Cash In {amount} {self.usd}"
        op_date = day or date.today()
        complex_transaction = ComplexTransaction.objects.using(
            settings.DB_DEFAULT
        ).create(
            master_user=self.master_user,
            owner=self.member,
            date=op_date,
            transaction_type=self.transaction_types[DEPOSIT],
            text=notes,
            user_text_10="1M",
        )
        responsible = self.create_responsible()
        account = portfolio.accounts.first()
        transaction = Transaction.objects.using(settings.DB_DEFAULT).create(
            master_user=self.master_user,
            owner=self.member,
            account_position=account,
            account_cash=account,
            account_interim=account,
            complex_transaction=complex_transaction,
            portfolio=portfolio,
            transaction_date=op_date,
            accounting_date=op_date,
            cash_date=op_date,
            settlement_currency=self.usd,
            transaction_currency=self.usd,
            cash_consideration=amount,
            carry_with_sign=0,
            overheads_with_sign=0,
            transaction_class=self.transaction_classes[TransactionClass.CASH_INFLOW],
            factor=1,
            reference_fx_rate=1,
            instrument=self.default_instrument,
            allocation_pl=self.default_instrument,
            linked_instrument=self.default_instrument,
            allocation_balance=self.default_instrument,
            counterparty=self.counter_party,
            responsible=responsible,
            strategy1_cash=self.strategies[1],
            strategy1_position=self.strategies[1],
            strategy2_cash=self.strategies[2],
            strategy2_position=self.strategies[2],
            strategy3_cash=self.strategies[3],
            strategy3_position=self.strategies[3],
            notes=notes,
        )
        return complex_transaction, transaction
