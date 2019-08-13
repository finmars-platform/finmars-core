from __future__ import unicode_literals

from django.contrib import admin

from poms.http_sessions.models import Session
from poms_app import settings

if settings.DEBUG:
    class SessionAdmin(admin.ModelAdmin):
        model = Session
        list_display = ['id', 'user', 'user_ip', 'human_user_agent', 'expire_date', 'current_master_user']
        list_display_links = ['id']
        list_select_related = ['user']
        list_filter = ['expire_date']
        search_fields = ['user__username']
        date_hierarchy = 'expire_date'
        fields = ['id', 'user', 'user_ip', 'user_agent', 'expire_date', 'current_master_user']
        readonly_fields = ['id', 'user', 'user_ip', 'user_agent', 'expire_date']
        raw_id_fields = ['user']

        def has_add_permission(self, request):
            return False


    admin.site.register(Session, SessionAdmin)
