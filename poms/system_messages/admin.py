from django.contrib import admin

from .models import SystemMessage, SystemMessageAttachment, SystemMessageMember


class SystemMessageAdmin(admin.ModelAdmin):
    model = SystemMessage
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'created_at', 'title', 'description', 'performed_by']
    search_fields = ['id', 'description']
    raw_id_fields = ['master_user', ]


admin.site.register(SystemMessage, SystemMessageAdmin)


class SystemMessageAttachmentAdmin(admin.ModelAdmin):
    model = SystemMessageAttachment
    list_display = ['id', 'system_message', 'file_report']
    search_fields = ['id']


admin.site.register(SystemMessageAttachment, SystemMessageAttachmentAdmin)


class SystemMessageMemberAdmin(admin.ModelAdmin):
    model = SystemMessageMember
    list_display = ['id', 'member', 'system_message', 'is_read', 'is_pinned']
    search_fields = ['id']
    raw_id_fields = ['member', 'system_message']


admin.site.register(SystemMessageMember, SystemMessageMemberAdmin)
