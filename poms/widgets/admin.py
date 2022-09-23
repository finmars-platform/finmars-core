from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.widgets.models import BalanceReportHistory, BalanceReportHistoryItem, PLReportHistory, PLReportHistoryItem, \
    WidgetStats


class BalanceReportHistoryAdmin(AbstractModelAdmin):
    model = BalanceReportHistory
    list_display = ['id', 'master_user', 'date', 'nav']
    list_select_related = ['master_user']
    search_fields = ['id', 'date']
    raw_id_fields = ['master_user']


admin.site.register(BalanceReportHistory, BalanceReportHistoryAdmin)



class BalanceReportHistoryItemAdmin(AbstractModelAdmin):
    model = BalanceReportHistoryItem
    list_display = ['id', 'balance_report_history', 'category', 'name', 'key']
    list_select_related = ['balance_report_history']
    search_fields = ['id', 'category', 'name', 'key']
    raw_id_fields = ['balance_report_history']


admin.site.register(BalanceReportHistoryItem, BalanceReportHistoryItemAdmin)


class PLReportHistoryAdmin(AbstractModelAdmin):
    model = PLReportHistory
    list_display = ['id', 'master_user', 'date', 'total']
    list_select_related = ['master_user']
    search_fields = ['id', 'date']
    raw_id_fields = ['master_user']


admin.site.register(PLReportHistory, PLReportHistoryAdmin)



class PLReportHistoryItemAdmin(AbstractModelAdmin):
    model = PLReportHistoryItem
    list_display = ['id', 'pl_report_history', 'category', 'name', 'key']
    list_select_related = ['pl_report_history']
    search_fields = ['id', 'category', 'name', 'key']
    raw_id_fields = ['pl_report_history']


admin.site.register(PLReportHistoryItem, PLReportHistoryItemAdmin)


class WidgetStatsAdmin(AbstractModelAdmin):
    model = WidgetStats
    list_display = ['id', 'master_user', 'date', 'portfolio', 'nav']
    list_select_related = ['master_user', 'portfolio']
    search_fields = ['id', 'date', 'portfolio']
    raw_id_fields = ['master_user', 'portfolio']


admin.site.register(WidgetStats, WidgetStatsAdmin)
