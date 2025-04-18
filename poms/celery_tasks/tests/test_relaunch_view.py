from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase


class CeleryTaskViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/tasks/task/"

        options = {"options": {"new_name": "t", "path": "space00000/yk/t1/"}}
        self.celery_task = CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            options_object=options,
            type="rename_directory_in_storage",
            verbose_name="Rename directory [Task-Test]",
        )

    def test__relaunch_without_options(self):
        options = {}
        completed_tasks = CeleryTask.objects.filter(type="rename_directory_in_storage")
        self.assertEqual(len(completed_tasks), 1)

        task_id = completed_tasks[0].pk
        relaunch_url = f"{self.url}{task_id}/relaunch/"
        response = self.client.post(path=relaunch_url, format="json", data=options)
        self.assertEqual(response.status_code, 200, response.content)

        completed_tasks = CeleryTask.objects.filter(type="rename_directory_in_storage")
        self.assertEqual(len(completed_tasks), 2)
        self.assertEqual(completed_tasks[0].options_object, completed_tasks[1].options_object)

    def test__relaunch_with_options(self):
        options = {"options": {"new_name": "t2", "path": "space00000/yk/t2/"}}
        completed_tasks = CeleryTask.objects.filter(type="rename_directory_in_storage")
        self.assertEqual(len(completed_tasks), 1)

        task_id = completed_tasks[0].pk
        relaunch_url = f"{self.url}{task_id}/relaunch/"
        response = self.client.post(path=relaunch_url, format="json", data=options)
        self.assertEqual(response.status_code, 200, response.content)

        completed_tasks = CeleryTask.objects.filter(type="rename_directory_in_storage")
        self.assertEqual(len(completed_tasks), 2)
        self.assertNotEqual(completed_tasks[0].options_object, completed_tasks[1].options_object)
