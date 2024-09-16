from django.apps import apps

from poms.common.common_base_test import BaseTestCase
from poms.iam.all_actions_names import (
    ALL_EXTRA_ACTIONS,
    FULL_ACCESS_ACTIONS,
    READ_ACCESS_ACTIONS,
)
from poms.iam.models import AccessPolicy
from poms.iam.policy_generator import (
    generate_full_access_policies_for_viewsets,
    generate_readonly_access_policies_for_viewsets,
    get_viewsets_from_all_apps,
    get_viewsets_from_any_app,
)


class ActionHandlingTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.all_actions = set()
        self.all_actions_names = set()
        self.all_viewsets = get_viewsets_from_all_apps()
        for viewset in self.all_viewsets:
            for action in viewset.get_extra_actions():
                self.all_actions.add(action)
                self.all_actions_names.add(action.__name__)

    def test__validate_actions_settings(self):
        self.assertEqual(FULL_ACCESS_ACTIONS.intersection(READ_ACCESS_ACTIONS), set())

        self.assertEqual(self.all_actions_names, ALL_EXTRA_ACTIONS)

        unknown_actions = {
            action
            for action in self.all_actions_names
            if action not in FULL_ACCESS_ACTIONS and action not in READ_ACCESS_ACTIONS
        }
        self.assertEqual(unknown_actions, set())

        unknown_actions = FULL_ACCESS_ACTIONS.union(READ_ACCESS_ACTIONS).difference(
            self.all_actions_names
        )
        self.assertEqual(unknown_actions, set())

    def test__get_views_from_all_apps(self):
        all_viewsets = []

        for app_config in apps.get_app_configs():
            if not app_config.name.startswith("poms"):
                # Skip Django's built-in apps
                continue

            app_viewsets = get_viewsets_from_any_app(app_config.label)
            all_viewsets.extend(app_viewsets)

        all_actions_names = set()
        for viewset in all_viewsets:
            for action in viewset.get_extra_actions():
                all_actions_names.add(action.__name__)

        new_actions = all_actions_names.difference(self.all_actions_names)
        self.assertEqual(len(new_actions), 0)

    def test__generate_full_access_policies_for_viewsets(self):
        all_access_policies = AccessPolicy.objects.all()
        self.assertEqual(all_access_policies.count(), 0)

        generate_full_access_policies_for_viewsets(self.all_viewsets)

        for policy in all_access_policies:
            self._check_policy(policy, "-full", "Full Access")

    def test__generate_readonly_access_policies_for_viewsets(self):
        all_access_policies = AccessPolicy.objects.all()
        self.assertEqual(all_access_policies.count(), 0)

        generate_readonly_access_policies_for_viewsets(self.all_viewsets)

        for policy in all_access_policies:
            self._check_policy(policy, "-readonly", "Readonly Access")

    def _check_policy(self, policy, arg1, arg2):
        self.assertEqual(policy.owner.username, "finmars_bot")
        self.assertTrue(f"local.poms.{self.space_code}" in policy.user_code)
        self.assertTrue(arg1 in policy.user_code)
        self.assertTrue(arg2 in policy.name)
