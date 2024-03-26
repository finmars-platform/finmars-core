from unittest import mock, skip

from poms.common.common_base_test import BaseTestCase, BIG

from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.celery_tasks.tasks import bulk_delete, bulk_restore
from poms.transactions.models import Transaction, TransactionType
from django.contrib.contenttypes.models import ContentType


@finmars_task(name="task_wo_task_id")
def simple_task(*args, **kwargs):
    print("task_wo_task_id is running")
    return


@finmars_task(name="complex_task")
def complex_task(task_id, *args, **kwargs):
    print(f"task_with_task_id task_id={task_id} is running")
    return


# @skip("temporally")
class FinmarsTaskTestCase(BaseTestCase):
    databases = "__all__"

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

        bulk_delete(task_id=self.celery_task.id)

        self.complex_transaction.refresh_from_db()
        self.assertTrue(self.complex_transaction.is_deleted)

        self.assertIsNone(Transaction.objects.filter(pk=self.transaction.id).first())

    @mock.patch("poms.celery_tasks.models.CeleryTask.update_progress")
    def test__complex_transaction_bulk_delete_handle_exception(self, update_progress):
        self.assertEqual(self.celery_task.status, CeleryTask.STATUS_INIT)

        update_progress.side_effect = [None, RuntimeError]

        bulk_delete(task_id=self.celery_task.id)

        self.celery_task.refresh_from_db()

        self.assertEqual(self.celery_task.status, CeleryTask.STATUS_ERROR)


class BulkRestoreTestCase(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.transaction_type = TransactionType.objects.all().first()
        content_type = ContentType.objects.get_for_model(TransactionType)
        content_type_key = f"{content_type.app_label}.{content_type.model}"
        ids_list = [self.transaction_type.id]

        self.assertNotEqual(len(ids_list), 0)

        data = {"ids": ids_list}

        options_object = {"content_type": content_type_key, "ids": data["ids"]}

        self.celery_task = CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            options_object=options_object,
            verbose_name="Bulk Restore",
            type="bulk_restore",
        )
        self.transaction_type.fake_delete()

    def test__complex_transaction_bulk_restore_set_is_deleted_true(self):
        self.assertTrue(self.transaction_type.is_deleted)

        bulk_restore(task_id=self.celery_task.id)

        self.transaction_type.refresh_from_db()
        self.assertFalse(self.transaction_type.is_deleted)

    @mock.patch("poms.celery_tasks.models.CeleryTask.update_progress")
    def test__complex_transaction_bulk_delete_handle_exception(self, update_progress):
        update_progress.side_effect = [None, RuntimeError]

        self.assertEqual(self.celery_task.status, CeleryTask.STATUS_INIT)

        bulk_restore(task_id=self.celery_task.id)

        self.celery_task.refresh_from_db()

        self.assertEqual(self.celery_task.status, CeleryTask.STATUS_ERROR)
