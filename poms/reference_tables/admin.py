from __future__ import unicode_literals

from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.reference_tables.models import ReferenceTable, ReferenceTableRow


class ReferenceTableRowInline(admin.TabularInline):
    model = ReferenceTableRow
    extra = 0

    fields = ('key', 'value')
    readonly_fields = ('id',)


class ReferenceTableAdmin(AbstractModelAdmin):
    model = ReferenceTable
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'name', ]
    list_select_related = ['master_user']
    search_fields = ['id', 'name']
    raw_id_fields = ['master_user']
    inlines = [
        ReferenceTableRowInline,
    ]


admin.site.register(ReferenceTable, ReferenceTableAdmin)
