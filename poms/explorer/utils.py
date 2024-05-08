import json
import logging
import os
from typing import Optional

from django.http import HttpResponse

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


def define_content_type(file_name: str) -> Optional[str]:
    return CONTENT_TYPES.get(os.path.splitext(file_name)[-1])


def join_path(space_code: str, path: Optional[str]) -> str:
    if path:
        return f"{space_code.rstrip('/')}/{path.lstrip('/')}"
    else:
        return f"{space_code.rstrip('/')}"


def remove_first_folder_from_path(path: str) -> str:
    return os.path.sep.join(path.split(os.path.sep)[1:])


def has_slash(path: str) -> bool:
    return path.startswith("/") or path.endswith("/")


def response_with_file(storage: FinmarsS3Storage, path: str) -> HttpResponse:
    try:
        with storage.open(path, "rb") as file:
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


def move_file(storage, root, source_folder, file_name, destination_folder):
    """
    Move a file from the source folder to the destination folder.

    Args:
        storage (Storage): The storage instance to use.
        root (str): The root path where the file is located.
        source_folder (str): The path of the source folder.
        file_name (str): The name of the file to be moved.
        destination_folder (str): The path of the destination folder.
    Returns:
        None
    """
    source_file_path = os.path.join(root, file_name)
    destination_file_path = os.path.join(
        destination_folder,
        os.path.relpath(source_file_path, source_folder),
    )

    # Read content of file
    content = storage.open(source_file_path).read()

    # Save content to destination
    storage.save(destination_file_path, content)

    # Delete file from source
    storage.delete(source_file_path)


def move_folder(storage, source_folder: str, destination_folder: str):
    """
    Move a folder and its contents recursively within the storage.
    Args:
        storage (Storage): The storage instance to use.
        source_folder (str): The path of the source folder.
        destination_folder (str): The path of the destination folder.
    Returns:
        None
    """

    for root, dirs, files in os.walk(source_folder):
        for dir_name in dirs:
            source_dir_path = os.path.join(root, dir_name)
            destination_dir_path = os.path.join(
                destination_folder,
                os.path.relpath(source_dir_path, source_folder),
            )

            if not storage.exists(destination_dir_path):
                storage.makedirs(destination_dir_path)

        for file_name in files:
            storage.move_file(root, source_folder, file_name, destination_folder)

    _l.info(
        f"folder '{source_folder}' moved to '{destination_folder}'")
