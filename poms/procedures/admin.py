from django.contrib import admin

from poms.procedures.models import RequestDataFileProcedure


class RequestDataFileProcedureAdmin(admin.ModelAdmin):
    model = RequestDataFileProcedure
    list_display = ['id', 'master_user', 'name', 'user_code', 'provider', 'scheme_name']
    raw_id_fields = ['master_user']


admin.site.register(RequestDataFileProcedure, RequestDataFileProcedureAdmin)