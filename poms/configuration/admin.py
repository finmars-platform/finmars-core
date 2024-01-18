from django.contrib import admin

from poms.configuration.models import Configuration


class ConfigurationAdmin(admin.ModelAdmin):
    model = Configuration
    list_display = [
        "id",
        "configuration_code",
        "name",
        "version",
    ]
    search_fields = [
        "id",
        "configuration_code",
        "name",
        "version",
    ]
    raw_id_fields = []
    inlines = []
