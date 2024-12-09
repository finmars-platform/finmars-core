import logging
import os

from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.common.storage import get_storage
from poms.explorer.models import StorageObject
from poms.explorer.utils import (
    count_files,
    delete_all_file_objects,
    is_system_path,
    last_dir_name,
    make_dir_path,
    move_dir,
    move_file,
    path_is_file,
    sync_file,
    sync_storage_objects,
    unzip_file,
    rename_file,
    rename_dir,
    copy_dir,
    copy_file,
    update_or_create_file_and_parents,
)
from poms.users.models import MasterUser, Member

storage = get_storage()

_l = logging.getLogger("poms.explorer")
MAX_FILES = 10000


@finmars_task(name="explorer.tasks.move_directory_in_storage", bind=True)
def move_directory_in_storage(self, *args, **kwargs):
    celery_task = CeleryTask.objects.get(id=kwargs["task_id"])
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    validated_data = celery_task.options_object
    directories = []
    files_paths = []
    items = validated_data["paths"]
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
            for _ in move_dir(storage, directory, new_destination_directory, celery_task):
                pass

        for file_path in files_paths:
            file_name = os.path.basename(file_path)
            destination_file_path = str(os.path.join(destination_directory, file_name))
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


@finmars_task(name="explorer.tasks.sync_storage_with_database", bind=True)
def sync_storage_with_database(self, *args, **kwargs):
    task_name = "sync_storage_with_database"

    celery_task = CeleryTask.objects.get(id=kwargs["task_id"])
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    delete_all_file_objects()  # this action in future could be removed !

    space_code = kwargs["context"]["space_code"]
    storage_root = f"{space_code}/"

    total_files = count_files(storage, storage_root)
    _l.info(f"sync_files_with_database: there are total {total_files} files")

    celery_task.update_progress(
        {
            "current": 0,
            "total": total_files,
            "percent": 0,
            "description": f"{task_name} starting ...",
        }
    )

    dirs, files = storage.listdir(storage_root)

    root_obj, _ = StorageObject.objects.get_or_create(
        path=make_dir_path(storage_root),
        parent=None,
    )

    _l.info(
        f"sync_files_with_database: storage_root {storage_root} "
        f"has {dirs} dirs, {len(files)}/{total_files} files"
    )

    try:
        for directory in dirs:
            if is_system_path(directory):
                continue

            directory_path = os.path.join(storage_root, directory)
            directory_obj, _ = StorageObject.objects.get_or_create(
                path=make_dir_path(directory_path),
                parent=root_obj,
            )
            sync_storage_objects(storage, directory_obj)

        for file_name in files:
            if is_system_path(file_name):
                continue
            file_path = os.path.join(storage_root, file_name)
            sync_file(storage, file_path, root_obj)

    except Exception as e:
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.verbose_result = f"failed, due to {repr(e)}"
        celery_task.save()
        _l.error(f"sync_files_with_database: failed due to {repr(e)}")
        return

    celery_task.update_progress(
        {
            "current": total_files,
            "total": total_files,
            "percent": 100,
            "description": f"{task_name} finished",
        }
    )

    celery_task.status = CeleryTask.STATUS_DONE
    celery_task.verbose_result = f"synced {total_files} files"
    celery_task.save()


@finmars_task(name="explorer.tasks.rename_directory_in_storage", bind=True)
def rename_directory_in_storage(self, *args, **kwargs):
    celery_task = CeleryTask.objects.get(id=kwargs["task_id"])
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    validated_data = celery_task.options_object
    path = validated_data["path"]
    new_name = validated_data["new_name"]

    is_file = path_is_file(storage, path)
    if is_file:
        total_items = 1
    else:
        dirs, files = storage.listdir(path)
        total_items = len(dirs + files)

    _l.info(f"rename_directory_in_storage: rename {path} to new name {new_name}")
    celery_task.update_progress(
        {
            "current": 0,
            "total": total_items,
            "percent": 0,
            "description": "rename_directory_in_storage starting ...",
        }
    )

    if is_file:
        destination_file_path =  os.path.join(os.path.dirname(path), new_name)
        rename_file(storage, path, str(destination_file_path))
    else:
        destination_dir_path = os.path.join(os.path.dirname(os.path.normpath(path)), new_name)
        for _ in rename_dir(storage, path, str(destination_dir_path), celery_task):
            pass

    celery_task.update_progress(
        {
            "current": total_items,
            "total": total_items,
            "percent": 100,
            "description": "rename_directory_in_storage finished",
        }
    )

    celery_task.status = CeleryTask.STATUS_DONE
    celery_task.verbose_result = "renamed file"
    celery_task.save()


@finmars_task(name="explorer.tasks.copy_directory_in_storage", bind=True)
def copy_directory_in_storage(self, *args, **kwargs):
    celery_task = CeleryTask.objects.get(id=kwargs["task_id"])
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    validated_data = celery_task.options_object

    directories = []
    files_paths = []
    items = validated_data["paths"]
    total_items = len(items)
    for item in items:
        if path_is_file(storage, item):
            files_paths.append(item)
        else:
            directories.append(item)

    destination_directory = validated_data["target_directory_path"]

    _l.info(
        f"copy_directory_in_storage: copy {len(directories)} dirs, {len(files_paths)} "
        f"files, total {total_items} items"
    )
    celery_task.update_progress(
        {
            "current": 0,
            "total": total_items,
            "percent": 0,
            "description": "copy_directory_in_storage starting ...",
        }
    )

    for directory in directories:
        last_dir = last_dir_name(directory)
        new_destination_directory = os.path.join(destination_directory, last_dir)
        for _ in copy_dir(storage, directory, new_destination_directory, celery_task):
            pass

    for file_path in files_paths:
        file_name = os.path.basename(file_path)
        destination_file_path = str(os.path.join(destination_directory, file_name))
        copy_file(storage, file_path, destination_file_path)

    celery_task.update_progress(
        {
            "current": total_items,
            "total": total_items,
            "percent": 100,
            "description": "copy_directory_in_storage finished",
        }
    )

    celery_task.status = CeleryTask.STATUS_DONE
    celery_task.verbose_result = f"copied {total_items} items"
    celery_task.save()


@finmars_task(name="explorer.tasks.update_create_path_in_storage", bind=True)
def update_create_path_in_storage(self, *args, **kwargs):
    celery_task = CeleryTask.objects.get(id=kwargs["task_id"])
    path = celery_task.options_object["path"]
    size = celery_task.options_object["size"]
    try:
        update_or_create_file_and_parents(path, size)
    except Exception as e:
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.verbose_result = f"failed to update/create {path} due to {repr(e)}"
    else:
        celery_task.status = CeleryTask.STATUS_DONE

    celery_task.save()


def start_update_create_path_in_storage(path: str, size: int):
    celery_task = CeleryTask.objects.create(
        master_user=MasterUser.objects.first(),
        member=Member.objects.first(),
        verbose_name="Create StorageObject(s)",
        type="update_create_path_in_storage",
        status=CeleryTask.STATUS_PENDING,
        options_object={
            "path": path,
            "size": size,
        },
    )
    update_create_path_in_storage.apply_async(kwargs=dict(task_id=celery_task.id))
