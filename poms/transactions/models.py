import json
import logging
import time
import traceback
from datetime import date
from math import isclose, isnan

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction
from django.utils.translation import gettext_lazy

from poms.accounts.models import Account
from poms.common.formula_accruals import f_xirr
from poms.common.models import (
    EXPRESSION_FIELD_LENGTH,
    AbstractClassModel,
    FakeDeletableModel,
    NamedModel,
    TimeStampedModel,
)
from poms.common.utils import date_now
from poms.configuration.models import ConfigurationModel
from poms.counterparties.models import Counterparty, Responsible
from poms.currencies.models import Currency, CurrencyHistory
from poms.instruments.models import (
    EventSchedule,
    Instrument,
    InstrumentClass,
    PricingPolicy,
)
from poms.obj_attrs.models import GenericAttribute
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.users.models import EcosystemDefault, FakeSequence, MasterUser

_l = logging.getLogger("poms.transactions")


class TransactionClass(AbstractClassModel):
    BUY = 1
    SELL = 2
    FX_TRADE = 3
    INSTRUMENT_PL = 4
    TRANSACTION_PL = 5
    TRANSFER = 6
    FX_TRANSFER = 7
    CASH_INFLOW = 8  # if portfolio registry, position increase
    CASH_OUTFLOW = 9  # if portfolio registry, position decrease

    DEFAULT = 10
    PLACEHOLDER = 11

    INJECTION = 12  # if portfolio registry, # share price increase
    DISTRIBUTION = 13  # if portfolio registry, # share price decrease

    INITIAL_POSITION = 14
    INITIAL_CASH = 15

    CLASSES = (
        (BUY, "BUY", gettext_lazy("Buy")),
        (SELL, "SELL", gettext_lazy("Sell")),
        (FX_TRADE, "FX_TRADE", gettext_lazy("FX Trade")),
        (INSTRUMENT_PL, "INSTRUMENT_PL", gettext_lazy("Instrument PL")),
        (TRANSACTION_PL, "TRANSACTION_PL", gettext_lazy("Transaction PL")),
        (TRANSFER, "TRANSFER", gettext_lazy("Transfer")),
        (FX_TRANSFER, "FX_TRANSFER", gettext_lazy("FX Transfer")),
        (CASH_INFLOW, "CASH_INFLOW", gettext_lazy("Cash-Inflow")),
        (CASH_OUTFLOW, "CASH_OUTFLOW", gettext_lazy("Cash-Outflow")),
        (DEFAULT, "-", gettext_lazy("Default")),
        (PLACEHOLDER, "PLACEHOLDER", gettext_lazy("Technical: Placeholder")),
        (INJECTION, "CASH_INJECTION", gettext_lazy("Cash-Injection")),
        (DISTRIBUTION, "CASH_DISTRIBUTION", gettext_lazy("Cash-Distribution")),
        (
            INITIAL_POSITION,
            "DATE_BALANCE_POSITION",
            gettext_lazy("Date Balance: Position"),
        ),
        (INITIAL_CASH, "DATE_BALANCE_CASH", gettext_lazy("Date Balance: Cash")),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("transaction class")
        verbose_name_plural = gettext_lazy("transaction classes")


class ComplexTransactionStatus(AbstractClassModel):
    BOOKED = 1
    PENDING = 2
    IGNORE = 3

    CLASSES = (
        (BOOKED, "BOOKED", gettext_lazy("Booked")),
        (PENDING, "PENDING", gettext_lazy("Pending")),
        (IGNORE, "IGNORE", gettext_lazy("Ignore")),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("complex transaction status")
        verbose_name_plural = gettext_lazy("complex transaction status")


class ActionClass(AbstractClassModel):
    CREATE_INSTRUMENT = 1
    CREATE_INSTRUMENT_PARAMETER = 2

    CLASSES = (
        (CREATE_INSTRUMENT, "CREATE_INSTRUMENT", gettext_lazy("Create instrument")),
        (
            CREATE_INSTRUMENT_PARAMETER,
            "CREATE_INSTRUMENT_PARAMETER",
            gettext_lazy("Create instrument parameter"),
        ),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("action class")
        verbose_name_plural = gettext_lazy("action classes")


class EventClass(AbstractClassModel):
    ONE_OFF = 1
    REGULAR = 2

    CLASSES = (
        (ONE_OFF, "ONE_OFF", gettext_lazy("One-off")),
        (REGULAR, "REGULAR", gettext_lazy("Regular")),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("event class")
        verbose_name_plural = gettext_lazy("event classes")


class NotificationClass(AbstractClassModel):
    DONT_REACT = 1
    APPLY_DEF_ON_EDATE = 2
    APPLY_DEF_ON_NDATE = 3

    INFORM_ON_NDATE_WITH_REACT = 4
    INFORM_ON_NDATE_APPLY_DEF = 5
    INFORM_ON_NDATE_DONT_REACT = 6
    INFORM_ON_EDATE_WITH_REACT = 7
    INFORM_ON_EDATE_APPLY_DEF = 8
    INFORM_ON_EDATE_DONT_REACT = 9

    INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_EDATE = 10
    INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_NDATE = 11
    INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_EDATE = 12
    INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_NDATE = 13
    INFORM_ON_NDATE_AND_EDATE_DONT_REACT = 14

    CLASSES = (
        (DONT_REACT, "DONT_REACT", gettext_lazy("Don't inform (don't react)")),
        (
            APPLY_DEF_ON_EDATE,
            "APPLY_DEF_ON_EDATE",
            gettext_lazy("Don't inform (apply default on effective date)"),
        ),
        (
            APPLY_DEF_ON_NDATE,
            "APPLY_DEF_ON_NDATE",
            gettext_lazy("Don't inform (apply default on notification date)"),
        ),
        (
            INFORM_ON_NDATE_WITH_REACT,
            "INFORM_ON_NDATE_WITH_REACT",
            gettext_lazy("Inform on notification date (with reaction)"),
        ),
        (
            INFORM_ON_NDATE_APPLY_DEF,
            "INFORM_ON_NDATE_APPLY_DEF",
            gettext_lazy("Inform on notification date (apply default)"),
        ),
        (
            INFORM_ON_NDATE_DONT_REACT,
            "INFORM_ON_NDATE_DONT_REACT",
            gettext_lazy("Inform on notification date (don't react)"),
        ),
        (
            INFORM_ON_EDATE_WITH_REACT,
            "INFORM_ON_EDATE_WITH_REACT",
            gettext_lazy("Inform on effective date (with reaction)"),
        ),
        (
            INFORM_ON_EDATE_APPLY_DEF,
            "INFORM_ON_EDATE_APPLY_DEF",
            gettext_lazy("Inform on effective date (apply default)"),
        ),
        (
            INFORM_ON_EDATE_DONT_REACT,
            "INFORM_ON_EDATE_DONT_REACT",
            gettext_lazy("Inform on effective date (don't react)"),
        ),
        (
            INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_EDATE,
            "INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_EDATE",
            gettext_lazy("Inform on notification date & effective date (with reaction on effective date)"),
        ),
        (
            INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_NDATE,
            "INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_NDATE",
            gettext_lazy("Inform on notification date & effective date (with reaction on notification date)"),
        ),
        (
            INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_EDATE,
            "INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_EDATE",
            gettext_lazy("Inform on notification date & effective date (apply default on effective date)"),
        ),
        (
            INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_NDATE,
            "INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_NDATE",
            gettext_lazy("Inform on notification date & effective date (apply default on notification date)"),
        ),
        (
            INFORM_ON_NDATE_AND_EDATE_DONT_REACT,
            "INFORM_ON_NDATE_AND_EDATE_DONT_REACT",
            gettext_lazy("Inform on notification date & effective date (don't react)"),
        ),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("notification class")
        verbose_name_plural = gettext_lazy("notification classes")

    @staticmethod
    def get_notify_on_effective_date_classes():
        return [
            NotificationClass.INFORM_ON_EDATE_WITH_REACT,
            NotificationClass.INFORM_ON_EDATE_APPLY_DEF,
            NotificationClass.INFORM_ON_EDATE_DONT_REACT,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_EDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_NDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_EDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_NDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_DONT_REACT,
        ]

    @property
    def is_notify_on_effective_date(self):
        return self.id in NotificationClass.get_notify_on_effective_date_classes()

    @staticmethod
    def get_notify_on_notification_date_classes():
        return [
            NotificationClass.INFORM_ON_NDATE_WITH_REACT,
            NotificationClass.INFORM_ON_NDATE_APPLY_DEF,
            NotificationClass.INFORM_ON_NDATE_DONT_REACT,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_EDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_NDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_EDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_NDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_DONT_REACT,
        ]

    @property
    def is_notify_on_notification_date(self):
        return self.id in NotificationClass.get_notify_on_notification_date_classes()

    @staticmethod
    def get_apply_default_on_effective_date_classes():
        return [
            NotificationClass.APPLY_DEF_ON_EDATE,
            NotificationClass.INFORM_ON_EDATE_APPLY_DEF,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_EDATE,
        ]

    @property
    def is_apply_default_on_effective_date(self):
        return self.id in NotificationClass.get_apply_default_on_effective_date_classes()

    @staticmethod
    def get_apply_default_on_notification_date_classes():
        return [
            NotificationClass.APPLY_DEF_ON_NDATE,
            NotificationClass.INFORM_ON_NDATE_APPLY_DEF,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_NDATE,
        ]

    @property
    def is_apply_default_on_notification_date(self):
        return self.id in NotificationClass.get_apply_default_on_notification_date_classes()

    @staticmethod
    def get_need_reaction_on_effective_date_classes():
        return [
            NotificationClass.INFORM_ON_EDATE_WITH_REACT,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_EDATE,
        ]

    @property
    def is_need_reaction_on_effective_date(self):
        return self.id in NotificationClass.get_need_reaction_on_effective_date_classes()

    @staticmethod
    def get_need_reaction_on_notification_date_classes():
        return [
            NotificationClass.INFORM_ON_NDATE_WITH_REACT,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_NDATE,
        ]

    @property
    def is_need_reaction_on_notification_date(self):
        return self.id in NotificationClass.get_need_reaction_on_notification_date_classes()


class PeriodicityGroup(AbstractClassModel):
    DAILY = 1
    WEEKLY = 2
    WEEKLY_EOW = 3
    BE_WEEKLY = 4
    BE_WEEKLY_EOW = 5
    MONTHLY = 6
    MONTHLY_EOM = 7
    QUARTERLY = 8
    QUARTERLY_CALENDAR = 9
    SEMI_ANUALLY = 10
    SEMI_ANUALLY_CALENDAR = 11
    ANUALLY = 12
    ANUALLY_CALENDAR = 13
    CLASSES = (
        (DAILY, "DAILY", gettext_lazy("daily")),
        (WEEKLY, "WEEKLY", gettext_lazy("weekly (+7d)")),
        (WEEKLY_EOW, "WEEKLY_EOW", gettext_lazy("weekly (eow)")),
        (BE_WEEKLY, "BE_WEEKLY", gettext_lazy("bi-weekly (+14d)")),
        (BE_WEEKLY_EOW, "BE_WEEKLY_EOW", gettext_lazy("bi-weekly (eow)")),
        (MONTHLY, "MONTHLY", gettext_lazy("monthly (+1m)")),
        (MONTHLY_EOM, "MONTHLY_EOM", gettext_lazy("monthly (eom)")),
        (QUARTERLY, "QUARTERLY", gettext_lazy("quarterly (+3m)")),
        (
            QUARTERLY_CALENDAR,
            "QUARTERLY_CALENDAR",
            gettext_lazy("quarterly (calendar)"),
        ),
        (SEMI_ANUALLY, "SEMI_ANUALLY", gettext_lazy("semi-anually (+6m)")),
        (
            SEMI_ANUALLY_CALENDAR,
            "SEMI_ANUALLY_CALENDAR",
            gettext_lazy("semi-anually (calendar)"),
        ),
        (ANUALLY, "ANUALLY", gettext_lazy("anually (+12m)")),
        (ANUALLY_CALENDAR, "ANUALLY_CALENDAR", gettext_lazy("anually (eoy)")),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("periodicity group")
        verbose_name_plural = gettext_lazy("periodicity group")


class TransactionTypeGroup(NamedModel, FakeDeletableModel, ConfigurationModel, TimeStampedModel):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="transaction_type_groups",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("transaction type group")
        verbose_name_plural = gettext_lazy("transaction type groups")
        # permissions = [
        #     # ('view_transactiontypegroup', 'Can view transaction type group'),
        #     ('manage_transactiontypegroup', 'Can manage transaction type group'),
        # ]

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10,
                "allow_null": True,
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10,
                "allow_null": True,
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10,
            },
            {
                "key": "configuration_code",
                "name": "Configuration code",
                "value_type": 10,
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
                "allow_null": True,
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10,
                "allow_null": True,
            },
            {
                "key": "show_transaction_details",
                "name": "Show transaction details",
                "value_type": 50,
                "allow_null": True,
            },
            {
                "key": "transaction_details_expr",
                "name": "Transaction details expr",
                "value_type": 10,
                "allow_null": True,
            },
        ]


class TransactionType(
    NamedModel,
    FakeDeletableModel,
    TimeStampedModel,
    ConfigurationModel,
):
    SHOW_PARAMETERS = 1
    HIDE_PARAMETERS = 2
    VISIBILITY_STATUS_CHOICES = (
        (SHOW_PARAMETERS, gettext_lazy("Show Parameters")),
        (HIDE_PARAMETERS, gettext_lazy("Hide Parameters")),
    )

    TYPE_DEFAULT = 1
    TYPE_PROCEDURE = 2  # Complex Transaction will not be created
    TYPE_CHOICES = (
        (TYPE_DEFAULT, gettext_lazy("Default")),
        (TYPE_PROCEDURE, gettext_lazy("Procedure")),
    )

    SKIP = 1
    BOOK_WITHOUT_UNIQUE_CODE = 2
    OVERWRITE = 3
    TREAT_AS_ERROR = 4
    BOOK_WITH_UNIQUE_CODE_CHOICES = (
        (SKIP, gettext_lazy("Skip")),
        (BOOK_WITHOUT_UNIQUE_CODE, gettext_lazy("Book without Unique Code")),
        (OVERWRITE, gettext_lazy("Overwrite")),
        (TREAT_AS_ERROR, gettext_lazy("Treat As Error")),  # Wtf?
    )

    master_user = models.ForeignKey(
        MasterUser,
        related_name="transaction_types",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    group = models.CharField(  # group user_code
        max_length=1024,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("group"),
    )
    date_expr = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("date expr"),
    )
    display_expr = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("display expr"),
    )
    context_parameters_notes = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("context parameters notes"),
    )
    transaction_unique_code_expr = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("transaction unique code expr"),
    )
    transaction_unique_code_options = models.PositiveSmallIntegerField(
        default=BOOK_WITHOUT_UNIQUE_CODE,
        choices=BOOK_WITH_UNIQUE_CODE_CHOICES,
        verbose_name=gettext_lazy("transaction unique code options"),
    )
    instrument_types = models.ManyToManyField(
        "instruments.InstrumentType",
        related_name="transaction_types",
        blank=True,
        verbose_name=gettext_lazy("instrument types"),
    )
    is_valid_for_all_portfolios = models.BooleanField(
        default=True,
        verbose_name=gettext_lazy("is valid for all portfolios"),
    )
    is_valid_for_all_instruments = models.BooleanField(
        default=True,
        verbose_name=gettext_lazy("is valid for all instruments"),
    )
    book_transaction_layout_json = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("book transaction layout json"),
    )
    attributes = GenericRelation(
        GenericAttribute,
        verbose_name=gettext_lazy("attributes"),
    )
    visibility_status = models.PositiveSmallIntegerField(
        default=SHOW_PARAMETERS,
        choices=VISIBILITY_STATUS_CHOICES,
        db_index=True,
        verbose_name=gettext_lazy("visibility_status"),
    )  # settings for complex transaction
    type = models.PositiveSmallIntegerField(
        default=TYPE_DEFAULT,
        choices=TYPE_CHOICES,
        db_index=True,
        verbose_name=gettext_lazy("type"),
    )
    user_text_1 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 1"),
    )
    user_text_2 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 2"),
    )
    user_text_3 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 3"),
    )
    user_text_4 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 4"),
    )
    user_text_5 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 5"),
    )
    user_text_6 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 6"),
    )
    user_text_7 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 7"),
    )
    user_text_8 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 8"),
    )
    user_text_9 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 9"),
    )
    user_text_10 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 10"),
    )
    user_text_11 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 11"),
    )
    user_text_12 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 12"),
    )
    user_text_13 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 13"),
    )
    user_text_14 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 14"),
    )
    user_text_15 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 15"),
    )
    user_text_16 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 16"),
    )
    user_text_17 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 17"),
    )
    user_text_18 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 18"),
    )
    user_text_19 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 19"),
    )
    user_text_20 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 20"),
    )
    user_text_21 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 21"),
    )
    user_text_22 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 22"),
    )
    user_text_23 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 23"),
    )
    user_text_24 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 24"),
    )
    user_text_25 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 25"),
    )
    user_text_26 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 26"),
    )
    user_text_27 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 27"),
    )
    user_text_28 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 28"),
    )
    user_text_29 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 29"),
    )
    user_text_30 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 30"),
    )
    user_number_1 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 1"),
    )
    user_number_2 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 2"),
    )
    user_number_3 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 3"),
    )
    user_number_4 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 4"),
    )
    user_number_5 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 5"),
    )
    user_number_6 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 6"),
    )
    user_number_7 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 7"),
    )
    user_number_8 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 8"),
    )
    user_number_9 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 9"),
    )
    user_number_10 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 10"),
    )
    user_number_11 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 11"),
    )
    user_number_12 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 12"),
    )
    user_number_13 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 13"),
    )
    user_number_14 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 14"),
    )
    user_number_15 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 15"),
    )
    user_number_16 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 16"),
    )
    user_number_17 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 17"),
    )
    user_number_18 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 18"),
    )
    user_number_19 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 19"),
    )
    user_number_20 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user number 20"),
    )
    user_date_1 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user date 1"),
    )
    user_date_2 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user date 2"),
    )
    user_date_3 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user date 3"),
    )
    user_date_4 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user date 4"),
    )
    user_date_5 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user date 5"),
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("transaction type")
        verbose_name_plural = gettext_lazy("transaction types")
        permissions = [
            ("manage_transactiontype", "Can manage transaction type"),
        ]
        ordering = ["user_code"]

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return [
            {"key": "name", "name": "Name", "value_type": 10},
            {"key": "short_name", "name": "Short name", "value_type": 10},
            {"key": "user_code", "name": "User code", "value_type": 10},
            {
                "key": "configuration_code",
                "name": "Configuration code",
                "value_type": 10,
            },
            {"key": "public_name", "name": "Public name", "value_type": 10},
            {"key": "notes", "name": "Notes", "value_type": 10},
            {"key": "group", "name": "Group", "value_type": "field"},
            {"key": "display_expr", "name": "Display Expression", "value_type": 10},
            {
                "key": "instrument_types",
                "name": "Instrument types",
                "value_content_type": "instruments.instrumenttype",
                "value_entity": "instrument-type",
                "code": "user_code",
                "value_type": "mc_field",
            },
            {
                "key": "portfolios",
                "name": "Portfolios",
                "value_content_type": "portfolios.portfolio",
                "value_entity": "portfolio",
                "code": "user_code",
                "value_type": "mc_field",
            },
            {"key": "user_text_1", "name": "User Text 1", "value_type": 10},
            {"key": "user_text_2", "name": "User Text 2", "value_type": 10},
            {"key": "user_text_3", "name": "User Text 3", "value_type": 10},
            {"key": "user_text_4", "name": "User Text 4", "value_type": 10},
            {"key": "user_text_5", "name": "User Text 5", "value_type": 10},
            {"key": "user_text_6", "name": "User Text 6", "value_type": 10},
            {"key": "user_text_7", "name": "User Text 7", "value_type": 10},
            {"key": "user_text_8", "name": "User Text 8", "value_type": 10},
            {"key": "user_text_9", "name": "User Text 9", "value_type": 10},
            {"key": "user_text_10", "name": "User Text 10", "value_type": 10},
            {"key": "user_text_11", "name": "User Text 11", "value_type": 10},
            {"key": "user_text_12", "name": "User Text 12", "value_type": 10},
            {"key": "user_text_13", "name": "User Text 13", "value_type": 10},
            {"key": "user_text_14", "name": "User Text 14", "value_type": 10},
            {"key": "user_text_15", "name": "User Text 15", "value_type": 10},
            {"key": "user_text_16", "name": "User Text 16", "value_type": 10},
            {"key": "user_text_17", "name": "User Text 17", "value_type": 10},
            {"key": "user_text_18", "name": "User Text 18", "value_type": 10},
            {"key": "user_text_19", "name": "User Text 19", "value_type": 10},
            {"key": "user_text_20", "name": "User Text 20", "value_type": 10},
            {"key": "user_text_21", "name": "User Text 21", "value_type": 10},
            {"key": "user_text_22", "name": "User Text 22", "value_type": 10},
            {"key": "user_text_23", "name": "User Text 23", "value_type": 10},
            {"key": "user_text_24", "name": "User Text 24", "value_type": 10},
            {"key": "user_text_25", "name": "User Text 25", "value_type": 10},
            {"key": "user_text_26", "name": "User Text 26", "value_type": 10},
            {"key": "user_text_27", "name": "User Text 27", "value_type": 10},
            {"key": "user_text_28", "name": "User Text 28", "value_type": 10},
            {"key": "user_text_29", "name": "User Text 29", "value_type": 10},
            {"key": "user_text_30", "name": "User Text 30", "value_type": 10},
            {"key": "user_number_1", "name": "User Number 1", "value_type": 10},
            {"key": "user_number_2", "name": "User Number 2", "value_type": 10},
            {"key": "user_number_3", "name": "User Number 3", "value_type": 10},
            {"key": "user_number_4", "name": "User Number 4", "value_type": 10},
            {"key": "user_number_5", "name": "User Number 5", "value_type": 10},
            {"key": "user_number_6", "name": "User Number 6", "value_type": 10},
            {"key": "user_number_7", "name": "User Number 7", "value_type": 10},
            {"key": "user_number_8", "name": "User Number 8", "value_type": 10},
            {"key": "user_number_9", "name": "User Number 9", "value_type": 10},
            {"key": "user_number_10", "name": "User Number 10", "value_type": 10},
            {"key": "user_number_11", "name": "User Number 11", "value_type": 10},
            {"key": "user_number_12", "name": "User Number 12", "value_type": 10},
            {"key": "user_number_13", "name": "User Number 13", "value_type": 10},
            {"key": "user_number_14", "name": "User Number 14", "value_type": 10},
            {"key": "user_number_15", "name": "User Number 15", "value_type": 10},
            {"key": "user_number_16", "name": "User Number 16", "value_type": 10},
            {"key": "user_number_17", "name": "User Number 17", "value_type": 10},
            {"key": "user_number_18", "name": "User Number 18", "value_type": 10},
            {"key": "user_number_19", "name": "User Number 19", "value_type": 10},
            {"key": "user_number_20", "name": "User Number 20", "value_type": 10},
            {"key": "user_date_1", "name": "User Date 1", "value_type": 10},
            {"key": "user_date_2", "name": "User Date 2", "value_type": 10},
            {"key": "user_date_3", "name": "User Date 3", "value_type": 10},
            {"key": "user_date_4", "name": "User Date 4", "value_type": 10},
            {"key": "user_date_5", "name": "User Date 5", "value_type": 10},
        ]

    @property
    def book_transaction_layout(self):
        try:
            return json.loads(self.book_transaction_layout_json) if self.book_transaction_layout_json else None
        except (ValueError, TypeError):
            return None

    @book_transaction_layout.setter
    def book_transaction_layout(self, data):
        self.book_transaction_layout_json = json.dumps(data, cls=DjangoJSONEncoder, sort_keys=True) if data else None


class TransactionTypeContextParameter(models.Model):
    STRING = 10
    NUMBER = 20
    # EXPRESSION = 30
    DATE = 40
    TYPES = (
        (NUMBER, gettext_lazy("Number")),
        (STRING, gettext_lazy("String")),
        (DATE, gettext_lazy("Date")),
    )

    transaction_type = models.ForeignKey(
        TransactionType,
        related_name="context_parameters",
        verbose_name=gettext_lazy("transaction type"),
        on_delete=models.CASCADE,
    )
    user_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("user code"),
    )
    name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("name"),
    )
    value_type = models.PositiveSmallIntegerField(
        default=STRING,
        choices=TYPES,
        verbose_name=gettext_lazy("value type"),
    )
    order = models.IntegerField(
        default=1,
        verbose_name=gettext_lazy("order"),
    )

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["transaction_type", "user_code"],
                name="unique ttype context parameter",
            )
        ]


class TransactionTypeInput(models.Model):
    STRING = 10
    NUMBER = 20
    DATE = 40
    RELATION = 100
    SELECTOR = 110
    BUTTON = 120
    JSON = 130
    TYPES = (
        (NUMBER, gettext_lazy("Number")),
        (STRING, gettext_lazy("String")),
        (DATE, gettext_lazy("Date")),
        (RELATION, gettext_lazy("Relation")),
        (SELECTOR, gettext_lazy("Selector")),
        (BUTTON, gettext_lazy("Button")),
        (JSON, gettext_lazy("JSON")),
    )

    transaction_type = models.ForeignKey(
        TransactionType,
        related_name="inputs",
        verbose_name=gettext_lazy("transaction type"),
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("name"),
    )
    tooltip = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("tooltip"),
    )
    verbose_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("verbose name"),
    )
    value_type = models.PositiveSmallIntegerField(
        default=NUMBER,
        choices=TYPES,
        verbose_name=gettext_lazy("value type"),
    )
    content_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("content type"),
        on_delete=models.SET_NULL,
    )
    reference_table = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("reference table"),
    )
    order = models.IntegerField(
        default=0,
        verbose_name=gettext_lazy("order"),
    )
    expression_iterations_count = models.IntegerField(
        default=1,
        verbose_name=gettext_lazy("expression_iterations_count"),
        help_text="Number of iterations for expression when recalculate",
    )
    value_expr = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("value expression"),
        help_text=gettext_lazy("this is expression for recalculate value"),
    )
    is_fill_from_context = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("is fill from context"),
    )
    context_property = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("context property"),
    )
    value = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("value"),
        help_text=gettext_lazy("this is expression for default value"),
    )
    settings = models.ForeignKey(
        "transactions.TransactionTypeInputSettings",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=gettext_lazy("settings"),
    )
    json_button_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("json button data"),
    )

    @property
    def button_data(self):
        if not self.json_button_data:
            return None

        try:
            return json.loads(self.json_button_data)
        except (ValueError, TypeError):
            return None

    @button_data.setter
    def button_data(self, val):
        if val:
            self.json_button_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.json_button_data = None

    class Meta:
        verbose_name = gettext_lazy("transaction type input")
        verbose_name_plural = gettext_lazy("transaction type inputs")
        unique_together = [
            ["transaction_type", "name"],
        ]
        index_together = [
            ["transaction_type", "order"],
        ]
        ordering = ["name"]

    def __str__(self):
        if self.value_type == self.RELATION:
            return f"{self.name}: {self.content_type}"
        else:
            return f"{self.name}: {self.get_value_type_display()}"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.verbose_name:
            self.verbose_name = self.name
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    @property
    def can_recalculate(self):
        return bool(self.value_expr) and self.value_type in [
            TransactionTypeInput.STRING,
            TransactionTypeInput.SELECTOR,
            TransactionTypeInput.DATE,
            TransactionTypeInput.NUMBER,
            TransactionTypeInput.RELATION,
        ]


class TransactionTypeInputSettings(models.Model):
    transaction_type_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="settings_old",
        verbose_name=gettext_lazy("transaction type input"),
    )
    linked_inputs_names = models.TextField(
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("linked_input_names"),
    )
    recalc_on_change_linked_inputs = models.TextField(
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("recalc on change linked inputs"),
    )


class RebookReactionChoice:
    CREATE = 0  # Used in Instrument Action
    SKIP = 1  # is not in use
    OVERWRITE = 2  # Used in Instrument Action
    CLEAR_AND_WRITE = 3
    CREATE_IF_NOT_EXIST = 4
    FIND_OR_CREATE = 5  # Used in Instrument Action
    CLEAR_AND_WRITE_OR_SKIP = 6
    CLEAR = 7
    TRY_DOWNLOAD_IF_ERROR_CREATE_DEFAULT = 8
    choices = (
        (CREATE, "Create"),  # simple entity create
        (SKIP, "Skip"),  # skip creating of entity
        (
            OVERWRITE,
            "Overwrite",
        ),  # rewrite entity if the same user_code already exists, if not -> create
        (CLEAR_AND_WRITE, "Clear all & Create"),
        # Special rewrite for entities without user_code (e.g.  Accruals schedule in Instrument)
        (CREATE_IF_NOT_EXIST, "Create if not exist"),
        (CLEAR_AND_WRITE_OR_SKIP, "If book: Clear & Append. If rebook: Skip"),
        # Create if there is no entity with same user_code, otherwise skip
        (TRY_DOWNLOAD_IF_ERROR_CREATE_DEFAULT, "Try download if error create default"),
    )


class TransactionTypeAction(models.Model):
    transaction_type = models.ForeignKey(
        TransactionType,
        related_name="actions",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("transaction type"),
    )
    order = models.IntegerField(
        default=0,
        verbose_name=gettext_lazy("order"),
    )
    action_notes = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("action notes"),
    )
    rebook_reaction = models.IntegerField(
        default=0,
        choices=RebookReactionChoice.choices,
    )
    condition_expr = models.CharField(
        max_length=1000,
        blank=True,
        default="",
        verbose_name=gettext_lazy("condition expression"),
    )

    class Meta:
        verbose_name = gettext_lazy("action")
        verbose_name_plural = gettext_lazy("actions")
        index_together = [
            ["transaction_type", "order"],
        ]
        ordering = ["order"]

    def __str__(self):
        return f"Action #{self.order}"


class TransactionTypeActionInstrument(TransactionTypeAction):
    user_code = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user code"),
    )
    name = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("name"),
    )
    public_name = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("public name"),
    )
    short_name = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("short name"),
    )
    notes = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("notes"),
    )
    instrument_type = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("instrument type"),
    )
    instrument_type_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("instrument type input"),
    )
    pricing_currency = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("pricing currency"),
    )
    pricing_currency_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("pricing currency input"),
    )
    price_multiplier = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.0",
        verbose_name=gettext_lazy("price multiplier"),
    )
    accrued_currency = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("accrued currency"),
    )
    accrued_currency_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("accrued currency input"),
    )
    accrued_multiplier = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.0",
        verbose_name=gettext_lazy("accrued multiplier"),
    )
    payment_size_detail = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("payment_size detail"),
    )
    payment_size_detail_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("payment size detail input"),
    )
    pricing_condition = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("pricing condition"),
    )
    pricing_condition_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("pricing condition input"),
    )
    default_price = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.0",
        verbose_name=gettext_lazy("default price"),
    )
    default_accrued = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.0",
        verbose_name=gettext_lazy("default accrued"),
    )
    user_text_1 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 1"),
    )
    user_text_2 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 2"),
    )
    user_text_3 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user text 3"),
    )
    reference_for_pricing = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=gettext_lazy("reference for pricing"),
    )
    maturity_date = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="now()",
        verbose_name=gettext_lazy("maturity date"),
    )
    maturity_price = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.0",
        verbose_name=gettext_lazy("default price"),
    )

    class Meta:
        verbose_name = gettext_lazy("transaction type action instrument")
        verbose_name_plural = gettext_lazy("transaction type action instruments")

    def __str__(self):
        return f"Instrument action #{self.order}"


class TransactionTypeActionTransaction(TransactionTypeAction):
    transaction_class = models.ForeignKey(
        TransactionClass,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=gettext_lazy("transaction class"),
    )
    instrument = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("instrument"),
    )
    instrument_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("instrument input"),
    )
    instrument_phantom = models.ForeignKey(
        TransactionTypeActionInstrument,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("instrument phantom"),
    )
    transaction_currency = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("transaction currency"),
    )
    transaction_currency_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("transaction currency input"),
    )
    position_size_with_sign = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.",
        verbose_name=gettext_lazy("position size with sign"),
    )
    settlement_currency = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("settlement currency"),
    )
    settlement_currency_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("settlement currency input"),
    )
    cash_consideration = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.",
        verbose_name=gettext_lazy("cash consideration"),
    )
    principal_with_sign = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.",
        verbose_name=gettext_lazy("principal with sign"),
    )
    carry_with_sign = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.",
        verbose_name=gettext_lazy("carry with sign"),
    )
    overheads_with_sign = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.",
        verbose_name=gettext_lazy("overheads with sign"),
    )
    portfolio = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("portfolio"),
    )
    portfolio_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("portfolio input"),
    )
    account_position = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("account position"),
    )
    account_position_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("account position input"),
    )
    account_cash = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("account cash"),
    )
    account_cash_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("account cash input"),
    )
    account_interim = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("account interim"),
    )
    account_interim_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("account interim input"),
    )
    accounting_date = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("accounting date"),
    )
    cash_date = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("cash date"),
    )
    strategy1_position = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("strategy1 position"),
    )
    strategy1_position_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("strategy 1 position input"),
    )
    strategy1_cash = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("strategy1 cash"),
    )
    strategy1_cash_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("strategy 1 cash input"),
    )
    strategy2_position = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("strategy2 position"),
    )
    strategy2_position_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("strategy 2 position input"),
    )
    strategy2_cash = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("strategy2 cash"),
    )
    strategy2_cash_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("strategy 2 cash input"),
    )
    strategy3_position = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("strategy3 position"),
    )
    strategy3_position_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("strategy 3 position input"),
    )
    strategy3_cash = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("strategy3 cash"),
    )
    strategy3_cash_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("strategy 3 cash input"),
    )
    linked_instrument = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("linked instrument"),
    )
    linked_instrument_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("linked instrument input"),
    )
    linked_instrument_phantom = models.ForeignKey(
        TransactionTypeActionInstrument,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("linked instrument phantom"),
    )
    allocation_balance = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("allocation balance"),
    )
    allocation_balance_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("allocation balance input"),
    )
    allocation_balance_phantom = models.ForeignKey(
        TransactionTypeActionInstrument,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("allocation balance phantom"),
    )
    allocation_pl = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("allocation pl"),
    )
    allocation_pl_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("allocation pl input"),
    )
    allocation_pl_phantom = models.ForeignKey(
        TransactionTypeActionInstrument,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("allocation pl phantom"),
    )
    responsible = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("responsible"),
    )
    responsible_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("responsible input"),
    )
    counterparty = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("responsible"),
    )
    counterparty_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("counterparty input"),
    )
    reference_fx_rate = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.0",
        verbose_name=gettext_lazy("reference FX-rate"),
    )
    factor = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.0",
        verbose_name=gettext_lazy("factor"),
    )
    trade_price = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.0",
        verbose_name=gettext_lazy("trade price"),
    )
    position_amount = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.0",
        verbose_name=gettext_lazy("position amount"),
    )
    principal_amount = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.0",
        verbose_name=gettext_lazy("principal amount"),
    )
    carry_amount = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.0",
        verbose_name=gettext_lazy("carry amount"),
    )
    overheads = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.0",
        verbose_name=gettext_lazy("overheads"),
    )
    notes = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("notes"),
    )
    user_text_1 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user_text_1"),
    )
    user_text_2 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user_text_2"),
    )
    user_text_3 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user_text_3"),
    )
    user_number_1 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        null=True,
        verbose_name=gettext_lazy("user_number_1"),
    )
    user_number_2 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        null=True,
        verbose_name=gettext_lazy("user_number_2"),
    )
    user_number_3 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        null=True,
        verbose_name=gettext_lazy("user_number_3"),
    )
    user_date_1 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        null=True,
        verbose_name=gettext_lazy("user_date_1"),
    )
    user_date_2 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        null=True,
        verbose_name=gettext_lazy("user_date_2"),
    )
    user_date_3 = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        null=True,
        verbose_name=gettext_lazy("user_date_3"),
    )
    is_canceled = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        null=True,
        verbose_name=gettext_lazy("is canceled"),
    )

    class Meta:
        verbose_name = gettext_lazy("transaction type action transaction")
        verbose_name_plural = gettext_lazy("transaction type action transactions")

    def __str__(self):
        return f"Transaction action #{self.order}"


class TransactionTypeActionInstrumentFactorSchedule(TransactionTypeAction):
    instrument = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("instrument"),
    )
    instrument_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("instrument input"),
    )
    instrument_phantom = models.ForeignKey(
        TransactionTypeActionInstrument,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("instrument phantom"),
    )
    effective_date = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("effective date"),
    )
    factor_value = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.0",
        verbose_name=gettext_lazy("factor value"),
    )

    class Meta:
        verbose_name = gettext_lazy("transaction type action instrument factor schedule")
        verbose_name_plural = gettext_lazy("transaction type action instrument factor schedules")

    def __str__(self):
        return f"InstrumentFactor action #{self.order}"


# DEPRECATED (25.05.2020), delete soon
class TransactionTypeActionInstrumentManualPricingFormula(TransactionTypeAction):
    instrument = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("instrument"),
    )
    instrument_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("instrument input"),
    )
    instrument_phantom = models.ForeignKey(
        TransactionTypeActionInstrument,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("instrument phantom"),
    )
    pricing_policy = models.ForeignKey(
        PricingPolicy,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("pricing policy"),
    )
    pricing_policy_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("pricing policy input"),
    )
    expr = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("expr"),
    )
    notes = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="",
        verbose_name=gettext_lazy("notes"),
    )

    class Meta:
        verbose_name = gettext_lazy("transaction type action instrument manual pricing formula")
        verbose_name_plural = gettext_lazy("transaction type action instrument manual pricing formula")

    def __str__(self):
        return f"InstrumentManualPricingFormula action #{self.order}"


class TransactionTypeActionInstrumentAccrualCalculationSchedules(TransactionTypeAction):
    instrument = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("instrument"),
    )
    instrument_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("instrument input"),
    )
    instrument_phantom = models.ForeignKey(
        TransactionTypeActionInstrument,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("instrument phantom"),
    )
    accrual_calculation_model = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("accrual calculation model"),
    )
    accrual_calculation_model_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("accrual calculation model input"),
    )
    periodicity = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("periodicity"),
    )
    periodicity_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("periodicity input"),
    )
    accrual_start_date = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("accrual start date"),
    )
    first_payment_date = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("first payment date"),
    )
    accrual_size = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0.0",
        verbose_name=gettext_lazy("accrual size"),
    )
    periodicity_n = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("periodicity n"),
    )
    notes = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="",
        verbose_name=gettext_lazy("notes"),
    )

    class Meta:
        verbose_name = gettext_lazy("transaction type action instrument accrual calculation schedules")
        verbose_name_plural = gettext_lazy("transaction type action instrument accrual calculation schedules")

    def __str__(self):
        return f"InstrumentAccrualCalculationSchedules action #{self.order}"


class TransactionTypeActionInstrumentEventSchedule(TransactionTypeAction):
    instrument = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("instrument"),
    )
    instrument_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("instrument input"),
    )
    instrument_phantom = models.ForeignKey(
        TransactionTypeActionInstrument,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("instrument phantom"),
    )
    periodicity = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("periodicity"),
    )
    periodicity_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("periodicity input"),
    )
    notification_class = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("notification class"),
    )
    notification_class_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("notification class input"),
    )
    event_class = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        null=True,
        verbose_name=gettext_lazy("event class"),
    )
    event_class_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("event class input"),
    )
    effective_date = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("effective date"),
    )
    final_date = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("final date"),
    )
    is_auto_generated = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("is autogenerated"),
    )
    notify_in_n_days = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("notify in n days"),
    )
    periodicity_n = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("periodicity n"),
    )
    name = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="",
        verbose_name=gettext_lazy("name"),
    )
    description = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="",
        verbose_name=gettext_lazy("description"),
    )

    class Meta:
        verbose_name = gettext_lazy("transaction type action instrument event schedules")
        verbose_name_plural = gettext_lazy("transaction type action instrument event schedules")

    def __str__(self):
        return f"TransactionTypeActionInstrumentEventSchedules action #{self.order}"


class TransactionTypeActionInstrumentEventScheduleAction(TransactionTypeAction):
    event_schedule = models.ForeignKey(
        EventSchedule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("event schedule"),
    )
    event_schedule_input = models.ForeignKey(
        TransactionTypeInput,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("event schedule input"),
    )
    event_schedule_phantom = models.ForeignKey(
        TransactionTypeActionInstrumentEventSchedule,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=gettext_lazy("event schedule phantom"),
        on_delete=models.SET_NULL,
    )
    transaction_type_from_instrument_type = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="",
        verbose_name=gettext_lazy("text"),
    )
    is_book_automatic = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default=False,
        verbose_name=gettext_lazy("is book automatic"),
        help_text=gettext_lazy("If checked - is book automatic"),
    )
    is_sent_to_pending = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default=False,
        verbose_name=gettext_lazy("is sent to pending"),
        help_text=gettext_lazy("If checked - is sent to pending"),
    )
    button_position = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="0",
        verbose_name=gettext_lazy("button position"),
    )
    text = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="",
        verbose_name=gettext_lazy("text"),
    )

    class Meta:
        verbose_name = gettext_lazy("transaction type action instrument event schedule action")
        verbose_name_plural = gettext_lazy("transaction type action instrument event schedule actions")

    def __str__(self):
        return f"TransactionTypeActionInstrumentEventScheduleAction action #{self.order}"


class TransactionTypeActionExecuteCommand(TransactionTypeAction):
    expr = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("expr"),
    )

    class Meta:
        verbose_name = gettext_lazy("transaction type action execute command action")
        verbose_name_plural = gettext_lazy("transaction type action execute command actions")

    def __str__(self):
        return f"TransactionTypeActionExecuteCommand action #{self.order}"


class EventToHandle(NamedModel):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="events_to_handle",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    transaction_type = models.ForeignKey(
        TransactionType,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("transaction type"),
    )
    notification_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("notification date"),
    )
    effective_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("effective date"),
    )

    class Meta(NamedModel.Meta):
        verbose_name = gettext_lazy("event to handle")
        verbose_name_plural = gettext_lazy("events to handle")


class ComplexTransaction(TimeStampedModel):
    PRODUCTION = 1
    PENDING = 2
    IGNORE = 3
    STATUS_CHOICES = (
        (PRODUCTION, gettext_lazy("Booked")),
        (PENDING, gettext_lazy("Pending")),
        (IGNORE, gettext_lazy("Ignore")),
    )

    SHOW_PARAMETERS = 1
    HIDE_PARAMETERS = 2
    VISIBILITY_STATUS_CHOICES = (
        (SHOW_PARAMETERS, gettext_lazy("Show Parameters")),
        (HIDE_PARAMETERS, gettext_lazy("Hide Parameters")),
    )

    master_user = models.ForeignKey(
        MasterUser,
        related_name="complex_transactions",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    owner = models.ForeignKey(
        "users.Member",
        verbose_name=gettext_lazy("owner"),
        on_delete=models.CASCADE,
    )
    transaction_type = models.ForeignKey(
        TransactionType,
        on_delete=models.PROTECT,
        db_index=True,
        verbose_name=gettext_lazy("transaction type"),
    )
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=gettext_lazy("is deleted"),
    )
    is_locked = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=gettext_lazy("is locked"),
    )
    is_canceled = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=gettext_lazy("is canceled"),
    )
    error_code = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("error code"),
    )
    date = models.DateField(
        default=date_now,
        db_index=True,
        verbose_name=gettext_lazy("date"),
    )
    status_old = models.PositiveSmallIntegerField(
        default=PRODUCTION,
        choices=STATUS_CHOICES,
        db_index=True,
        verbose_name=gettext_lazy("status"),
    )
    status = models.ForeignKey(
        ComplexTransactionStatus,
        on_delete=models.PROTECT,
        default=ComplexTransactionStatus.BOOKED,
        verbose_name=gettext_lazy("status"),
    )
    visibility_status = models.PositiveSmallIntegerField(
        default=SHOW_PARAMETERS,
        choices=VISIBILITY_STATUS_CHOICES,
        db_index=True,
        verbose_name=gettext_lazy("visibility_status"),
    )
    code = models.IntegerField(
        unique=True,
        verbose_name=gettext_lazy("code"),
        db_index=True,
    )
    transaction_unique_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("transaction unique code"),
    )
    # POSSIBLY DEPRECATED
    deleted_transaction_unique_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("deleted transaction unique code"),
    )
    text = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("text"),
        db_index=True,
    )
    user_text_1 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 1"),
    )
    user_text_2 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 2"),
    )
    user_text_3 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 3"),
    )
    user_text_4 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 4"),
    )
    user_text_5 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 5"),
    )
    user_text_6 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 6"),
    )
    user_text_7 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 7"),
    )
    user_text_8 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 8"),
    )
    user_text_9 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 9"),
    )
    user_text_10 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 10"),
    )
    user_text_11 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 11"),
    )
    user_text_12 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 12"),
    )
    user_text_13 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 13"),
    )
    user_text_14 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 14"),
    )
    user_text_15 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 15"),
    )
    user_text_16 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 16"),
    )
    user_text_17 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 17"),
    )
    user_text_18 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 18"),
    )
    user_text_19 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 19"),
    )
    user_text_20 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 20"),
    )
    user_text_21 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 21"),
    )
    user_text_22 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 22"),
    )
    user_text_23 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 23"),
    )
    user_text_24 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 24"),
    )
    user_text_25 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 25"),
    )
    user_text_26 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 26"),
    )
    user_text_27 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 27"),
    )
    user_text_28 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 28"),
    )
    user_text_29 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 29"),
    )
    user_text_30 = models.TextField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("user text 30"),
    )
    user_number_1 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 1"),
    )
    user_number_2 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 2"),
    )
    user_number_3 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 3"),
    )
    user_number_4 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 4"),
    )
    user_number_5 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 5"),
    )
    user_number_6 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 6"),
    )
    user_number_7 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 7"),
    )
    user_number_8 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 8"),
    )
    user_number_9 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 9"),
    )
    user_number_10 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 10"),
    )
    user_number_11 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 11"),
    )
    user_number_12 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 12"),
    )
    user_number_13 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 13"),
    )
    user_number_14 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 14"),
    )
    user_number_15 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 15"),
    )
    user_number_16 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 16"),
    )
    user_number_17 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 17"),
    )
    user_number_18 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 18"),
    )
    user_number_19 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 19"),
    )
    user_number_20 = models.FloatField(
        null=True,
        verbose_name=gettext_lazy("user number 20"),
    )
    user_date_1 = models.DateField(
        blank=True,
        db_index=True,
        null=True,
        verbose_name=gettext_lazy("user date 1"),
    )
    user_date_2 = models.DateField(
        blank=True,
        db_index=True,
        null=True,
        verbose_name=gettext_lazy("user date 2"),
    )
    user_date_3 = models.DateField(
        blank=True,
        db_index=True,
        null=True,
        verbose_name=gettext_lazy("user date 3"),
    )
    user_date_4 = models.DateField(
        blank=True,
        db_index=True,
        null=True,
        verbose_name=gettext_lazy("user date 4"),
    )
    user_date_5 = models.DateField(
        blank=True,
        db_index=True,
        null=True,
        verbose_name=gettext_lazy("user date 5"),
    )
    attributes = GenericRelation(
        GenericAttribute,
        verbose_name=gettext_lazy("attributes"),
    )
    linked_import_task = models.ForeignKey(
        "celery_tasks.CeleryTask",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("linked import task"),
    )
    execution_log = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("execution log"),
    )
    source_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("source data"),
    )

    @property
    def source(self):
        return None if self.source_data is None else json.loads(self.source_data)

    @source.setter
    def source(self, value):
        if value is None:
            self.source_data = None
        else:
            self.source_data = json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, indent=1)

    class Meta:
        verbose_name = gettext_lazy("complex transaction")
        verbose_name_plural = gettext_lazy("complex transactions")
        index_together = [["transaction_type", "code"]]
        ordering = ["code"]

        permissions = (
            ("view_complextransaction_show_parameters", "Show Parameters"),
            ("view_complextransaction_hide_parameters", "Hide Parameters"),
        )

    def __str__(self):
        return str(self.code)

    def save(self, *args, **kwargs):
        if self.code is None or self.code == 0:
            self.code = FakeSequence.next_value(self.transaction_type.master_user, "complex_transaction", d=100)

        _l.debug(f"ComplexTransaction.save {self.code} {self.date} {self.transaction_unique_code}")

        super().save(*args, **kwargs)

    def fake_delete(self):
        if self.is_deleted:
            # if the transaction was already marked as deleted, then do real delete
            self.delete()
            return

        with transaction.atomic():
            self.is_deleted = True
            fields_to_update = ["is_deleted", "modified_at"]
            if hasattr(self, "transaction_unique_code"):
                # self.deleted_transaction_unique_code = self.transaction_unique_code
                # TODO possibly do not remove

                self.transaction_unique_code = None

                fields_to_update.extend(("deleted_transaction_unique_code", "transaction_unique_code"))

            for tx in self.transactions.all():
                tx.delete()

            self.save(update_fields=fields_to_update)


class ComplexTransactionInput(models.Model):
    complex_transaction = models.ForeignKey(
        ComplexTransaction,
        on_delete=models.CASCADE,
        related_name="inputs",
        verbose_name=gettext_lazy("complex transaction"),
    )
    transaction_type_input = models.ForeignKey(
        TransactionTypeInput,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=gettext_lazy("transaction type input"),
    )
    value_relation = models.TextField(
        default="",
        blank=True,
        verbose_name=gettext_lazy("value relation"),
    )
    value_string = models.TextField(
        default="",
        blank=True,
        verbose_name=gettext_lazy("value string"),
    )
    value_float = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("value float"),
    )
    value_date = models.DateField(
        default=date.min,
        verbose_name=gettext_lazy("value date"),
    )
    account = models.ForeignKey(
        "accounts.Account",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("account"),
    )
    instrument_type = models.ForeignKey(
        "instruments.InstrumentType",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("instrument type"),
    )
    instrument = models.ForeignKey(
        "instruments.Instrument",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("instrument"),
    )
    currency = models.ForeignKey(
        "currencies.Currency",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("currency"),
    )
    counterparty = models.ForeignKey(
        "counterparties.Counterparty",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("counterparty"),
    )
    responsible = models.ForeignKey(
        "counterparties.Responsible",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("responsible"),
    )
    portfolio = models.ForeignKey(
        Portfolio,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("portfolio"),
    )
    strategy1 = models.ForeignKey(
        "strategies.Strategy1",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("strategy 1"),
    )
    strategy2 = models.ForeignKey(
        "strategies.Strategy2",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("strategy 2"),
    )
    strategy3 = models.ForeignKey(
        "strategies.Strategy3",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("strategy 3"),
    )
    daily_pricing_model = models.ForeignKey(
        "instruments.DailyPricingModel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("daily pricing model"),
    )
    payment_size_detail = models.ForeignKey(
        "instruments.PaymentSizeDetail",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("payment size detail"),
    )
    pricing_policy = models.ForeignKey(
        "instruments.PricingPolicy",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=gettext_lazy("pricing policy"),
    )
    periodicity = models.ForeignKey(
        "instruments.Periodicity",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=gettext_lazy("periodicity"),
    )
    accrual_calculation_model = models.ForeignKey(
        "instruments.AccrualCalculationModel",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=gettext_lazy("accrual calculation model"),
    )
    event_class = models.ForeignKey(
        EventClass,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=gettext_lazy("event class"),
    )
    notification_class = models.ForeignKey(
        NotificationClass,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=gettext_lazy("notification class"),
    )

    class Meta:
        verbose_name = gettext_lazy("complex transaction input")
        verbose_name_plural = gettext_lazy("complex transaction inputs")
        unique_together = [
            [
                "complex_transaction",
                "transaction_type_input",
            ]
        ]


class Transaction(models.Model):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="transactions",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    owner = models.ForeignKey(
        "users.Member",
        verbose_name=gettext_lazy("owner"),
        on_delete=models.CASCADE,
    )
    complex_transaction = models.ForeignKey(
        ComplexTransaction,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name=gettext_lazy("complex transaction"),
    )
    complex_transaction_order = models.PositiveSmallIntegerField(
        default=0.0,
        verbose_name=gettext_lazy("complex transaction order"),
    )
    transaction_code = models.IntegerField(
        unique=True,
        verbose_name=gettext_lazy("transaction code"),
        help_text="More Human Readable ID, like Complex Transaction has 100, then Transaction will have 101",
        db_index=True,
    )
    transaction_class = models.ForeignKey(
        TransactionClass,
        on_delete=models.PROTECT,
        db_index=True,
        verbose_name=gettext_lazy("transaction class"),
        help_text=(
            "Important entity, depending on class will be applied different method "
            "to calculate report (e.g. Buy, Sell, Transfer)"
        ),
    )
    is_canceled = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=gettext_lazy("is canceled"),
        help_text="Transaction will be filtered out from report calculation",
    )
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=gettext_lazy("is deleted"),
    )
    error_code = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("error code"),
    )
    # Position related
    instrument = models.ForeignKey(
        Instrument,
        related_name="transactions",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Link to Instrument, could be null if we describing cash",
        verbose_name=gettext_lazy("instrument"),
    )
    transaction_currency = models.ForeignKey(
        Currency,
        related_name="transactions",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("transaction currency"),
    )
    position_size_with_sign = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("position size with sign"),
    )
    # Cash related
    settlement_currency = models.ForeignKey(
        Currency,
        related_name="transactions_settlement_currency",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("settlement currency"),
    )
    cash_consideration = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("cash consideration"),
    )
    # P&L related
    principal_with_sign = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("principal with sign"),
    )
    carry_with_sign = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("carry with sign"),
    )
    overheads_with_sign = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("overheads with sign"),
    )
    # accounting dates
    transaction_date = models.DateField(
        editable=False,
        default=date_now,
        db_index=True,
        verbose_name=gettext_lazy("transaction date"),
    )
    accounting_date = models.DateField(
        default=date_now,
        db_index=True,
        verbose_name=gettext_lazy("accounting date"),
    )
    cash_date = models.DateField(
        default=date_now,
        db_index=True,
        verbose_name=gettext_lazy("cash date"),
    )
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("portfolio"),
        db_index=True,
    )
    # accounts
    account_position = models.ForeignKey(
        Account,
        related_name="transactions_account_position",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("account position"),
    )
    account_cash = models.ForeignKey(
        Account,
        related_name="transactions_account_cash",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("account cash"),
    )
    account_interim = models.ForeignKey(
        Account,
        related_name="transactions_account_interim",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("account interim"),
    )
    # strategies
    strategy1_position = models.ForeignKey(
        Strategy1,
        related_name="transactions_strategy1_position",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy 1 cash"),
    )
    strategy1_cash = models.ForeignKey(
        Strategy1,
        related_name="transactions_strategy1_cash",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy 1 position"),
    )
    strategy2_position = models.ForeignKey(
        Strategy2,
        related_name="transactions_strategy2_position",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy 2 cash"),
    )
    strategy2_cash = models.ForeignKey(
        Strategy2,
        related_name="transactions_strategy2_cash",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy 2 position"),
    )
    strategy3_position = models.ForeignKey(
        Strategy3,
        related_name="transactions_strategy3_position",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy 3 cash"),
    )
    strategy3_cash = models.ForeignKey(
        Strategy3,
        related_name="transactions_strategy3_cash",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy 3 position"),
    )
    # responsible & counterparty
    responsible = models.ForeignKey(
        Responsible,
        related_name="transactions",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("responsible"),
        help_text=gettext_lazy("Trader or transaction executor"),
    )
    counterparty = models.ForeignKey(
        Counterparty,
        related_name="transactions",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("counterparty"),
    )
    linked_instrument = models.ForeignKey(
        Instrument,
        related_name="transactions_linked",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("linked instrument"),
    )
    # allocations
    allocation_balance = models.ForeignKey(
        Instrument,
        related_name="transactions_allocation_balance",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("allocation balance"),
    )
    allocation_pl = models.ForeignKey(
        Instrument,
        related_name="transactions_allocation_pl",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("allocation P&L"),
    )
    reference_fx_rate = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("reference fx-rate"),
        help_text=gettext_lazy(
            "FX rate to convert from Settlement ccy to Instrument Ccy on Accounting Date (trade date)"
        ),
        #     TODO need more explicit example
    )
    is_locked = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("is locked"),
        help_text=gettext_lazy("If checked - transaction cannot be changed"),
    )
    factor = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("factor"),
        help_text=gettext_lazy("Multiplier (for calculations on the form)"),
    )
    trade_price = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("trade price"),
        help_text=gettext_lazy("Price (for calculations on the form)"),
    )
    ytm_at_cost = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("YTM at cost"),
        help_text=gettext_lazy("YTM at cost"),
    )
    position_amount = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("position amount"),
        help_text=gettext_lazy("Absolute value of Position with Sign (for calculations on the form)"),
    )
    principal_amount = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("principal amount"),
        help_text=gettext_lazy("Absolute value of Principal with Sign (for calculations on the form)"),
    )
    carry_amount = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("carry amount"),
        help_text=gettext_lazy("Absolute value of Carry with Sign (for calculations on the form)"),
    )
    overheads = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("overheads"),
        help_text=gettext_lazy("Absolute value of overheads (for calculations on the form)"),
    )
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("notes"),
        db_index=True,
    )
    user_text_1 = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("user_text_1"),
        db_index=True,
    )
    user_text_2 = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("user_text_2"),
        db_index=True,
    )
    user_text_3 = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("user_text_3"),
        db_index=True,
    )
    user_number_1 = models.FloatField(
        default=0.0,
        null=True,
        verbose_name=gettext_lazy("user_number_1"),
    )
    user_number_2 = models.FloatField(
        default=0.0,
        null=True,
        verbose_name=gettext_lazy("user_number_2"),
    )
    user_number_3 = models.FloatField(
        default=0.0,
        null=True,
        verbose_name=gettext_lazy("user_number_3"),
    )
    user_date_1 = models.DateField(
        blank=True,
        db_index=True,
        null=True,
        verbose_name=gettext_lazy("user date 1"),
    )
    user_date_2 = models.DateField(blank=True, db_index=True, null=True, verbose_name=gettext_lazy("user date 2"))
    user_date_3 = models.DateField(
        blank=True,
        db_index=True,
        null=True,
        verbose_name=gettext_lazy("user date 3"),
    )
    attributes = GenericRelation(
        GenericAttribute,
        verbose_name=gettext_lazy("attributes"),
    )

    class Meta:
        verbose_name = gettext_lazy("transaction")
        verbose_name_plural = gettext_lazy("transactions")
        index_together = [
            ["master_user", "transaction_code"],
            ["accounting_date", "cash_date"],
            ["master_user", "transaction_class", "accounting_date"],
        ]
        ordering = ["transaction_date", "transaction_code"]

        permissions = (("partial_view_transaction", "Partial View"),)

    def __str__(self):
        return str(self.transaction_code)

    @property
    def is_buy(self):
        return self.transaction_class_id == TransactionClass.BUY

    @property
    def is_sell(self):
        return self.transaction_class_id == TransactionClass.SELL

    @property
    def is_fx_trade(self):
        return self.transaction_class_id == TransactionClass.FX_TRADE

    @property
    def is_instrument_pl(self):
        return self.transaction_class_id == TransactionClass.INSTRUMENT_PL

    @property
    def is_transaction_pl(self):
        return self.transaction_class_id == TransactionClass.TRANSACTION_PL

    @property
    def is_transfer(self):
        return self.transaction_class_id == TransactionClass.TRANSFER

    @property
    def is_fx_transfer(self):
        return self.transaction_class_id == TransactionClass.FX_TRANSFER

    @property
    def is_cash_inflow(self):
        return self.transaction_class_id == TransactionClass.CASH_INFLOW

    @property
    def is_cash_outflow(self):
        return self.transaction_class_id == TransactionClass.CASH_OUTFLOW

    def get_instr_ytm_data_d0_v0(self, dt):
        return dt, -(self.trade_price * self.instrument.price_multiplier * self.instrument.get_factor(dt))

    def get_instr_ytm_data(self, dt):
        if hasattr(self, "_instr_ytm_data"):
            return self._instr_ytm_data

        instr = self.instrument

        if instr.maturity_date is None or instr.maturity_date == date.max:
            # _l.debug('get_instr_ytm_data: [], maturity_date rule')
            return []
        if instr.maturity_price is None or isnan(instr.maturity_price) or isclose(instr.maturity_price, 0.0):
            # _l.debug('get_instr_ytm_data: [], maturity_price rule')
            return []

        try:
            d0, v0 = self.get_instr_ytm_data_d0_v0(dt)
        except ArithmeticError:
            return None

        data = [(d0, v0)]

        for cpn_date, cpn_val in instr.get_future_coupons(begin_date=d0, with_maturity=False):
            try:
                factor = instr.get_factor(cpn_date)
                k = instr.accrued_multiplier * factor * (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx)
            except ArithmeticError:
                k = 0
            data.append((cpn_date, cpn_val * k))

        prev_factor = None
        for factor in instr.factor_schedules.all():
            if factor.effective_date < d0 or factor.effective_date > instr.maturity_date:
                prev_factor = factor
                continue

            prev_factor_value = prev_factor.factor_value if prev_factor else 1.0
            factor_value = factor.factor_value

            k = (prev_factor_value - factor_value) * instr.price_multiplier
            data.append((factor.effective_date, instr.maturity_price * k))

            prev_factor = factor

        factor = instr.get_factor(instr.maturity_date)
        k = instr.price_multiplier * factor
        data.append((instr.maturity_date, instr.maturity_price * k))

        # sort by date
        data.sort()
        self._instr_ytm_data = data

        return data

    def get_instr_ytm_x0(self, dt):
        try:
            accrual_size = self.instrument.get_accrual_size(dt)
            return (
                (accrual_size * self.instrument.accrued_multiplier)
                * (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx)
                / (self.trade_price * self.instrument.price_multiplier)
            )
        except ArithmeticError:
            return 0

    def calculate_ytm(self) -> float:
        ecosystem_default = EcosystemDefault.cache.get_cache(master_user_pk=self.instrument.master_user.pk)

        try:
            return self._calculate_ytm_value(ecosystem_default)

        except Exception as e:
            _l.error(f"calculate_ytm error {repr(e)} {traceback.format_exc()}")
            return 0

    def _calculate_ytm_value(self, ecosystem_default):
        process_st = time.perf_counter()

        if self.instrument.accrued_currency_id == self.instrument.pricing_currency_id:
            self.instr_accrued_ccy_cur_fx = 1
            self.instr_pricing_ccy_cur_fx = 1
        else:
            self.instr_accrued_ccy_cur_fx = (
                1
                if ecosystem_default.currency_id == self.instrument.accrued_currency_id
                else CurrencyHistory.objects.get(
                    date=self.accounting_date,
                    currency=self.instrument.accrued_currency,
                ).fx_rate
            )
            if ecosystem_default.currency_id == self.instrument.pricing_currency_id:
                self.instr_pricing_ccy_cur_fx = 1
            else:
                self.instr_pricing_ccy_cur_fx = CurrencyHistory.objects.get(
                    date=self.accounting_date,
                    currency=self.instrument.pricing_currency,
                ).fx_rate

        dt = self.accounting_date

        if (
            self.instrument.maturity_date is None
            or self.instrument.maturity_date == date.max
            or str(self.instrument.maturity_date) == "2999-01-01"
            or str(self.instrument.maturity_date) == "2099-01-01"
        ):
            try:
                accrual_size = self.instrument.get_accrual_size(dt)
                ytm = (accrual_size * self.instrument.accrued_multiplier) / (
                    self.trade_price * self.instrument.price_multiplier
                )

            except ArithmeticError:
                ytm = 0

            _l.debug(
                "Transaction.calculate_ytm done: %s",
                f"{time.perf_counter() - process_st:3.3f}",
            )

            return ytm

        x0 = self.get_instr_ytm_x0(dt)

        # _l.debug('Transaction.calculate_ytm: x0 %s' % x0)

        data = self.get_instr_ytm_data(dt)

        # _l.debug('Transaction.calculate_ytm: data %s' % data)

        ytm = f_xirr(data, x0=x0) if data else 0.0
        _l.info(
            "Transaction.calculate_ytm done: %s",
            f"{time.perf_counter() - process_st:3.3f}",
        )

        return ytm

    def save(self, *args, **kwargs):
        _l.debug(f"Transaction.save: {self}")

        kwargs.pop("calc_cash", None)

        if not self.accounting_date:
            self.accounting_date = date_now()

        if not self.cash_date:
            self.cash_date = date_now()

        self.transaction_date = min(self.accounting_date, self.cash_date)
        if self.transaction_code is None or self.transaction_code == 0:
            if self.complex_transaction is None:
                self.transaction_code = FakeSequence.next_value(self.master_user, "transaction")
            else:
                self.transaction_code = self.complex_transaction.code + self.complex_transaction_order

        try:
            self.ytm_at_cost = self.calculate_ytm()
        except Exception as error:
            _l.error(f"Transaction.save: Cant calculate transaction ytm_at_cost {error}")

        if self.ytm_at_cost is None:
            self.ytm_at_cost = 0

        _l.debug(f"Transaction.save: ytm is {self.ytm_at_cost}")

        super().save(*args, **kwargs)

        if self.portfolio:
            # force run of calculate_first_transactions_dates and update portfolio
            _l.debug("Transaction.save: recalculate first_transactions_dates in portfolio")
            self.portfolio.save()

        if self.instrument:
            # force run of calculate_first_transactions_dates and update instrument
            _l.debug("Transaction.save: recalculate first_transactions_dates in instrument")
            self.instrument.save()

    def delete(self, *args, **kwargs):
        _l.debug(f"Transaction.delete: {self.id}")

        super().delete(*args, **kwargs)

        if self.portfolio:
            # force run of calculate_first_transactions_dates and update portfolio
            _l.debug("Transaction.delete: recalculate first_transactions_dates in portfolio")
            self.portfolio.save()

        if self.instrument:
            # force run of calculate_first_transactions_dates and update instrument
            _l.debug("Transaction.save: recalculate first_transactions_dates in instrument")
            self.instrument.save()

    def is_can_calc_cash_by_formulas(self):
        return (
            self.transaction_class_id in [TransactionClass.BUY, TransactionClass.SELL]
            and self.instrument.instrument_type.instrument_class_id == InstrumentClass.CONTRACT_FOR_DIFFERENCE
        )

    def calc_cash_by_formulas(self, save=True):
        pass


class ExternalCashFlow(models.Model):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="external_cash_flows",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    date = models.DateField(
        default=date_now,
        db_index=True,
        verbose_name=gettext_lazy("date"),
    )
    portfolio = models.ForeignKey(
        Portfolio,
        related_name="external_cash_flows",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("portfolio"),
    )
    account = models.ForeignKey(
        Account,
        related_name="external_cash_flows",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("account"),
    )
    currency = models.ForeignKey(
        Currency,
        related_name="external_cash_flows",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("currency"),
    )
    amount = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("amount"),
    )

    class Meta:
        verbose_name = gettext_lazy("external cash flow")
        verbose_name_plural = gettext_lazy("external cash flows")
        ordering = ["date"]

    def __str__(self):
        return (
            f"{self.date}: {self.portfolio} - {self.account} - "
            f"{list(self.strategies.all())} - {self.currency} = {self.amount}"
        )


class ExternalCashFlowStrategy(models.Model):
    external_cash_flow = models.ForeignKey(
        ExternalCashFlow,
        related_name="strategies",
        verbose_name=gettext_lazy("external cash flow"),
        on_delete=models.CASCADE,
    )
    order = models.IntegerField(
        default=0,
        verbose_name=gettext_lazy("order"),
    )
    strategy1 = models.ForeignKey(
        Strategy1,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="external_cash_flow_strategies1",
        verbose_name=gettext_lazy("strategy1"),
    )
    strategy2 = models.ForeignKey(
        Strategy2,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="external_cash_flow_strategies2",
        verbose_name=gettext_lazy("strategy2"),
    )
    strategy3 = models.ForeignKey(
        Strategy3,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="external_cash_flow_strategies3",
        verbose_name=gettext_lazy("strategy3"),
    )

    class Meta:
        verbose_name = gettext_lazy("external cash flow strategy")
        verbose_name_plural = gettext_lazy("external cash flow strtegies")
        ordering = ["order"]

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.strategy = None

    def __str__(self):
        return f"{self.strategy}"
