import logging
import os

from poms.celery_tasks import finmars_task
from poms.common.storage import get_storage
from poms.explorer.utils import (
    count_files,
    last_dir_name,
    move_dir,
    move_file,
    path_is_file,
    sync_file_in_database,
    sync_files,
    unzip_file,
)

storage = get_storage()

_l = logging.getLogger("poms.explorer")
MAX_FILES = 10000


@finmars_task(name="explorer.tasks.move_directory_in_storage", bind=True)
def move_directory_in_storage(self, *args, **kwargs):
    from poms.celery_tasks.models import CeleryTask

    context = kwargs["context"]
    celery_task = CeleryTask.objects.get(id=kwargs["task_id"])
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    validated_data = celery_task.options_object
    directories = []
    files_paths = []
    items = validated_data["items"]
    total_items = len(items)
    for item in items:
        if path_is_file(storage, item):
            files_paths.append(item)
        else:
            directories.append(item)

    destination_directory = validated_data["target_directory_path"]

    _l.info(
        f"move_directory_in_storage: move {len(directories)} dirs, {len(files_paths)} "
        f"files, total {total_items} items"
    )
    celery_task.update_progress(
        {
            "current": 0,
            "total": total_items,
            "percent": 0,
            "description": "move_directory_in_storage starting ...",
        }
    )

    try:
        for directory in directories:
            last_dir = last_dir_name(directory)
            new_destination_directory = os.path.join(destination_directory, last_dir)
            move_dir(storage, directory, new_destination_directory, celery_task)

        for file_path in files_paths:
            file_name = os.path.basename(file_path)
            destination_file_path = os.path.join(destination_directory, file_name)
            move_file(storage, file_path, destination_file_path)

    except Exception as e:
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.verbose_result = f"failed, due to {repr(e)}"
        celery_task.save()
        return

    celery_task.update_progress(
        {
            "current": total_items,
            "total": total_items,
            "percent": 100,
            "description": "move_directory_in_storage finished",
        }
    )

    celery_task.status = CeleryTask.STATUS_DONE
    celery_task.verbose_result = f"moved {total_items} items"
    celery_task.save()


@finmars_task(name="explorer.tasks.unzip_file_in_storage", bind=True)
def unzip_file_in_storage(self, *args, **kwargs):
    from poms.celery_tasks.models import CeleryTask

    context = kwargs["context"]
    celery_task = CeleryTask.objects.get(id=kwargs["task_id"])
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    validated_data = celery_task.options_object
    zipped_file_path = validated_data["file_path"]
    destination_path = validated_data["target_directory_path"]

    _l.info(
        f"unzip_file_in_storage: file_path={zipped_file_path} "
        f"destination_path={destination_path}"
    )
    celery_task.update_progress(
        {
            "current": 0,
            "total": 1,
            "percent": 0,
            "description": "unzip_file_in_storage starting ...",
        }
    )

    try:
        unzip_file(storage, zipped_file_path, destination_path, celery_task)
    except Exception as e:
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.verbose_result = f"failed, due to {repr(e)}"
        celery_task.save()
        return

    celery_task.status = CeleryTask.STATUS_DONE
    celery_task.verbose_result = f"unzip {zipped_file_path} to {destination_path}"
    celery_task.save()


@finmars_task(name="explorer.tasks.sync_files_with_database", bind=True)
def sync_files_with_database(self, *args, **kwargs):
    from poms.celery_tasks.models import CeleryTask

    celery_task = CeleryTask.objects.get(id=kwargs["task_id"])
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    space_code = kwargs["context"]["space_code"]
    storage_root = f"{space_code}/"

    total_files = count_files(storage, storage_root)

    _l.info(f"sync_files_with_database: {total_files} files")
    celery_task.update_progress(
        {
            "current": 0,
            "total": total_files,
            "percent": 0,
            "description": "sync_files_with_database starting ...",
        }
    )

    dirs, files = storage.listdir(storage_root)

    try:
        for directory in dirs:
            sync_files(storage, directory)

        for file_path in files:
            sync_file_in_database(storage, file_path)

    except Exception as e:
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.verbose_result = f"failed, due to {repr(e)}"
        celery_task.save()
        return

    celery_task.update_progress(
        {
            "current": total_files,
            "total": total_files,
            "percent": 100,
            "description": "sync_files_with_database finished",
        }
    )

    celery_task.status = CeleryTask.STATUS_DONE
    celery_task.verbose_result = f"synced {total_files} items"
    celery_task.save()
