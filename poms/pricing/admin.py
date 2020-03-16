from django.contrib import admin


from django.contrib import admin

from poms.pricing.models import InstrumentPricingSchemeType, CurrencyPricingSchemeType, InstrumentPricingScheme, \
    CurrencyPricingScheme, PricingProcedure, InstrumentPricingPolicy, \
    InstrumentTypePricingPolicy, CurrencyPricingPolicy, PricingProcedureInstance, \
    PricingProcedureBloombergInstrumentResult, PricingProcedureBloombergCurrencyResult, \
    PricingProcedureWtradeInstrumentResult, PriceHistoryError, \
    CurrencyHistoryError, PricingParentProcedureInstance


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


class PricingProcedureAdmin(admin.ModelAdmin):
    model = PricingProcedure
    list_display = ['id', 'name', 'master_user', 'notes', 'notes_for_users', 'price_date_from', 'price_date_to', 'price_balance_date']


admin.site.register(PricingProcedure, PricingProcedureAdmin)


class PricingParentProcedureInstanceAdmin(admin.ModelAdmin):
    model = PricingParentProcedureInstance
    list_display = ['id', 'master_user', 'pricing_procedure', 'created', 'modified']
    raw_id_fields = ['master_user', 'pricing_procedure']


admin.site.register(PricingParentProcedureInstance, PricingParentProcedureInstanceAdmin)


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


class PricingProcedureInstanceAdmin(admin.ModelAdmin):
    model = PricingProcedureInstance
    list_display = ['id', 'pricing_procedure', 'master_user', 'status']
    raw_id_fields = ['pricing_procedure', 'master_user']


admin.site.register(PricingProcedureInstance, PricingProcedureInstanceAdmin)


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



