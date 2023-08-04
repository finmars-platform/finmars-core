import json
import logging
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path
from typing import Iterable
from zipfile import ZIP_DEFLATED, ZipFile

from django.db import transaction
from django.utils.timezone import now
from django.conf import settings

from celery import shared_task

from poms.common.storage import get_storage
from poms.history.models import HistoricalRecord
from poms.history.utils import (
    get_local_path,
    get_storage_path,
    save_to_local_file,
    save_to_remote_storage,
    vacuum_table,
)
from poms.users.models import MasterUser

log = f"history_{Path(__name__).stem}.clear_old_journal_records:"
_l = logging.getLogger("poms.history")

DATE_FORMAT = "%Y-%m-%d"


def zip_records_to_buffer(filename: str, records: Iterable) -> bytes:
    dict_list = [record.as_dict for record in records]

    str_buffer = StringIO()
    json.dump(dict_list, str_buffer, ensure_ascii=False)

    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w", compression=ZIP_DEFLATED) as zip_file:
        zip_file.writestr(f"{filename}.json", str_buffer.getvalue())

    return zip_buffer.getvalue()


def delete_selected_records(records_to_delete: Iterable):
    ids = [record.id for record in records_to_delete]

    with transaction.atomic():
        records = HistoricalRecord.objects.filter(id__in=ids).select_for_update()
        records.delete()


@finmars_task(name="history_tasks.clear_old_journal_records")
def clear_old_journal_records():
    """
    Remove historical records older than ttl days, and save them into a file
    """

    _l.info(f"{log} started...")

    master = MasterUser.objects.first()
    ttl = MasterUser.JOURNAL_POLICY_DAYS.get(master.journal_storage_policy, 30)

    delete_time = now() - timedelta(days=ttl)
    date_from = delete_time.strftime(DATE_FORMAT)
    date_to = now().strftime(DATE_FORMAT)
    filename = f"{date_from}__{date_to}"

    records_to_delete = HistoricalRecord.objects.filter(created__lt=delete_time)

    count = records_to_delete.count()

    _l.info(f"{log} {count} records to be deleted")
    if not records_to_delete:
        _l.info(f"{log} aborted, nothing to delete")
        return

    buffer = zip_records_to_buffer(filename, records_to_delete)
    _l.info(f"{log} created buffer of {len(buffer)} size")

    try:
        if storage := get_storage():
            remote_path = get_storage_path(filename)
            save_to_remote_storage(storage, remote_path, buffer)
            _l.info(f"{log} records saved to remote storage {remote_path}")
        else:
            local_path = get_local_path(filename)
            save_to_local_file(local_path, buffer)
            _l.info(f"{log} records saved to local file {local_path}")
    except Exception as e:
        _l.error(f"{log} unable to save deleted records: {e}")
        return

    try:
        delete_selected_records(records_to_delete)
        vacuum_table(table=HistoricalRecord)
    except Exception as e:
        _l.error(f"{log} unable to delete records and vacuum the table: {e}")
    else:
        _l.info(f"{log} {count} deleted from history")
