from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

from poms.accounts.models import Account
from poms.common.admin import AbstractModelAdmin, ClassModelAdmin
from poms.counterparties.models import Counterparty, Responsible
from poms.currencies.models import Currency
from poms.instruments.models import (
    DailyPricingModel,
    Instrument,
    InstrumentType,
    PaymentSizeDetail,
)
from poms.integrations.models import PriceDownloadScheme
from poms.obj_attrs.admin import GenericAttributeInline
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.transactions.models import (
    ActionClass,
    ComplexTransaction,
    ComplexTransactionInput,
    ComplexTransactionStatus,
    EventClass,
    EventToHandle,
    ExternalCashFlow,
    ExternalCashFlowStrategy,
    NotificationClass,
    PeriodicityGroup,
    Transaction,
    TransactionClass,
    TransactionType,
    TransactionTypeActionInstrument,
    TransactionTypeActionInstrumentAccrualCalculationSchedules,
    TransactionTypeActionInstrumentEventSchedule,
    TransactionTypeActionInstrumentEventScheduleAction,
    TransactionTypeActionInstrumentFactorSchedule,
    TransactionTypeActionInstrumentManualPricingFormula,
    TransactionTypeActionTransaction,
    TransactionTypeGroup,
    TransactionTypeInput,
    TransactionTypeInputSettings,
)


class TransactionTypeGroupAdmin(AbstractModelAdmin):
    model = TransactionTypeGroup
    master_user_path = "master_user"
    list_display = [
        "id",
        "master_user",
        "user_code",
        "name",
        "is_deleted",
    ]
    list_select_related = ["master_user"]
    list_filter = [
        "is_deleted",
    ]
    search_fields = ["id", "user_code", "name"]
    raw_id_fields = ["master_user"]
    inlines = []


class TransactionTypeInputAdmin(AbstractModelAdmin):
    model = TransactionTypeInput
    master_user_path = "transaction_type__master_user"
    list_display = [
        "id",
        "master_user",
        "transaction_type",
        "order",
        "name",
        "value_type",
        "content_type",
    ]
    list_select_related = ["transaction_type", "transaction_type__master_user"]
    search_fields = ["id", "name"]
    raw_id_fields = ["transaction_type"]

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = "transaction_type__master_user"


class TransactionTypeInputSettingsAdmin(AbstractModelAdmin):
    model = TransactionTypeInputSettings
    list_display = ["id", "transaction_type_input", "linked_inputs_names"]


class TransactionTypeActionInstrumentAdmin(AbstractModelAdmin):
    model = TransactionTypeActionInstrument
    master_user_path = "transaction_type__master_user"
    list_display = ["id", "master_user", "transaction_type", "order", "action_notes"]
    list_select_related = ["transaction_type", "transaction_type__master_user"]
    search_fields = ["id"]
    raw_id_fields = ["transaction_type"]

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = "transaction_type__master_user"


class TransactionTypeActionTransactionAdmin(AbstractModelAdmin):
    model = TransactionTypeActionTransaction
    master_user_path = "transaction_type__master_user"
    list_display = ["id", "master_user", "transaction_type", "order", "action_notes"]
    list_select_related = ["transaction_type", "transaction_type__master_user"]
    search_fields = ["id"]
    raw_id_fields = ["transaction_type"]

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = "transaction_type__master_user"


class TransactionTypeActionInstrumentFactorScheduleAdmin(AbstractModelAdmin):
    model = TransactionTypeActionInstrumentFactorSchedule
    master_user_path = "transaction_type__master_user"
    list_display = ["id", "master_user", "transaction_type", "order", "action_notes"]
    list_select_related = ["transaction_type", "transaction_type__master_user"]
    search_fields = ["id"]
    raw_id_fields = ["transaction_type"]

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = "transaction_type__master_user"


class TransactionTypeActionInstrumentEventScheduleActionAdmin(AbstractModelAdmin):
    model = TransactionTypeActionInstrumentEventScheduleAction
    master_user_path = "transaction_type__master_user"
    list_display = ["id", "master_user", "transaction_type", "order", "action_notes"]
    list_select_related = ["transaction_type", "transaction_type__master_user"]
    search_fields = ["id"]
    raw_id_fields = ["transaction_type"]

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = "transaction_type__master_user"


class TransactionTypeActionInstrumentManualPricingFormulaAdmin(AbstractModelAdmin):
    model = TransactionTypeActionInstrumentManualPricingFormula
    master_user_path = "transaction_type__master_user"
    list_display = ["id", "master_user", "transaction_type", "order", "action_notes"]
    list_select_related = ["transaction_type", "transaction_type__master_user"]
    search_fields = ["id"]
    raw_id_fields = ["transaction_type"]

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = "transaction_type__master_user"


class TransactionTypeActionInstrumentAccrualCalculationSchedulesAdmin(
    AbstractModelAdmin
):
    model = TransactionTypeActionInstrumentAccrualCalculationSchedules
    master_user_path = "transaction_type__master_user"
    list_display = ["id", "master_user", "transaction_type", "order", "action_notes"]
    list_select_related = ["transaction_type", "transaction_type__master_user"]
    search_fields = ["id"]
    raw_id_fields = ["transaction_type"]

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = "transaction_type__master_user"


class TransactionTypeActionInstrumentEventScheduleAdmin(AbstractModelAdmin):
    model = TransactionTypeActionInstrumentEventSchedule
    master_user_path = "transaction_type__master_user"
    list_display = ["id", "master_user", "transaction_type", "order", "action_notes"]
    list_select_related = ["transaction_type", "transaction_type__master_user"]
    search_fields = ["id"]
    raw_id_fields = ["transaction_type"]

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = "transaction_type__master_user"


class TransactionTypeInputInline(admin.TabularInline):
    model = TransactionTypeInput
    extra = 0
    raw_id_fields = ("settings",)
    readonly_fields = ("id",)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "content_type":
            qs = kwargs.get("queryset", db_field.remote_field.model.objects)
            models = [
                Account,
                Instrument,
                InstrumentType,
                Currency,
                Counterparty,
                Responsible,
                Strategy1,
                Strategy2,
                Strategy3,
                DailyPricingModel,
                PaymentSizeDetail,
                PriceDownloadScheme,
                Portfolio,
            ]
            ctypes = [ContentType.objects.get_for_model(model).pk for model in models]
            kwargs["queryset"] = qs.filter(pk__in=ctypes)
        return super().formfield_for_foreignkey(db_field, request=request, **kwargs)


def input_filter_by_master_user(form, field_name, master_user):
    f = form.base_fields[field_name]
    f.queryset = f.queryset.filter(master_user=master_user)


def input_filter_owner(form, field_name, transaction_type):
    f = form.base_fields[field_name]
    f.queryset = f.queryset.filter(transaction_type=transaction_type)


class TransactionTypeActionInstrumentInline(admin.StackedInline):
    model = TransactionTypeActionInstrument
    extra = 0
    fields = (
        "order",
        "action_notes",
        "user_code",
        (
            "name",
            "short_name",
            "public_name",
        ),
        "notes",
        (
            "instrument_type",
            "instrument_type_input",
        ),
        (
            "pricing_currency",
            "pricing_currency_input",
        ),
        "price_multiplier",
        (
            "accrued_currency",
            "accrued_currency_input",
        ),
        "accrued_multiplier",
        (
            "payment_size_detail",
            "payment_size_detail_input",
        ),
        (
            "default_price",
            "default_accrued",
        ),
        (
            "user_text_1",
            "user_text_2",
            "user_text_3",
        ),
        ("reference_for_pricing",),
        ("maturity_date",),
    )
    raw_id_fields = (
        "instrument_type_input",
        "pricing_currency_input",
        "accrued_currency_input",
        "payment_size_detail_input",
    )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name.endswith("_input"):
            qs = kwargs.get("queryset", db_field.remote_field.model.objects)
            kwargs["queryset"] = qs.select_related("content_type")
        return super().formfield_for_foreignkey(db_field, request=request, **kwargs)


class TransactionTypeActionTransactionInline(admin.StackedInline):
    model = TransactionTypeActionTransaction
    extra = 0
    fields = (
        "order",
        "transaction_class",
        ("instrument", "instrument_input", "instrument_phantom"),
        ("transaction_currency", "transaction_currency_input"),
        "position_size_with_sign",
        ("settlement_currency", "settlement_currency_input"),
        "cash_consideration",
        ("principal_with_sign", "carry_with_sign", "overheads_with_sign"),
        ("portfolio", "portfolio_input"),
        ("account_position", "account_position_input"),
        ("account_cash", "account_cash_input"),
        ("account_interim", "account_interim_input"),
        ("accounting_date", "cash_date"),
        ("strategy1_position", "strategy1_position_input"),
        ("strategy1_cash", "strategy1_cash_input"),
        ("strategy2_position", "strategy2_position_input"),
        ("strategy2_cash", "strategy2_cash_input"),
        ("strategy3_position", "strategy3_position_input"),
        ("strategy3_cash", "strategy3_cash_input"),
        ("responsible", "responsible_input"),
        ("counterparty", "counterparty_input"),
        ("linked_instrument", "linked_instrument_input", "linked_instrument_phantom"),
        (
            "allocation_balance",
            "allocation_balance_input",
            "allocation_balance_phantom",
        ),
        ("allocation_pl", "allocation_pl_input", "allocation_pl_phantom"),
        "reference_fx_rate",
        "factor",
        "trade_price",
        "position_amount",
        ("principal_amount", "carry_amount", "overheads"),
        "notes",
    )
    raw_id_fields = (
        "portfolio_input",
        "instrument_input",
        "instrument_phantom",
        "transaction_currency_input",
        "settlement_currency_input",
        "account_position_input",
        "account_cash_input",
        "account_interim_input",
        "strategy1_position_input",
        "strategy1_cash_input",
        "strategy2_position_input",
        "strategy2_cash_input",
        "strategy3_position_input",
        "strategy3_cash_input",
        "responsible_input",
        "counterparty_input",
        "linked_instrument_input",
        "linked_instrument_phantom",
        "allocation_balance_input",
        "allocation_balance_phantom",
        "allocation_pl_input",
        "allocation_pl_phantom",
    )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name.endswith("_input"):
            qs = kwargs.get("queryset", db_field.remote_field.model.objects)
            kwargs["queryset"] = qs.select_related("content_type")
        return super().formfield_for_foreignkey(db_field, request=request, **kwargs)


class EventToHandleInline(admin.StackedInline):
    model = EventToHandle
    list_display = ["id", "master_user", "name"]
    raw_id_fields = ["master_user"]
    extra = 0


class TransactionTypeAdmin(AbstractModelAdmin):
    model = TransactionType
    master_user_path = "master_user"
    list_display = [
        "id",
        "master_user",
        "user_code",
        "name",
        "is_deleted",
    ]
    list_select_related = ["master_user"]
    list_filter = [
        "is_deleted",
    ]
    search_fields = ["id", "user_code", "name"]
    raw_id_fields = ["master_user", "instrument_types"]
    inlines = [
        TransactionTypeInputInline,
        TransactionTypeActionInstrumentInline,
        TransactionTypeActionTransactionInline,
        EventToHandleInline,
    ]
    save_as = True

    def get_formset(self, request, obj=None, **kwargs):
        f = super().get_formset(request, obj=obj, **kwargs)
        input_filter_by_master_user(f.form, "instrument_types", obj.master_user)
        input_filter_by_master_user(f.form, "portfolios", obj.master_user)
        return f


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    show_change_link = True
    raw_id_fields = [
        "master_user",
        "instrument",
        "transaction_currency",
        "settlement_currency",
        "portfolio",
        "account_position",
        "account_cash",
        "account_interim",
        "strategy1_position",
        "strategy1_cash",
        "strategy2_position",
        "strategy2_cash",
        "strategy3_position",
        "strategy3_cash",
        "responsible",
        "counterparty",
        "linked_instrument",
        "allocation_balance",
        "allocation_pl",
    ]


class ComplexTransactionInputInline(admin.TabularInline):
    model = ComplexTransactionInput
    extra = 0
    raw_id_fields = (
        "transaction_type_input",
        "account",
        "instrument_type",
        "instrument",
        "currency",
        "counterparty",
        "responsible",
        "portfolio",
        "strategy1",
        "strategy2",
        "strategy3",
    )
    readonly_fields = ("id",)


class ComplexTransactionAdmin(AbstractModelAdmin):
    model = ComplexTransaction
    master_user_path = "transaction_type__master_user"
    list_display = [
        "id",
        "master_user",
        "date",
        "transaction_type",
        "code",
        "transaction_unique_code",
        "status",
        "is_deleted",
        "modified_at",
    ]
    list_select_related = ["transaction_type", "transaction_type__master_user"]
    list_filter = [
        "date",
    ]
    search_fields = ["id"]
    raw_id_fields = ["transaction_type"]
    inlines = [
        GenericAttributeInline,
        TransactionInline,
        ComplexTransactionInputInline,
    ]
    save_as = True

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = "transaction_type__master_user"


class TransactionAdmin(AbstractModelAdmin):
    model = Transaction
    master_user_path = "master_user"
    list_display = [
        "id",
        "master_user",
        "transaction_date",
        "transaction_code",
        "complex_transaction",
        "transaction_class",
        "instrument",
        "transaction_currency",
        "settlement_currency",
    ]
    list_select_related = [
        "master_user",
        "complex_transaction",
        "transaction_class",
        "instrument",
        "transaction_currency",
        "settlement_currency",
        "portfolio",
        "account_cash",
        "account_position",
        "account_interim",
        "strategy1_position",
        "strategy1_cash",
        "strategy2_position",
        "strategy2_cash",
        "strategy3_position",
        "strategy3_cash",
        "linked_instrument",
        "allocation_balance",
        "allocation_pl",
    ]
    list_filter = [
        "transaction_date",
    ]
    search_fields = ["id"]
    date_hierarchy = "transaction_date"
    raw_id_fields = [
        "master_user",
        "complex_transaction",
        "instrument",
        "transaction_currency",
        "settlement_currency",
        "portfolio",
        "account_position",
        "account_cash",
        "account_interim",
        "strategy1_position",
        "strategy1_cash",
        "strategy2_position",
        "strategy2_cash",
        "strategy3_position",
        "strategy3_cash",
        "responsible",
        "counterparty",
        "linked_instrument",
        "allocation_balance",
        "allocation_pl",
    ]
    inlines = [
        GenericAttributeInline,
    ]
    fields = (
        "master_user",
        "transaction_code",
        ("complex_transaction", "complex_transaction_order"),
        "transaction_class",
        ("instrument", "transaction_currency", "position_size_with_sign"),
        ("settlement_currency", "cash_consideration"),
        ("principal_with_sign", "carry_with_sign", "overheads_with_sign"),
        ("accounting_date", "cash_date"),
        "portfolio",
        ("account_position", "account_cash", "account_interim"),
        ("strategy1_position", "strategy1_cash"),
        ("strategy2_position", "strategy2_cash"),
        ("strategy3_position", "strategy3_cash"),
        ("responsible", "counterparty"),
        "linked_instrument",
        ("allocation_balance", "allocation_pl"),
        "reference_fx_rate",
        ("factor", "trade_price"),
        "position_amount",
        ("principal_amount", "carry_amount", "overheads"),
        "notes",
    )
    save_as = True


class ExternalCashFlowStrategyInline(admin.TabularInline):
    model = ExternalCashFlowStrategy
    raw_id_fields = ["strategy1", "strategy2", "strategy3"]
    extra = 0


class ExternalCashFlowAdmin(AbstractModelAdmin):
    model = ExternalCashFlow
    master_user_path = "master_user"
    list_display = [
        "id",
        "master_user",
        "portfolio",
        "account",
        "currency",
        "date",
        "amount",
    ]
    list_select_related = [
        "master_user",
        "portfolio",
        "account",
        "currency",
    ]
    date_hierarchy = "date"
    inlines = [ExternalCashFlowStrategyInline]
    raw_id_fields = ["master_user", "portfolio", "account", "currency"]


admin.site.register(ExternalCashFlow, ExternalCashFlowAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(TransactionClass, ClassModelAdmin)
admin.site.register(ActionClass, ClassModelAdmin)
admin.site.register(EventClass, ClassModelAdmin)
admin.site.register(NotificationClass, ClassModelAdmin)
admin.site.register(PeriodicityGroup, ClassModelAdmin)
admin.site.register(ComplexTransactionStatus, ClassModelAdmin)
admin.site.register(ComplexTransaction, ComplexTransactionAdmin)
admin.site.register(TransactionType, TransactionTypeAdmin)
admin.site.register(
    TransactionTypeActionInstrumentEventSchedule,
    TransactionTypeActionInstrumentEventScheduleAdmin,
)
admin.site.register(
    TransactionTypeActionInstrumentEventScheduleAction,
    TransactionTypeActionInstrumentEventScheduleActionAdmin,
)

admin.site.register(
    TransactionTypeActionInstrumentAccrualCalculationSchedules,
    TransactionTypeActionInstrumentAccrualCalculationSchedulesAdmin,
)
admin.site.register(
    TransactionTypeActionInstrumentManualPricingFormula,
    TransactionTypeActionInstrumentManualPricingFormulaAdmin,
)
admin.site.register(
    TransactionTypeActionInstrumentFactorSchedule,
    TransactionTypeActionInstrumentFactorScheduleAdmin,
)
admin.site.register(
    TransactionTypeActionTransaction, TransactionTypeActionTransactionAdmin
)
admin.site.register(
    TransactionTypeActionInstrument, TransactionTypeActionInstrumentAdmin
)
admin.site.register(TransactionTypeInputSettings, TransactionTypeInputSettingsAdmin)
admin.site.register(TransactionTypeGroup, TransactionTypeGroupAdmin)
