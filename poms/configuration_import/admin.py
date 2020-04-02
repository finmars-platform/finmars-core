from django.contrib import admin

from poms.configuration_import.models import ConfigurationEntityArchetype


class ConfigurationEntityArchetypeAdmin(admin.ModelAdmin):
    model = ConfigurationEntityArchetype
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'name', 'content_type']
    raw_id_fields = ['master_user', 'content_type']


admin.site.register(ConfigurationEntityArchetype, ConfigurationEntityArchetypeAdmin)
