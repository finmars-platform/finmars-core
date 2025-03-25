from poms.celery_tasks import finmars_task
from poms.common.common_base_test import BaseTestCase
from poms_app.celery import get_celery_task_names


class CeleryTaskTests(BaseTestCase):

    def test__fake_task(self):
        # Register a fake task
        @finmars_task(name="test_task.fake_task")
        def fake_task():
            pass

        task_names = get_celery_task_names()

        self.assertIsInstance(task_names, list)
        self.assertIn("test_task.fake_task", task_names)

    @BaseTestCase.cases(
        ("1", "configuration.import_configuration"),
        ("2", "csv_import.simple_import"),
        ("3", "explorer.tasks.move_directory_in_storage"),
        ("4", "file_reports.clear_old_file_reports"),
        ("5", "instruments.calculate_prices_accrued_price"),
    )
    def test__existing_tasks(self, task_name):

        task_names = set(get_celery_task_names())

        self.assertIn(task_name, task_names)
