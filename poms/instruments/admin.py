from __future__ import unicode_literals

from django.contrib import admin, messages
from django.db import models
from django.forms import widgets
from django.utils.translation import ugettext_lazy

from poms.common.admin import ClassModelAdmin, AbstractModelAdmin
from poms.instruments.models import Instrument, PriceHistory, InstrumentClass, InstrumentType, \
    DailyPricingModel, AccrualCalculationModel, Periodicity, CostMethod, \
    ManualPricingFormula, AccrualCalculationSchedule, InstrumentFactorSchedule, EventSchedule, \
    PricingPolicy, PaymentSizeDetail, EventScheduleAction, EventScheduleConfig, GeneratedEvent, PricingCondition
from poms.instruments.tasks import calculate_prices_accrued_price
from poms.obj_attrs.admin import GenericAttributeInline
from poms.obj_perms.admin import GenericObjectPermissionInline
from poms.tags.admin import GenericTagLinkInline

admin.site.register(InstrumentClass, ClassModelAdmin)
admin.site.register(DailyPricingModel, ClassModelAdmin)
admin.site.register(PricingCondition, ClassModelAdmin)
admin.site.register(AccrualCalculationModel, ClassModelAdmin)
admin.site.register(Periodicity, ClassModelAdmin)
admin.site.register(CostMethod, ClassModelAdmin)
admin.site.register(PaymentSizeDetail, ClassModelAdmin)


class PricingPolicyAdmin(AbstractModelAdmin):
    model = PricingPolicy
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'user_code', 'name', ]
    list_select_related = ['master_user']
    search_fields = ['id', 'user_code', 'name']
    raw_id_fields = ['master_user']


admin.site.register(PricingPolicy, PricingPolicyAdmin)


class InstrumentTypeAdmin(AbstractModelAdmin):
    model = InstrumentType
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'user_code', 'name', 'instrument_class', 'is_deleted', ]
    list_select_related = ['master_user', 'instrument_class']
    list_filter = ['instrument_class', 'is_deleted', ]
    search_fields = ['id', 'user_code', 'name']
    raw_id_fields = ['master_user', 'one_off_event', 'regular_event', 'factor_same', 'factor_up', 'factor_down']
    inlines = [
        GenericTagLinkInline,
        GenericObjectPermissionInline,
        # UserObjectPermissionInline,
        # GroupObjectPermissionInline,
    ]


admin.site.register(InstrumentType, InstrumentTypeAdmin)


# class InstrumentAttributeInline(AbstractAttributeInline):
#     model = InstrumentAttribute


class ManualPricingFormulaInline(admin.TabularInline):
    model = ManualPricingFormula
    extra = 0
    raw_id_fields = ['pricing_policy']
    formfield_overrides = {
        models.TextField: {'widget': widgets.Textarea(attrs={'cols': '40', 'rows': '3'})},
    }


class AccrualCalculationScheduleInline(admin.TabularInline):
    model = AccrualCalculationSchedule
    extra = 0
    formfield_overrides = {
        models.TextField: {'widget': widgets.Textarea(attrs={'cols': '40', 'rows': '3'})},
    }


class InstrumentFactorScheduleInline(admin.TabularInline):
    model = InstrumentFactorSchedule
    extra = 0


class InstrumentAdmin(AbstractModelAdmin):
    model = Instrument
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'instrument_type', 'user_code', 'name', 'is_deleted']
    list_select_related = ['master_user', 'instrument_type', 'pricing_currency', 'accrued_currency']
    list_filter = ['instrument_type__instrument_class', 'is_deleted', ]
    search_fields = ['id', 'user_code', 'name']
    raw_id_fields = ['master_user', 'instrument_type', 'pricing_currency', 'accrued_currency', 'price_download_scheme']
    inlines = [
        # InstrumentAttributeInline,
        ManualPricingFormulaInline,
        AccrualCalculationScheduleInline,
        InstrumentFactorScheduleInline,
        # EventScheduleInline,
        GenericAttributeInline,
        GenericTagLinkInline,
        GenericObjectPermissionInline,
        # UserObjectPermissionInline,
        # GroupObjectPermissionInline,
    ]
    actions = ['calculate_prices_accrued_price', 'rebuild_event_schedules']

    def rebuild_event_schedules(self, request, queryset):
        for instr in queryset:
            try:
                instr.rebuild_event_schedules()
            except ValueError as e:
                messages.error(request, '%s: %s' % (instr, e))

    rebuild_event_schedules.short_description = "Rebuild event schedules"

    def calculate_prices_accrued_price(self, request, queryset):
        # for instrument in queryset:
        #     instrument.calculate_prices_accrued_price()
        calculate_prices_accrued_price(instruments=queryset)
        # calculate_prices_accrued_price_async.apply_async(
        #     kwargs={
        #         'instruments': list(queryset.values_list('id', flat=True))
        #     }
        # ).wait()

    calculate_prices_accrued_price.short_description = "Calculate accrued price for prices"


admin.site.register(Instrument, InstrumentAdmin)


class ManualPricingFormulaAdmin(AbstractModelAdmin):
    model = AccrualCalculationSchedule
    master_user_path = 'instrument__master_user'
    list_display = ['id', 'master_user', 'instrument', 'pricing_policy']
    list_select_related = ['instrument', 'instrument__master_user', 'pricing_policy']
    search_fields = ['instrument__id', 'instrument__user_code', 'instrument__name']
    raw_id_fields = ['instrument', 'pricing_policy']

    def master_user(self, obj):
        return obj.instrument.master_user

    master_user.admin_order_field = 'instrument__master_user'


admin.site.register(ManualPricingFormula, ManualPricingFormulaAdmin)


class AccrualCalculationScheduleAdmin(AbstractModelAdmin):
    model = AccrualCalculationSchedule
    master_user_path = 'instrument__master_user'
    list_display = ['id', 'master_user', 'instrument', 'accrual_start_date', 'first_payment_date',
                    'accrual_calculation_model', 'periodicity']
    list_select_related = ['instrument', 'instrument__master_user', 'accrual_calculation_model', 'periodicity']
    list_filter = ['accrual_calculation_model', 'periodicity']
    search_fields = ['instrument__id', 'instrument__user_code', 'instrument__name']
    raw_id_fields = ['instrument']

    def master_user(self, obj):
        return obj.instrument.master_user

    master_user.admin_order_field = 'instrument__master_user'


admin.site.register(AccrualCalculationSchedule, AccrualCalculationScheduleAdmin)


class InstrumentFactorScheduleAdmin(AbstractModelAdmin):
    model = InstrumentFactorSchedule
    master_user_path = 'instrument__master_user'
    list_display = ['id', 'master_user', 'instrument', 'effective_date', 'factor_value']
    list_select_related = ['instrument', 'instrument__master_user']
    list_filter = ['effective_date']
    search_fields = ['instrument__id', 'instrument__user_code', 'instrument__name']
    raw_id_fields = ['instrument']

    def master_user(self, obj):
        return obj.instrument.master_user

    master_user.admin_order_field = 'instrument__master_user'


admin.site.register(InstrumentFactorSchedule, InstrumentFactorScheduleAdmin)


class EventScheduleActionInline(admin.TabularInline):
    model = EventScheduleAction
    raw_id_fields = ['transaction_type']
    extra = 0


class EventScheduleAdmin(AbstractModelAdmin):
    model = EventSchedule
    master_user_path = 'instrument__master_user'
    list_display = ['id', 'master_user', 'instrument', 'effective_date', 'name', 'event_class', 'notification_class',
                    'periodicity', 'final_date', 'is_auto_generated', 'accrual_calculation_schedule', 'factor_schedule',
                    '_actions']
    list_select_related = ['instrument', 'instrument__master_user', 'event_class', 'notification_class', 'periodicity',
                           'accrual_calculation_schedule', 'factor_schedule']
    list_filter = ['effective_date', 'event_class', 'notification_class', 'periodicity']
    date_hierarchy = 'effective_date'
    search_fields = ['instrument__id', 'instrument__user_code', 'instrument__name']
    raw_id_fields = ['instrument', 'accrual_calculation_schedule']
    save_as = True

    inlines = [
        EventScheduleActionInline
    ]

    def get_queryset(self, request):
        qs = super(EventScheduleAdmin, self).get_queryset(request)
        return qs.prefetch_related('actions', 'actions__transaction_type')

    def master_user(self, obj):
        return obj.instrument.master_user

    master_user.admin_order_field = 'instrument__master_user'

    def _actions(self, obj):
        n = []
        for a in obj.actions.all():
            n.append(a.transaction_type.name)
        return ', '.join(n)

    _actions.short_description = ugettext_lazy('Actions')


admin.site.register(EventSchedule, EventScheduleAdmin)


class EventScheduleActionAdmin(AbstractModelAdmin):
    model = EventScheduleAction
    master_user_path = 'event_schedule__instrument__master_user'
    list_display = ['id', 'master_user', 'instrument', 'event_schedule', 'transaction_type', 'text',
                    'is_sent_to_pending', 'is_book_automatic', 'button_position']
    list_select_related = ['event_schedule', 'event_schedule__instrument', 'event_schedule__instrument__master_user',
                           'transaction_type']
    search_fields = ['event_schedule__instrument__id', 'event_schedule__instrument__user_code',
                     'event_schedule__instrument__name']
    raw_id_fields = ['event_schedule', 'transaction_type']

    def master_user(self, obj):
        return obj.event_schedule.instrument.master_user

    master_user.admin_order_field = 'event_schedule__instrument__master_user'

    def instrument(self, obj):
        return obj.event_schedule.instrument

    instrument.admin_order_field = 'event_schedule__instrument'


admin.site.register(EventScheduleAction, EventScheduleActionAdmin)


class PriceHistoryAdmin(AbstractModelAdmin):
    model = PriceHistory
    master_user_path = 'instrument__master_user'
    list_display = ['id', 'master_user', 'instrument', 'pricing_policy', 'date', 'principal_price', 'accrued_price']
    list_select_related = ['instrument', 'instrument__master_user', 'pricing_policy']
    search_fields = ['instrument__id', 'instrument__user_code', 'instrument__name']
    list_filter = ['date']
    date_hierarchy = 'date'
    raw_id_fields = ['instrument', 'pricing_policy']

    # actions = ['calculate_accrued_price']

    def master_user(self, obj):
        return obj.instrument.master_user

    master_user.admin_order_field = 'instrument__master_user'

    # def calculate_accrued_price(self, request, queryset):
    #     for p in queryset:
    #         p.calculate_accrued_price(save=True)
    #
    # calculate_accrued_price.short_description = "Calculate accrued price"


admin.site.register(PriceHistory, PriceHistoryAdmin)


# class InstrumentAttributeTypeAdmin(AbstractAttributeTypeAdmin):
#     inlines = [
#         AbstractAttributeTypeClassifierInline,
#         AbstractAttributeTypeOptionInline,
#         GenericObjectPermissionInline,
#         # UserObjectPermissionInline,
#         # GroupObjectPermissionInline,
#     ]
#
#
# admin.site.register(InstrumentAttributeType, InstrumentAttributeTypeAdmin)
#
# admin.site.register(InstrumentClassifier, ClassifierAdmin)


class GeneratedEventAdmin(AbstractModelAdmin):
    model = GeneratedEvent
    master_user_path = 'master_user'
    list_display = ('id', 'master_user', 'status', 'effective_date', 'effective_date_notified',
                    'notification_date', 'notification_date_notified', 'event_schedule',
                    'instrument', 'portfolio', 'account', 'strategy1', 'strategy2', 'strategy3', 'position', 'action',
                    'transaction_type', 'complex_transaction', 'member',)
    list_select_related = ('master_user', 'event_schedule', 'instrument', 'portfolio', 'account', 'strategy1',
                           'strategy2', 'strategy3', 'action', 'transaction_type', 'member',)
    list_filter = ['status', 'notification_date', 'effective_date']
    date_hierarchy = 'effective_date'
    raw_id_fields = ('master_user', 'event_schedule', 'instrument', 'portfolio', 'account', 'strategy1',
                     'strategy2', 'strategy3', 'action', 'transaction_type', 'complex_transaction', 'member',)


admin.site.register(GeneratedEvent, GeneratedEventAdmin)


class EventScheduleConfigAdmin(AbstractModelAdmin):
    model = EventScheduleConfig
    master_user_path = 'master_user'
    list_display = ('id', 'master_user')
    list_select_related = ('master_user', 'notification_class',)
    raw_id_fields = ('master_user',)

    # def master_user(self, obj):
    #     return obj.instrument.master_user

    # master_user.admin_order_field = 'instrument__master_user'


admin.site.register(EventScheduleConfig, EventScheduleConfigAdmin)
