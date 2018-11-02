from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

from poms.accounts.models import Account
from poms.common.admin import ClassModelAdmin, AbstractModelAdmin
from poms.counterparties.models import Responsible, Counterparty
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, PaymentSizeDetail, DailyPricingModel, InstrumentType
from poms.integrations.models import PriceDownloadScheme
from poms.obj_attrs.admin import GenericAttributeInline
from poms.obj_perms.admin import GenericObjectPermissionInline
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy3, Strategy2, Strategy1
from poms.transactions.models import TransactionClass, Transaction, TransactionType, TransactionTypeInput, \
    ActionClass, EventToHandle, ExternalCashFlow, ExternalCashFlowStrategy, NotificationClass, \
    EventClass, PeriodicityGroup, TransactionTypeActionInstrument, TransactionTypeActionTransaction, ComplexTransaction, \
    TransactionTypeGroup, ComplexTransactionInput, TransactionTypeActionInstrumentFactorSchedule, \
    TransactionTypeActionInstrumentManualPricingFormula, TransactionTypeActionInstrumentAccrualCalculationSchedules, \
    TransactionTypeActionInstrumentEventSchedule, TransactionTypeActionInstrumentEventScheduleAction

admin.site.register(TransactionClass, ClassModelAdmin)
admin.site.register(ActionClass, ClassModelAdmin)
admin.site.register(EventClass, ClassModelAdmin)
admin.site.register(NotificationClass, ClassModelAdmin)
admin.site.register(PeriodicityGroup, ClassModelAdmin)


class TransactionTypeGroupAdmin(AbstractModelAdmin):
    model = TransactionTypeGroup
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'user_code', 'name', 'is_deleted', ]
    list_select_related = ['master_user']
    list_filter = ['is_deleted', ]
    search_fields = ['id', 'user_code', 'name']
    raw_id_fields = ['master_user']
    inlines = [
        GenericObjectPermissionInline,
        # UserObjectPermissionInline,
        # GroupObjectPermissionInline,
    ]


admin.site.register(TransactionTypeGroup, TransactionTypeGroupAdmin)


class TransactionTypeInputAdmin(AbstractModelAdmin):
    model = TransactionTypeInput
    master_user_path = 'transaction_type__master_user'
    list_display = ['id', 'master_user', 'transaction_type', 'order', 'name', 'value_type', 'content_type']
    list_select_related = ['transaction_type', 'transaction_type__master_user']
    search_fields = ['id', 'name']
    raw_id_fields = ['transaction_type']

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = 'transaction_type__master_user'


admin.site.register(TransactionTypeInput, TransactionTypeInputAdmin)


class TransactionTypeActionInstrumentAdmin(AbstractModelAdmin):
    model = TransactionTypeActionInstrument
    master_user_path = 'transaction_type__master_user'
    list_display = ['id', 'master_user', 'transaction_type', 'order', 'action_notes']
    list_select_related = ['transaction_type', 'transaction_type__master_user']
    search_fields = ['id']
    raw_id_fields = ['transaction_type']

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = 'transaction_type__master_user'


admin.site.register(TransactionTypeActionInstrument, TransactionTypeActionInstrumentAdmin)


class TransactionTypeActionTransactionAdmin(AbstractModelAdmin):
    model = TransactionTypeActionTransaction
    master_user_path = 'transaction_type__master_user'
    list_display = ['id', 'master_user', 'transaction_type', 'order', 'action_notes']
    list_select_related = ['transaction_type', 'transaction_type__master_user']
    search_fields = ['id']
    raw_id_fields = ['transaction_type']

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = 'transaction_type__master_user'


admin.site.register(TransactionTypeActionTransaction, TransactionTypeActionTransactionAdmin)


class TransactionTypeActionInstrumentFactorScheduleAdmin(AbstractModelAdmin):
    model = TransactionTypeActionInstrumentFactorSchedule
    master_user_path = 'transaction_type__master_user'
    list_display = ['id', 'master_user', 'transaction_type', 'order', 'action_notes']
    list_select_related = ['transaction_type', 'transaction_type__master_user']
    search_fields = ['id']
    raw_id_fields = ['transaction_type']

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = 'transaction_type__master_user'


admin.site.register(TransactionTypeActionInstrumentFactorSchedule, TransactionTypeActionInstrumentFactorScheduleAdmin)


class TransactionTypeActionInstrumentManualPricingFormulaAdmin(AbstractModelAdmin):
    model = TransactionTypeActionInstrumentManualPricingFormula
    master_user_path = 'transaction_type__master_user'
    list_display = ['id', 'master_user', 'transaction_type', 'order', 'action_notes']
    list_select_related = ['transaction_type', 'transaction_type__master_user']
    search_fields = ['id']
    raw_id_fields = ['transaction_type']

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = 'transaction_type__master_user'


admin.site.register(TransactionTypeActionInstrumentManualPricingFormula, TransactionTypeActionInstrumentManualPricingFormulaAdmin)


class TransactionTypeActionInstrumentAccrualCalculationSchedulesAdmin(AbstractModelAdmin):
    model = TransactionTypeActionInstrumentAccrualCalculationSchedules
    master_user_path = 'transaction_type__master_user'
    list_display = ['id', 'master_user', 'transaction_type', 'order', 'action_notes']
    list_select_related = ['transaction_type', 'transaction_type__master_user']
    search_fields = ['id']
    raw_id_fields = ['transaction_type']

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = 'transaction_type__master_user'


admin.site.register(TransactionTypeActionInstrumentAccrualCalculationSchedules, TransactionTypeActionInstrumentAccrualCalculationSchedulesAdmin)


class TransactionTypeActionInstrumentEventScheduleAdmin(AbstractModelAdmin):
    model = TransactionTypeActionInstrumentEventSchedule
    master_user_path = 'transaction_type__master_user'
    list_display = ['id', 'master_user', 'transaction_type', 'order', 'action_notes']
    list_select_related = ['transaction_type', 'transaction_type__master_user']
    search_fields = ['id']
    raw_id_fields = ['transaction_type']

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = 'transaction_type__master_user'


admin.site.register(TransactionTypeActionInstrumentEventSchedule, TransactionTypeActionInstrumentEventScheduleAdmin)


class TransactionTypeActionInstrumentEventScheduleActionAdmin(AbstractModelAdmin):
    model = TransactionTypeActionInstrumentEventScheduleAction
    master_user_path = 'transaction_type__master_user'
    list_display = ['id', 'master_user', 'transaction_type', 'order', 'action_notes']
    list_select_related = ['transaction_type', 'transaction_type__master_user']
    search_fields = ['id']
    raw_id_fields = ['transaction_type']

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = 'transaction_type__master_user'


admin.site.register(TransactionTypeActionInstrumentEventScheduleAction, TransactionTypeActionInstrumentEventScheduleActionAdmin)

class TransactionTypeInputInline(admin.TabularInline):
    model = TransactionTypeInput
    extra = 0
    # fields = (
    #     'id', 'name', 'value_type', 'content_type',
    #     'verbose_name', 'order',
    #     'is_fill_from_context', 'value',
    #     'account', 'instrument_type', 'instrument', 'currency', 'counterparty',
    #     'responsible', 'portfolio', 'strategy1', 'strategy2', 'strategy3', 'price_download_scheme',
    #     'daily_pricing_model', 'payment_size_detail',)
    # fieldsets = (
    #     (None, {
    #         'fields': ('id', 'name', 'value_type', 'content_type', 'verbose_name', 'order',)
    #     }),
    #     ('Defaults', {
    #         'classes': ('collapse',),
    #         'fields': ('is_fill_from_context', 'value',
    #                    'account', 'instrument_type', 'instrument', 'currency', 'counterparty',
    #                    'responsible', 'portfolio', 'strategy1', 'strategy2', 'strategy3', 'price_download_scheme',
    #                    'daily_pricing_model', 'payment_size_detail',),
    #     }),
    # )
    raw_id_fields = ('account', 'instrument_type', 'instrument', 'currency', 'counterparty',
                     'responsible', 'portfolio', 'strategy1', 'strategy2', 'strategy3', 'price_download_scheme')
    readonly_fields = ('id',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'content_type':
            qs = kwargs.get('queryset', db_field.remote_field.model.objects)
            models = [Account, Instrument, InstrumentType, Currency, Counterparty, Responsible, Strategy1, Strategy2,
                      Strategy3, DailyPricingModel, PaymentSizeDetail, PriceDownloadScheme, Portfolio]
            ctypes = [ContentType.objects.get_for_model(model).pk for model in models]
            kwargs['queryset'] = qs.filter(pk__in=ctypes)
        return super(TransactionTypeInputInline, self).formfield_for_foreignkey(db_field, request=request, **kwargs)


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
        'order',
        'action_notes',
        'user_code',
        ('name', 'short_name', 'public_name',),
        'notes',
        ('instrument_type', 'instrument_type_input',),
        ('pricing_currency', 'pricing_currency_input',),
        'price_multiplier',
        ('accrued_currency', 'accrued_currency_input',),
        'accrued_multiplier',
        ('payment_size_detail', 'payment_size_detail_input',),
        ('default_price', 'default_accrued',),
        ('user_text_1', 'user_text_2', 'user_text_3',),
        ('daily_pricing_model', 'daily_pricing_model_input',),
        ('reference_for_pricing', 'price_download_scheme', 'price_download_scheme_input',),
        ('maturity_date',),
    )

    raw_id_fields = (
        'instrument_type', 'instrument_type_input',
        'pricing_currency', 'pricing_currency_input',
        'accrued_currency', 'accrued_currency_input',
        'payment_size_detail_input',
        'daily_pricing_model_input',
        'price_download_scheme', 'price_download_scheme_input',
    )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name.endswith('_input'):
            qs = kwargs.get('queryset', db_field.remote_field.model.objects)
            kwargs['queryset'] = qs.select_related('content_type')
        return super(TransactionTypeActionInstrumentInline, self).formfield_for_foreignkey(db_field, request=request,
                                                                                           **kwargs)


class TransactionTypeActionTransactionInline(admin.StackedInline):
    model = TransactionTypeActionTransaction
    extra = 0
    fields = (
        'order',
        'transaction_class',
        ('instrument', 'instrument_input', 'instrument_phantom'),
        ('transaction_currency', 'transaction_currency_input'),
        'position_size_with_sign',
        ('settlement_currency', 'settlement_currency_input'),
        'cash_consideration',
        ('principal_with_sign', 'carry_with_sign', 'overheads_with_sign'),
        ('portfolio', 'portfolio_input'),
        ('account_position', 'account_position_input'),
        ('account_cash', 'account_cash_input'),
        ('account_interim', 'account_interim_input'),
        ('accounting_date', 'cash_date'),
        ('strategy1_position', 'strategy1_position_input'),
        ('strategy1_cash', 'strategy1_cash_input'),
        ('strategy2_position', 'strategy2_position_input'),
        ('strategy2_cash', 'strategy2_cash_input'),
        ('strategy3_position', 'strategy3_position_input'),
        ('strategy3_cash', 'strategy3_cash_input'),
        ('responsible', 'responsible_input'),
        ('counterparty', 'counterparty_input'),
        ('linked_instrument', 'linked_instrument_input', 'linked_instrument_phantom'),
        ('allocation_balance', 'allocation_balance_input', 'allocation_balance_phantom'),
        ('allocation_pl', 'allocation_pl_input', 'allocation_pl_phantom'),

        'reference_fx_rate',
        'factor',
        'trade_price',
        'position_amount',
        ('principal_amount', 'carry_amount', 'overheads'),

        'notes',
    )
    raw_id_fields = (
        'portfolio', 'portfolio_input',
        'instrument', 'instrument_input', 'instrument_phantom',
        'transaction_currency', 'transaction_currency_input',
        'settlement_currency', 'settlement_currency_input',
        'account_position', 'account_position_input',
        'account_cash', 'account_cash_input',
        'account_interim', 'account_interim_input',
        'strategy1_position', 'strategy1_position_input',
        'strategy1_cash', 'strategy1_cash_input',
        'strategy2_position', 'strategy2_position_input',
        'strategy2_cash', 'strategy2_cash_input',
        'strategy3_position', 'strategy3_position_input',
        'strategy3_cash', 'strategy3_cash_input',
        'responsible', 'responsible_input',
        'counterparty', 'counterparty_input',

        'linked_instrument', 'linked_instrument_input', 'linked_instrument_phantom',
        'allocation_balance', 'allocation_balance_input', 'allocation_balance_phantom',
        'allocation_pl', 'allocation_pl_input', 'allocation_pl_phantom',
    )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name.endswith('_input'):
            qs = kwargs.get('queryset', db_field.remote_field.model.objects)
            kwargs['queryset'] = qs.select_related('content_type')
        return super(TransactionTypeActionTransactionInline, self).formfield_for_foreignkey(db_field, request=request,
                                                                                            **kwargs)


class EventToHandleInline(admin.StackedInline):
    model = EventToHandle
    list_display = ['id', 'master_user', 'name']
    raw_id_fields = ['master_user']
    extra = 0


class TransactionTypeAdmin(AbstractModelAdmin):
    model = TransactionType
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'user_code', 'name', 'is_deleted', ]
    list_select_related = ['master_user']
    list_filter = ['is_deleted', ]
    search_fields = ['id', 'user_code', 'name']
    raw_id_fields = ['master_user', 'group', 'instrument_types']
    inlines = [
        TransactionTypeInputInline,
        TransactionTypeActionInstrumentInline,
        TransactionTypeActionTransactionInline,
        EventToHandleInline,
        GenericObjectPermissionInline,
        # UserObjectPermissionInline,
        # GroupObjectPermissionInline,
    ]
    save_as = True

    # def get_inline_instances(self, request, obj=None):
    #     if obj:
    #         return super(TransactionTypeAdmin, self).get_inline_instances(request, obj)
    #     return []

    # def get_readonly_fields(self, request, obj=None):
    #     fields = super(TransactionTypeAdmin, self).get_readonly_fields(request, obj)
    #     if obj:
    #         fields += ('master_user',)
    #     else:
    #         fields += ('instrument_types',)
    #     return fields

    def get_formset(self, request, obj=None, **kwargs):
        f = super(TransactionTypeAdmin, self).get_formset(request, obj=obj, **kwargs)
        input_filter_by_master_user(f.form, 'instrument_types', obj.master_user)
        input_filter_by_master_user(f.form, 'portfolios', obj.master_user)
        return f


admin.site.register(TransactionType, TransactionTypeAdmin)


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    show_change_link = True
    raw_id_fields = [
        'master_user', 'instrument', 'transaction_currency', 'settlement_currency',
        'portfolio', 'account_position', 'account_cash', 'account_interim',
        'strategy1_position', 'strategy1_cash', 'strategy2_position', 'strategy2_cash',
        'strategy3_position', 'strategy3_cash',
        'responsible', 'counterparty', 'linked_instrument', 'allocation_balance', 'allocation_pl',
    ]


class ComplexTransactionInputInline(admin.TabularInline):
    model = ComplexTransactionInput
    extra = 0
    raw_id_fields = (
        'transaction_type_input', 'account', 'instrument_type', 'instrument', 'currency', 'counterparty',
        'responsible', 'portfolio', 'strategy1', 'strategy2', 'strategy3', 'price_download_scheme'
    )
    readonly_fields = ('id',)


class ComplexTransactionAdmin(AbstractModelAdmin):
    model = ComplexTransaction
    master_user_path = 'transaction_type__master_user'
    list_display = ['id', 'master_user', 'date', 'transaction_type', 'code', 'status', 'is_deleted', ]
    list_select_related = ['transaction_type', 'transaction_type__master_user']
    list_filter = ['is_deleted', 'date', ]
    search_fields = ['id']
    raw_id_fields = ['transaction_type']
    inlines = [GenericAttributeInline, TransactionInline, ComplexTransactionInputInline, ]
    save_as = True

    def master_user(self, obj):
        return obj.transaction_type.master_user

    master_user.admin_order_field = 'transaction_type__master_user'


admin.site.register(ComplexTransaction, ComplexTransactionAdmin)


# class EventToHandleAdmin(HistoricalAdmin):
#     model = EventToHandle
#     list_display = ['id', 'master_user', 'name', 'transaction_type']
#     raw_id_fields = ['master_user', 'transaction_type']
#
#
# admin.site.register(EventToHandle, HistoricalAdmin)


# class TransactionAttributeInline(AbstractAttributeInline):
#     model = TransactionAttribute
#     fields = ['attribute_type', 'value_string', 'value_float', 'value_date']
#     raw_id_fields = ['attribute_type']


class TransactionAdmin(AbstractModelAdmin):
    model = Transaction
    master_user_path = 'master_user'
    list_display = [
        'id',
        'master_user',
        'transaction_date',
        'transaction_code',
        'complex_transaction',
        'transaction_class',
        # 'accounting_date',
        # 'cash_date',
        'instrument',
        'transaction_currency',
        # 'position_size_with_sign',
        'settlement_currency',
        # 'cash_consideration',
        # 'principal_with_sign',
        # 'carry_with_sign',
        # 'overheads_with_sign',
        # 'portfolio',
        # 'account_cash',
        # 'account_position',
        # 'account_interim',
        # 'strategy1_position',
        # 'strategy1_cash',
        # 'strategy2_position',
        # 'strategy2_cash',
        # 'strategy3_position',
        # 'strategy3_cash',
        # 'linked_instrument',
        # 'allocation_balance',
        # 'allocation_pl',
        'is_deleted',
    ]
    list_select_related = [
        'master_user', 'complex_transaction', 'transaction_class',
        'instrument', 'transaction_currency', 'settlement_currency',
        'portfolio', 'account_cash', 'account_position', 'account_interim',
        'strategy1_position', 'strategy1_cash', 'strategy2_position', 'strategy2_cash',
        'strategy3_position', 'strategy3_cash',
        'linked_instrument',
        'allocation_balance', 'allocation_pl',
    ]
    list_filter = ['is_deleted', 'transaction_date', ]
    search_fields = ['id']
    date_hierarchy = 'transaction_date'
    raw_id_fields = [
        'master_user', 'complex_transaction', 'instrument', 'transaction_currency', 'settlement_currency',
        'portfolio', 'account_position', 'account_cash', 'account_interim',
        'strategy1_position', 'strategy1_cash', 'strategy2_position', 'strategy2_cash',
        'strategy3_position', 'strategy3_cash', 'responsible', 'counterparty',
        'linked_instrument', 'allocation_balance', 'allocation_pl',
    ]
    inlines = [
        # AbstractAttributeInline,
        GenericAttributeInline,
    ]
    fields = (
        'master_user',
        'transaction_code',
        ('complex_transaction', 'complex_transaction_order'),
        'transaction_class',
        ('instrument', 'transaction_currency', 'position_size_with_sign'),
        ('settlement_currency', 'cash_consideration'),
        ('principal_with_sign', 'carry_with_sign', 'overheads_with_sign'),
        ('accounting_date', 'cash_date'),
        'portfolio',
        ('account_position', 'account_cash', 'account_interim'),
        ('strategy1_position', 'strategy1_cash'),
        ('strategy2_position', 'strategy2_cash'),
        ('strategy3_position', 'strategy3_cash'),
        ('responsible', 'counterparty'),
        'linked_instrument',
        ('allocation_balance', 'allocation_pl'),
        'reference_fx_rate',
        ('is_locked', 'is_deleted'),
        ('factor', 'trade_price'),
        'position_amount',
        ('principal_amount', 'carry_amount', 'overheads'),
        'notes',
    )
    save_as = True


admin.site.register(Transaction, TransactionAdmin)


# class TransactionAttributeTypeAdmin(AbstractAttributeTypeAdmin):
#     inlines = [
#         AbstractAttributeTypeClassifierInline,
#         AbstractAttributeTypeOptionInline,
#         GenericObjectPermissionInline,
#         # UserObjectPermissionInline,
#         # GroupObjectPermissionInline,
#     ]
#
#
# admin.site.register(TransactionAttributeType, TransactionAttributeTypeAdmin)
#
# admin.site.register(TransactionClassifier, ClassifierAdmin)


# admin.site.register(TransactionAttributeTypeOption, AbstractAttributeTypeOptionAdmin)
# admin.site.register(TransactionAttributeTypeUserObjectPermission, UserObjectPermissionAdmin)
# admin.site.register(TransactionAttributeTypeGroupObjectPermission, GroupObjectPermissionAdmin)


class ExternalCashFlowStrategyInline(admin.TabularInline):
    model = ExternalCashFlowStrategy
    raw_id_fields = ['strategy1', 'strategy2', 'strategy3']
    extra = 0


class ExternalCashFlowAdmin(AbstractModelAdmin):
    model = ExternalCashFlow
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'portfolio', 'account', 'currency', 'date', 'amount']
    list_select_related = ['master_user', 'portfolio', 'account', 'currency', ]
    date_hierarchy = 'date'
    inlines = [ExternalCashFlowStrategyInline]
    raw_id_fields = ['master_user', 'portfolio', 'account', 'currency']


admin.site.register(ExternalCashFlow, ExternalCashFlowAdmin)
