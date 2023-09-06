from django.contrib import admin

from poms.celery_tasks.models import CeleryTask, CeleryWorker
from poms.common.admin import AbstractModelAdmin


@admin.register(CeleryTask)
class CeleryTaskAdmin(admin.ModelAdmin):
    model = CeleryTask
    master_user_path = "master_user"
    list_display = [
        "id",
        "master_user",
        "parent",
        "celery_task_id",
        "type",
        "status",
        "created",
        "modified",
    ]
    search_fields = [
        "id",
        "type",
    ]
    raw_id_fields = [
        "master_user",
    ]




class CeleryWorkerAdmin(AbstractModelAdmin):
    model = CeleryWorker
    list_display = [
        "id",
        "worker_name",
        "queue",
        "memory_limit",
        "status"
    ]


admin.site.register(CeleryWorker, CeleryWorkerAdmin)