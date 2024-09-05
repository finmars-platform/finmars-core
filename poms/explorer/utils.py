import json
import logging
import os
import zipfile
from pathlib import Path
from typing import Optional

from django.core.files.base import ContentFile
from django.http import HttpResponse

from poms.celery_tasks.models import CeleryTask
from poms.common.storage import FinmarsS3Storage

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
SYSTEM_PATHS = {".hello-world", ".system", ".init"}
TRUTHY_VALUES = {"true", "1", "yes"}


def is_true_value(value: str) -> bool:
    return bool(value and (value.lower() in TRUTHY_VALUES))


def is_system_path(path: str) -> bool:
    return path.startswith(".")


def define_content_type(file_name: str) -> Optional[str]:
    return CONTENT_TYPES.get(os.path.splitext(file_name)[-1])


def join_path(space_code: str, path: Optional[str]) -> str:
    if path:
        return f"{space_code.rstrip('/')}/{path.lstrip('/')}"
    else:
        return f"{space_code.rstrip('/')}"


def make_dir_path(path: str) -> str:
    from poms.explorer.models import DIR_SUFFIX

    return f"{path.rstrip('/')}{DIR_SUFFIX}"


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

    start_dir = source_dir
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


def sync_storage_objects(storage: FinmarsS3Storage, start_directory) -> int:
    """
    Recursively syncs files/directories in the root directory and
    all its subdirectories with database file/directory objects.
    Args:
        storage: The storage instance to use.
        start_directory: The directory from which to start syncing.
    Returns:
        The total number of files in the start directory and all its subdirectories.
    """

    def sync_files_helper(directory) -> int:
        from poms.explorer.models import FinmarsDirectory

        directory_path = directory.path.removesuffix("*")

        dir_names, file_names = storage.listdir(directory_path)

        _l.info(
            f"sync_files: directory_path {directory.path} "
            f"try to sync {len(file_names)} files"
        )

        count = len(file_names)
        for file in file_names:
            if is_system_path(file):
                continue

            sync_file(storage, str(os.path.join(directory_path, file)), directory)

        for subdir in dir_names:
            if is_system_path(subdir):
                continue

            sub_directory, created = FinmarsDirectory.objects.get_or_create(
                path=os.path.join(directory_path, subdir), parent=directory
            )
            count += sync_files_helper(sub_directory)

        return count

    return sync_files_helper(start_directory)


def sync_file(storage: FinmarsS3Storage, filepath: str, directory):
    """
    Creates or updates file model in database for the given file path in the storage
    Args:
        storage: The storage instance to use
        filepath: path to the file in storage
        directory: directory to which the file belongs
    """
    from poms.explorer.models import FinmarsFile

    _l.info(f"sync_file: filepath {filepath} directory {directory.path}")
    FinmarsFile.objects.update_or_create(
        path=filepath,
        parent=directory,
        defaults=dict(size=storage.size(filepath)),
    )


def delete_all_file_objects():
    from poms.explorer.models import FinmarsFile

    FinmarsFile.objects.all().delete()
    _l.warning("deleted all file objects from database!")


def split_path(path: str) -> list[str]:
    """
    Splits a given path string into a list of directory names,
    excluding the last element (the file name).
    Args:
        path (str): The path string to be split, should not start with '/'
    Returns:
        list[str]: A list of directory names, excluding the last element (the file name).

    Example:
        split_path("/path/to/file.txt")
        ['path', 'path/to']
    """
    dir_list = list(Path(path).parts)[:-1]
    return ["/".join(dir_list[: i + 1]) for i in range(len(dir_list))]


def update_or_create_file_and_parents(path: str, size: int) -> str:
    """
    Creates or updates a file model and all its parent directories in the database
    Args:
        path (str): The path to the file in the storage
        size (int): The size of the file in bytes

    Returns:
        str: The path of the newly created or updated file model
    """
    from poms.explorer.models import (
        DIR_SUFFIX,
        FinmarsDirectory,
        FinmarsFile,
    )

    _l.info(f"update_or_create_file_and_parents: starts with {path}")

    path = path.removeprefix("/")
    if not path:
        raise RuntimeError(f"update_or_create_file_and_parents: empty path '{path}'")

    parent = None
    for dir_path in split_path(path):
        dir_obj, created = FinmarsDirectory.objects.update_or_create(
            path=f"{dir_path}{DIR_SUFFIX}",
            defaults={"parent": parent},
        )
        if created:
            _l.info(
                f"update_or_create_file_and_parents: created directory {dir_obj.path}"
            )
        parent = dir_obj

    if parent is None:
        raise RuntimeError(
            f"update_or_create_file_and_parents: no parent path '{path}'"
        )

    file, created = FinmarsFile.objects.update_or_create(
        path=path,
        defaults={"size": size, "parent": parent},
    )
    if created:
        _l.info(f"update_or_create_file_and_parents: created file {file.path}")

    return file.path


def paginate(items: list, page_size: int, page_number: int, base_url: str) -> dict:
    """
    Returns a slice of items for the given page number, plus URLs for previous and next pages.

    :param items: The list of items to paginate
    :param page_size: The number of items per page
    :param page_number: The page number to return (1-indexed)
    :param base_url: The base URL for the pagination links
    :return: A dict containing the paginated items, previous page URL, and next page URL
    """
    start = (page_number - 1) * page_size
    end = start + page_size
    paginated_items = items[start:end]
    delimiter = "&" if "?" in base_url else "?"
    previous_page_number = page_number - 1

    previous_page_url = (
        f"{base_url}{delimiter}page={previous_page_number}&page_size={page_size}"
        if previous_page_number > 0
        else None
    )

    next_page_number = page_number + 1
    next_page_url = (
        f"{base_url}{delimiter}page={next_page_number}&page_size={page_size}"
        if next_page_number <= (len(items) // page_size) + 1
        else None
    )

    return {
        "items": paginated_items,
        "previous_url": previous_page_url,
        "next_url": next_page_url,
        "count": len(items),
    }


def gen_path_copy(storage: FinmarsS3Storage, path: str) -> str:
    """
    Generate new path startswith _copy(number) for file (or directory).
    Args:
        storage (FinmarsS3Storage): The storage object to use.
        path (str): The path of the object (file system).
    Returns:
        str: new path (name of object (file system) end startswith _copy(number)).
    """
    base_name = os.path.basename(path)
    if base_name.startswith("."):
        # for .init
        return path

    name_parts = base_name.split(".")
    if len(name_parts) > 1:
        # For file
        base_name = name_parts[0]
        dase_dir = os.path.dirname(path)
        extension = "." + ".".join(name_parts[1:])

    else:
        # For directory
        base_name = last_dir_name(path).removesuffix("/")
        dase_dir = os.path.dirname(os.path.normpath(path))
        extension = "/"

    pref: int = 0
    while True:
        pref += 1
        new_name = f"{base_name}_copy({pref}){extension}"
        new_path = os.path.join(dase_dir, new_name)

        if not storage.exists(new_path):
            return new_path


def copy_file(
    storage: FinmarsS3Storage, source_file_path: str, destin_file_path: str
) -> None:
    """
    Copy a file from the source path to the destination path within the storage.
    If file name exists in destiny_file_path that name will change to file name + copy(copy number).
    Args:
        storage (Storage): The storage instance to use.
        source_file_path (str): The path of the source file.
        destin_file_path (str): The path of the destination file.
    Returns:
        None
    """

    if storage.exists(destin_file_path):
        destin_file_path = gen_path_copy(storage=storage, path=destin_file_path)
        _l.info(
            f"copy_file: file from {source_file_path} "
            f"already exists in target path, path has updated to {destin_file_path}"
        )
    file_name = os.path.basename(destin_file_path)

    _l.info(
        f"copy_file: copy file {file_name} from {source_file_path} "
        f"to {destin_file_path}"
    )

    content = storage.open(source_file_path).read()
    _l.info(
        f"copy_file: with content len={len(content)} "
        f"from {source_file_path} to {destin_file_path}"
    )

    storage.save(destin_file_path, ContentFile(content, name=file_name))
    _l.info(f"copy_file: content saved to {destin_file_path}")


def copy_dir(
    storage: FinmarsS3Storage,
    source_dir: str,
    destin_dir: str,
    celery_task: CeleryTask,
) -> None:
    """
    Copy a directory and its contents recursively within the storage and update the
    celery task progress. Empty directories will not be copy/created in the storage!
    If directory name exists in destin_dir that name will change to directory name + copy(copy number).
    Args:
        storage (Storage): The storage instance to use.
        source_dir (str): The path of the source directory.
        destin_dir (str): The path of the destination directory.
        celery_task (CeleryTask): The celery task to update.
    Returns:
        None
    """
    _l.info(f"copy_dir: copy content of directory '{source_dir}' to '{destin_dir}'")

    dirs, files = storage.listdir(source_dir)

    if storage.exists(destin_dir):
        destin_dir = gen_path_copy(storage=storage, path=destin_dir)
        _l.info(
            f"copy_dir: directory from {source_dir} "
            f"already exists in target path, path has updated to {destin_dir}"
        )

    for dir_name in dirs:
        s_dir = os.path.join(source_dir, dir_name)
        d_dir = os.path.join(destin_dir, dir_name)
        copy_dir(storage, s_dir, d_dir, celery_task)

    for file_name in files:
        s_file = os.path.join(source_dir, file_name)
        d_file = os.path.join(destin_dir, file_name)
        copy_file(storage, s_file, d_file)

    celery_task.refresh_from_db()
    progres_dict = celery_task.progress_object
    progres_dict["current"] += len(files)
    progres_dict["percent"] = int(progres_dict["current"] / progres_dict["total"] * 100)
    celery_task.update_progress(progres_dict)


def rename_file(
    storage: FinmarsS3Storage, source_file_path: str, destin_file_path: str
):
    """
    Rename a file from the source path to the destination path within the storage.
    Args:
        storage (Storage): The storage instance to use.
        source_file_path (str): The path of the source file.
        destin_file_path (str): The path of the destination file.
    Returns:
        None
    """
    file_name = os.path.basename(destin_file_path)
    _l.info(f"rename_file: rename {source_file_path} to {destin_file_path}")

    content = storage.open(source_file_path).read()
    _l.info(
        f"rename_file: with content len={len(content)} "
        f"from {source_file_path} to {destin_file_path}"
    )

    storage.save(destin_file_path, ContentFile(content, name=file_name))
    _l.info(f"rename_file: content saved to {destin_file_path}")

    storage.delete(source_file_path)
    _l.info(f"rename_file: source file {source_file_path} deleted")


def rename_dir(
    storage: FinmarsS3Storage,
    source_dir: str,
    destin_dir: str,
):
    """
    Rename a directory recursively within the storage and update the celery task progress.
    Empty directories will not be moved/created in the storage!
    Args:
        storage (Storage): The storage instance to use.
        source_dir (str): The path of the source directory.
        destin_dir (str): The path of the destination directory.

    Returns:
        None
    """
    _l.info(f"rename_dir: move content of directory '{source_dir}' to '{destin_dir}'")

    dirs, files = storage.listdir(source_dir)

    for dir_name in dirs:
        s_dir = os.path.join(source_dir, dir_name)
        d_dir = os.path.join(destin_dir, dir_name)
        rename_dir(storage, s_dir, d_dir)

    for file_name in files:
        s_file = os.path.join(source_dir, file_name)
        d_file = os.path.join(destin_dir, file_name)
        rename_file(storage, s_file, d_file)
