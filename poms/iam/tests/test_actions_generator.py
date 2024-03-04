from collections import namedtuple
from typing import Callable

from poms.common.common_base_test import BaseTestCase
from poms.iam.policy_generator import get_viewsets_from_all_apps
from poms.iam.all_actions_names import (
    ALL_ACTIONS,
    READ_ACCESS,
    FULL_ACCESS,
)

READ_MODE = "read"
WRITE_MODE = "write"

ActionMode = namedtuple("ActionMode", ["name", "mode"])


def get_action_name_and_access_mode(action: Callable) -> ActionMode:
    action_name = action.__name__
    if action_name in FULL_ACCESS:
        return ActionMode(action_name, WRITE_MODE)
    elif action_name in READ_ACCESS:
        return ActionMode(action_name, READ_MODE)
    else:
        raise RuntimeError(f"Unknown viewset action {action_name}")


class ActionHandlingTest(BaseTestCase):
    databases = "__all__"

    def test_actions_handling(self):
        from pprint import pprint

        self.assertEqual(FULL_ACCESS.intersection(READ_ACCESS), set())

        all_actions = set()
        for viewset in get_viewsets_from_all_apps():
            for action in viewset.get_extra_actions():
                all_actions.add(action.__name__)

        self.assertEqual(all_actions, ALL_ACTIONS)

        unknown_actions = {
            action
            for action in all_actions
            if action not in FULL_ACCESS and action not in READ_ACCESS
        }
        self.assertEqual(unknown_actions, set())

        unknown_actions = FULL_ACCESS.union(READ_ACCESS).difference(all_actions)
        pprint(sorted(unknown_actions))
