from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.notifications.models import Notification


class NotificationAdmin(AbstractModelAdmin):
    model = Notification
    master_user_path = "recipient_member__master_user"
    list_display = [
        "id",
        "master_user",
        "recipient",
        "recipient_member",
        "create_date",
        "__str__",
        "actor",
        "verb",
        "action_object",
        "target",
    ]
    list_select_related = [
        "recipient",
        "recipient_member",
    ]
    raw_id_fields = ["recipient", "recipient_member"]
    date_hierarchy = "create_date"

    def get_queryset(self, request):
        queryset = super(NotificationAdmin, self).get_queryset(request)
        queryset.prefetch_related("actor", "action_object", "target")
        return queryset

    def master_user(self, obj):
        return getattr(obj.recipient_member, "master_user", None)

    master_user.admin_order_field = "recipient_member__master_user"


admin.site.register(Notification, NotificationAdmin)
