from unittest import mock

from django.contrib.contenttypes.models import ContentType

from poms.celery_tasks.models import CeleryTask
from poms.celery_tasks.tasks import bulk_restore
from poms.common.common_base_test import BaseTestCase
from poms.transactions.models import TransactionType


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

        bulk_restore(
            task_id=self.celery_task.id,
            kwargs={
                "context": {
                    "realm_code": None,
                    "space_code": self.master_user.space_code,
                }
            },
        )

        self.transaction_type.refresh_from_db()
        self.assertFalse(self.transaction_type.is_deleted)

    @mock.patch("poms.celery_tasks.models.CeleryTask.update_progress")
    def test__complex_transaction_bulk_restore_handle_exception(self, update_progress):
        update_progress.side_effect = [None, ZeroDivisionError]

        self.assertEqual(self.celery_task.status, CeleryTask.STATUS_INIT)

        with self.assertRaises(RuntimeError):
            bulk_restore(
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
