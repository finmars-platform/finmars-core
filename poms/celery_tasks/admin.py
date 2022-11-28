from django.contrib import admin

from poms.celery_tasks.models import CeleryTask


class CeleryTaskAdmin(admin.ModelAdmin):
    model = CeleryTask
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'parent', 'celery_task_id', 'type', 'status', 'created', 'modified']
    search_fields = ['id', 'type']
    raw_id_fields = ['master_user']


admin.site.register(CeleryTask, CeleryTaskAdmin)
