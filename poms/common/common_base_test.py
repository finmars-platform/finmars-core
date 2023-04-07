import random
import string
from datetime import date, datetime, timedelta

from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from poms.accounts.models import Account
from poms.counterparties.models import Counterparty, Responsible
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, InstrumentClass, InstrumentType
from poms.portfolios.models import Portfolio, PortfolioRegister
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.transactions.models import (
    TransactionClass,
    TransactionType,
    TransactionTypeGroup,
    Transaction,
    ComplexTransaction,
)
from poms.users.models import EcosystemDefault, MasterUser


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


class BaseTestCase(TestCase, metaclass=TestMetaClass):
    client: APIClient = None
    patchers: list = []

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
    def random_future_date(cls, interval=30) -> date:
        days = cls.random_int(1, interval)
        return datetime.now().date() + timedelta(days=days)

    @classmethod
    def random_choice(cls, choices: list):
        return random.choice(choices)

    def init_test_case(self):
        self.client = APIClient()
        self.db_data = DbInitializer()


MASTER_USER = "Experimental_Master"
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
INSTRUMENTS = [
    ("Apple", "stocks", InstrumentClass.GENERAL),
    ("Boeing", "stocks", InstrumentClass.GENERAL),
    ("Tesla", "stocks", InstrumentClass.GENERAL),
    ("Pfizer", "stocks", InstrumentClass.GENERAL),
    ("Bitcoin", "Crypto", InstrumentClass.CONTRACT_FOR_DIFFERENCE),
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


class DbInitializer:
    def get_or_create_master_user(self) -> MasterUser:
        master_user = MasterUser.objects.first() or MasterUser.objects.create_master_user(
            name=MASTER_USER,
            journal_status="disabled",
            base_api_url=settings.BASE_API_URL,
        )
        EcosystemDefault.objects.get_or_create(master_user=master_user)
        return master_user

    def create_unified_group(self):
        return TransactionTypeGroup.objects.filter(
            name=UNIFIED,
            user_code=UNIFIED,
            short_name=UNIFIED,
        ).first() or TransactionTypeGroup.objects.create(
            master_user=self.master_user,
            name=UNIFIED,
            user_code=UNIFIED,
            short_name=UNIFIED,
        )

    def get_or_create_default_instrument(self):
        return Instrument.objects.filter(
            user_code="-",
        ).first() or Instrument.objects.create(
            master_user=self.master_user,
            name="-",
            user_code="-",
            short_name="-",
            public_name="-",
            instrument_type=InstrumentType.objects.first(),
            accrued_currency=self.usd,
            pricing_currency=self.usd,
            maturity_date=date.today(),
        )

    def get_or_create_instruments(self) -> dict:
        instruments = {}
        for name, type_, class_id in INSTRUMENTS:
            instrument_type = InstrumentType.objects.filter(
                name=type_,
            ).first() or InstrumentType.objects.create(
                master_user=self.master_user,
                instrument_class_id=class_id,
                name=type_,
                user_code=type_,
                short_name=type_,
                public_name=type_,
            )
            instrument = Instrument.objects.filter(
                name=name,
            ).first() or Instrument.objects.create(
                master_user=self.master_user,
                instrument_type=instrument_type,
                name=name,
                accrued_currency=self.usd,
                pricing_currency=self.usd,
                maturity_date=date.today(),
            )
            if not instrument.maturity_date:
                instrument.maturity_date = date.today()
                instrument.save()

            instruments[name] = instrument
        return instruments

    def create_accounts_and_portfolios(self) -> tuple:
        portfolios = {}
        accounts = {}
        for name in PORTFOLIOS:
            account = Account.objects.filter(
                name=name
            ).first() or Account.objects.create(
                master_user=self.master_user,
                name=name,
            )
            accounts[name] = account

            portfolio = Portfolio.objects.filter(
                name=name
            ).first() or Portfolio.objects.create(
                master_user=self.master_user,
                name=name,
            )
            portfolio.accounts.clear()
            portfolio.accounts.add(account)
            portfolio.save()

            portfolios[name] = portfolio

        return accounts, portfolios

    def get_or_create_currency_usd(self):
        return Currency.objects.filter(
            user_code=USD,
        ).first() or Currency.objects.create(
            master_user=self.master_user,
            user_code=USD,
            name=USD,
            default_fx_rate=1,
        )

    def get_or_create_types(self) -> dict:
        types = {}
        for name in TRANSACTIONS_TYPES:
            type_obj = TransactionType.objects.filter(
                user_code=name,
            ).first() or TransactionType.objects.create(
                master_user=self.master_user,
                name=name,
                user_code=name,
                short_name=name,
                group=self.group,
            )
            types[name] = type_obj

        return types

    def get_or_create_classes(self) -> dict:
        classes = {}
        for class_id in TRANSACTIONS_CLASSES:
            name = f"transaction_class_{class_id}"
            record = TransactionClass.objects.filter(
                id=class_id
            ).first() or TransactionClass.objects.create(
                id=class_id,
                user_code=name,
                name=name,
                short_name=name,
            )
            classes[class_id] = record
        return classes

    def get_or_create_strategies(self):
        strategies = {}
        for i, model in enumerate([Strategy1, Strategy2, Strategy3]):
            if not (strategy := model.objects.first()):
                strategy = model.objects.create(
                    master_user=self.master_user,
                    name=f"strategy_{i+1}",
                )
            strategies[i + 1] = strategy
        return strategies

    def create_counter_party(self):
        name = "test_counter_party"
        return Counterparty.objects.first() or Counterparty.objects.create(
            master_user=self.master_user,
            name=name,
            user_code=name,
            short_name=name,
        )

    def create_responsible(self):
        name = "test_responsible"
        return Responsible.objects.first() or Responsible.objects.create(
            master_user=self.master_user,
            name=name,
            user_code=name,
            short_name=name,
        )

    def cash_in_transaction(self, portfolio: Portfolio, amount: int = 1000) -> tuple:
        notes = f"Cash In {amount} {self.usd}"
        op_date = date.today()
        complex_transaction = ComplexTransaction.objects.create(
            master_user=self.master_user,
            date=op_date,
            transaction_type=self.transaction_types[DEPOSIT],
            text=notes,
            user_text_10="1M",
        )
        account = portfolio.accounts.first()
        transaction = Transaction.objects.create(
            master_user=self.master_user,
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
            responsible=self.responsible,
            strategy1_cash=self.strategies[1],
            strategy1_position=self.strategies[1],
            strategy2_cash=self.strategies[2],
            strategy2_position=self.strategies[2],
            strategy3_cash=self.strategies[3],
            strategy3_position=self.strategies[3],
            notes=notes,
        )
        return complex_transaction, transaction

    def create_portfolio_register(self, portfolio: Portfolio, instrument: Instrument):
        return PortfolioRegister.objects.filter(
            portfolio=portfolio,
            linked_instrument=instrument,
        ).first() or PortfolioRegister.objects.create(
            master_user=self.master_user or MasterUser.objects.first(),
            portfolio=portfolio,
            linked_instrument=instrument,
            valuation_currency=self.usd,
        )

    def __init__(self):
        self.master_user = self.get_or_create_master_user()
        self.group = self.create_unified_group()
        self.usd = self.get_or_create_currency_usd()
        self.strategies = self.get_or_create_strategies()
        self.counter_party = self.create_counter_party()
        self.responsible = self.create_responsible()
        self.accounts, self.portfolios = self.create_accounts_and_portfolios()
        self.transaction_types = self.get_or_create_types()
        self.instruments = self.get_or_create_instruments()
        self.transaction_classes = self.get_or_create_classes()
        self.transaction_types = self.get_or_create_types()
        self.instruments = self.get_or_create_instruments()
        self.default_instrument = self.get_or_create_default_instrument()
        print("----------- db initialized with mandatory data -------------")
