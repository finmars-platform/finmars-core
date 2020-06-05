
from celery import shared_task

import logging

from poms.file_reports.models import FileReport

from django.utils.timezone import now


_l = logging.getLogger('poms.file_reports')

@shared_task(name='file_reports.clear_old_file_reports', bind=True, ignore_result=True)
def clear_old_file_reports(self,):

    _l.info("File Reports: clear_old_file_reports")

    today = now()

    ids_to_delete = []

    items = FileReport.objects.all()

    for item in items:

        diff = today - item.created_at

        if diff.days > 10:
            ids_to_delete.append(item.id)

    if len(ids_to_delete):
        FileReport.objects.filter(id__in=ids_to_delete).delete()

    _l.info("File Reports deletes %s" % len(ids_to_delete))
