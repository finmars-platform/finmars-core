from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.reports.models import BalanceReportCustomField, PLReportCustomField, TransactionReportCustomField, \
    BalanceReportInstance,  PLReportInstance, \
    PerformanceReportInstanceItem, PerformanceReportInstance


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


class BalanceReportInstanceAdmin(AbstractModelAdmin):
    model = BalanceReportInstance
    master_user_path = 'master_user'
    list_display = ['id', 'name', 'master_user', 'report_date', 'report_currency']
    list_select_related = ['master_user']
    raw_id_fields = ['master_user']


admin.site.register(BalanceReportInstance, BalanceReportInstanceAdmin)


class PLReportInstanceAdmin(AbstractModelAdmin):
    model = PLReportInstance
    master_user_path = 'master_user'
    list_display = ['id', 'name', 'master_user', 'report_date', 'pl_first_date', 'report_currency']
    list_select_related = ['master_user']
    raw_id_fields = ['master_user']


admin.site.register(PLReportInstance, PLReportInstanceAdmin)

class PerformanceReportInstanceAdmin(AbstractModelAdmin):
    model = PerformanceReportInstance
    master_user_path = 'master_user'
    list_display = ['id', 'name', 'master_user', 'begin_date', 'end_date', 'report_currency']
    list_select_related = ['master_user']
    raw_id_fields = ['master_user']


admin.site.register(PerformanceReportInstance, PerformanceReportInstanceAdmin)


class PerformanceReportInstanceItemAdmin(AbstractModelAdmin):
    model = PerformanceReportInstanceItem
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'report_instance', 'begin_date', 'end_date', 'report_currency']
    list_select_related = ['master_user', 'report_instance']
    raw_id_fields = ['master_user', 'report_instance']


admin.site.register(PerformanceReportInstanceItem, PerformanceReportInstanceItemAdmin)
