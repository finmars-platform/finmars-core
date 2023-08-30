from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now

from django_celery_beat.models import CrontabSchedule, PeriodicTask

from poms.common.common_base_test import BaseTestCase, change_created_time
from poms.history.models import HistoricalRecord
from poms.history.tasks import clear_old_journal_records
from poms.transactions.models import Transaction
from poms.users.models import MasterUser

TEST_AMOUNT = 50


class CalculateDailySumTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

        new_time = now() - timedelta(days=100)
        for _ in range(TEST_AMOUNT):  # create historical records
            record = HistoricalRecord.objects.create(
                master_user=MasterUser.objects.first(),
                user_code=self.random_string(),
                action=HistoricalRecord.ACTION_CREATE,
                content_type=ContentType.objects.get_for_model(Transaction),
            )
            change_created_time(record, new_time)

    def test__all_records_deleted(self):
        self.assertEqual(HistoricalRecord.objects.count(), TEST_AMOUNT)

        clear_old_journal_records()

        self.assertEqual(HistoricalRecord.objects.count(), 0)

    def test__periodic_task_created(self):
        crontabs = CrontabSchedule.objects.all()
        self.assertEqual(crontabs.count(), 4)

        periodic_tasks = PeriodicTask.objects.all()
        self.assertEqual(periodic_tasks.count(), 1)

        task = periodic_tasks.filter(id=6).first()
        self.assertEqual(task.name, "SYSTEM: Clean Old Historical Records")
