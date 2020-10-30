from django.contrib import admin
from .models import SystemMessage


class SystemMessageAdmin(admin.ModelAdmin):
    model = SystemMessage
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'created', 'text', 'source']
    search_fields = ['id', 'text']
    raw_id_fields = ['master_user', ]


admin.site.register(SystemMessage, SystemMessageAdmin)

