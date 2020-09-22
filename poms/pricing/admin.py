from django.contrib import admin


from django.contrib import admin

from poms.pricing.models import InstrumentPricingSchemeType, CurrencyPricingSchemeType, InstrumentPricingScheme, \
    CurrencyPricingScheme, InstrumentPricingPolicy, \
    InstrumentTypePricingPolicy, CurrencyPricingPolicy, \
    PricingProcedureBloombergInstrumentResult, PricingProcedureBloombergCurrencyResult, \
    PricingProcedureWtradeInstrumentResult, PriceHistoryError, \
    CurrencyHistoryError, PricingProcedureBloombergForwardInstrumentResult


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


class PricingProcedureBloombergInstrumentResultAdmin(admin.ModelAdmin):
    model = PricingProcedureBloombergInstrumentResult
    list_display = ['id', 'master_user', 'procedure', 'instrument', 'pricing_policy', 'reference', 'date', 'ask_value', 'bid_value', 'last_value']
    raw_id_fields = ['instrument', 'pricing_policy']


admin.site.register(PricingProcedureBloombergInstrumentResult, PricingProcedureBloombergInstrumentResultAdmin)


class PricingProcedureBloombergForwardInstrumentResultAdmin(admin.ModelAdmin):
    model = PricingProcedureBloombergForwardInstrumentResult
    list_display = ['id', 'master_user', 'procedure', 'instrument', 'pricing_policy', 'reference', 'date', 'price_code_parameters', 'price_code_value', 'tenor_type', 'tenor_clause']
    raw_id_fields = ['instrument', 'pricing_policy']


admin.site.register(PricingProcedureBloombergForwardInstrumentResult, PricingProcedureBloombergForwardInstrumentResultAdmin)


class PricingProcedureBloombergCurrencyResultAdmin(admin.ModelAdmin):
    model = PricingProcedureBloombergCurrencyResult
    list_display = ['id', 'master_user', 'procedure', 'currency', 'pricing_policy', 'reference', 'date', 'fx_rate_parameters', 'fx_rate_value']
    raw_id_fields = ['currency', 'pricing_policy']


admin.site.register(PricingProcedureBloombergCurrencyResult, PricingProcedureBloombergCurrencyResultAdmin)


class PricingProcedureWtradeInstrumentResultAdmin(admin.ModelAdmin):
    model = PricingProcedureWtradeInstrumentResult
    list_display = ['id', 'master_user', 'procedure', 'instrument', 'pricing_policy', 'reference', 'date', 'open_value', 'close_value', 'high_value', 'low_value', 'volume_value']
    raw_id_fields = ['instrument', 'pricing_policy']


admin.site.register(PricingProcedureWtradeInstrumentResult, PricingProcedureWtradeInstrumentResultAdmin)


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


class PriceHistoryErrorAdmin(admin.ModelAdmin):
    model = PriceHistoryError
    list_display = ['id', 'procedure_instance', 'master_user',
                    'instrument', 'pricing_policy', 'pricing_scheme',
                    'date', 'principal_price', 'accrued_price',
                    'price_error_text', 'accrual_error_text']
    raw_id_fields = ['procedure_instance', 'master_user', 'instrument', 'pricing_policy', 'pricing_scheme']


admin.site.register(PriceHistoryError, PriceHistoryErrorAdmin)


class CurrencyHistoryErrorAdmin(admin.ModelAdmin):
    model = CurrencyHistoryError
    list_display = ['id', 'procedure_instance', 'master_user',
                    'currency', 'pricing_policy', 'pricing_scheme',
                    'date', 'fx_rate',
                    'error_text']
    raw_id_fields = ['procedure_instance', 'master_user', 'currency', 'pricing_policy', 'pricing_scheme']


admin.site.register(CurrencyHistoryError, CurrencyHistoryErrorAdmin)



