from urllib.parse import unquote
import io
import json
import logging
import os
import traceback
from datetime import date

from rest_framework.authtoken.models import Token

import requests
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.core.files.base import File
from django.db import transaction
from django.utils.timezone import now

from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.common.models import ProxyRequest, ProxyUser
from poms.common.storage import get_storage
from poms.common.utils import get_serializer
from poms.configuration.handlers import (
    export_configuration_to_directory,
    export_workflows_to_directory,
)
from poms.configuration.models import Configuration
from poms.configuration.utils import (
    create_or_update_workflow_template,
    list_json_files,
    load_file,
    read_json_file,
    run_workflow,
    save_json_to_file,
    unzip_to_directory,
    upload_directory_to_storage,
    wait_workflow_until_end,
)
from poms.file_reports.models import FileReport
from poms.users.models import EcosystemDefault
from poms_app import settings

_l = logging.getLogger("poms.configuration")

User = get_user_model()
storage = get_storage()


def _run_action(task: CeleryTask, action: dict):
    workflow = action.get("workflow", None)
    if workflow:
        try:
            _l.info(f"import_configuration.going to execute workflow {workflow}")

            response_data = run_workflow(workflow, {}, task)

            response_data = wait_workflow_until_end(response_data["id"], task)

            _l.info(f"import_configuration.workflow finished {response_data}")

        except Exception as e:
            _l.error(
                f"Could not execute workflow {e} traceback {traceback.format_exc()}"
            )


@finmars_task(name="configuration.import_configuration", bind=True)
def import_configuration(self, task_id: int, *args, **kwargs) -> None:
    _l.info("import_configuration")
    _l.info(f"import_configuration {task_id}")

    task = CeleryTask.objects.get(id=task_id)
    task.celery_task_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    task.save()

    _l.info("import_configuration.task master_user %s" % task.master_user)

    def generate_json_report(task, stats):
        result = stats

        current_date_time = now().strftime("%Y-%m-%d-%H-%M")
        file_name = f"file_report_{current_date_time}_task_{task.id}.json"

        file_report = FileReport()

        _l.info("TransactionImportProcess.generate_json_report uploading file")

        file_report.upload_file(
            file_name=file_name,
            text=json.dumps(result, indent=4, default=str),
            master_user=task.master_user,
        )
        file_report.master_user = task.master_user
        file_report.name = (
            f"Configuration Import {current_date_time} (Task {task.id}).json"
        )
        file_report.file_name = file_name
        file_report.type = "configuration.import_configuration"
        file_report.notes = "System File"
        file_report.content_type = "application/json"

        file_report.save()

        _l.info(f"ConfigurationImportManager.json_report {file_report}")
        _l.info(f"ConfigurationImportManager.json_report {file_report.file_url}")

        return file_report

    proxy_user = ProxyUser(task.member, task.master_user)
    proxy_request = ProxyRequest(proxy_user)

    context = {
        "master_user": task.master_user,
        "member": task.member,
        "request": proxy_request,
    }

    file_path = task.options_object["file_path"]

    output_directory = os.path.join(
        settings.BASE_DIR,
        f"tmp/{str(task.master_user.space_code)}/task_{str(task.id)}/",
    )

    if not os.path.exists(output_directory):
        os.makedirs(output_directory, exist_ok=True)

    local_file_path = storage.download_file_and_save_locally(
        file_path, f"{output_directory}file.zip"
    )

    _l.info(f"import_configuration got {file_path}")

    output_directory = os.path.join(
        settings.BASE_DIR,
        f"configurations/{str(task.master_user.space_code)}/{str(task.id)}/source",
    )

    if not os.path.exists(
        os.path.join(
            settings.BASE_DIR,
            f"configurations/{str(task.master_user.space_code)}/{str(task.id)}/source",
        )
    ):
        os.makedirs(output_directory, exist_ok=True)

    unzip_to_directory(local_file_path, output_directory)

    _l.info(f"import_configuration unzip_to_directory {output_directory}")

    try:
        manifest = read_json_file(os.path.join(output_directory, "manifest.json"))

    except Exception as e:
        _l.error(f"import_configuration read_json_file {e}")
        manifest = None

        if not task.notes:
            task.notes = ""

        task.notes = task.notes = "Manifest is not found ⚠️"

    json_files = list_json_files(output_directory)

    task.update_progress(
        {
            "current": 0,
            "total": len(json_files),
            "percent": 0,
            "description": "Going to import items",
        }
    )

    index = 0

    stats = {"configuration": {}, "workflow": {}, "manifest": {}, "other": {}}

    for json_file_path in json_files:
        index = index + 1

        task.update_progress(
            {
                "current": index,
                "total": len(json_files),
                "percent": round(index / (len(json_files) / 100)),
                "description": f"Going to import {json_file_path}",
            }
        )

        if json_file_path.endswith("manifest.json"):
            stats["manifest"][json_file_path] = {"status": "skip"}
            continue

        json_data = read_json_file(json_file_path)

        if "workflows" in json_file_path:
            if not json_file_path.endswith("workflow.json"):
                stats["other"][json_file_path] = {"status": "skip"}
                continue

            if (
                not isinstance(json_data, dict)
                or not (version := json_data.get("version"))
                or version != "2"
                or not json_data.get("workflow")
            ):
                stats["workflow"][json_file_path] = {
                    "status": "skip",
                    "reason": "not template format",
                }
                continue

            try:
                create_or_update_workflow_template(task.master_user, json_data)

                description = f"WorkflowTemplate created {json_file_path}"
                stats["workflow"][json_file_path] = {"status": "success"}

            except Exception as e:
                _l.error(f"create Workflow Template for workflow v2 {e}")
                description = f"Error {json_file_path}"
                stats["workflow"][json_file_path] = {
                    "status": "error",
                    "error_message": str(e),
                }
            finally:
                task.update_progress(
                    {
                        "current": index,
                        "total": len(json_files),
                        "percent": round(index / (len(json_files) / 100)),
                        "description": description,
                    }
                )

        else:
            try:
                content_type = json_data["meta"]["content_type"]
                user_code = json_data.get("user_code")
                SerializerClass = get_serializer(content_type)

                Model = SerializerClass.Meta.model

                if user_code is not None:
                    # Check if the instance already exists

                    try:  # if member specific entity
                        Model.objects.model._meta.get_field("member")
                        instance = Model.objects.filter(
                            user_code=user_code, member=task.member
                        ).first()
                    except FieldDoesNotExist:
                        instance = Model.objects.filter(user_code=user_code).first()
                else:
                    instance = None

                if content_type == "system.whitelabelmodel":
                    model_name = content_type = json_data["meta"]["model_name"]
                    directory_with_files = (
                        f"{output_directory}/{model_name}/{user_code.split(':')[-1]}"
                    )

                    files_key = [
                        "favicon_url",
                        "logo_dark_url",
                        "logo_light_url",
                        "theme_css_url",
                    ]
                    for key in files_key:
                        relative_file_path = json_data.get(key)
                        file_name = os.path.basename(relative_file_path)
                        file_path = os.path.join(
                            directory_with_files, unquote(file_name)
                        )

                        if "css" in key:
                            data_key = key.replace("url", "file")
                        else:
                            data_key = key.replace("url", "image")

                        json_data[data_key] = load_file(file_path)

                serializer = SerializerClass(
                    instance=instance, data=json_data, context=context
                )

                if serializer.is_valid():
                    # Perform any desired actions, such as saving the data to the database
                    serializer.save()
                    stats["configuration"][json_file_path] = {"status": "success"}
                    description = f"Imported {json_file_path}"

                else:
                    stats["configuration"][json_file_path] = {
                        "status": "error",
                        "error_message": str(serializer.errors),
                    }
                    _l.error(f"Invalid data in {json_file_path}: {serializer.errors}")
                    description = f"Error {json_file_path}"

            except Exception as e:
                _l.error(f"import_configuration {e} traceback {traceback.format_exc()}")

                stats["configuration"][json_file_path] = {
                    "status": "error",
                    "error_message": str(e),
                }
                description = f"Error {json_file_path}"

            finally:
                task.update_progress(
                    {
                        "current": index,
                        "total": len(json_files),
                        "percent": round(index / (len(json_files) / 100)),
                        "description": description,
                    }
                )

    # Import Workflows

    if manifest:
        # only if manifest is present

        configuration_code_as_path = "/".join(manifest["configuration_code"].split("."))

        dest_workflow_directory = (
            f"{task.master_user.space_code}/workflows/{configuration_code_as_path}"
        )

        _l.info(f"dest_workflow_directory {dest_workflow_directory}")

        upload_directory_to_storage(
            f"{output_directory}/workflows", dest_workflow_directory
        )

        if manifest.get("actions", None):
            for action in manifest["actions"]:
                _run_action(task, action)

    _l.info("Workflows uploaded")

    file_report = generate_json_report(task, stats)

    task.add_attachment(file_report.id)

    task.status = CeleryTask.STATUS_DONE
    task.save()


@finmars_task(name="configuration.export_configuration", bind=True)
def export_configuration(self, task_id, *args, **kwargs):
    _l.info("export_configuration")

    task = CeleryTask.objects.get(id=task_id)
    task.celery_task_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    task.save()

    configuration_code = task.options_object["configuration_code"]

    configuration = Configuration.objects.get(configuration_code=configuration_code)

    _l.info(f"configuration {configuration}")

    source_directory = os.path.join(
        settings.BASE_DIR,
        f"configurations/{str(task.master_user.space_code)}/{str(task.id)}/source",
    )

    if not os.path.exists(source_directory):
        os.makedirs(source_directory, exist_ok=True)

    _l.info("export_configuration.Configuration exporting...")

    export_configuration_to_directory(
        source_directory, configuration, task.master_user, task.member
    )

    _l.info("export_configuration.Configuration exported to directory")

    _l.info("export_configuration.Workflows exporting...")

    try:
        export_workflows_to_directory(
            source_directory, configuration, task.master_user, task.member
        )
    except Exception as e:
        if not task.notes:
            task.notes = ""

        task.notes = task.notes + "Workflow is not found ⚠️ \n"
        task.notes = task.notes + str(e)

    manifest_filepath = f"{source_directory}/manifest.json"

    manifest = configuration.manifest or {
        "name": configuration.name,
        "configuration_code": configuration.configuration_code,
        "version": configuration.version,
        "channel": configuration.channel,
        "date": str(date.today()),
    }

    save_json_to_file(manifest_filepath, manifest)

    storage_directory = (
        f"{task.master_user.space_code}/configurations/{configuration.configuration_code}"
        f"/{configuration.version}/"
        if configuration.is_from_marketplace
        else f"{task.master_user.space_code}/configurations/custom/"
        f"{configuration.configuration_code}/{configuration.version}/"
    )
    upload_directory_to_storage(source_directory, storage_directory)

    _l.info("export_configuration. Done")

    task.status = CeleryTask.STATUS_DONE
    task.save()


@finmars_task(name="configuration.push_configuration_to_marketplace", bind=True)
def push_configuration_to_marketplace(self, task_id, *args, **kwargs):
    _l.info("push_configuration_to_marketplace")

    task = CeleryTask.objects.get(id=task_id)
    task.celery_task_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    task.save()

    options_object = task.options_object

    username = options_object["username"]
    password = options_object["password"]

    del options_object["username"]
    del options_object["password"]

    task.options_object = options_object
    task.save()

    configuration = Configuration.objects.get(
        configuration_code=options_object["configuration_code"]
    )

    path = (
        f"/configurations/{configuration.configuration_code}/{configuration.version}/"
        if configuration.is_from_marketplace
        else f"/configurations/custom/{configuration.configuration_code}/{configuration.version}/"
    )

    _l.info(f"path {path}")

    zip_file_path = storage.download_directory_content_as_zip(path)

    data = {
        "configuration_code": configuration.configuration_code,
        "name": configuration.name,
        "version": configuration.version,
        "channel": configuration.channel,
        "description": configuration.description,
        "author": username,
        "changelog": options_object.get("changelog", ""),
        "manifest": json.dumps(configuration.manifest),
    }

    _l.info(
        f"push_configuration_to_marketplace.data {data} zip_file_path {zip_file_path}"
    )

    files = {"file": open(zip_file_path, "rb")}

    headers = {"Content-type": "application/json", "Accept": "application/json"}

    response = requests.post(
        url="https://marketplace.finmars.com/api/v1/login/",
        json={"username": username, "password": password},
        headers=headers,
    )

    auth_data = response.json()

    # _l.info('data %s' % data)

    token = auth_data["token"]

    headers = {"Authorization": f"Token {token}"}

    response = requests.post(
        url="https://marketplace.finmars.com/api/v1/configuration/push/",
        data=data,
        files=files,
        headers=headers,
    )

    if response.status_code != 200:
        task.status = CeleryTask.STATUS_ERROR
        task.error_message = response.text
        task.save()
        raise RuntimeError(response.text)
    else:
        _l.info("push_configuration_to_marketplace.Configuration pushed to marketplace")

        task.verbose_result = {"message": "Configuration pushed to marketplace"}
        task.status = CeleryTask.STATUS_DONE

    task.save()


@finmars_task(name="configuration.install_configuration_from_marketplace", bind=True)
def install_configuration_from_marketplace(self, *args, **kwargs):
    task_id = kwargs.get("task_id")

    task = CeleryTask.objects.get(id=task_id)
    task.celery_task_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    task.save()

    ecosystem_defaults = EcosystemDefault.cache.get_cache(
        master_user_pk=task.master_user.pk
    )

    _l.info(
        f"install_configuration_from_marketplace started: task.id={task.id} "
        f"options={task.options_object}"
    )

    options_object = task.options_object
    #
    # # Implement when keycloak is refactored
    # # access_token = options_object['access_token']
    # #
    # # del options_object['access_token']
    #
    # task.options_object = options_object
    # task.save()

    headers = {}
    # headers['Authorization'] = 'Token ' + access_token


    if ecosystem_defaults.license_key:

        _l.info(f"license_key found. add to headers request to marketplace")

        headers['X-License'] = ecosystem_defaults.license_key

    if "^" in options_object["version"]:  # latest
        data = {"configuration_code": options_object["configuration_code"]}

        response = requests.post(
            url="https://marketplace.finmars.com/api/v1/configuration/find-release-latest/",
            data=data,
            headers=headers,
        )
    else:
        data = {
            "configuration_code": options_object["configuration_code"],
            "channel": options_object["channel"],
            "version": options_object["version"],
        }

        response = requests.post(
            url="https://marketplace.finmars.com/api/v1/configuration/find-release/",
            data=data,
            headers=headers,
        )

    if response.status_code != 200:
        task.status = CeleryTask.STATUS_ERROR
        task.error_message = response.text
        task.save()
        raise Exception(response.text)

    remote_configuration_release = response.json()
    remote_configuration = remote_configuration_release["configuration_object"]

    _l.info(f"remote_configuration {remote_configuration_release}")

    try:
        configuration = Configuration.objects.get(
            configuration_code=remote_configuration["configuration_code"]
        )
    except Exception:
        configuration = Configuration.objects.create(
            configuration_code=remote_configuration["configuration_code"],
            version="0.0.0",
        )

    configuration.name = remote_configuration["name"]
    configuration.description = remote_configuration["description"]
    configuration.version = remote_configuration_release["version"]
    configuration.channel = remote_configuration_release["channel"]
    configuration.is_package = False
    configuration.manifest = remote_configuration_release["manifest"]
    configuration.is_from_marketplace = True
    configuration.type = remote_configuration.get("type", "general")

    configuration.save()

    if task.parent:
        with transaction.atomic():
            task.parent.refresh_from_db()

            step = task.options_object["step"]
            total = len(task.parent.options_object["dependencies"]) + len(
                task.parent.options_object["actions"]
            )
            percent = int((step / total) * 100)

            description = f"Step {step}/{total} is installing {configuration.name}"

            task.parent.update_progress(
                {
                    "current": step,
                    "total": total,
                    "percent": percent,
                    "description": description,
                }
            )

    response = requests.get(
        url="https://marketplace.finmars.com/api/v1/configuration-release/"
        + str(remote_configuration_release["id"])
        + "/download/",
        headers=headers,
    )

    destination_path = os.path.join(
        settings.BASE_DIR,
        f"configurations/{str(task.master_user.space_code)}/{str(task.id)}/archive.zip",
    )

    if response.status_code != 200:
        task.status = CeleryTask.STATUS_ERROR
        task.error_message = response.text
        task.save()
        raise RuntimeError(response.text)

    os.makedirs(os.path.dirname(destination_path), exist_ok=True)

    storage_file_path = f"/public/import-configurations/{str(task.id)}_archive.zip"

    byte_stream = io.BytesIO(response.content)
    storage.save(storage_file_path, File(byte_stream, f"{str(task.id)}_archive.zip"))

    import_configuration_celery_task = CeleryTask.objects.create(
        master_user=task.master_user,
        member=task.member,
        parent=task,
        verbose_name="Configuration Import",
        type="configuration_import",
    )

    options_object = {
        "file_path": storage_file_path,
    }

    import_configuration_celery_task.options_object = options_object
    import_configuration_celery_task.save()

    # sync call
    # .si is important, we do not need to pass result from previous task

    import_configuration(import_configuration_celery_task.id)
    # seems self is not needed

    if task.parent:
        with transaction.atomic():
            task.parent.refresh_from_db()

            step = task.options_object["step"]
            total = len(task.parent.options_object["dependencies"]) + len(
                task.parent.options_object["actions"]
            )
            percent = int((step / total) * 100)

            description = f"Step {step}/{total} is installed. {configuration.name}"

            task.parent.update_progress(
                {
                    "current": step,
                    "total": total,
                    "percent": percent,
                    "description": description,
                }
            )

    result_object = {
        "configuration_import": {"task_id": import_configuration_celery_task.id}
    }
    task.result_object = result_object

    task.status = CeleryTask.STATUS_DONE
    task.save()


@finmars_task(name="configuration.finish_package_install", bind=True)
def finish_package_install(self, task_id, *args, **kwargs):
    task = CeleryTask.objects.get(id=task_id)

    with transaction.atomic():
        task.refresh_from_db()
        options = task.options_object

        _l.info(f"finish_package_install task.id={task.id}  options={options}")

        if "dependencies" not in options:
            raise ValueError(
                "finish_package_install: invalid configuration, no dependencies !"
            )

        task.update_progress(
            {
                "current": len(options["dependencies"]),
                "total": len(options["dependencies"]),
                "percent": 100,
                "description": "Installation complete",
            }
        )
        task.status = CeleryTask.STATUS_DONE
        task.verbose_result = "Configuration package installed successfully"
        task.save()


@finmars_task(name="configuration.install_package_from_marketplace", bind=True)
def install_package_from_marketplace(self, task_id, *args, **kwargs):
    _l.info("install_package_from_marketplace")

    parent_task = CeleryTask.objects.get(id=task_id)
    # task.celery_task_id = self.request.id
    # task.status = CeleryTask.STATUS_PENDING
    # task.save()

    # try:

    parent_options_object = parent_task.options_object

    # TODO Implement when keycloak refactored
    # access_token = options_object['access_token']
    #
    # del options_object['access_token']

    # task.options_object = options_object
    # task.save()

    data = {
        "configuration_code": parent_options_object["configuration_code"],
        "version": parent_options_object["version"],
        "channel": parent_options_object["channel"],
    }
    headers = {}
    # headers['Authorization'] = 'Token ' + access_token

    # _l.info('push_configuration_to_marketplace.headers %s' % headers)

    response = requests.post(
        url="https://marketplace.finmars.com/api/v1/configuration/find-release/",
        data=data,
        headers=headers,
    )
    if response.status_code != 200:
        parent_task.status = CeleryTask.STATUS_ERROR
        parent_task.error_message = response.text
        parent_task.save()
        raise RuntimeError(response.text)

    remote_configuration_release = response.json()
    remote_configuration = remote_configuration_release["configuration_object"]

    _l.info(f"remote_configuration {remote_configuration_release}")

    try:
        configuration = Configuration.objects.get(
            configuration_code=remote_configuration["configuration_code"]
        )
    except Exception:
        configuration = Configuration.objects.create(
            configuration_code=remote_configuration["configuration_code"]
        )

    configuration.name = remote_configuration["name"]
    configuration.description = remote_configuration["description"]
    configuration.version = remote_configuration_release["version"]
    configuration.channel = remote_configuration_release["channel"]
    configuration.is_package = True
    configuration.manifest = remote_configuration_release["manifest"]
    configuration.is_from_marketplace = True
    configuration.type = remote_configuration_release.get("type", "general")

    configuration.save()

    with transaction.atomic():
        CeleryTask.objects.select_related().select_for_update().filter(id=task_id)

        manifest_dependencies = configuration.manifest.get("dependencies", [])
        manifest_actions = configuration.manifest.get("actions", [])

        parent_options_object["dependencies"] = manifest_dependencies
        parent_options_object["actions"] = manifest_actions
        parent_options_object.pop("access_token", None)

        parent_task.options_object = parent_options_object
        parent_task.save(force_update=True)

        _l.info(f"parent_task id={parent_task.id} options={parent_task.options_object}")

        celery_task_list = []
        for step, dependency in enumerate(manifest_dependencies, start=1):
            child_celery_task = CeleryTask.objects.create(
                master_user=parent_task.master_user,
                member=parent_task.member,
                parent=parent_task,
                verbose_name="Install Configuration From Marketplace",
                type="install_configuration_from_marketplace",
            )

            dependency_channel = remote_configuration_release["channel"]

            if "channel" in dependency:
                dependency_channel = dependency["channel"]

            child_options_object = {
                "configuration_code": dependency["configuration_code"],
                "version": dependency["version"],
                "channel": dependency_channel,
                "is_package": False,
                "step": step,
                # "access_token": access_token
            }

            child_celery_task.options_object = child_options_object
            child_celery_task.save()

            celery_task_list.append(child_celery_task)

        parent_task.update_progress(
            {
                "current": 0,
                "total": len(manifest_dependencies) + len(manifest_actions),
                "percent": 0,
                "description": "Installation started",
            }
        )

        parent_task.refresh_from_db()
        _l.info(
            f"parent_task id={parent_task.id} options={parent_task.options_object} "
            f"progres={parent_task.progress}"
            f"created {len(parent_task.options_object.get('dependencies', [])) + 1}"
            f" child tasks, starting workflow..."
        )

    for i, celery_task in enumerate(celery_task_list):
        try:
            install_configuration_from_marketplace(task_id=celery_task.id)
        except Exception as e:
            celery_task_list = celery_task_list[i + 1 :]
            for celery_task in celery_task_list:
                celery_task.status = CeleryTask.STATUS_CANCELED
            CeleryTask.objects.bulk_update(celery_task_list, ["status"])
            raise e

    parent_task.update_progress(
        {
            "current": len(manifest_dependencies),
            "total": len(manifest_dependencies) + len(manifest_actions),
            "percent": 100,
            "description": "Installation complete",
        }
    )

    try:
        if configuration.manifest and "primary_module" in configuration.manifest:
            primary_configuration = Configuration.objects.get(
                configuration_code=configuration.manifest["primary_module"]
            )
            primary_configuration.is_primary = True
            primary_configuration.save()

    except Exception as e:
        _l.error(f"install_package_from_marketplace error: {str(e)}")

    if manifest_actions:
        total = len(manifest_dependencies) + len(manifest_actions)
        step = len(manifest_dependencies)
        percent = int((step / total) * 100)
        parent_task.update_progress(
            {
                "current": step,
                "total": total,
                "percent": percent,
                "description": "Run actions",
            }
        )

        for action in manifest_actions:
            _run_action(parent_task, action)

            step = step + 1
            percent = int((step / total) * 100)
            parent_task.update_progress(
                {
                    "current": step,
                    "total": total,
                    "percent": percent,
                    "description": "Run actions",
                }
            )

        _l.info("Workflows uploaded")

    parent_task.status = CeleryTask.STATUS_DONE
    parent_task.verbose_result = "Configuration package installed successfully"
    parent_task.save()

    # # .si is important, we do not need to pass result from previous task
    # workflow_list = [
    #     install_configuration_from_marketplace.si(task_id=celery_task.id)
    #     for celery_task in celery_task_list
    # ]
    # workflow_list.append(finish_package_install.si(task_id=parent_task.id))
    # workflow = chain(*workflow_list)
    # # execute the chain
    #
    # # workflow.apply_async()
    # workflow()
