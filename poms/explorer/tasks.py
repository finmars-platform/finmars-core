import logging
import os

from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.common.storage import get_storage
from poms.explorer.utils import (
    join_path,
    last_dir_name,
    move_dir,
    move_file,
    path_is_file,
)
from poms.system_messages.handlers import send_system_message
from poms.users.models import MasterUser

storage = get_storage()

_l = logging.getLogger("poms.explorer")


@finmars_task(name="explorer.tasks.move_directory_in_storage", bind=True)
def move_directory_in_storage(self, task_id, *args, **kwargs):
    celery_task = CeleryTask.objects.get(id=task_id)
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    validated_data = celery_task.options
    directories = []
    files_paths = []
    for item in validated_data["items"]:
        if path_is_file(storage, item):
            files_paths.append(item)
        else:
            directories.append(item)

    destination_directory = validated_data["target_directory_path"]

    _l.info(
        f"move_directory_in_storage: move {len(directories)} directories & {len(files_paths)} files"
    )

    for directory in directories:
        last_dir = last_dir_name(directory)
        new_destination_directory = os.path.join(destination_directory, last_dir)
        move_dir(storage, directory, new_destination_directory)

    for file_path in files_paths:
        file_name = os.path.basename(file_path)
        destination_file_path = os.path.join(destination_directory, file_name)
        move_file(storage, file_path, destination_file_path)
