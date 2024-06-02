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
    for item in validated_data["items"]:
        if path_is_file(storage, item):
            files_paths.append(item)
        else:
            directories.append(item)

    destination_directory = validated_data["target_directory_path"]
    total_files = count_files(storage, destination_directory)
    if total_files > MAX_FILES:
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.verbose_result = (
            f"number of files to be moved {total_files} > max allowed {MAX_FILES}"
        )
        celery_task.save()
        return

    _l.info(
        f"move_directory_in_storage: move {len(directories)} directories & {len(files_paths)} files"
    )
    celery_task.update_progress(
        {
            "current": 0,
            "total": total_files,
            "percent": 0,
            "description": "move_directory_in_storage starting ...",
        }
    )

    for directory in directories:
        last_dir = last_dir_name(directory)
        new_destination_directory = os.path.join(destination_directory, last_dir)
        move_dir(storage, directory, new_destination_directory, celery_task)

    for file_path in files_paths:
        file_name = os.path.basename(file_path)
        destination_file_path = os.path.join(destination_directory, file_name)
        move_file(storage, file_path, destination_file_path)

    celery_task.update_progress(
        {
            "current": total_files,
            "total": total_files,
            "percent": 100,
            "description": "move_directory_in_storage finished",
        }
    )

    celery_task.status = CeleryTask.STATUS_DONE
    celery_task.verbose_result = f"moved {total_files} files"
    celery_task.save()
