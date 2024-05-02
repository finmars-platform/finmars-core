import os
from typing import Optional

from bs4 import BeautifulSoup


def define_content_type(file_name: str) -> Optional[str]:
    if not file_name:
        return

    content_type = None

    if file_name.endswith(".html"):
        content_type = "text/html"

    elif file_name.endswith(".txt"):
        content_type = "plain/text"

    elif file_name.endswith(".js"):
        content_type = "text/javascript"

    elif file_name.endswith(".csv"):
        content_type = "text/csv"

    elif file_name.endswith(".json"):
        content_type = "application/json"

    elif file_name.endswith(".yml") or file_name.endswith(".yaml"):
        content_type = "application/yaml"

    elif file_name.endswith(".py"):
        content_type = "text/x-python"

    elif file_name.endswith(".png"):
        content_type = "image/png"

    elif file_name.endswith("jpg") or file_name.endswith("jpeg"):
        content_type = "image/jpeg"

    elif file_name.endswith(".pdf"):
        content_type = "application/pdf"

    elif file_name.endswith(".doc") or file_name.endswith(".docx"):
        content_type = "application/msword"

    elif file_name.endswith(".css"):
        content_type = "text/css"

    elif file_name.endswith(".xls"):
        content_type = "application/vnd.ms-excel"

    elif file_name.endswith(".xlsx"):
        content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    return content_type


def join_path(space_code: str, path: str) -> str:
    space_code = space_code.removesuffix("/")
    path = path.removeprefix("/")
    return f"{space_code}/{path}"


def remove_first_folder_from_path(path: str) -> str:
    split_path = path.split(os.path.sep)
    return os.path.sep.join(split_path[1:])


def sanitize_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for script in soup(["script", "style"]):  # Remove these tags
        script.extract()

    return str(soup)
