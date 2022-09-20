from __future__ import unicode_literals

from django.contrib import admin

from poms.chats.models import Thread, Message, DirectMessage, ThreadGroup
from poms.common.admin import AbstractModelAdmin
from poms.obj_perms.admin import GenericObjectPermissionInline

class ThreadGroupAdmin(AbstractModelAdmin):
    model = ThreadGroup
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'name', 'is_deleted', ]
    list_select_related = ['master_user', ]
    search_fields = ['id', 'name']
    list_filter = ['is_deleted', ]
    raw_id_fields = ['master_user', ]
    inlines = [
        GenericObjectPermissionInline,
        # UserObjectPermissionInline,
        # GroupObjectPermissionInline
    ]


admin.site.register(ThreadGroup, ThreadGroupAdmin)


class ThreadAdmin(AbstractModelAdmin):
    model = Thread
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'thread_group', 'subject', 'created', 'closed', 'is_deleted', ]
    list_select_related = ['master_user', 'thread_group', ]
    list_filter = ['created', 'closed', 'is_deleted', ]
    search_fields = ['id', 'subject']
    date_hierarchy = 'created'
    raw_id_fields = ['master_user', 'thread_group', ]
    inlines = [
        GenericObjectPermissionInline,
        # UserObjectPermissionInline,
        # GroupObjectPermissionInline
    ]


admin.site.register(Thread, ThreadAdmin)


class MessageAdmin(AbstractModelAdmin):
    model = Message
    master_user_path = 'thread__master_user'
    list_display = ['id', 'master_user', 'thread', 'created', 'sender', 'short_text']
    list_select_related = ['thread', 'thread__master_user', 'sender']
    search_fields = ['thread__id', 'thread__subject']
    date_hierarchy = 'created'
    raw_id_fields = ['thread', 'sender']

    def master_user(self, obj):
        return obj.thread.master_user

    master_user.admin_order_field = 'thread__master_user'


admin.site.register(Message, MessageAdmin)


class DirectMessageAdmin(admin.ModelAdmin):
    model = DirectMessage
    list_display = ['id', 'created', 'sender', 'recipient', 'short_text']
    list_select_related = ['sender', 'recipient']
    date_hierarchy = 'created'
    raw_id_fields = ['recipient', 'sender']


admin.site.register(DirectMessage, DirectMessageAdmin)
