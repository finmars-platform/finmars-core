from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.workflows.models import Workflow, WorkflowStep


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 0


class WorkflowAdmin(AbstractModelAdmin):
    model = Workflow
    list_display = ['id', 'master_user', 'name', 'notes']
    list_select_related = ['master_user']
    search_fields = ['id', 'name']
    raw_id_fields = ['master_user']
    inlines = [
        WorkflowStepInline
    ]


admin.site.register(Workflow, WorkflowAdmin)
