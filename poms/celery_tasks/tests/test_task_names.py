from unittest.mock import patch, MagicMock

from django.test import TestCase

from poms_app.celery import app  # Make sure to import your Celery app
from poms.celery_tasks import get_celery_task_names


class GetCeleryTaskNamesTest(TestCase):

    def test_print_all_names(self):
        task_names = get_celery_task_names()
        print(task_names)

    @patch("poms.celery_tasks.app.control.inspect")
    def test_get_celery_task_names_with_tasks(self, mock_inspect):
        mock_registered = MagicMock()
        mock_registered.registered.return_value = {
            "worker1": ["tasks.task1", "tasks.task2"],
            "worker2": ["tasks.task3", "tasks.task2"],
        }
        mock_inspect.return_value = mock_registered

        task_names = get_celery_task_names()

        self.assertEqual(sorted(task_names), sorted(["tasks.task1", "tasks.task2", "tasks.task3"]))

    @patch("poms.celery_tasks.app.control.inspect")
    def test_get_celery_task_names_no_tasks(self, mock_inspect):
        mock_registered = MagicMock()
        mock_registered.registered.return_value = None  # No registered tasks
        mock_inspect.return_value = mock_registered

        task_names = get_celery_task_names()

        self.assertEqual(task_names, [])

    @patch("poms.celery_tasks.app.control.inspect")
    def test_get_celery_task_names_empty_tasks(self, mock_inspect):
        mock_registered = MagicMock()
        mock_registered.registered.return_value = {}  # Empty registered tasks dict
        mock_inspect.return_value = mock_registered

        task_names = get_celery_task_names()

        self.assertEqual(task_names, [])
