import logging

from celery import shared_task
from django.utils.timezone import now

from poms.celery_tasks import finmars_task
from poms.file_reports.models import FileReport

_l = logging.getLogger('poms.file_reports')


@finmars_task(name='file_reports.clear_old_file_reports', bind=True)
def clear_old_file_reports(self, ):
    _l.debug("File Reports: clear_old_file_reports")

    today = now()

    ids_to_delete = []

    items = FileReport.objects.all()

    for item in items:

        diff = today - item.created_at

        if diff.days > 10:
            ids_to_delete.append(item.id)

    if len(ids_to_delete):
        FileReport.objects.filter(id__in=ids_to_delete).delete()

    _l.debug("File Reports deletes %s" % len(ids_to_delete))
