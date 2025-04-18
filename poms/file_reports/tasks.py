import logging
from datetime import timedelta

from django.utils.timezone import now

from poms.celery_tasks import finmars_task
from poms.file_reports.models import FileReport

_l = logging.getLogger("poms.file_reports")


@finmars_task(name="file_reports.clear_old_file_reports", bind=True)
def clear_old_file_reports(self, *args, **kwargs):
    ten_days_ago = now() - timedelta(days=10)
    deleted_count, _ = FileReport.objects.filter(created_at__lt=ten_days_ago).delete()

    _l.debug(f"clear_old_file_reports: delete {deleted_count} records")
