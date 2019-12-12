from django.contrib import admin

from poms.reconciliation.models import ReconciliationComplexTransactionField, ReconciliationBankFileField, \
    ReconciliationNewBankFileField


class ReconciliationComplexTransactionFieldAdmin(admin.ModelAdmin):
    model = ReconciliationComplexTransactionField
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'reference_name', 'description', 'value_string', 'value_float', 'value_date',
                    'status', 'match_date', 'notes']
    search_fields = ['id', 'reference_name', 'value_string']
    raw_id_fields = ['master_user']
    inlines = []


admin.site.register(ReconciliationComplexTransactionField, ReconciliationComplexTransactionFieldAdmin)


class ReconciliationBankFileFieldAdmin(admin.ModelAdmin):
    model = ReconciliationBankFileField
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'source_id', 'reference_name', 'description', 'value_string', 'value_float', 'value_date',
                    'status', 'reference_date', 'notes']
    search_fields = ['id', 'reference_name', 'value_string']
    raw_id_fields = ['master_user']
    inlines = []


admin.site.register(ReconciliationBankFileField, ReconciliationBankFileFieldAdmin)


class ReconciliationNewBankFileFieldAdmin(admin.ModelAdmin):
    model = ReconciliationNewBankFileField
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'source_id', 'reference_name', 'description', 'value_string', 'value_float', 'value_date',
                    'reference_date']
    search_fields = ['id', 'reference_name', 'value_string']
    raw_id_fields = ['master_user']
    inlines = []


admin.site.register(ReconciliationNewBankFileField, ReconciliationNewBankFileFieldAdmin)