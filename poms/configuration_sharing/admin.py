from django.contrib import admin

# Register your models here.
from poms.configuration_sharing.models import SharedConfigurationFile, InviteToSharedConfigurationFile


class SharedConfigurationFileAdmin(admin.ModelAdmin):
    model = SharedConfigurationFile
    list_display = ['id', 'name', 'notes', 'publicity_type', 'user', 'linked_master_user']
    search_fields = ['id', 'name']


admin.site.register(SharedConfigurationFile, SharedConfigurationFileAdmin)


class InviteToSharedConfigurationFileAdmin(admin.ModelAdmin):
    model = InviteToSharedConfigurationFile
    list_display = ['id', 'member_from', 'member_to', 'status', 'shared_configuration_file']
    search_fields = ['id']


admin.site.register(InviteToSharedConfigurationFile, InviteToSharedConfigurationFileAdmin)