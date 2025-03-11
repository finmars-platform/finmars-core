import contextlib
import json
import logging
import os
import re
import time
from typing import Any
import zipfile

import requests
from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.core.files.base import ContentFile
from django.http import FileResponse

from poms.common.http_client import HttpClient
from poms.common.storage import get_storage
from poms.common.utils import get_content_type_by_name, get_serializer
from poms.auth_tokens.utils import get_refresh_token
from poms.users.models import MasterUser

_l = logging.getLogger("poms.configuration")

storage = get_storage()


class DeleteFileAfterResponse(FileResponse):
    def __init__(self, *args, **kwargs):
        self.path_to_delete = kwargs.pop("path_to_delete", None)
        super().__init__(*args, **kwargs)

    def close(self):
        super().close()
        if self.path_to_delete:
            with contextlib.suppress(FileNotFoundError):
                os.remove(self.path_to_delete)


def replace_special_chars_and_spaces(code: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", code)


def remove_id_key_recursively(data):
    if not isinstance(data, dict):
        return data

    # Remove 'id' key if present
    data.pop("id", None)

    # Recursively process nested dictionaries
    for key, value in data.items():
        if isinstance(value, dict):
            remove_id_key_recursively(value)
        elif isinstance(value, list):
            for item in value:
                remove_id_key_recursively(item)

    return data


def user_code_to_file_name(configuration_code, user_code):
    try:
        code = user_code.split(f"{configuration_code}:")[1]

        return replace_special_chars_and_spaces(code).lower()

    except Exception:
        return replace_special_chars_and_spaces(user_code).lower()


def save_json_to_file(file_path, json_data):
    try:
        # Create the folder if it doesn't exist
        folder = os.path.dirname(file_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(json_data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        _l.error(f"save_json_to_file {file_path}: {e}")

        raise e


def read_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def zip_directory(source_dir, output_zipfile):
    with zipfile.ZipFile(output_zipfile, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                archive.write(file_path, arcname=arcname)


def remove_object_keys(d: dict) -> dict:
    return {key: value for key, value in d.items() if "_object" not in key}


def model_has_field(model, field_name):
    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False


def save_whitelable_files(folder_path: str, json_data: dict[str, Any], context: dict[str, Any]) -> None:
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        master_user: MasterUser = context["master_user"]
        space_code = master_user.space_code

        files_key = ["favicon_url", "logo_dark_url", "logo_light_url", "theme_css_url"] 
        for key in files_key:
            file_path = json_data.get(key)
            src_file_path = os.path.join(space_code, file_path)

            with storage.open(src_file_path, "rb") as src_file:
                file_name = os.path.basename(src_file.name)
                dst_file_path = os.path.join(folder_path, file_name)

                with open(dst_file_path, "w") as dst_file:
                    dst_file.write(src_file.read())

    except Exception as e:
        _l.error(f"save_whitelable_files to {folder_path}: {e}")
        raise e


def save_serialized_entity(content_type, configuration_code, source_directory, context):
    try:
        model = apps.get_model(content_type)
    except Exception as e:
        raise RuntimeError(
            f"Could not find model for content type: {content_type}"
        ) from e

    dash = f"{configuration_code}:-"

    if model_has_field(model, "is_deleted"):
        filtered_objects = model.objects.filter(
            configuration_code=configuration_code, is_deleted=False
        ).exclude(user_code=dash)
    else:
        filtered_objects = model.objects.filter(
            configuration_code=configuration_code
        ).exclude(user_code=dash)

    serializer_class = get_serializer(content_type)

    for item in filtered_objects:
        serializer = serializer_class(item, context=context)
        serialized_data = remove_id_key_recursively(serializer.data)

        if "is_deleted" in serialized_data:
            serialized_data.pop("is_deleted")

        if "is_enabled" in serialized_data:
            serialized_data.pop("is_enabled")

        if "deleted_user_code" in serialized_data:
            serialized_data.pop("deleted_user_code")

        if "members" in serialized_data:
            serialized_data.pop("members")

        if "owner" in serialized_data:
            serialized_data.pop("owner")

        if "created_at" in serialized_data:
            serialized_data.pop("created_at")

        if "modified_at" in serialized_data:
            serialized_data.pop("modified_at")

        serialized_data = remove_object_keys(serialized_data)
        path = f"{source_directory}/{user_code_to_file_name(configuration_code, item.user_code)}"
        save_json_to_file(f"{path}.json", serialized_data)

        if content_type == "system.whitelabelmodel":
            save_whitelable_files(path, serialized_data, context)


def save_serialized_attribute_type(
        content_type, configuration_code, content_type_key, source_directory, context
):
    try:
        model = apps.get_model(content_type)
    except Exception as e:
        raise RuntimeError(
            f"Could not find model for content type: {content_type}"
        ) from e

    entity_content_type = get_content_type_by_name(content_type_key)

    filtered_objects = model.objects.filter(
        configuration_code=configuration_code, content_type=entity_content_type
    )

    SerializerClass = get_serializer(content_type)

    for item in filtered_objects:
        serializer = SerializerClass(item, context=context)
        serialized_data = remove_id_key_recursively(serializer.data)

        # TODO convert content_type_id to content_type_key

        if "deleted_user_code" in serialized_data:
            serialized_data.pop("deleted_user_code")

        path = f"{source_directory}/{user_code_to_file_name(configuration_code, item.user_code)}.json"

        save_json_to_file(path, serialized_data)


def save_serialized_custom_fields(
        configuration_code, report_content_type, source_directory, context
):
    """

    :param configuration_code:
    :param report_content_type: Allowed values: 'reports.balancereport', 'reports.plreport', 'reports.transactionreport'
    :type report_content_type: str
    :param source_directory:
    :param context:
    :return:
    """
    from poms.reports.models import (
        BalanceReportCustomField,
        PLReportCustomField,
        TransactionReportCustomField,
    )
    from poms.reports.serializers import (
        BalanceReportCustomFieldSerializer,
        PLReportCustomFieldSerializer,
        TransactionReportCustomFieldSerializer,
    )

    custom_fields_map = {
        "reports.balancereport": [
            BalanceReportCustomField,
            BalanceReportCustomFieldSerializer,
        ],
        "reports.plreport": [
            PLReportCustomField,
            PLReportCustomFieldSerializer,
        ],
        "reports.transactionreport": [
            TransactionReportCustomField,
            TransactionReportCustomFieldSerializer,
        ],
    }

    if report_content_type not in custom_fields_map:
        raise RuntimeError(
            f"Could not find report with content type: {report_content_type}"
        )

    model = custom_fields_map[report_content_type][0]
    SerializerClass = custom_fields_map[report_content_type][1]

    filtered_objects = model.objects.filter(
        configuration_code=configuration_code, master_user=context["master_user"]
    )

    for item in filtered_objects:
        serializer = SerializerClass(item, context=context)
        serialized_data = remove_id_key_recursively(serializer.data)

        path = f"{source_directory}/{user_code_to_file_name(configuration_code, item.user_code)}.json"

        save_json_to_file(path, serialized_data)


def save_serialized_layout(content_type, configuration_code, source_directory, context):
    try:
        model = apps.get_model(content_type)
    except Exception as e:
        raise RuntimeError(
            f"Could not find model for content type: {content_type}"
        ) from e

    filtered_objects = model.objects.filter(
        configuration_code=configuration_code, member=context["member"]
    )

    _l.info(f"filtered_objects {filtered_objects}")

    SerializerClass = get_serializer(content_type)

    for item in filtered_objects:
        serializer = SerializerClass(item, context=context)
        # serialized_data = remove_id_key_recursively(serializer.data)
        serialized_data = serializer.data

        serialized_data.pop("id")

        path = (
                source_directory
                + "/"
                + user_code_to_file_name(configuration_code, item.user_code)
                + ".json"
        )

        save_json_to_file(path, serialized_data)


def save_serialized_entity_layout(
        content_type, configuration_code, content_type_key, source_directory, context
):
    try:
        model = apps.get_model(content_type)
    except Exception as e:
        raise RuntimeError(
            f"Could not find model for content type: {content_type}"
        ) from e

    entity_content_type = get_content_type_by_name(content_type_key)

    _l.info(f"save_serialized_entity_layout.entity_content_type {entity_content_type}")

    filtered_objects = model.objects.filter(
        configuration_code=configuration_code,
        content_type=entity_content_type,
        member=context["member"],
    )

    _l.info(f"filtered_objects {filtered_objects}")

    SerializerClass = get_serializer(content_type)

    for item in filtered_objects:
        serializer = SerializerClass(item, context=context)
        # serialized_data = remove_id_key_recursively(serializer.data)
        serialized_data = serializer.data

        serialized_data.pop("id")

        if "reportOptions" in serialized_data["data"]:
            serialized_data["data"]["reportOptions"]["accounts"] = []
            serialized_data["data"]["reportOptions"]["accounts_object"] = []
            serialized_data["data"]["reportOptions"]["portfolios"] = []
            serialized_data["data"]["reportOptions"]["portfolios_object"] = []

        path = (
                source_directory
                + "/"
                + user_code_to_file_name(configuration_code, item.user_code)
                + ".json"
        )

        save_json_to_file(path, serialized_data)


def unzip_to_directory(input_zipfile, output_directory):
    with zipfile.ZipFile(input_zipfile) as zf:
        zf.extractall(path=output_directory)


def list_json_files(directory: str) -> list[str]:
    json_files = []

    for root, _, files in os.walk(directory):
        json_files.extend(
            os.path.join(root, file) for file in files if file.endswith(".json")
        )
    return json_files


def copy_directory(src_dir, dst_dir):
    directories, files = storage.listdir(src_dir)

    # Copy files
    for file_name in files:
        src_file_path = os.path.join(src_dir, file_name)
        dst_file_path = os.path.join(dst_dir, file_name)

        with storage.open(src_file_path, "rb") as src_file:
            content = src_file.read()
            with storage.open(dst_file_path, "wb") as dst_file:
                dst_file.write(content)

    # Recursively copy subdirectories
    for directory in directories:
        src_subdir = os.path.join(src_dir, directory)
        dst_subdir = os.path.join(dst_dir, directory)

        if not storage.exists(dst_subdir):
            storage.makedirs(dst_subdir)

        copy_directory(src_subdir, dst_subdir)



def upload_directory_to_storage(local_directory, storage_directory):
    for root, dirs, files in os.walk(local_directory):
        for file in files:
            local_file_path = os.path.join(root, file)
            storage_file_path = os.path.join(
                storage_directory, os.path.relpath(local_file_path, local_directory)
            )

            with open(local_file_path, "rb") as local_file:
                content = local_file.read()
                storage.save(storage_file_path, ContentFile(content))


def get_headers_with_token(token: str):
    return {
        "Content-type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    } 


def run_workflow(user_code, payload, master_task):
    from django.contrib.auth import get_user_model

    from rest_framework_simplejwt.tokens import RefreshToken

    from poms_app import settings

    User = get_user_model()

    bot = User.objects.get(username="finmars_bot")

    refresh = get_refresh_token(bot, master_task.master_user)

    # _l.info('refresh %s' % refresh.access_token)

    headers = get_headers_with_token(refresh.access_token)

    realm_code = master_task.master_user.realm_code
    space_code = master_task.master_user.space_code
    url = f"https://{settings.DOMAIN_NAME}/{realm_code}/{space_code}/workflow/api/workflow/run-workflow/"

    data = {"user_code": user_code, "payload": payload, "platform_task_id": master_task.id}

    response = requests.post(url, headers=headers, json=data)

    return response.json()


def get_workflow(workflow_id: int, master_task):
    from django.contrib.auth import get_user_model

    from rest_framework_simplejwt.tokens import RefreshToken

    from poms_app import settings

    User = get_user_model()

    bot = User.objects.get(username="finmars_bot")

    refresh = get_refresh_token(bot, master_task.master_user)

    # _l.info('refresh %s' % refresh.access_token)

    headers = get_headers_with_token(refresh.access_token)

    realm_code = master_task.master_user.realm_code
    space_code = master_task.master_user.space_code
    url = f"https://{settings.DOMAIN_NAME}/{realm_code}/{space_code}/workflow/api/workflow/{workflow_id}/"

    response = requests.get(url, headers=headers)

    return response.json()


def wait_workflow_until_end(workflow_id: int, master_task):
    while True:
        workflow = get_workflow(workflow_id, master_task)

        if workflow["status"] not in ("init", "progress"):
            return workflow

        time.sleep(10)


def get_default_configuration_code():
    from poms.users.models import MasterUser
    master_user = MasterUser.objects.all().first()

    return f"local.poms.{master_user.space_code}"


def create_or_update_workflow_template(platform, json_data: dict[str, Any]):
    from django.contrib.auth import get_user_model

    from poms_app import settings

    user_code = json_data["workflow"]["user_code"]
    _l.info(f"Create or update Workflow Template for workflow v2 {user_code}")

    http_client = HttpClient()

    User = get_user_model()
    bot = User.objects.get(username="finmars_bot")
    refresh = get_refresh_token(bot, platform)
    headers = get_headers_with_token(refresh.access_token)

    base_url = f"https://{settings.DOMAIN_NAME}/{platform.realm_code}/{platform.space_code}"
    api_endpoint = "workflow/api/v1/workflow-template"

    workflow_template_data = {
        "name": json_data["workflow"].get("name"),
        "user_code": user_code,
        "notes": json_data["workflow"].get("notes"),
        "data": json_data
    }

    # check if workflow template exists
    workflow_templates_response_data = http_client.get(
        f"{base_url}/{api_endpoint}/?user_code={user_code}",
        headers=headers,
    )

    if workflow_templates_response_data.get("count"):
        workflow_template_id = workflow_templates_response_data["results"][0]["id"]
        http_client.put(
            f"{base_url}/{api_endpoint}/{workflow_template_id}/",
            json=workflow_template_data,
            headers=headers,
        )
    else:
        http_client.post(
            f"{base_url}/workflow/api/v1/workflow-template/",
            json=workflow_template_data,
            headers=headers,
        )
