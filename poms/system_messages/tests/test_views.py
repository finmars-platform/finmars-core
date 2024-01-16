from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.system_messages.models import SystemMessage, SystemMessageMember

API_URL = (
    f"/{settings.BASE_API_URL}/api/v1/system-messages/message/?"
    f"page_size=100&created_after=2023-11-6&action_status=2,3&type=2,3"
)
REQUEST_PARAMS = {
    "page_size": 100,
    "created_after": "2023-11-06",
    "action_status": "2,3",
    "type": "2,3",
}


class MemberViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = API_URL

    def create_system_message(self, title: str) -> SystemMessage:
        system_message = SystemMessage.objects.create(
            master_user=self.master_user,
            type=SystemMessage.TYPE_ERROR,
            action_status=SystemMessage.ACTION_STATUS_REQUIRED,
            title=title,
            description=self.random_string(),
        )
        SystemMessageMember.objects.create(
            system_message=system_message,
            member=self.member,
        )
        return system_message

    def test__check_api_url(self):
        response = self.client.get(path=self.url, data=REQUEST_PARAMS)
        self.assertEqual(response.status_code, 200, response.content)

    @BaseTestCase.cases(
        ("workflow", "workflow"),
        ("Workflow_failed.", "Workflow_failed."),
        ("No_WorkFlow", "No_WorkFlow"),
        ("WORKFLOW_IS_BIG", "WORKFLOW_IS_BIG"),
    )
    def test__list_workflow_excluded(self, title):
        self.create_system_message(title)
        self.create_system_message("Normal flow")

        self.assertEqual(SystemMessage.objects.all().count(), 2)

        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(response_json["count"], 1)

    @BaseTestCase.cases(
        ("workflow", "workflow"),
        ("Workflow_failed.", "Workflow_failed."),
        ("No_WorkFlow", "No_WorkFlow"),
        ("WORKFLOW_IS_BIG", "WORKFLOW_IS_BIG"),
    )
    def test__list_workflow_all_excluded(self, title):
        self.create_system_message(title)
        self.create_system_message(title)

        self.assertEqual(SystemMessage.objects.all().count(), 2)

        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(response_json["count"], 0)

    @BaseTestCase.cases(
        ("workflo-w", "workflo-w"),
        ("Worflow_failed.", "Worflow_failed."),
        ("No_Worklow", "No_Worklow"),
        ("WORKFLO_IS_BIG", "WORKFLO_IS_BIG"),
    )
    def test__list_no_workflow(self, title):
        self.create_system_message(title)
        self.create_system_message(title)

        self.assertEqual(SystemMessage.objects.all().count(), 2)

        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(response_json["count"], 2)
