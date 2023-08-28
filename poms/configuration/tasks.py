import json
import logging
import os
import traceback
from datetime import date

import requests
from celery import chain
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
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
    list_json_files,
    read_json_file,
    run_workflow,
    save_directory_to_storage,
    save_json_to_file,
    unzip_to_directory,
    upload_directory_to_storage,
    wait_workflow_until_end,
)
from poms.file_reports.models import FileReport
from poms_app import settings

_l = logging.getLogger("poms.configuration")

User = get_user_model()
storage = get_storage()


@finmars_task(name="configuration.import_configuration", bind=True)
def import_configuration(self, task_id):
    _l.info("import_configuration")
    _l.info("import_configuration %s" % task_id)

    task = CeleryTask.objects.get(id=task_id)
    task.celery_task_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    task.save()

    def generate_json_report(task, stats):
        result = stats

        current_date_time = now().strftime("%Y-%m-%d-%H-%M")
        file_name = "file_report_%s_task_%s.json" % (current_date_time, task.id)

        file_report = FileReport()

        _l.info("TransactionImportProcess.generate_json_report uploading file")

        file_report.upload_file(
            file_name=file_name,
            text=json.dumps(result, indent=4, default=str),
            master_user=task.master_user,
        )
        file_report.master_user = task.master_user
        file_report.name = "Configuration Import %s (Task %s).json" % (
            current_date_time,
            task.id,
        )
        file_report.file_name = file_name
        file_report.type = "configuration.import_configuration"
        file_report.notes = "System File"
        file_report.content_type = "application/json"

        file_report.save()

        _l.info("ConfigurationImportManager.json_report %s" % file_report)
        _l.info("ConfigurationImportManager.json_report %s" % file_report.file_url)

        return file_report

    try:
        proxy_user = ProxyUser(task.member, task.master_user)
        proxy_request = ProxyRequest(proxy_user)

        context = {
            "master_user": task.master_user,
            "member": task.member,
            "request": proxy_request,
        }

        file_path = task.options_object["file_path"]

        _l.info("import_configuration got %s" % file_path)

        output_directory = os.path.join(
            settings.BASE_DIR, "configurations/" + str(task.id) + "/source"
        )

        if not os.path.exists(
                os.path.join(
                    settings.BASE_DIR, "configurations/" + str(task.id) + "/source"
                )
        ):
            os.makedirs(output_directory, exist_ok=True)

        unzip_to_directory(file_path, output_directory)

        _l.info("import_configuration unzip_to_directory %s" % output_directory)

        try:
            manifest = read_json_file(os.path.join(output_directory, "manifest.json"))

        except Exception as e:
            _l.error("import_configuration read_json_file %s" % e)
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

        index = 1

        stats = {"configuration": {}}

        for json_file in json_files:
            if "manifest.json" in json_file:
                index = index + 1
                continue

            if "workflows" in json_file:  # skip all json files that workflows
                index = index + 1
                continue

            task.update_progress(
                {
                    "current": index,
                    "total": len(json_files),
                    "percent": round(index / (len(json_files) / 100)),
                    "description": "Going to import %s" % json_file,
                }
            )

            try:
                json_data = read_json_file(json_file)

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
                        pass

                else:
                    instance = None

                serializer = SerializerClass(
                    instance=instance, data=json_data, context=context
                )

                if serializer.is_valid():
                    # Perform any desired actions, such as saving the data to the database
                    serializer.save()

                    stats["configuration"][json_file] = {"status": "success"}

                    task.update_progress(
                        {
                            "current": index,
                            "total": len(json_files),
                            "percent": round(index / (len(json_files) / 100)),
                            "description": "Imported %s" % json_file,
                        }
                    )

                else:
                    stats["configuration"][json_file] = {
                        "status": "error",
                        "error_message": str(serializer.errors),
                    }

                    _l.error(f"Invalid data in {json_file}: {serializer.errors}")

                    task.update_progress(
                        {
                            "current": index,
                            "total": len(json_files),
                            "percent": round(index / (len(json_files) / 100)),
                            "description": "Error %s" % json_file,
                        }
                    )

            except Exception as e:
                _l.error("import_configuration e %s" % e)
                _l.error("import_configuration traceback %s" % traceback.format_exc())

                stats["configuration"][json_file] = {
                    "status": "error",
                    "error_message": str(e),
                }

                task.update_progress(
                    {
                        "current": index,
                        "total": len(json_files),
                        "percent": round(index / (len(json_files) / 100)),
                        "description": "Error %s" % json_file,
                    }
                )

            index = index + 1

        # Import Workflows

        if manifest:
            # only if manifest is present

            configuration_code_as_path = "/".join(
                manifest["configuration_code"].split(".")
            )

            dest_workflow_directory = (
                    settings.BASE_API_URL + "/workflows/" + configuration_code_as_path
            )

            _l.info("dest_workflow_directory %s" % dest_workflow_directory)

            upload_directory_to_storage(
                output_directory + "/workflows", dest_workflow_directory
            )

            if manifest.get("actions", None):
                for action in manifest["actions"]:
                    workflow = action.get("workflow", None)

                    if workflow:
                        try:
                            _l.info(
                                "import_configuration.going to execute workflow %s"
                                % workflow
                            )

                            response_data = run_workflow(workflow, {})

                            id = response_data["id"]

                            response_data = wait_workflow_until_end(id)

                            _l.info(
                                "import_configuration.workflow finished %s"
                                % response_data
                            )

                        except Exception as e:
                            _l.error("Could not execute workflow e %s" % e)
                            _l.error(
                                "Could not execute workflow traceback %s"
                                % traceback.format_exc()
                            )

        _l.info("Workflows uploaded")

        file_report = generate_json_report(task, stats)

        task.add_attachment(file_report.id)

        task.status = CeleryTask.STATUS_DONE
        task.save()

    except Exception as e:
        _l.error("import_configuration error: %s" % str(e))
        _l.error("import_configuration traceback: %s" % traceback.format_exc())

        task.status = CeleryTask.STATUS_ERROR
        task.error_message = str(e)
        task.save()


@finmars_task(name="configuration.export_configuration", bind=True)
def export_configuration(self, task_id):
    _l.info("export_configuration")

    task = CeleryTask.objects.get(id=task_id)
    task.celery_task_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    task.save()

    try:
        configuration_code = task.options_object["configuration_code"]

        configuration = Configuration.objects.get(configuration_code=configuration_code)

        _l.info("configuration %s" % configuration)

        # zip_filename = configuration.name + '.zip'
        source_directory = os.path.join(
            settings.BASE_DIR, "configurations/" + str(task.id) + "/source"
        )
        # output_zipfile = os.path.join(settings.BASE_DIR,
        #   'configurations/' + str(task.id) + '/' + zip_filename)

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

        manifest_filepath = source_directory + "/manifest.json"

        manifest = configuration.manifest or {
            "name": configuration.name,
            "configuration_code": configuration.configuration_code,
            "version": configuration.version,
            "date": str(date.today()),
        }

        save_json_to_file(manifest_filepath, manifest)

        if configuration.is_from_marketplace:
            storage_directory = (
                    settings.BASE_API_URL
                    + "/configurations/"
                    + configuration.configuration_code
                    + "/"
                    + configuration.version
                    + "/"
            )
        else:
            storage_directory = (
                    settings.BASE_API_URL
                    + "/configurations/custom/"
                    + configuration.configuration_code
                    + "/"
                    + configuration.version
                    + "/"
            )

        save_directory_to_storage(source_directory, storage_directory)

        # Create Configuration zip file
        # zip_directory(source_directory, output_zipfile)

        # storage.save(output_zipfile, tmpf)

        # response = DeleteFileAfterResponse(open(output_zipfile, 'rb'), content_type='application/zip',
        #                                    path_to_delete=output_zipfile)
        # response['Content-Disposition'] = u'attachment; filename="{filename}'.format(
        #     filename=zip_filename)

        _l.info("export_configuration. Done")

        task.status = CeleryTask.STATUS_DONE
        task.save()

    except Exception as e:
        _l.error("export_configuration error: %s" % str(e))
        _l.error("export_configuration traceback: %s" % traceback.format_exc())

        task.status = CeleryTask.STATUS_ERROR
        task.error_message = str(e)
        task.save()


@finmars_task(name="configuration.push_configuration_to_marketplace", bind=True)
def push_configuration_to_marketplace(self, task_id):
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

    try:
        configuration = Configuration.objects.get(
            configuration_code=options_object["configuration_code"]
        )

        if configuration.is_from_marketplace:
            path = (
                    settings.BASE_API_URL
                    + "/configurations/"
                    + configuration.configuration_code
                    + "/"
                    + configuration.version
            )
        else:
            path = (
                    settings.BASE_API_URL
                    + "/configurations/custom/"
                    + configuration.configuration_code
                    + "/"
                    + configuration.version
            )

        zip_file_path = storage.download_directory_as_zip(path)

        data = {
            "configuration_code": configuration.configuration_code,
            "name": configuration.name,
            "version": configuration.version,
            "description": configuration.description,
            "author": username,
            "changelog": options_object.get("changelog", ""),
            "manifest": json.dumps(configuration.manifest),
        }

        _l.info("push_configuration_to_marketplace.data %s" % data)
        _l.info("push_configuration_to_marketplace.zip_file_path %s" % zip_file_path)

        files = {"file": open(zip_file_path, "rb")}

        # headers = {}
        # headers['Authorization'] = 'Token ' + access_token

        # _l.info('refresh %s' % refresh.access_token)

        headers = {"Content-type": "application/json", "Accept": "application/json"}

        response = requests.post(
            url="https://marketplace.finmars.com/api/v1/login/",
            json={"username": username, "password": password},
            headers=headers,
        )

        auth_data = response.json()

        # _l.info('data %s' % data)

        token = auth_data["token"]

        headers = {"Authorization": "Token %s" % token}

        # _l.info('push_configuration_to_marketplace.headers %s' % headers)

        response = requests.post(
            url="https://marketplace.finmars.com/api/v1/configuration/push/",
            data=data,
            files=files,
            headers=headers,
        )

        if response.status_code != 200:
            task.status = CeleryTask.STATUS_ERROR
            task.error_message = str(response.text)
            task.save()

        else:
            _l.info(
                "push_configuration_to_marketplace.Configuration pushed to marketplace"
            )

            task.verbose_result = {"message": "Configuration pushed to marketplace"}
            task.status = CeleryTask.STATUS_DONE
            task.save()

    except Exception as e:
        _l.error("push_configuration_to_marketplace error: %s" % str(e))
        _l.error(
            "push_configuration_to_marketplace traceback: %s" % traceback.format_exc()
        )

        task.status = CeleryTask.STATUS_ERROR
        task.error_message = str(e)
        task.save()


@finmars_task(name="configuration.install_configuration_from_marketplace", bind=True)
def install_configuration_from_marketplace(self, **kwargs):
    task_id = kwargs.get("task_id")

    _l.info("install_configuration_from_marketplace")

    task = CeleryTask.objects.get(id=task_id)
    task.celery_task_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    task.save()

    try:
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
                "version": options_object["version"],
            }

            response = requests.post(
                url="https://marketplace.finmars.com/api/v1/configuration/find-release/",
                data=data,
                headers=headers,
            )

        if response.status_code != 200:
            task.status = CeleryTask.STATUS_ERROR
            task.error_message = str(response.text)
            task.save()
            raise Exception(response.text)

        remote_configuration_release = response.json()
        remote_configuration = remote_configuration_release["configuration_object"]

        _l.info("remote_configuration %s" % remote_configuration_release)

        try:
            configuration = Configuration.objects.get(
                configuration_code=remote_configuration["configuration_code"]
            )
        except Exception:
            configuration = Configuration.objects.create(
                configuration_code=remote_configuration["configuration_code"],
                version="0.0.0",
            )

        # Probably deprecated
        # if not is_newer_version(remote_configuration_release['version'], configuration.version):
        #
        #     if remote_configuration_release['version'] == configuration.version:
        #         task.verbose_result = {"message": "Local Configuration has equal version %s to proposed %s" % (
        #             configuration.version, remote_configuration_release['version'])}
        #     else:
        #         task.verbose_result = {"message": "Local Configuration has newer version %s then proposed %s" % (
        #             configuration.version, remote_configuration_release['version'])}
        #
        #     task.status = CeleryTask.STATUS_DONE
        #     task.save()
        #     return

        configuration.name = remote_configuration["name"]
        configuration.description = remote_configuration["description"]
        configuration.version = remote_configuration_release["version"]
        configuration.is_package = False
        configuration.manifest = remote_configuration_release["manifest"]
        configuration.is_from_marketplace = True

        configuration.save()

        if task.parent:
            step = task.options_object["step"]
            total = len(task.parent.options_object["dependencies"])
            percent = int((step / total) * 100)

            description = "Step %s/%s is installing. %s" % (
                step,
                total,
                configuration.name,
            )

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
            settings.BASE_DIR, "configurations/" + str(task.id) + "/archive.zip"
        )

        if response.status_code != 200:
            task.status = CeleryTask.STATUS_ERROR
            task.error_message = str(response.text)
            task.save()
            raise Exception(response.text)

        else:
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)

            # Write the file to the destination path
            with open(destination_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        import_configuration_celery_task = CeleryTask.objects.create(
            master_user=task.master_user,
            member=task.member,
            parent=task,
            verbose_name="Configuration Import",
            type="configuration_import",
        )

        options_object = {
            "file_path": destination_path,
        }

        import_configuration_celery_task.options_object = options_object
        import_configuration_celery_task.save()

        # sync call
        # .si is important, we do not need to pass result from previous task

        import_configuration(
            import_configuration_celery_task.id
        )  # seems self is not needed
        # result = import_configuration.apply_async(kwargs={'task_id': import_configuration_celery_task.id})

        if task.parent:
            step = task.options_object["step"]
            total = len(task.parent.options_object["dependencies"])
            percent = int((step / total) * 100)

            description = "Step %s/%s is installed. %s" % (
                step,
                total,
                configuration.name,
            )

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

    except Exception as e:
        _l.error("install_configuration_from_marketplace error: %s" % str(e))
        _l.error(
            "install_configuration_from_marketplace traceback: %s"
            % traceback.format_exc()
        )

        task.status = CeleryTask.STATUS_ERROR
        task.error_message = str(e)
        task.save()


@finmars_task(name="configuration.finish_package_install", bind=True)
def finish_package_install(self, task_id):
    task = CeleryTask.objects.get(id=task_id)
    task.status = CeleryTask.STATUS_DONE

    options = task.options_object

    _l.info("finish_package_install %s" % options)
    _l.info("finish_package_install task %s" % task.id)

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
    task.verbose_result = "Configuration package installed successfully"
    task.save()


@finmars_task(name="configuration.install_package_from_marketplace", bind=True)
def install_package_from_marketplace(self, task_id):
    _l.info("install_configuration_from_marketplace")

    task = CeleryTask.objects.get(id=task_id)
    # task.celery_task_id = self.request.id
    # task.status = CeleryTask.STATUS_PENDING
    # task.save()

    # try:

    options_object = task.options_object

    # TODO Implement when keycloak refactored
    # access_token = options_object['access_token']
    #
    # del options_object['access_token']

    # task.options_object = options_object
    # task.save()

    data = {
        "configuration_code": options_object["configuration_code"],
        "version": options_object["version"],
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
        task.status = CeleryTask.STATUS_ERROR
        task.error_message = str(response.text)
        task.save()
        raise Exception(response.text)

    remote_configuration_release = response.json()
    remote_configuration = remote_configuration_release["configuration_object"]

    _l.info("remote_configuration %s" % remote_configuration_release)

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
    configuration.is_package = True
    configuration.manifest = remote_configuration_release["manifest"]
    configuration.is_from_marketplace = True

    configuration.save()

    task_list = []

    step = 1

    manifest_dependencies = configuration.manifest.get("dependencies", [])
    # if not manifest_dependencies:
        # raise ValueError(
        #     "install_package_from_marketplace: invalid configuration, no dependencies !"
        # )

    options_object["dependencies"] = manifest_dependencies

    task.options_object = options_object
    task.save()

    _l.info("Main Task saved %s" % task.options_object)
    _l.info("Main Task id %s" % task.id)

    for dependency in manifest_dependencies:
        module_celery_task = CeleryTask.objects.create(
            master_user=task.master_user,
            member=task.member,
            parent=task,
            verbose_name="Install Configuration From Marketplace",
            type="install_configuration_from_marketplace",
        )

        child_options_object = {
            "configuration_code": dependency["configuration_code"],
            "version": dependency["version"],
            "is_package": False,
            "step": step
            # "access_token": access_token
        }

        module_celery_task.options_object = child_options_object
        module_celery_task.save()

        # .si is important, we do not need to pass result from previous task
        task_list.append(
            install_configuration_from_marketplace.si(task_id=module_celery_task.id)
        )

        step += 1

    # .si is important, we do not need to pass result from previous task
    task_list.append(finish_package_install.si(task_id=task.id))

    workflow = chain(*task_list)

    task.update_progress(
        {
            "current": 0,
            "total": len(manifest_dependencies),
            "percent": 0,
            "description": "Installation started",
        }
    )

    # execute the chain
    workflow.apply_async()

    # except Exception as e:
    #
    #     _l.error('install_configuration_from_marketplace error: %s' % str(e))
    #     _l.error('install_configuration_from_marketplace traceback: %s' % traceback.format_exc())
    #
    #     task.status = CeleryTask.STATUS_ERROR
    #     task.error_message = str(e)
    #     task.save()
