from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import CsvImportScheme, EntityField, CsvField, CsvDataImport


class CsvImportAdmin(admin.ModelAdmin):
    list_display = ('id', 'scheme')


class CsvSchemeAdmin(admin.ModelAdmin):
    list_display = ('id', 'scheme_name', 'content_type', 'master_user')


class CsvImportSchemaFieldsAdmin(admin.ModelAdmin):
    list_display = ('scheme', 'column', 'name')


class CsvImportSchemaEntityFieldAdmin(admin.ModelAdmin):
    list_display = ('scheme', 'name', 'expression')


admin.site.register(CsvDataImport, CsvImportAdmin)
admin.site.register(CsvImportScheme, CsvSchemeAdmin)
admin.site.register(CsvField, CsvImportSchemaFieldsAdmin)
admin.site.register(EntityField, CsvImportSchemaEntityFieldAdmin)
