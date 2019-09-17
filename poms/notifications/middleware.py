# coding=utf-8
from __future__ import unicode_literals

from poms.notifications.models import Notification


class NotificationMiddleware(object):
    def process_response(self, request, response):
        if request.user.is_authenticated:
            new_val = Notification.objects.filter(recipient=request.user).count()
            # response['Notification-Unread-Count'] = new_val
            # patch_vary_headers(response, ['Notification-Unread-Count'])
            val = request.COOKIES.get('notification_unread_count')
            if val != new_val:
                response.set_cookie('notification_unread_count', value=new_val, max_age=60)
        return response
