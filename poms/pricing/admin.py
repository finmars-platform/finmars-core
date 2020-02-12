from django.contrib import admin


from django.contrib import admin

from poms.pricing.models import InstrumentPricingSchemeType, CurrencyPricingSchemeType, InstrumentPricingScheme, \
    CurrencyPricingScheme, PricingProcedureBloombergResult, PricingProcedure


class InstrumentPricingSchemeTypeAdmin(admin.ModelAdmin):
    model = InstrumentPricingSchemeType,
    list_display = ['id', 'name', 'notes', 'input_type']


admin.site.register(InstrumentPricingSchemeType, InstrumentPricingSchemeTypeAdmin)


class CurrencyPricingSchemeTypeAdmin(admin.ModelAdmin):
    model = CurrencyPricingSchemeType,
    list_display = ['id', 'name', 'notes', 'input_type']


admin.site.register(CurrencyPricingSchemeType, CurrencyPricingSchemeTypeAdmin)


class InstrumentPricingSchemeAdmin(admin.ModelAdmin):
    model = InstrumentPricingScheme,
    list_display = ['id', 'name', 'master_user', 'notes', 'notes_for_users', 'error_handler']


admin.site.register(InstrumentPricingScheme, InstrumentPricingSchemeAdmin)


class CurrencyPricingSchemeAdmin(admin.ModelAdmin):
    model = CurrencyPricingScheme,
    list_display = ['id', 'name', 'master_user', 'notes', 'notes_for_users', 'error_handler']


admin.site.register(CurrencyPricingScheme, CurrencyPricingSchemeAdmin)


class PricingProcedureBloombergResultAdmin(admin.ModelAdmin):
    model = PricingProcedureBloombergResult,
    list_display = ['id', 'master_user', 'procedure', 'instrument', 'pricing_policy', 'reference', 'date', 'ask_value', 'bid_value', 'last_value']


admin.site.register(PricingProcedureBloombergResult, PricingProcedureBloombergResultAdmin)


class PricingProcedureAdmin(admin.ModelAdmin):
    model = PricingProcedure,
    list_display = ['id', 'name', 'master_user', 'notes', 'notes_for_users', 'price_date_from', 'price_date_to', 'price_balance_date']


admin.site.register(PricingProcedure, PricingProcedureAdmin)
