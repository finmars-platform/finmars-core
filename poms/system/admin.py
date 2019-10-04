from django.contrib import admin

# Register your models here.

from django.contrib import admin
from poms.common.admin import AbstractModelAdmin
from poms.system.models import EcosystemConfiguration


class EcosystemConfigurationAdmin(AbstractModelAdmin):
    model = EcosystemConfiguration
    list_display = ['id', 'name']
    search_fields = ['id', 'name']


admin.site.register(EcosystemConfiguration, EcosystemConfigurationAdmin)