import binascii
import json
import logging
import os
import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy

import pytz

from poms.common.models import FakeDeletableModel
from poms.common.utils import get_content_type_by_name

AVAILABLE_APPS = [
    "accounts",
    "counterparties",
    "currencies",
    "instruments",
    "portfolios",
    "strategies",
    "transactions",
    "reports",
    "users",
]

LANGUAGE_MAX_LENGTH = 5
TIMEZONE_MAX_LENGTH = 20
TIMEZONE_CHOICES = sorted([(k, k) for k in pytz.all_timezones])
TIMEZONE_COMMON_CHOICES = sorted([(k, k) for k in pytz.common_timezones])

_l = logging.getLogger("poms.users")


class ResetPasswordToken(models.Model):
    class Meta:
        verbose_name = gettext_lazy("Password Reset Token")
        verbose_name_plural = gettext_lazy("Password Reset Tokens")

    @staticmethod
    def generate_key():
        """generates a pseudo random code using os.urandom and binascii.hexlify"""
        return binascii.hexlify(os.urandom(32)).decode()

    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="password_reset_tokens",
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy(
            "The User which is associated to this password reset token"
        ),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=gettext_lazy("When was this token generated"),
    )
    # Key field, though it is not the primary key of the model
    key = models.CharField(
        gettext_lazy("Key"),
        max_length=64,
        db_index=True,
        unique=True,
    )
    ip_address = models.GenericIPAddressField(
        gettext_lazy("The IP address of this session"),
        default="127.0.0.1",
    )
    user_agent = models.CharField(
        max_length=256,
        verbose_name=gettext_lazy("HTTP User Agent"),
        default="",
    )

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ResetPasswordToken, self).save(*args, **kwargs)

    def __str__(self):
        return "Password reset token for user {user}".format(user=self.user)


class MasterUserManager(models.Manager):
    def create_master_user(self, user=None, **kwargs):
        obj = MasterUser(**kwargs)
        obj.token = uuid.uuid4().hex
        obj.save()

        obj.create_defaults()

        return obj


class MasterUser(models.Model):
    """
    Master User

    One of core entities, and its most important.
    Its a Finmars Installation instance, it uses Space Id (space_code) which make
    each Finmars installation unique
    Sometimes master_user called as ecosystem, workspace, space or even ledger

    In old days, Finmars Installation was a single Django App and Single Database,
    and inside one database
    to be able have multiple Installations this entity was created. And this why
    almost any Entity has a Relation to MasterUser or Member

    """

    STATUS_ONLINE = 1
    STATUS_OFFLINE = 2
    STATUS_BACKUP = 3

    STATUSES = (
        (STATUS_ONLINE, gettext_lazy("Online")),
        (STATUS_OFFLINE, gettext_lazy("Offline")),
        (STATUS_BACKUP, gettext_lazy("Backup")),
    )

    JOURNAL_STATUS_FULL = "full"
    JOURNAL_STATUS_DISABLED = "disabled"

    JOURNAL_STATUS_CHOICES = (
        (JOURNAL_STATUS_FULL, gettext_lazy("Full")),
        (JOURNAL_STATUS_DISABLED, gettext_lazy("Disabled")),
    )

    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    JOURNAL_POLICY_DAYS = {WEEK: 7, MONTH: 30, QUARTER: 90}

    name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("name"),
    )

    realm_code = models.CharField(
        max_length=255,
        # unique=True, # fix later in 1.9.0, because existing spaces could not have realm_code yet
        null=True,
        blank=True,
        verbose_name=gettext_lazy("realm_code"),
    )

    space_code = models.CharField(
        max_length=255,
        unique=True,
        # null=True,
        # blank=True,
        verbose_name=gettext_lazy("space_code"),
    )

    description = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("description"),
    )
    status = models.PositiveSmallIntegerField(
        default=STATUS_ONLINE,
        choices=STATUSES,
        verbose_name=gettext_lazy("status"),
    )
    journal_status = models.CharField(
        max_length=25,
        default=JOURNAL_STATUS_FULL,
        choices=JOURNAL_STATUS_CHOICES,
        verbose_name="journal status",
    )
    language = models.CharField(
        max_length=LANGUAGE_MAX_LENGTH,
        default=settings.LANGUAGE_CODE,
        verbose_name=gettext_lazy("language"),
    )
    timezone = models.CharField(
        max_length=TIMEZONE_MAX_LENGTH,
        default=settings.TIME_ZONE,
        verbose_name=gettext_lazy("timezone"),
        help_text="timezone to use",
    )
    notification_business_days = models.IntegerField(default=0)
    user_code_counters = ArrayField(
        models.IntegerField(null=True, blank=True),
        null=True,
        blank=True,
    )
    token = models.CharField(
        unique=True,
        max_length=32,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("token"),
        help_text="access token",
    )
    unique_id = models.UUIDField(
        null=True,
        blank=True,
    )
    journal_storage_policy = models.CharField(
        max_length=32,
        default=MONTH,
        verbose_name=gettext_lazy("journal_policy"),
        help_text="period to keep records (week, month, quarter & etc)",
    )

    objects = MasterUserManager()

    class Meta:
        verbose_name = gettext_lazy("master user")
        verbose_name_plural = gettext_lazy("master users")

    def __str__(self):
        return self.name

    def create_user_fields(self):
        from poms.ui.models import ComplexTransactionUserField, InstrumentUserField

        finmars_bot = Member.objects.get(username="finmars_bot")

        for i in range(20):
            num = str(i + 1)
            key = f"user_text_{num}"
            ComplexTransactionUserField.objects.create(
                master_user=self,
                owner=finmars_bot,
                key=key,
                name=f"User Text {num}",
                user_code=key,
            )

        for i in range(20):
            num = str(i + 1)
            key = f"user_number_{num}"
            ComplexTransactionUserField.objects.create(
                master_user=self,
                owner=finmars_bot,
                key=key,
                name=f"User Number {num}",
                user_code=key,
            )

        for i in range(5):
            num = str(i + 1)
            key = f"user_date_{num}"
            ComplexTransactionUserField.objects.create(
                master_user=self,
                owner=finmars_bot,
                key=key,
                name=f"User Date {num}",
                user_code=key,
            )

        for i in range(3):
            num = str(i + 1)
            key = f"user_text_{num}"
            InstrumentUserField.objects.create(
                master_user=self,
                owner=finmars_bot,
                key=key,
                name=f"User Text {num}",
                user_code=key,
            )

    def create_entity_tooltips(self):
        from poms.ui.models import EntityTooltip

        entity_fields = [
            {
                "content_type": "instruments.instrument",
                "fields": [
                    {"name": "User Code", "key": "user_code"},
                    {"name": "Name", "key": "name"},
                    {"name": "Short Name", "key": "short_name"},
                    {"name": "Public Name", "key": "public_name"},
                    {"name": "Notes", "key": "notes"},
                    {"name": "Instrument Tye", "key": "instrument_type"},
                    {"name": "Is Active", "key": "is_active"},
                    {"name": "Reference for Pricing", "key": "reference_for_pricing"},
                    {"name": "Maturity Date", "key": "maturity_date"},
                    {"name": "Default Price", "key": "default_price"},
                    {"name": "Default Accrued", "key": "default_accrued"},
                    {"name": "Pricing Currency", "key": "pricing_currency"},
                    {"name": "Accrued Currency", "key": "accrued_currency"},
                    {"name": "Pricing Condition", "key": "pricing_condition"},
                    {"name": "Price Multiplier", "key": "price_multiplier"},
                    {"name": "Accrued Multiplier", "key": "accrued_multiplier"},
                    {"name": "Payment Size Detail", "key": "payment_size_detail"},
                    {"name": "Maturity Price", "key": "maturity_price"},
                    {"name": "User Text 1", "key": "user_text_1"},
                    {"name": "User Text 2", "key": "user_text_2"},
                    {"name": "User Text 3", "key": "user_text_3"},
                ],
            },
            {
                "content_type": "instruments.instrumenttype",
                "fields": [
                    {"name": "User Code", "key": "user_code"},
                    {"name": "Name", "key": "name"},
                    {"name": "Short Name", "key": "short_name"},
                    {"name": "Public Name", "key": "public_name"},
                    {"name": "Notes", "key": "notes"},
                    {"name": "Factor Down", "key": "factor_down"},
                    {"name": "Factor Same", "key": "factor_same"},
                    {"name": "Factor Up", "key": "factor_up"},
                    {"name": "Instrument Class", "key": "instrument_class"},
                    {"name": "One Off Event", "key": "one_off_event"},
                    {"name": "Regular Event", "key": "regular_event"},
                ],
            },
            {
                "content_type": "portfolios.portfolio",
                "fields": [
                    {"name": "User Code", "key": "user_code"},
                    {"name": "Name", "key": "name"},
                    {"name": "Short Name", "key": "short_name"},
                    {"name": "Public Name", "key": "public_name"},
                    {"name": "Notes", "key": "notes"},
                ],
            },
            {
                "content_type": "accounts.account",
                "fields": [
                    {"name": "User Code", "key": "user_code"},
                    {"name": "Name", "key": "name"},
                    {"name": "Short Name", "key": "short_name"},
                    {"name": "Public Name", "key": "public_name"},
                    {"name": "Notes", "key": "notes"},
                    {"name": "Type", "key": "type"},
                ],
            },
            {
                "content_type": "accounts.accounttype",
                "fields": [
                    {"name": "User Code", "key": "user_code"},
                    {"name": "Name", "key": "name"},
                    {"name": "Short Name", "key": "short_name"},
                    {"name": "Public Name", "key": "public_name"},
                    {"name": "Notes", "key": "notes"},
                    {
                        "name": "Transaction Details Expression",
                        "key": "transaction_details_expr",
                    },
                    {
                        "name": "Show Transaction Details",
                        "key": "show_transaction_details",
                    },
                ],
            },
            {
                "content_type": "counterparties.responsible",
                "fields": [
                    {"name": "User Code", "key": "user_code"},
                    {"name": "Name", "key": "name"},
                    {"name": "Short Name", "key": "short_name"},
                    {"name": "Public Name", "key": "public_name"},
                    {"name": "Group", "key": "group"},
                ],
            },
            {
                "content_type": "counterparties.counterparty",
                "fields": [
                    {"name": "User Code", "key": "user_code"},
                    {"name": "Name", "key": "name"},
                    {"name": "Short Name", "key": "short_name"},
                    {"name": "Public Name", "key": "public_name"},
                    {"name": "Notes", "key": "notes"},
                    {"name": "Group", "key": "group"},
                ],
            },
            {
                "content_type": "strategies.strategy1",
                "fields": [
                    {"name": "User Code", "key": "user_code"},
                    {"name": "Name", "key": "name"},
                    {"name": "Short Name", "key": "short_name"},
                    {"name": "Public Name", "key": "public_name"},
                    {"name": "Notes", "key": "notes"},
                    {"name": "Group", "key": "subgroup"},
                ],
            },
            {
                "content_type": "strategies.strategy2",
                "fields": [
                    {"name": "User Code", "key": "user_code"},
                    {"name": "Name", "key": "name"},
                    {"name": "Short Name", "key": "short_name"},
                    {"name": "Public Name", "key": "public_name"},
                    {"name": "Notes", "key": "notes"},
                    {"name": "Group", "key": "subgroup"},
                ],
            },
            {
                "content_type": "strategies.strategy3",
                "fields": [
                    {"name": "User Code", "key": "user_code"},
                    {"name": "Name", "key": "name"},
                    {"name": "Short Name", "key": "short_name"},
                    {"name": "Public Name", "key": "public_name"},
                    {"name": "Notes", "key": "notes"},
                    {"name": "Group", "key": "subgroup"},
                ],
            },
            {
                "content_type": "currencies.currency",
                "fields": [
                    {"name": "User Code", "key": "user_code"},
                    {"name": "Name", "key": "name"},
                    {"name": "Short Name", "key": "short_name"},
                    {"name": "Public Name", "key": "public_name"},
                    {"name": "Notes", "key": "notes"},
                    {"name": "Default FX Rate", "key": "default_fx_rate"},
                    {"name": "Reference For Pricing", "key": "reference_for_pricing"},
                ],
            },
            {
                "content_type": "instruments.pricehistory",
                "fields": [
                    {"name": "Instrument", "key": "instrument"},
                    {"name": "Date", "key": "date"},
                    {"name": "Pricing Policy", "key": "pricing_policy"},
                    {"name": "Principal Price", "key": "principal_price"},
                    {"name": "Accrued Price", "key": "accrued_price"},
                ],
            },
            {
                "content_type": "currencies.currencyhistory",
                "fields": [
                    {"name": "Currency", "key": "currency"},
                    {"name": "Date", "key": "date"},
                    {"name": "Pricing Policy", "key": "pricing_policy"},
                    {"name": "FX Rate", "key": "fx_rate"},
                ],
            },
        ]

        for entity in entity_fields:
            content_type = get_content_type_by_name(entity["content_type"])

            for field in entity["fields"]:
                try:
                    item = EntityTooltip.objects.get(
                        master_user=self, key=field["key"], content_type=content_type
                    )

                    item.name = field["name"]
                    item.save()

                except EntityTooltip.DoesNotExist:
                    item = EntityTooltip.objects.create(
                        master_user=self,
                        name=field["name"],
                        key=field["key"],
                        content_type=content_type,
                    )
                    item.save()

    def create_color_palettes(self):
        from poms.ui.models import ColorPalette, ColorPaletteColor

        finmars_bot = Member.objects.get(username="finmars_bot")

        default_color_map = {
            0: "#000000",
            1: "#0080FF",
            2: "#8080C0",
            3: "#8080FF",
            4: "#FF8080",
            5: "#FF80C0",
            6: "#FF00FF",
            7: "#0F87FF",
            8: "#FFFF80",
            9: "#FF0000",
            10: "#804040",
            11: "#8000FF",
            12: "#80FFFF",
            13: "#0080C0",
            14: "#FF8040",
            15: "#808040",
        }

        for i in range(1):
            user_code = "Default Palette" if i == 0 else f"Palette {str(i)}"
            try:
                palette = ColorPalette.objects.get(
                    master_user=self,
                    owner=finmars_bot,
                    user_code=user_code,
                )

            except ColorPalette.DoesNotExist:
                palette = ColorPalette.objects.create(
                    master_user=self,
                    owner=finmars_bot,
                    user_code=user_code,
                )

                palette.name = user_code
                palette.is_default = i == 0
                palette.save()

            for x in range(16):
                try:
                    color = ColorPaletteColor.objects.get(
                        color_palette=palette,
                        order=x,
                    )

                    if not color.value:
                        color.value = default_color_map[x]
                        color.save()

                except ColorPaletteColor.DoesNotExist:
                    color = ColorPaletteColor.objects.create(
                        color_palette=palette,
                        order=x,
                    )

                    color.name = f"Color {str(x + 1)}"
                    color.save()

    def create_defaults(self, user=None):
        from poms.accounts.models import Account, AccountType
        from poms.counterparties.models import (
            Counterparty,
            CounterpartyGroup,
            Responsible,
            ResponsibleGroup,
        )
        from poms.currencies.models import Currency, currencies_data
        from poms.instruments.models import (
            AccrualCalculationModel,
            EventScheduleConfig,
            Instrument,
            InstrumentClass,
            InstrumentType,
            PaymentSizeDetail,
            Periodicity,
            PricingCondition,
            PricingPolicy,
        )
        from poms.portfolios.models import Portfolio

        from poms.strategies.models import (
            Strategy1,
            Strategy1Group,
            Strategy1Subgroup,
            Strategy2,
            Strategy2Group,
            Strategy2Subgroup,
            Strategy3,
            Strategy3Group,
            Strategy3Subgroup,
        )
        from poms.transactions.models import TransactionType, TransactionTypeGroup

        if not EventScheduleConfig.objects.filter(master_user=self).exists():
            EventScheduleConfig.create_default(master_user=self)

        try:
            finmars_bot = Member.objects.get(username="finmars_bot")
        except Exception as e:
            # Its needed for tests context

            from django.contrib.auth.models import User

            try:
                user = User.objects.get(username="finmars_bot")

            except Exception as e:
                user = User.objects.create(username="finmars_bot")

            finmars_bot = Member.objects.create(
                user=user, username="finmars_bot", master_user=self, is_admin=True
            )

        ccys = {}
        ccy = Currency.objects.create(
            master_user=self, name="-", user_code="-", owner=finmars_bot
        )
        ccy_usd = None
        dc_reference_for_pricing = ""

        for dc in currencies_data.values():
            dc_user_code = dc["user_code"]
            dc_name = dc.get("name", dc_user_code)
            if dc_user_code != "-":
                if dc_user_code == "USD":
                    c = Currency.objects.create(
                        master_user=self,
                        user_code=dc_user_code,
                        short_name=dc_user_code,
                        name=dc_name,
                        owner=finmars_bot,
                        reference_for_pricing=dc_reference_for_pricing,
                    )
                    ccy_usd = c
                else:
                    c = Currency.objects.create(
                        master_user=self,
                        user_code=dc_user_code,
                        short_name=dc_user_code,
                        name=dc_name,
                        owner=finmars_bot,
                        reference_for_pricing=dc_reference_for_pricing,
                    )
                ccys[c.user_code] = c

        account_type = AccountType.objects.create(
            master_user=self, name="-", owner=finmars_bot
        )
        account = Account.objects.create(
            master_user=self, type=account_type, name="-", owner=finmars_bot
        )

        counterparty_group = CounterpartyGroup.objects.create(
            master_user=self,
            name="-",
            owner=finmars_bot,
        )
        counterparty = Counterparty.objects.create(
            master_user=self,
            group=counterparty_group,
            name="-",
            owner=finmars_bot,
        )
        responsible_group = ResponsibleGroup.objects.create(
            master_user=self,
            name="-",
            owner=finmars_bot,
        )
        responsible = Responsible.objects.create(
            master_user=self,
            group=responsible_group,
            name="-",
            owner=finmars_bot,
        )
        portfolio = Portfolio.objects.create(
            master_user=self,
            name="-",
            owner=finmars_bot,
        )
        instrument_general_class = InstrumentClass.objects.get(
            pk=InstrumentClass.GENERAL
        )
        instrument_type = InstrumentType.objects.create(
            master_user=self,
            instrument_class=instrument_general_class,
            name="-",
            owner=finmars_bot,
        )
        instrument = Instrument.objects.create(
            master_user=self,
            instrument_type=instrument_type,
            pricing_currency=ccy,
            accrued_currency=ccy,
            name="-",
            owner=finmars_bot,
        )
        strategy1_group = Strategy1Group.objects.create(
            master_user=self,
            name="-",
            owner=finmars_bot,
        )
        strategy1_subgroup = Strategy1Subgroup.objects.create(
            master_user=self,
            group=strategy1_group,
            name="-",
            owner=finmars_bot,
        )
        strategy1 = Strategy1.objects.create(
            master_user=self,
            subgroup=strategy1_subgroup,
            name="-",
            owner=finmars_bot,
        )
        strategy2_group = Strategy2Group.objects.create(
            master_user=self,
            name="-",
            owner=finmars_bot,
        )
        strategy2_subgroup = Strategy2Subgroup.objects.create(
            master_user=self,
            group=strategy2_group,
            name="-",
            owner=finmars_bot,
        )
        strategy2 = Strategy2.objects.create(
            master_user=self,
            subgroup=strategy2_subgroup,
            name="-",
            owner=finmars_bot,
        )
        strategy3_group = Strategy3Group.objects.create(
            master_user=self,
            name="-",
            owner=finmars_bot,
        )
        strategy3_subgroup = Strategy3Subgroup.objects.create(
            master_user=self,
            group=strategy3_group,
            name="-",
            owner=finmars_bot,
        )
        strategy3 = Strategy3.objects.create(
            master_user=self,
            subgroup=strategy3_subgroup,
            name="-",
            owner=finmars_bot,
        )
        transaction_type = TransactionType.objects.create(
            master_user=self,
            name="-",
            owner=finmars_bot,
        )
        transaction_type_group = TransactionTypeGroup.objects.create(
            master_user=self,
            name="-",
            owner=finmars_bot,
        )
        pricing_policy = PricingPolicy.objects.create(
            master_user=self,
            name="-",
            expr="(ask+bid)/2",
            owner=finmars_bot,
        )
        # pricing_policy_dft = PricingPolicy.objects.create(
        #     master_user=self,
        #     name="DFT",
        #     expr="(ask+bid)/2",
        # )

        # bloomberg = ProviderClass.objects.get(pk=ProviderClass.BLOOMBERG)

        # TODO refactor later, that thing used in report logic,
        # TODO so, someday we need to change it to take defaults from EcosystemDefault
        self.system_currency = ccy_usd
        self.currency = ccy
        self.account_type = account_type
        self.account = account
        self.counterparty_group = counterparty_group
        self.counterparty = counterparty
        self.responsible_group = responsible_group
        self.responsible = responsible
        self.portfolio = portfolio
        self.instrument_type = instrument_type
        self.instrument = instrument
        self.strategy1_group = strategy1_group
        self.strategy1_subgroup = strategy1_subgroup
        self.strategy1 = strategy1
        self.strategy2_group = strategy2_group
        self.strategy2_subgroup = strategy2_subgroup
        self.strategy2 = strategy2
        self.strategy3_group = strategy3_group
        self.strategy3_subgroup = strategy3_subgroup
        self.strategy3 = strategy3
        self.transaction_type_group = transaction_type_group
        self.mismatch_portfolio = portfolio
        self.mismatch_account = account
        self.pricing_policy = pricing_policy
        self.transaction_type = transaction_type

        ecosystem_defaults = EcosystemDefault()

        ecosystem_defaults.master_user = self
        # ecosystem_defaults.currency = ccy
        # Should be  usd by default 2023-11-14 szhitenev
        ecosystem_defaults.currency = ccy_usd
        ecosystem_defaults.account_type = account_type
        ecosystem_defaults.account = account
        ecosystem_defaults.counterparty_group = counterparty_group
        ecosystem_defaults.counterparty = counterparty
        ecosystem_defaults.responsible_group = responsible_group
        ecosystem_defaults.responsible = responsible
        ecosystem_defaults.portfolio = portfolio
        ecosystem_defaults.instrument_type = instrument_type
        ecosystem_defaults.instrument = instrument
        ecosystem_defaults.strategy1_group = strategy1_group
        ecosystem_defaults.strategy1_subgroup = strategy1_subgroup
        ecosystem_defaults.strategy1 = strategy1
        ecosystem_defaults.strategy2_group = strategy2_group
        ecosystem_defaults.strategy2_subgroup = strategy2_subgroup
        ecosystem_defaults.strategy2 = strategy2
        ecosystem_defaults.strategy3_group = strategy3_group
        ecosystem_defaults.strategy3_subgroup = strategy3_subgroup
        ecosystem_defaults.strategy3 = strategy3
        ecosystem_defaults.transaction_type_group = transaction_type_group
        ecosystem_defaults.mismatch_portfolio = portfolio
        ecosystem_defaults.mismatch_account = account
        ecosystem_defaults.pricing_policy = pricing_policy
        ecosystem_defaults.transaction_type = transaction_type

        ecosystem_defaults.instrument_class = InstrumentClass.objects.get(
            pk=InstrumentClass.DEFAULT
        )
        ecosystem_defaults.accrual_calculation_model = (
            AccrualCalculationModel.objects.get(
                pk=AccrualCalculationModel.DAY_COUNT_SIMPLE
            )
        )
        ecosystem_defaults.payment_size_detail = PaymentSizeDetail.objects.get(
            pk=PaymentSizeDetail.DEFAULT
        )
        ecosystem_defaults.periodicity = Periodicity.objects.get(pk=Periodicity.DEFAULT)
        ecosystem_defaults.pricing_condition = PricingCondition.objects.get(
            pk=PricingCondition.NO_VALUATION
        )

        ecosystem_defaults.save()

        self.create_user_fields()
        self.create_entity_tooltips()
        self.create_color_palettes()

        self.save()

        FakeSequence.objects.get_or_create(master_user=self, name="complex_transaction")
        FakeSequence.objects.get_or_create(master_user=self, name="transaction")

    def patch_currencies(
        self, overwrite_name=False, overwrite_reference_for_pricing=False
    ):
        from poms.currencies.models import Currency, currencies_data

        ccys_existed = {
            c.user_code: c
            for c in Currency.objects.filter(master_user=self, is_deleted=False)
        }

        ccys = {}
        for dc in currencies_data.values():
            dc_user_code = dc["user_code"]
            dc_name = dc.get("name", dc_user_code)
            dc_reference_for_pricing = dc.get("reference_for_pricing", None)

            if dc_user_code in ccys_existed:
                c1 = ccys_existed[dc_user_code]
                is_change = False

                if overwrite_name or not c1.name:
                    c1.name = dc_name
                    is_change = True

                if overwrite_name or not c1.short_name:
                    c1.short_name = dc_name
                    is_change = True

                if overwrite_name or not c1.public_name:
                    c1.public_name = dc_name
                    is_change = True

                if overwrite_reference_for_pricing or not c1.reference_for_pricing:
                    c1.reference_for_pricing = dc_reference_for_pricing
                    is_change = True

                if is_change:
                    c1.save()
            else:
                c = Currency.objects.create(
                    master_user=self,
                    user_code=dc_user_code,
                    name=dc_name,
                    short_name=dc_user_code,
                    public_name=dc_name,
                    reference_for_pricing=dc_reference_for_pricing,
                )
                ccys[c.user_code] = c

    def patch_bloomberg_currency_mappings(self, overwrite_mapping=False):
        from poms.currencies.models import Currency, currencies_data
        from poms.integrations.models import CurrencyMapping, ProviderClass

        bloomberg = ProviderClass.objects.get(pk=ProviderClass.BLOOMBERG)

        ccys = {c.user_code: c for c in Currency.objects.filter(master_user=self)}

        mapping_existed = {
            m.currency_id: m
            for m in CurrencyMapping.objects.filter(
                master_user=self, provider=bloomberg
            )
        }

        for dc in currencies_data.values():
            dc_user_code = dc["user_code"]
            if dc_user_code != "-" and dc_user_code in ccys:
                c = ccys[dc_user_code]
                dc_bloomberg = dc["bloomberg"]

                if c.id in mapping_existed:
                    if overwrite_mapping:
                        mapping = mapping_existed[c.id]
                        mapping.value = dc_bloomberg
                        mapping.save()
                else:
                    CurrencyMapping.objects.create(
                        master_user=self,
                        provider=bloomberg,
                        value=dc_bloomberg,
                        currency=c,
                    )


class EcosystemDefault(models.Model):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="ecosystem_default",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    account_type = models.ForeignKey(
        "accounts.AccountType",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("account type"),
    )
    account = models.ForeignKey(
        "accounts.Account",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("account"),
    )
    currency = models.ForeignKey(
        "currencies.Currency",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("currency"),
    )
    counterparty_group = models.ForeignKey(
        "counterparties.CounterpartyGroup",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("counterparty group"),
    )
    counterparty = models.ForeignKey(
        "counterparties.Counterparty",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("counterparty"),
    )
    responsible_group = models.ForeignKey(
        "counterparties.ResponsibleGroup",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("responsible group"),
    )
    responsible = models.ForeignKey(
        "counterparties.Responsible",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("responsible"),
    )
    instrument_type = models.ForeignKey(
        "instruments.InstrumentType",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("instrument type"),
    )
    instrument = models.ForeignKey(
        "instruments.Instrument",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("instrument"),
    )
    portfolio = models.ForeignKey(
        "portfolios.Portfolio",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("portfolio"),
    )
    strategy1_group = models.ForeignKey(
        "strategies.Strategy1Group",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy1 group"),
    )
    strategy1_subgroup = models.ForeignKey(
        "strategies.Strategy1Subgroup",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy1 subgroup"),
    )
    strategy1 = models.ForeignKey(
        "strategies.Strategy1",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy1"),
    )
    strategy2_group = models.ForeignKey(
        "strategies.Strategy2Group",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy2 group"),
    )
    strategy2_subgroup = models.ForeignKey(
        "strategies.Strategy2Subgroup",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy2 subgroup"),
    )
    strategy2 = models.ForeignKey(
        "strategies.Strategy2",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy2"),
    )
    strategy3_group = models.ForeignKey(
        "strategies.Strategy3Group",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy3 group"),
    )
    strategy3_subgroup = models.ForeignKey(
        "strategies.Strategy3Subgroup",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy3 subgroup"),
    )
    strategy3 = models.ForeignKey(
        "strategies.Strategy3",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("strategy3"),
    )
    transaction_type = models.ForeignKey(
        "transactions.TransactionType",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("transaction type"),
    )
    transaction_type_group = models.ForeignKey(
        "transactions.TransactionTypeGroup",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("transaction type group"),
    )
    mismatch_portfolio = models.ForeignKey(
        "portfolios.Portfolio",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ecosystem_default_mismatch_portfolio",
        verbose_name=gettext_lazy("mismatch portfolio"),
    )
    mismatch_account = models.ForeignKey(
        "accounts.Account",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ecosystem_default_mismatch_account",
        verbose_name=gettext_lazy("mismatch account"),
    )
    pricing_policy = models.ForeignKey(
        "instruments.PricingPolicy",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("pricing policy"),
    )
    instrument_class = models.ForeignKey(
        "instruments.InstrumentClass",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("instrument class"),
    )
    accrual_calculation_model = models.ForeignKey(
        "instruments.AccrualCalculationModel",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("accrual calculation model"),
    )
    payment_size_detail = models.ForeignKey(
        "instruments.PaymentSizeDetail",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("payment size detail"),
    )
    periodicity = models.ForeignKey(
        "instruments.Periodicity",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("periodicity"),
    )
    pricing_condition = models.ForeignKey(
        "instruments.PricingCondition",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("pricing condition"),
    )


class Member(FakeDeletableModel):
    DO_NOT_NOTIFY = 1
    SHOW_AND_EMAIL = 2
    EMAIL_ONLY = 3
    SHOW_ONLY = 4
    NOTIFICATION_STATUS_CHOICES = (
        (DO_NOT_NOTIFY, gettext_lazy("Do not notify")),
        (SHOW_AND_EMAIL, gettext_lazy("Show & Email notifications")),
        (EMAIL_ONLY, gettext_lazy("Email notifications")),
        (SHOW_ONLY, gettext_lazy("Show notifications")),
    )

    STATUS_ACTIVE = "active"
    STATUS_BLOCKED = "blocked"
    STATUS_DELETED = "deleted"
    STATUS_INVITED = "invited"
    STATUS_INVITE_DECLINED = "invite_declined"

    MEMBER_STATUS_CHOICES = (
        (STATUS_ACTIVE, gettext_lazy("Active")),
        (STATUS_BLOCKED, gettext_lazy("Blocked")),
        (STATUS_DELETED, gettext_lazy("Deleted")),
        (STATUS_INVITED, gettext_lazy("Invited")),
        (STATUS_INVITE_DECLINED, gettext_lazy("Invite Declined")),
    )

    master_user = models.ForeignKey(
        MasterUser,
        related_name="members",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        verbose_name=gettext_lazy("user"),
    )
    username = models.CharField(
        max_length=255,
        blank=True,
        default="",
        editable=False,
        verbose_name=gettext_lazy("username"),
    )
    first_name = models.CharField(
        max_length=30,
        blank=True,
        default="",
        editable=False,
        verbose_name=gettext_lazy("first name"),
    )
    last_name = models.CharField(
        max_length=30,
        blank=True,
        default="",
        editable=False,
        verbose_name=gettext_lazy("last name"),
    )
    email = models.EmailField(
        blank=True,
        default="",
        editable=False,
        verbose_name=gettext_lazy("email"),
    )
    notification_level = models.PositiveSmallIntegerField(
        default=SHOW_ONLY,
        choices=NOTIFICATION_STATUS_CHOICES,
        db_index=True,
        verbose_name=gettext_lazy("notification level"),
    )
    interface_level = models.PositiveSmallIntegerField(
        default=20,
        db_index=True,
        verbose_name=gettext_lazy("interface level"),
    )
    join_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=gettext_lazy("join date"),
    )
    is_owner = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("is owner"),
    )
    is_admin = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("is admin"),
    )
    json_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("json data"),
    )
    status = models.CharField(
        max_length=255,
        choices=MEMBER_STATUS_CHOICES,
        default="active",
    )

    @property
    def data(self):
        if not self.json_data:
            return None
        try:
            return json.loads(self.json_data)
        except (ValueError, TypeError):
            return None

    @data.setter
    def data(self, val):
        if val:
            self.json_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.json_data = None

    class Meta(FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("member")
        verbose_name_plural = gettext_lazy("members")
        unique_together = [["master_user", "user"]]
        ordering = ["username"]

    def save(self, *args, **kwargs):
        from poms.configuration.utils import get_default_configuration_code
        from poms.ui.models import MemberLayout

        instance = super().save(*args, **kwargs)

        configuration_code = get_default_configuration_code()
        try:
            layout, _ = MemberLayout.objects.get_or_create(
                member_id=self.id,
                owner_id=self.id,
                configuration_code=configuration_code,
                user_code=f"{configuration_code}:default_member_layout",
                defaults={
                    "name": "default",
                    "is_default": True,
                },
            )
        except Exception as e:
            _l.error(f"Could not create member {self.username} layout due to {repr(e)}")

        return instance

    def __str__(self):
        return self.username

    def fake_delete(self):
        # self.user = None # WTF, why we need this?, user should be keeped with member (since 2023-01-01)
        self.is_deleted = True
        self.save()

    @property
    def is_superuser(self):
        return self.is_owner or self.is_admin

    @property
    def display_name(self):
        if self.first_name or self.last_name:
            return " ".join([self.first_name, self.last_name])
        else:
            return self.username


class OtpToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="otp_tokens",
        verbose_name=gettext_lazy("OTP Token"),
    )
    name = models.CharField(
        max_length=80,
        verbose_name=gettext_lazy("name"),
    )
    secret = models.CharField(
        max_length=16,
        blank=True,
        default="",
        editable=False,
        verbose_name=gettext_lazy("secret"),
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("is active"),
    )


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="profile",
        verbose_name=gettext_lazy("user"),
        on_delete=models.CASCADE,
    )
    language = models.CharField(
        max_length=LANGUAGE_MAX_LENGTH,
        default=settings.LANGUAGE_CODE,
        verbose_name=gettext_lazy("language"),
    )
    timezone = models.CharField(
        max_length=TIMEZONE_MAX_LENGTH,
        default=settings.TIME_ZONE,
        verbose_name=gettext_lazy("timezone"),
    )
    two_factor_verification = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("two factor verification"),
    )
    active_master_user = models.ForeignKey(
        MasterUser,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("master user"),
        on_delete=models.SET_NULL,
    )
    user_unique_id = models.UUIDField(
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = gettext_lazy("profile")
        verbose_name_plural = gettext_lazy("profiles")

    def __str__(self):
        return self.user.username


class UsercodePrefix(models.Model):
    master_user = models.ForeignKey(
        MasterUser,
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    value = models.CharField(
        max_length=80,
        verbose_name=gettext_lazy("prefix"),
    )
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("notes"),
    )


class FakeSequence(models.Model):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="fake_sequences",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        max_length=80,
        verbose_name=gettext_lazy("name"),
    )
    value = models.PositiveIntegerField(
        default=0,
        verbose_name=gettext_lazy("value"),
    )

    class Meta:
        verbose_name = gettext_lazy("fake sequence")
        verbose_name_plural = gettext_lazy("fake sequences")
        unique_together = [["master_user", "name"]]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}: {self.value}"

    @classmethod
    def next_value(cls, master_user, name, d=1):
        seq, created = cls.objects.update_or_create(master_user=master_user, name=name)

        if not d:
            d = 1
        if d == 1:
            seq.value += 1
        else:
            seq.value = ((seq.value + d) // d) * d

        seq.save(update_fields=["value"])

        return seq.value


# @receiver(post_save, dispatch_uid='create_profile', sender=settings.AUTH_USER_MODEL)
# def create_profile(sender, instance=None, created=None, **kwargs):
#     if created:
#         UserProfile.objects.create(
#             user=instance,
#             language=settings.LANGUAGE_CODE,
#             timezone=settings.TIME_ZONE,
#         )
#
#
# @receiver(post_save, dispatch_uid='update_member_when_member_created', sender=Member)
# def update_member_when_member_created(sender, instance=None, created=None, **kwargs):
#     if created:
#         instance.username = instance.user.username
#         instance.first_name = instance.user.first_name
#         instance.last_name = instance.user.last_name
#         instance.email = instance.user.email
#         instance.save(update_fields=['username', 'first_name', 'last_name', 'email'])
#
#
# @receiver(post_save, dispatch_uid='update_member_when_user_updated', sender=settings.AUTH_USER_MODEL)
# def update_member_when_user_updated(sender, instance=None, created=None, **kwargs):
#     if not created:
#         instance.members.all().update(
#             username=instance.username,
#             first_name=instance.first_name,
#             last_name=instance.last_name,
#             email=instance.email
#         )
