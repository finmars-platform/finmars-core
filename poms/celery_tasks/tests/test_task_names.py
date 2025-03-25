from django.test import TestCase
from poms_app.celery import app, get_celery_task_names
from poms.celery_tasks import finmars_task


class CeleryTaskTests(TestCase):
    def test_get_celery_task_names(self):
        # Register a test task (or use your real tasks)
        @finmars_task(name="test_task.fake_task")
        def fake_task():
            pass

        # Call the function
        task_names = get_celery_task_names()

        # Verify
        self.assertIsInstance(task_names, list)
        self.assertIn("test_task.fake_task", task_names)
