from django.contrib import admin

from poms.procedures.models import RequestDataFileProcedure, RequestDataFileProcedureInstance


class RequestDataFileProcedureAdmin(admin.ModelAdmin):
    model = RequestDataFileProcedure
    list_display = ['id', 'master_user', 'name', 'user_code', 'provider', 'scheme_name',
                    'price_date_from', 'price_date_from_expr',
                    'price_date_to', 'price_date_to_expr']
    raw_id_fields = ['master_user']


admin.site.register(RequestDataFileProcedure, RequestDataFileProcedureAdmin)


class RequestDataFileProcedureInstanceAdmin(admin.ModelAdmin):
    model = RequestDataFileProcedureInstance
    list_display = ['id', 'master_user', 'procedure', 'created', 'modified', 'status']
    raw_id_fields = ['master_user']


admin.site.register(RequestDataFileProcedureInstance, RequestDataFileProcedureInstanceAdmin)