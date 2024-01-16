# import time

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
# from poms.integrations.tasks import ttl_finisher


class TtlFinisherTest(BaseTestCase):
    databases = "__all__"

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
        ("2_sec", 2),
        ("3_sec", 3),
        ("5_sec", 5),
    )
    def test__task_id(self, ttl: int):
        task = CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            verbose_name="test",
            function_name="test",
            type="import_from_database",
            status=CeleryTask.STATUS_PENDING,
            result="{}",
        )
        task.refresh_from_db()

        # print(f"test started task_id={task.id} for {ttl} secs {time.time()}")
        #
        # ttl_finisher.apply_async(kwargs={"task_id": task.id}, countdown=ttl)
        # time.sleep(ttl + 2)
        #
        # print(f"test ended task_id={task.id} after {ttl} secs {time.time()}")
        #
        # task.refresh_from_db()
        # self.assertEqual(task.status, CeleryTask.STATUS_TIMEOUT)
