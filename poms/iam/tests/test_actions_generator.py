from poms.common.common_base_test import BaseTestCase
from poms.system_messages.views import SystemMessageViewSet


class ActionListTest(BaseTestCase):
    databases = "__all__"

    def test_actions_of_syste_message_viewset(self):
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

        actions = [action.__name__ for action in viewset.get_extra_actions()]

        self.assertEqual(actions, expected_list)
