from django.conf import settings
from django.contrib import admin
from django.utils.translation import gettext_lazy

admin.site.site_title = gettext_lazy("Finmars site admin")
admin.site.site_header = gettext_lazy("Finmars administration")
admin.site.index_title = gettext_lazy("Finmars site administration")
admin.site.empty_value_display = "<small>NULL</small>"

if "django_celery_results" in settings.INSTALLED_APPS:
    from django_celery_results.admin import TaskResultAdmin
    from django_celery_results.models import TaskResult

    class TaskResultAdminExt(TaskResultAdmin):
        search_fields = ["task_id"]
        list_filter = ["status"]

    admin.site.unregister(TaskResult)
    admin.site.register(TaskResult, TaskResultAdminExt)
