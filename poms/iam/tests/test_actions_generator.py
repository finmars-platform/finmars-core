from typing import Callable
from collections import namedtuple

from rest_framework.viewsets import ViewSet
from rest_framework.views import APIView

from poms.common.common_base_test import BaseTestCase
from poms.system_messages.views import SystemMessageViewSet


WRITE_ACCESS_ACTIONS = {
    "create",
    "update",
    "destroy",
    "delete",
    "bulk_create",
    "bulk_destroy",
    "bulk_delete",
    "bulk_update",
    "mark_all_as_read",
    "mark_as_read",
    "mark_as_solved",
    "solve",
    "pin",
    "unpin",
    "comment",
    "clear_bin",
    "execute",
    "cancel",
    "abort_transaction_import",
    "filtered",
    "ev_item",
    "ev_group",
    "create_worker",
    "start",
    "restart",
    "stop",
    "export",
    "seal",
    "unseal",
    "book",
    "update_pricing",
}
READ_ACCESS_ACTIONS = {
    "retrieve",
    "list",
    "list_ev_group",
    "list_ev_item",
    "stats",
    "attributes",
    "view_log",
    "status",
    "primary",
    "data",
    "content_type",
    "get_metadata",
    "get_inception_date",
    "ping",
    "objects_to_recalculate",
}

READ_MODE = "read"
WRITE_MODE = "write"

ActionMode = namedtuple("ActionMode", ["name", "mode"])


def get_action_name_and_access_mode(action: Callable) -> ActionMode:
    action_name = action.__name__
    if action_name in WRITE_ACCESS_ACTIONS:
        return ActionMode(action_name, WRITE_MODE)
    elif action_name in READ_ACCESS_ACTIONS:
        return ActionMode(action_name, READ_MODE)
    else:
        raise RuntimeError(f"Unknown viewset action {action_name}")


class ActionListTest(BaseTestCase):
    databases = "__all__"

    def test_actions_of_system_message_viewset(self):
        viewset = SystemMessageViewSet()
        expected_list = [
            "bulk_delete",
            "comment",
            "list_ev_group",
            "list_ev_item",
            "mark_all_as_read",
            "mark_as_read",
            "mark_as_solved",
            "pin",
            "solve",
            "stats",
            "unpin",
        ]

        for action in viewset.get_extra_actions():
            print(get_action_name_and_access_mode(action))
