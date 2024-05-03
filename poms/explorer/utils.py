import json
import logging
import os
from typing import Optional

from django.http import HttpResponse

from bs4 import BeautifulSoup

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
    soup = BeautifulSoup(html, "html.parser")
    for script in soup(["script", "style"]):  # Remove these tags
        script.extract()
    return str(soup)
