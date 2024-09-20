from datetime import timedelta
from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now

from poms.common.common_base_test import BaseTestCase, change_created_time
from poms.history.models import HistoricalRecord
from poms.history.tasks import DAYS_30, clear_old_journal_records
from poms.transactions.models import Transaction
from poms.users.models import MasterUser

TEST_AMOUNT = 30


class CalculateDailySumTestCase(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.storage = mock.Mock()
        self.storage.save.return_value = None
        new_time = now() - timedelta(days=DAYS_30 + 1)
        for _ in range(TEST_AMOUNT):  # create historical records
            record = HistoricalRecord.objects.create(
                master_user=MasterUser.objects.first(),
                user_code=self.random_string(),
                action=HistoricalRecord.ACTION_CREATE,
                content_type=ContentType.objects.get_for_model(Transaction),
            )
            change_created_time(record, new_time)

    @mock.patch("poms.history.tasks.get_storage")
    def test__all_records_deleted(self, get_storage_mock):
        get_storage_mock.return_value = self.storage
        self.assertEqual(HistoricalRecord.objects.count(), TEST_AMOUNT)

        clear_old_journal_records()

        self.assertEqual(HistoricalRecord.objects.count(), 0)
