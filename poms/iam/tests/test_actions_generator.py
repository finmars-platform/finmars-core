from typing import Callable
from collections import namedtuple

from poms.common.common_base_test import BaseTestCase
from poms.system_messages.views import SystemMessageViewSet
from poms.iam.policy_generator import get_viewsets_from_all_apps


WRITE_ACCESS_ACTIONS = {
    "create",
    "update",
    "destroy",
    "delete",
    "bulk_create",
    "bulk_delete",
    "bulk_update",
    "bulk_restore",
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
    "unsubscribe",
    "update_master_user",
    "update_properties",
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
        from pprint import pprint

        all_actions = set()

        for viewset in get_viewsets_from_all_apps():
            for action in viewset.get_extra_actions():
                all_actions.add(action.__name__)

        pprint(sorted(all_actions))

        unknown_actions = {
            action
            for action in all_actions
            if action not in WRITE_ACCESS_ACTIONS and action not in READ_ACCESS_ACTIONS
        }
        pprint(sorted(unknown_actions))

        # for action in viewset.get_extra_actions():
        #     print(get_action_name_and_access_mode(action))
