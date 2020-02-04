from django.contrib import admin


from django.contrib import admin

from poms.pricing.models import InstrumentPricingSchemeType, CurrencyPricingSchemeType, InstrumentPricingScheme, \
    CurrencyPricingScheme


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
    list_display = ['id', 'name', 'master_user', 'notes', 'notes_for_user', 'error_handler']


admin.site.register(InstrumentPricingScheme, InstrumentPricingSchemeAdmin)


class CurrencyPricingSchemeAdmin(admin.ModelAdmin):
    model = CurrencyPricingScheme,
    list_display = ['id', 'name', 'master_user', 'notes', 'notes_for_user', 'error_handler']


admin.site.register(CurrencyPricingScheme, CurrencyPricingSchemeAdmin)