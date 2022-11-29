from rest_framework.permissions import BasePermission


class GeneratedEventPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        # return obj.status == GeneratedEvent.NEW and \
        #        (obj.is_need_reaction_on_effective_date() or obj.is_need_reaction_on_notification_date())
        return obj.is_need_reaction
