from django.contrib import admin


from django.contrib import admin

from poms.pricing.models import InstrumentPricingSchemeType, CurrencyPricingSchemeType, InstrumentPricingScheme, \
    CurrencyPricingScheme, PricingProcedureBloombergResult, PricingProcedure, InstrumentPricingPolicy, \
    InstrumentTypePricingPolicy, CurrencyPricingPolicy


class InstrumentPricingSchemeTypeAdmin(admin.ModelAdmin):
    model = InstrumentPricingSchemeType
    list_display = ['id', 'name', 'notes', 'input_type']


admin.site.register(InstrumentPricingSchemeType, InstrumentPricingSchemeTypeAdmin)


class CurrencyPricingSchemeTypeAdmin(admin.ModelAdmin):
    model = CurrencyPricingSchemeType
    list_display = ['id', 'name', 'notes', 'input_type']


admin.site.register(CurrencyPricingSchemeType, CurrencyPricingSchemeTypeAdmin)


class InstrumentPricingSchemeAdmin(admin.ModelAdmin):
    model = InstrumentPricingScheme
    list_display = ['id', 'name', 'master_user', 'notes', 'notes_for_users', 'error_handler']


admin.site.register(InstrumentPricingScheme, InstrumentPricingSchemeAdmin)


class CurrencyPricingSchemeAdmin(admin.ModelAdmin):
    model = CurrencyPricingScheme
    list_display = ['id', 'name', 'master_user', 'notes', 'notes_for_users', 'error_handler']


admin.site.register(CurrencyPricingScheme, CurrencyPricingSchemeAdmin)


class PricingProcedureBloombergResultAdmin(admin.ModelAdmin):
    model = PricingProcedureBloombergResult
    list_display = ['id', 'master_user', 'procedure', 'instrument', 'pricing_policy', 'reference', 'date', 'ask_value', 'bid_value', 'last_value']
    raw_id_fields = ['instrument', 'pricing_policy']


admin.site.register(PricingProcedureBloombergResult, PricingProcedureBloombergResultAdmin)


class PricingProcedureAdmin(admin.ModelAdmin):
    model = PricingProcedure,
    list_display = ['id', 'name', 'master_user', 'notes', 'notes_for_users', 'price_date_from', 'price_date_to', 'price_balance_date']


admin.site.register(PricingProcedure, PricingProcedureAdmin)


class InstrumentPricingPolicyAdmin(admin.ModelAdmin):
    model = InstrumentPricingPolicy
    list_display = ['id', 'instrument', 'pricing_policy', 'pricing_scheme', 'notes', 'default_value', 'attribute_key']
    raw_id_fields = ['instrument', 'pricing_policy', 'pricing_scheme']


admin.site.register(InstrumentPricingPolicy, InstrumentPricingPolicyAdmin)


class InstrumentTypePricingPolicyAdmin(admin.ModelAdmin):
    model = InstrumentTypePricingPolicy
    list_display = ['id', 'instrument_type', 'pricing_policy', 'pricing_scheme', 'notes', 'default_value', 'attribute_key']
    raw_id_fields = ['instrument_type', 'pricing_policy', 'pricing_scheme']


admin.site.register(InstrumentTypePricingPolicy, InstrumentTypePricingPolicyAdmin)


class CurrencyPricingPolicyAdmin(admin.ModelAdmin):
    model = CurrencyPricingPolicy
    list_display = ['id', 'currency', 'pricing_policy', 'pricing_scheme', 'notes', 'default_value', 'attribute_key']
    raw_id_fields = ['currency', 'pricing_policy', 'pricing_scheme']


admin.site.register(CurrencyPricingPolicy, CurrencyPricingPolicyAdmin)