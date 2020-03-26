from django.contrib import admin

from poms.layout_recovery.models import LayoutArchetype


class LayoutArchetypeAdmin(admin.ModelAdmin):
    model = LayoutArchetype
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'name', 'content_type']
    raw_id_fields = ['master_user', 'content_type']


admin.site.register(LayoutArchetype, LayoutArchetypeAdmin)
