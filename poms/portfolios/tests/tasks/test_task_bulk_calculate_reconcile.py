from unittest import mock

from django.conf import settings

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BIG, SMALL, BaseTestCase
from poms.common.exceptions import FinmarsBaseException
from poms.portfolios.models import PortfolioReconcileGroup, PortfolioReconcileHistory
from poms.portfolios.tasks import bulk_calculate_reconcile_history

DATE = settings.API_DATE_FORMAT


class CalculateReconcileHistoryTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.portfolio_1 = self.db_data.portfolios[BIG]
        self.portfolio_2 = self.db_data.portfolios[SMALL]
        self.reconcile_group = self.create_reconcile_group()

    def create_reconcile_group(self) -> PortfolioReconcileGroup:
        return PortfolioReconcileGroup.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            name=self.random_string(),
            params={
                "precision": 1,
                "round_digits": 2,
                "only_errors": False,
                "report_ttl": 90,
                "notifications": {},
            },
        )

    def create_celery_task(self, options=None) -> CeleryTask:
        self.celery_task = CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            verbose_name="Bulk Calculate Portfolio Reconcile History",
            type="bulk_calculate_reconcile_history",
            status=CeleryTask.STATUS_INIT,
        )
        self.celery_task.options_object = options
        self.celery_task.save()

        return self.celery_task

    def test__invalid_celery_task(self):
        with self.assertRaises(FinmarsBaseException):
            bulk_calculate_reconcile_history(task_id=self.random_int())

    @mock.patch("poms.portfolios.tasks.send_system_message")
    def test__no_options_in_celery_task(self, system_message):
        celery_task = self.create_celery_task()

        bulk_calculate_reconcile_history(task_id=celery_task.id)

        celery_task.refresh_from_db()
        self.assertEqual(celery_task.status, CeleryTask.STATUS_ERROR)
        system_message.assert_called_once()

    @mock.patch("poms.portfolios.tasks.send_system_message")
    def test__invalid_group_user_code(self, system_message):
        options = {
            "master_user": self.master_user,
            "member": self.member,
            "dates": [self.yesterday().strftime(DATE), self.today().strftime(DATE)],
            "reconcile_groups": [self.random_string()],
        }
        celery_task = self.create_celery_task(options=options)

        bulk_calculate_reconcile_history(task_id=celery_task.id)

        celery_task.refresh_from_db()
        self.assertEqual(celery_task.status, CeleryTask.STATUS_ERROR)
        system_message.assert_called_once()

    @mock.patch("poms.portfolios.models.PortfolioReconcileHistory.calculate")
    def test__valid_task(self, calculate):
        self.assertEqual(PortfolioReconcileHistory.objects.count(), 0)

        options = {
            "master_user": self.master_user,
            "member": self.member,
            "dates": [self.yesterday().strftime(DATE), self.today().strftime(DATE)],
            "reconcile_groups": [self.reconcile_group.user_code],
        }
        celery_task = self.create_celery_task(options=options)

        bulk_calculate_reconcile_history(task_id=celery_task.id)

        celery_task.refresh_from_db()
        self.assertEqual(
            celery_task.status, CeleryTask.STATUS_DONE, celery_task.error_message
        )

        self.assertEqual(calculate.call_count, 2)  # once per date

        self.assertEqual(PortfolioReconcileHistory.objects.count(), 2)

    @mock.patch("poms.celery_tasks.models.CeleryTask.update_progress")
    @mock.patch("poms.portfolios.models.PortfolioReconcileHistory.calculate")
    def test__calculation_failed(self, calculate, update_progress):
        options = {
            "master_user": self.master_user,
            "member": self.member,
            "dates": [self.yesterday().strftime(DATE), self.today().strftime(DATE)],
            "reconcile_groups": [self.reconcile_group.user_code],
        }
        celery_task = self.create_celery_task(options=options)
        calculate.side_effect = FinmarsBaseException(error_key="test", message="error")

        bulk_calculate_reconcile_history(task_id=celery_task.id)

        celery_task.refresh_from_db()
        self.assertEqual(
            celery_task.status, CeleryTask.STATUS_ERROR, celery_task.error_message
        )

        messages = celery_task.error_message.split("\n")
        self.assertEqual(len(messages), 2)

        for msg in messages:
            self.assertIn(self.reconcile_group.user_code, msg)

        self.assertEqual(calculate.call_count, 2)  # once per date
        self.assertEqual(update_progress.call_count, 2)  # twice per reconcile_group

        self.assertEqual(PortfolioReconcileHistory.objects.count(), 2)
