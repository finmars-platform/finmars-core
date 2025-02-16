from unittest import mock  # , skip

from django.conf import settings

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BIG, BaseTestCase, SMALL
from poms.portfolios.models import PortfolioReconcileGroup, PortfolioReconcileHistory
from poms.portfolios.tasks import calculate_portfolio_reconcile_history
from poms.common.exceptions import FinmarsBaseException



class CalculateReconcileHistoryTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.portfolio_1 = self.db_data.portfolios[BIG]
        self.portfolio_2 = self.db_data.portfolios[SMALL]
        self.group = self.create_reconcile_group()

    def create_reconcile_group(self) -> PortfolioReconcileGroup:
        return PortfolioReconcileGroup.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            name=self.random_string(),
            params={
                "precision": 1,
                "only_errors": False,
            }
        )

    def create_celery_task(self, options = None) -> CeleryTask:
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

    # @skip("temporally")
    def test__invalid_celery_task(self):
        with self.assertRaises(FinmarsBaseException):
            calculate_portfolio_reconcile_history(task_id=self.random_int())

    @mock.patch("poms.portfolios.tasks.send_system_message")
    def test__no_options_in_celery_task(self, system_message):
        celery_task = self.create_celery_task()

        with self.assertRaises(FinmarsBaseException):
            calculate_portfolio_reconcile_history(task_id=celery_task.id)

        celery_task.refresh_from_db()
        self.assertEqual(celery_task.status, CeleryTask.STATUS_ERROR)
        system_message.assert_called_once()

    # # @skip("temporally")
    # @mock.patch("poms.portfolios.tasks.send_system_message")
    # def test__invalid_portfolio_user_code(self, system_message):
    #     options = {
    #         "date_from": self.yesterday().strftime(settings.API_DATE_FORMAT),
    #         "date_to": self.today().strftime(settings.API_DATE_FORMAT),
    #         "portfolios": [self.random_string(5)]
    #     }
    #     celery_task = self.create_celery_task(options=options)
    #
    #     calculate_portfolio_register_price_history(task_id=celery_task.id)
    #
    #     celery_task.refresh_from_db()
    #     self.assertEqual(celery_task.status, CeleryTask.STATUS_DONE)
    #     self.assertEqual(system_message.call_count, 2)
    #
    # @mock.patch("poms.portfolios.tasks.send_system_message")
    # def test__valid_portfolio_user_code(self, system_message):
    #     self.create_portfolio_register()
    #     options = {
    #         "date_from": self.yesterday().strftime(settings.API_DATE_FORMAT),
    #         "date_to": self.today().strftime(settings.API_DATE_FORMAT),
    #         "portfolios": [self.user_code]
    #     }
    #     celery_task = self.create_celery_task(options=options)
    #
    #     calculate_portfolio_register_price_history(task_id=celery_task.id)
    #
    #     celery_task.refresh_from_db()
    #     self.assertEqual(celery_task.status, CeleryTask.STATUS_DONE)
    #     self.assertEqual(system_message.call_count, 2)
