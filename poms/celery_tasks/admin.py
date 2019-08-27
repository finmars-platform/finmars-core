from django.contrib import admin

from poms.celery_tasks.models import CeleryTask


class CsvSchemeAdmin(admin.ModelAdmin):
    model = CeleryTask
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'task_id', 'task_type', 'task_status']
    search_fields = ['id', 'task_type']
    raw_id_fields = ['master_user']


admin.site.register(CeleryTask, CsvSchemeAdmin)
