from unittest import mock

from poms.celery_tasks.models import CeleryTask
from poms.celery_tasks.tasks import bulk_delete
from poms.common.common_base_test import BIG, BaseTestCase
from poms.transactions.models import Transaction


class BulkDeleteTestCase(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.portfolio = self.db_data.portfolios[BIG]
        self.complex_transaction, self.transaction = self.db_data.cash_in_transaction(
            self.portfolio
        )
        options_object = {
            "content_type": "transactions.complextransaction",
            "ids": [self.complex_transaction.id],
        }
        self.celery_task = CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            options_object=options_object,
            verbose_name="Bulk Delete",
            type="bulk_delete",
        )

    def test__complex_transaction_bulk_delete_set_is_deleted_true(self):
        self.assertFalse(self.complex_transaction.is_deleted)
        self.assertIsNotNone(self.transaction)

        bulk_delete(
            task_id=self.celery_task.id,
            kwargs={
                "context": {
                    "realm_code": None,
                    "space_code": self.master_user.space_code,
                }
            },
        )

        self.complex_transaction.refresh_from_db()
        self.assertTrue(self.complex_transaction.is_deleted)

        self.assertIsNone(Transaction.objects.filter(pk=self.transaction.id).first())

    @mock.patch("poms.celery_tasks.models.CeleryTask.update_progress")
    def test__complex_transaction_bulk_delete_handle_exception(self, update_progress):
        self.assertEqual(self.celery_task.status, CeleryTask.STATUS_INIT)

        update_progress.side_effect = [None, RuntimeError]

        bulk_delete(
            task_id=self.celery_task.id,
            kwargs={
                "context": {
                    "realm_code": None,
                    "space_code": self.master_user.space_code,
                }
            },
        )

        self.celery_task.refresh_from_db()

        self.assertEqual(self.celery_task.status, CeleryTask.STATUS_ERROR)
