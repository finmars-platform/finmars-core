from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.reports.models import BalanceReportCustomField, PLReportCustomField, TransactionReportCustomField


class BalanceReportCustomFieldAdmin(AbstractModelAdmin):
    model = BalanceReportCustomField
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'name', 'user_code']
    list_select_related = ['master_user']
    search_fields = ['id', 'name', 'user_code']
    raw_id_fields = ['master_user']


admin.site.register(BalanceReportCustomField, BalanceReportCustomFieldAdmin)


class PLReportCustomFieldAdmin(AbstractModelAdmin):
    model = PLReportCustomField
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'name', 'user_code']
    list_select_related = ['master_user']
    search_fields = ['id', 'name', 'user_code']
    raw_id_fields = ['master_user']


admin.site.register(PLReportCustomField, PLReportCustomFieldAdmin)

class TransactionReportCustomFieldAdmin(AbstractModelAdmin):
    model = TransactionReportCustomField
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'name', 'user_code']
    list_select_related = ['master_user']
    search_fields = ['id', 'name', 'user_code']
    raw_id_fields = ['master_user']


admin.site.register(TransactionReportCustomField, TransactionReportCustomFieldAdmin)