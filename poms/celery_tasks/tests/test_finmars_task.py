from poms.common.common_base_test import BaseTestCase

from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask

@finmars_task(name="task_wo_task_id")
def simple_task():
    print("task_wo_task_id is running")
    return


@finmars_task(name="complex_task")
def complex_task(task_id):
    print(f"task_with_task_id task_id={task_id} is running")
    return


class FinmarsTaskTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

    def test__run_simple_task(self):
        simple_task.before_start(self.random_string(), None, None)
        simple_task.update_progress(self.random_string())

        self.assertIsNone(simple_task.finmars_task)

    def test__run_task_with_task_id(self):
        celery_task = CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
        )

        self.assertIsNone(complex_task.finmars_task)

        complex_task.before_start(
            self.random_string(),
            None,
            {"task_id": celery_task.id},
        )

        self.assertIsNotNone(complex_task.finmars_task)

        message = self.random_string()
        complex_task.update_progress(message)

        celery_task.refresh_from_db()
        self.assertEqual(celery_task.status, CeleryTask.STATUS_PENDING)
        self.assertEqual(celery_task.progress, message)
