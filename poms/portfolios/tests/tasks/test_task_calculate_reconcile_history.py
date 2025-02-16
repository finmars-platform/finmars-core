from unittest import mock

from django.conf import settings

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BIG, SMALL, BaseTestCase
from poms.common.exceptions import FinmarsBaseException
from poms.portfolios.models import PortfolioReconcileGroup, PortfolioReconcileHistory
from poms.portfolios.tasks import calculate_portfolio_reconcile_history

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
                "only_errors": False,
            },
        )

    def create_celery_task(self, options=None) -> CeleryTask:
        self.celery_task = CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            verbose_name="Calculate Portfolio Reconcile History",
            type="calculate_portfolio_reconcile_history",
            status=CeleryTask.STATUS_INIT,
        )
        self.celery_task.options_object = options
        self.celery_task.save()

        return self.celery_task

    def test__invalid_celery_task(self):
        with self.assertRaises(FinmarsBaseException):
            calculate_portfolio_reconcile_history(task_id=self.random_int())

    @mock.patch("poms.portfolios.tasks.send_system_message")
    def test__no_options_in_celery_task(self, system_message):
        celery_task = self.create_celery_task()

        calculate_portfolio_reconcile_history(task_id=celery_task.id)

        celery_task.refresh_from_db()
        self.assertEqual(celery_task.status, CeleryTask.STATUS_ERROR)
        system_message.assert_called_once()

    @mock.patch("poms.portfolios.tasks.send_system_message")
    def test__invalid_group_user_code(self, system_message):
        options = {
            "master_user": self.master_user,
            "member": self.member,
            "dates": [self.yesterday().strftime(DATE), self.today().strftime(DATE)],
            "portfolio_reconcile_group": self.random_string(),
        }
        celery_task = self.create_celery_task(options=options)

        calculate_portfolio_reconcile_history(task_id=celery_task.id)

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
            "portfolio_reconcile_group": self.reconcile_group.user_code,
        }
        celery_task = self.create_celery_task(options=options)

        calculate_portfolio_reconcile_history(task_id=celery_task.id)

        celery_task.refresh_from_db()
        self.assertEqual(celery_task.status, CeleryTask.STATUS_DONE, celery_task.error_message)

        self.assertEqual(calculate.call_count, 2)  # once per date

        self.assertEqual(PortfolioReconcileHistory.objects.count(), 2)
