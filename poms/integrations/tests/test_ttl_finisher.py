import time
from unittest import mock

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.integrations.tasks import ttl_finisher


class TtlFinisherTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

    def create_task(self, name: str, func: str):
        return CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            verbose_name=name,
            function_name=func,
            type="import_from_database",
            status=CeleryTask.STATUS_PENDING,
            result="{}",
        )

    @BaseTestCase.cases(
        ("1_sec", 1),
        ("3_sec", 3),
        ("5_sec", 5),
    )
    def test__task_id(self, ttl: int):
        task = self.create_task(name="test", func="ttl_finisher")

        with mock.patch("poms_app.settings.CELERY_ALWAYS_EAGER", True, create=True):
            ttl_finisher.apply_async(kwargs={"task_id": task.id}, countdown=ttl)
            time.sleep(ttl + 1)
            print(f"test ended after {ttl+1} secs")
            task.refresh_from_db()
            self.assertEqual(task.status, CeleryTask.STATUS_TIMEOUT)
