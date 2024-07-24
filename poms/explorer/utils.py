import json
import logging
import os
import zipfile
from typing import Optional

from django.core.files.base import ContentFile
from django.http import HttpResponse

from poms.celery_tasks.models import CeleryTask
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import FinmarsFile

_l = logging.getLogger("poms.explorer")

CONTENT_TYPES = {
    ".html": "text/html",
    ".txt": "plain/text",
    ".js": "text/javascript",
    ".csv": "text/csv",
    ".json": "application/json",
    ".yml": "application/yaml",
    ".yaml": "application/yaml",
    ".py": "text/x-python",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/msword",
    ".css": "text/css",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def define_content_type(file_name: str) -> Optional[str]:
    return CONTENT_TYPES.get(os.path.splitext(file_name)[-1])


def join_path(space_code: str, path: Optional[str]) -> str:
    if path:
        return f"{space_code.rstrip('/')}/{path.lstrip('/')}"
    else:
        return f"{space_code.rstrip('/')}"


def remove_first_dir_from_path(path: str) -> str:
    return os.path.sep.join(path.split(os.path.sep)[1:])


def response_with_file(storage: FinmarsS3Storage, path: str) -> HttpResponse:
    try:
        with storage.open(path) as file:
            result = file.read()
            file_content_type = define_content_type(file.name)
            response = (
                HttpResponse(result, content_type=file_content_type)
                if file_content_type
                else HttpResponse(result)
            )
    except Exception as e:
        _l.error(f"get file resulted in {repr(e)}")
        data = {"error": repr(e)}
        response = HttpResponse(
            json.dumps(data),
            content_type="application/json",
            status=400,
            reason="Bad Request",
        )
    return response


# PROBABLY DEPRECATED
def sanitize_html(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for script in soup(["script", "style"]):  # Remove these tags
        script.extract()
    return str(soup)


def path_is_file(storage: FinmarsS3Storage, file_path: str) -> bool:
    """
    Check if the given path is a file in the storage.
    Args:
        storage (FinmarsS3Storage): The storage object to use.
        file_path (str): The path of the file to check.
    Returns:
        bool: True if the path is a file, False otherwise.
    """
    try:
        file_size = storage.size(file_path)
        _l.info(f"path_is_file: {file_path} size is {file_size}")
        return file_size > 0

    except Exception as e:
        _l.error(f"path_is_file check resulted in {repr(e)}")
        return False


TRUTHY_VALUES = {"true", "1", "yes"}


def check_is_true(value: str) -> bool:
    return bool(value and (value.lower() in TRUTHY_VALUES))


def last_dir_name(path: str) -> str:
    if not path:
        return path

    path = path.removesuffix("/")
    return f"{path.rsplit('/', 1)[-1]}/"


def move_file(storage: FinmarsS3Storage, source_file_path: str, destin_file_path: str):
    """
    Move a file from the source path to the destination path within the storage.

    Args:
        storage (Storage): The storage instance to use.
        source_file_path (str): The path of the source file.
        destin_file_path (str): The path of the destination file.
    Returns:
        None
    """
    file_name = os.path.basename(source_file_path)
    _l.info(
        f"move_file: move file {file_name} from {source_file_path} "
        f"to {destin_file_path}"
    )

    content = storage.open(source_file_path).read()
    _l.info(
        f"move_file: with content len={len(content)} "
        f"from {source_file_path} to {destin_file_path}"
    )

    storage.save(destin_file_path, ContentFile(content, name=file_name))
    _l.info(f"move_file: content saved to {destin_file_path}")

    storage.delete(source_file_path)
    _l.info(f"move_file: source file {source_file_path} deleted")


def move_dir(
    storage: FinmarsS3Storage,
    source_dir: str,
    destin_dir: str,
    celery_task: CeleryTask,
):
    """
    Move a directory and its contents recursively within the storage
    and update the celery task progress. Empty directories will not be moved/created
    in the storage!
    Args:
        storage (Storage): The storage instance to use.
        source_dir (str): The path of the source directory.
        destin_dir (str): The path of the destination directory.
        celery_task (CeleryTask): The celery task to update.
    Returns:
        None
    """
    _l.info(f"move_dir: move content of directory '{source_dir}' to '{destin_dir}'")

    dirs, files = storage.listdir(source_dir)

    for dir_name in dirs:
        s_dir = os.path.join(source_dir, dir_name)
        d_dir = os.path.join(destin_dir, dir_name)
        move_dir(storage, s_dir, d_dir, celery_task)

    for file_name in files:
        s_file = os.path.join(source_dir, file_name)
        d_file = os.path.join(destin_dir, file_name)
        move_file(storage, s_file, d_file)

    celery_task.refresh_from_db()
    progres_dict = celery_task.progress_object
    progres_dict["current"] += len(files)
    progres_dict["percent"] = int(progres_dict["current"] / progres_dict["total"] * 100)
    celery_task.update_progress(progres_dict)


def count_files(storage: FinmarsS3Storage, source_dir: str) -> int:
    """
    Recursively count the number of files in a directory and all its subdirectories
    Args:
        storage: The storage instance to use.
        source_dir: The path of the source directory.
    Returns:
        The total number of files in the directory and all its subdirectories.
    """

    def count_files_helper(dir_path: str) -> int:
        dirs, files = storage.listdir(dir_path)
        count = len(files)
        for subdir in dirs:
            count += count_files_helper(os.path.join(dir_path, subdir))
        return count
    start_dir = str(source_dir)
    _l.info(f"count_files: from directory {start_dir}")
    return count_files_helper(start_dir)


def unzip_file(
    storage: FinmarsS3Storage,
    zip_path: str,
    destination_folder: str,
    celery_task: CeleryTask,
):
    """
    Unzips a file from the given zip_path using the provided storage object.
    Args:
        celery_task: CeleryTask - The celery task to update progress.
        storage (FinmarsS3Storage): The storage object to use.
        zip_path (str): The path to the zip file to unzip.
        destination_folder (str): The folder where the contents of
                the zip file will be extracted.
    Returns:
        None
    """
    _l.info(f"unzip_file: zip_path {zip_path} destination_folder {destination_folder}")
    zip_archive = storage.open(zip_path)

    with zipfile.ZipFile(zip_archive) as s3_zip:
        file_names = s3_zip.namelist()
        _l.info(f"unzip_file: try to unzip files {file_names} from archive {zip_path}")
        celery_task.refresh_from_db()
        progress_dict = celery_task.progress_object
        progress_dict.update(
            {
                "current": 0,
                "total": len(file_names),
                "percent": 0,
                "description": "unzip_file_in_storage in progress",
            }
        )
        celery_task.update_progress(progress_dict)

        for file_name in file_names:
            if file_name.startswith("__") or file_name.startswith("._"):
                _l.info(f"unzip_file: skip system file {file_name}")
                continue

            progress_dict["current"] += 1
            progress_dict["percent"] = int(
                progress_dict["current"] / progress_dict["total"] * 100,
            )
            celery_task.update_progress(progress_dict)

            dest_file_path = os.path.join(destination_folder, file_name)
            with s3_zip.open(file_name) as zipped_file:
                content = zipped_file.read()
                storage.save(dest_file_path, ContentFile(content, name=file_name))
                _l.info(
                    f"unzip_file: save {file_name} of size {len(content)} "
                    f"type {type(content)} to {dest_file_path}"
                )

        progress_dict.update(
            {"description": "unzip_file_in_storage finished", "percent": 100}
        )
        celery_task.update_progress(progress_dict)


def sync_files(storage: FinmarsS3Storage, source_dir: str) -> int:
    """
    Recursively syncs files in a directory and all its subdirectories with database file
    objects.
    Args:
        storage: The storage instance to use.
        source_dir: The path of the source directory.
    Returns:
        The total number of files in the directory and all its subdirectories.
    """

    def sync_files_helper(dir_path: str) -> int:
        dirs, files = storage.listdir(dir_path)
        count = len(files)
        for file in files:
            sync_file_in_database(storage, file)
        for subdir in dirs:
            count += sync_files_helper(os.path.join(dir_path, subdir))
        return count

    start_dir = str(source_dir)  # to avoid source_dir modification
    _l.info(f"sync_files: from directory {start_dir}")
    return sync_files_helper(start_dir)


def sync_file_in_database(storage: FinmarsS3Storage, filepath: str):
    """
    Creates or updates file model in database for the given file path
    Args:
        storage: The storage instance to use
        filepath: path to the file in storage
    """

    path, name = os.path.split(filepath)
    size = storage.size(filepath)

    _, created = FinmarsFile.objects.update_or_create(
        name=name,
        path=path,
        defaults=dict(size=size),
    )

    _l.info(
        f"sync_file_in_database: {'created' if created else 'updated'} "
        f"for {filepath} with size {size}"
    )
