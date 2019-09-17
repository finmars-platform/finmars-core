from __future__ import unicode_literals, print_function

from django import forms
from django.contrib import admin
from django.urls import reverse_lazy
from django.utils.html import escape
from django.utils.translation import ugettext_lazy

from poms.common.admin import ClassModelAdmin, AbstractModelAdmin
from poms.integrations.models import Task, ImportConfig, ProviderClass, CurrencyMapping, \
    InstrumentTypeMapping, FactorScheduleDownloadMethod, AccrualScheduleDownloadMethod, \
    InstrumentDownloadScheme, InstrumentDownloadSchemeInput, InstrumentDownloadSchemeAttribute, PriceDownloadScheme, \
    AccrualCalculationModelMapping, PeriodicityMapping, PricingAutomatedSchedule, AccountMapping, InstrumentMapping, \
    CounterpartyMapping, ResponsibleMapping, PortfolioMapping, Strategy1Mapping, Strategy2Mapping, Strategy3Mapping, \
    DailyPricingModelMapping, PaymentSizeDetailMapping, PriceDownloadSchemeMapping, InstrumentAttributeValueMapping, \
    ComplexTransactionImportScheme, ComplexTransactionImportSchemeField, ComplexTransactionImportSchemeInput, \
    ComplexTransactionImportSchemeRule, PortfolioClassifierMapping, AccountClassifierMapping, \
    CounterpartyClassifierMapping, ResponsibleClassifierMapping, InstrumentClassifierMapping

admin.site.register(ProviderClass, ClassModelAdmin)
admin.site.register(FactorScheduleDownloadMethod, ClassModelAdmin)
admin.site.register(AccrualScheduleDownloadMethod, ClassModelAdmin)


class ImportConfigForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), required=False)

    class Meta:
        model = ImportConfig
        fields = ['master_user', 'provider', 'p12cert', 'password', 'cert', 'key']


class ImportConfigAdmin(AbstractModelAdmin):
    model = ImportConfig
    master_user_path = 'master_user'
    form = ImportConfigForm
    list_display = ['id', 'master_user', 'provider', ]
    list_select_related = ['master_user', 'provider', ]
    raw_id_fields = ['master_user', ]


admin.site.register(ImportConfig, ImportConfigAdmin)


class InstrumentDownloadSchemeInputInline(admin.TabularInline):
    model = InstrumentDownloadSchemeInput
    extra = 0


class InstrumentDownloadSchemeAttributeInline(admin.TabularInline):
    model = InstrumentDownloadSchemeAttribute
    extra = 0
    raw_id_fields = ['attribute_type']


class InstrumentDownloadSchemeAdmin(AbstractModelAdmin):
    model = InstrumentDownloadScheme
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'provider', 'scheme_name', 'fields0']
    list_select_related = ['master_user', 'provider', ]
    list_filter = ['provider']
    search_fields = ['id', 'scheme_name', ]
    raw_id_fields = ['master_user', 'price_download_scheme']
    inlines = [
        InstrumentDownloadSchemeInputInline,
        InstrumentDownloadSchemeAttributeInline,
    ]
    save_as = True

    def fields0(self, obj):
        f = obj.fields
        if f:
            return ', '.join(f)
        return None

    fields0.short_description = ugettext_lazy('fields')


admin.site.register(InstrumentDownloadScheme, InstrumentDownloadSchemeAdmin)


class PriceDownloadSchemeAdmin(AbstractModelAdmin):
    model = PriceDownloadScheme
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'provider', 'scheme_name', 'instrument_yesterday_fields0',
                    'instrument_history_fields0', 'currency_history_fields0']
    list_select_related = ['master_user', 'provider']
    list_filter = ['provider']
    search_fields = ['id', 'scheme_name']
    raw_id_fields = ['master_user']

    def instrument_yesterday_fields0(self, obj):
        f = obj.instrument_yesterday_fields
        if f:
            return ', '.join(f)
        return None

    instrument_yesterday_fields0.short_description = ugettext_lazy('instrument yesterday fields')

    def instrument_history_fields0(self, obj):
        f = obj.instrument_history_fields
        if f:
            return ', '.join(f)
        return None

    instrument_history_fields0.short_description = ugettext_lazy('instrument history fields')

    def currency_history_fields0(self, obj):
        f = obj.currency_history_fields
        if f:
            return ', '.join(f)
        return None

    currency_history_fields0.short_description = ugettext_lazy('currency history fields')


admin.site.register(PriceDownloadScheme, PriceDownloadSchemeAdmin)


# -------


class AbstractMappingAdmin(AbstractModelAdmin):
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'provider', 'value', 'content_object', ]
    list_select_related = ['master_user', 'provider', 'content_object', ]
    raw_id_fields = ['master_user', 'content_object', ]
    search_fields = ['value', ]


class AbstractClassifierMappingAdmin(AbstractModelAdmin):
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'provider', 'value', 'attribute_type', 'content_object', ]
    list_select_related = ['master_user', 'provider', 'attribute_type', 'content_object', ]
    raw_id_fields = ['master_user', 'attribute_type', 'content_object', ]
    search_fields = ['value', ]


class InstrumentAttributeValueMappingAdmin(AbstractMappingAdmin):
    list_display = AbstractMappingAdmin.list_display + ['value_string', 'value_float', 'value_date', 'classifier']
    list_select_related = AbstractMappingAdmin.list_select_related + ['classifier']
    raw_id_fields = AbstractMappingAdmin.raw_id_fields + ['classifier']


admin.site.register(CurrencyMapping, AbstractMappingAdmin)
admin.site.register(InstrumentTypeMapping, AbstractMappingAdmin)
admin.site.register(AccrualCalculationModelMapping, AbstractMappingAdmin)
admin.site.register(InstrumentAttributeValueMapping, InstrumentAttributeValueMappingAdmin)
admin.site.register(PeriodicityMapping, AbstractMappingAdmin)
admin.site.register(AccountMapping, AbstractMappingAdmin)
admin.site.register(AccountClassifierMapping, AbstractClassifierMappingAdmin)
admin.site.register(InstrumentMapping, AbstractMappingAdmin)
admin.site.register(InstrumentClassifierMapping, AbstractClassifierMappingAdmin)
admin.site.register(CounterpartyMapping, AbstractMappingAdmin)
admin.site.register(CounterpartyClassifierMapping, AbstractClassifierMappingAdmin)
admin.site.register(ResponsibleMapping, AbstractMappingAdmin)
admin.site.register(ResponsibleClassifierMapping, AbstractClassifierMappingAdmin)
admin.site.register(PortfolioMapping, AbstractMappingAdmin)
admin.site.register(PortfolioClassifierMapping, AbstractClassifierMappingAdmin)
admin.site.register(Strategy1Mapping, AbstractMappingAdmin)
admin.site.register(Strategy2Mapping, AbstractMappingAdmin)
admin.site.register(Strategy3Mapping, AbstractMappingAdmin)
admin.site.register(DailyPricingModelMapping, AbstractMappingAdmin)
admin.site.register(PaymentSizeDetailMapping, AbstractMappingAdmin)
admin.site.register(PriceDownloadSchemeMapping, AbstractMappingAdmin)


# class CurrencyMappingAdmin(AbstractModelAdmin):
#     model = CurrencyMapping
#     master_user_path = 'master_user'
#     list_display = ['id', 'master_user', 'provider', 'value', 'currency']
#     list_select_related = ['master_user', 'provider', 'currency']
#     raw_id_fields = ['master_user', 'currency']
#     ordering = ['master_user', 'provider', 'value']
#
#
# admin.site.register(CurrencyMapping, CurrencyMappingAdmin)
#
#
# class InstrumentTypeMappingAdmin(AbstractModelAdmin):
#     model = InstrumentTypeMapping
#     master_user_path = 'master_user'
#     list_display = ['id', 'master_user', 'provider', 'value', 'instrument_type']
#     list_select_related = ['master_user', 'provider', 'instrument_type']
#     raw_id_fields = ['master_user', 'instrument_type']
#     ordering = ['master_user', 'provider', 'value']
#
#
# admin.site.register(InstrumentTypeMapping, InstrumentTypeMappingAdmin)
#
#
# class AccrualCalculationModelMappingAdmin(AbstractModelAdmin):
#     model = AccrualCalculationModelMapping
#     master_user_path = 'master_user'
#     list_display = ['id', 'master_user', 'provider', 'value', 'accrual_calculation_model']
#     list_select_related = ['master_user', 'accrual_calculation_model', 'provider']
#     list_filter = ['accrual_calculation_model']
#     raw_id_fields = ['master_user']
#     ordering = ['master_user', 'provider', 'value']
#
#
# admin.site.register(AccrualCalculationModelMapping, AccrualCalculationModelMappingAdmin)
#
#
# class PeriodicityMappingAdmin(AbstractModelAdmin):
#     model = PeriodicityMapping
#     master_user_path = 'master_user'
#     list_display = ['id', 'master_user', 'provider', 'value', 'periodicity']
#     list_select_related = ['master_user', 'provider', 'periodicity']
#     list_filter = ['periodicity']
#     raw_id_fields = ['master_user']
#     ordering = ['master_user', 'provider', 'value']
#
#
# admin.site.register(PeriodicityMapping, PeriodicityMappingAdmin)
#
#
# class InstrumentAttributeValueMappingAdmin(AbstractModelAdmin):
#     model = InstrumentAttributeValueMapping
#     master_user_path = 'master_user'
#     list_display = ['id', 'master_user', 'provider', 'value', 'attribute_type', 'value_string', 'value_float',
#                     'value_date', 'classifier']
#     list_select_related = ['attribute_type__master_user', 'attribute_type', 'classifier', 'provider']
#     raw_id_fields = ['master_user', 'attribute_type', 'classifier']
#     ordering = ['master_user', 'provider', 'value']
#
#     def master_user(self, obj):
#         return obj.attribute_type.master_user
#
#     master_user.admin_order_field = 'attribute_type__master_user__name'
#
#
# admin.site.register(InstrumentAttributeValueMapping, InstrumentAttributeValueMappingAdmin)


# -------

class TaskAdmin(AbstractModelAdmin):
    model = Task
    master_user_path = 'master_user'
    list_display = ['id', 'parent', 'created', 'status', 'master_user', 'member', 'provider', 'action',
                    'response_id']
    list_select_related = ['parent', 'master_user', 'member', 'provider']
    raw_id_fields = ['master_user', 'member', 'parent']
    search_fields = ['response_id', ]
    list_filter = ['provider', 'created', 'action', 'status', ]
    date_hierarchy = 'created'

    readonly_fields = [
        'id', 'celery_tasks_id',
        'master_user', 'member', 'parent',
        'provider', 'action', 'status',
        'request_id', 'response_id', 'options', 'result',
    ]

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        pass


admin.site.register(Task, TaskAdmin)


class PricingAutomatedScheduleAdmin(AbstractModelAdmin):
    model = PricingAutomatedSchedule
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'is_enabled', 'cron_expr', 'last_run_at', 'next_run_at', 'last_run_task_url']
    list_select_related = ['master_user', ]
    list_filter = ['is_enabled', 'last_run_at', 'next_run_at']
    date_hierarchy = 'next_run_at'
    raw_id_fields = ['master_user', ]

    # readonly_fields = ['latest_running', 'latest_task']

    def last_run_task_url(self, obj):
        t = obj.last_run_task
        if t:
            return '<a href="%s">%s</a>' % (reverse_lazy("admin:integrations_task_change", args=(t.id,)), escape(t.id))
        return None

    last_run_task_url.allow_tags = True
    last_run_task_url.short_description = ugettext_lazy('last run task')


admin.site.register(PricingAutomatedSchedule, PricingAutomatedScheduleAdmin)


# --------


class ComplexTransactionImportSchemeInputInline(admin.TabularInline):
    model = ComplexTransactionImportSchemeInput
    extra = 0


class ComplexTransactionImportSchemeRuleInline(admin.TabularInline):
    model = ComplexTransactionImportSchemeRule
    raw_id_fields = ['transaction_type']
    show_change_link = True
    extra = 0


class ComplexTransactionImportSchemeFieldInline(admin.TabularInline):
    model = ComplexTransactionImportSchemeField
    raw_id_fields = ['rule', 'transaction_type_input']
    extra = 0


class ComplexTransactionImportSchemeAdmin(AbstractModelAdmin):
    model = ComplexTransactionImportScheme
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'scheme_name']
    list_select_related = ['master_user', ]
    search_fields = ['id', 'scheme_name', ]
    raw_id_fields = ['master_user']
    save_as = True
    inlines = [
        ComplexTransactionImportSchemeInputInline, ComplexTransactionImportSchemeRuleInline,
    ]


admin.site.register(ComplexTransactionImportScheme, ComplexTransactionImportSchemeAdmin)


# class ComplexTransactionImportSchemeInputdmin(AbstractModelAdmin):
#     model = ComplexTransactionImportSchemeInput
#     master_user_path = 'scheme__master_user'
#     list_display = ['id', 'master_user', 'scheme', 'name']
#     list_select_related = ['scheme', 'scheme__master_user', ]
#     search_fields = ['id', 'scheme__scheme_name', ]
#     raw_id_fields = ['scheme', ]
#
#     def master_user(self, obj):
#         return obj.scheme.master_user
#
#     master_user.admin_order_field = 'scheme__master_user'
#
#
# admin.site.register(ComplexTransactionImportSchemeInput, ComplexTransactionImportSchemeInputdmin)


class ComplexTransactionImportSchemeRuledmin(AbstractModelAdmin):
    model = ComplexTransactionImportSchemeRule
    master_user_path = 'scheme__master_user'
    list_display = ['id', 'master_user', 'scheme', 'value', 'transaction_type']
    list_select_related = ['scheme', 'scheme__master_user', ]
    search_fields = ['id', 'scheme__scheme_name', ]
    raw_id_fields = ['scheme', 'transaction_type']
    inlines = [
        ComplexTransactionImportSchemeFieldInline,
    ]

    def master_user(self, obj):
        return obj.scheme.master_user

    master_user.admin_order_field = 'scheme__master_user'


admin.site.register(ComplexTransactionImportSchemeRule, ComplexTransactionImportSchemeRuledmin)


# class ComplexTransactionImportSchemeFieldAdmin(AbstractModelAdmin):
#     model = ComplexTransactionImportSchemeField
#     master_user_path = 'rule__scheme__master_user'
#     list_display = ['id', 'master_user', 'scheme', 'rule', 'input']
#     list_select_related = ['rule', 'rule__scheme', 'rule__scheme__master_user', ]
#     search_fields = ['id', 'rule__scheme__scheme_name', ]
#     raw_id_fields = ['scheme', 'rule', ]
#
#     def master_user(self, obj):
#         return obj.rule.scheme.master_user
#
#     master_user.admin_order_field = 'rule__scheme__master_user'
#
#     def scheme(self, obj):
#         return obj.rule.scheme
#
#     scheme.admin_order_field = 'rule__scheme'
#
#
# admin.site.register(ComplexTransactionImportSchemeField, ComplexTransactionImportSchemeFieldAdmin)
