import os
from typing import Optional

from django.core.files import File

from bs4 import BeautifulSoup


def define_content_type(file: File) -> Optional[str]:
    file_content_type = None
    file_name = file.name

    if file_name.endswith(".html"):
        file_content_type = "text/html"

    elif file_name.endswith(".txt"):
        file_content_type = "plain/text"

    elif file_name.endswith(".js"):
        file_content_type = "text/javascript"

    elif file_name.endswith(".csv"):
        file_content_type = "text/csv"

    elif file_name.endswith(".json"):
        file_content_type = "application/json"

    elif file_name.endswith(".yml") or file_name.endswith(".yaml"):
        file_content_type = "application/yaml"

    elif file_name.endswith(".py"):
        file_content_type = "text/x-python"

    elif file_name.endswith(".png"):
        file_content_type = "image/png"

    elif file_name.endswith("jpg") or file_name.endswith("jpeg"):
        file_content_type = "image/jpeg"

    elif file_name.endswith(".pdf"):
        file_content_type = "application/pdf"

    elif file_name.endswith(".doc") or file_name.endswith(".docx"):
        file_content_type = "application/msword"

    elif file_name.endswith(".css"):
        file_content_type = "text/css"

    elif file_name.endswith(".xls"):
        file_content_type = "application/vnd.ms-excel"

    elif file_name.endswith(".xlsx"):
        file_content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    return file_content_type


def sanitize_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for script in soup(["script", "style"]):  # Remove these tags
        script.extract()

    return str(soup)


def join_path(space_code: str, path: str) -> str:
    return f"{space_code}{path}" if path[0] == "/" else f"{space_code}/{path}"


def remove_first_folder_from_path(path: str) -> str:
    split_path = path.split(os.path.sep)
    return os.path.sep.join(split_path[1:])
