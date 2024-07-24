import contextlib
import logging
import traceback
from datetime import datetime, timedelta, timezone

from django.contrib.contenttypes.models import ContentType
import django.db.utils
from django.utils.timezone import now

from celery.utils.log import get_task_logger

from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.system_messages.handlers import send_system_message
from poms.users.models import MasterUser
from poms_app.celery import app

celery_logger = get_task_logger(__name__)
_l = logging.getLogger("poms.celery_tasks")


@finmars_task(name="celery_tasks.remove_old_tasks", bind=True)
def remove_old_tasks(self, *args, **kwargs):
    try:
        tasks = CeleryTask.objects.filter(created__lte=now() - timedelta(days=30))

        count = tasks.count()

        _l.info(f"Delete {count} tasks")
        # Only one Space per Scheme
        master_user = MasterUser.objects.all().first()
        tasks.delete()

        send_system_message(
            master_user=master_user,
            type="info",
            title="Old Task Clearance",
            description=f"Finmars removed {count} tasks",
        )

    except Exception as e:
        # Only one Space per Scheme
        master_user = MasterUser.objects.all().first()

        send_system_message(
            master_user=master_user,
            action_status="required",
            type="warning",
            title="Could not delete old Tasks",
            description=str(e),
        )

        _l.error(f"remove_old_tasks.exception {repr(e)} {traceback.format_exc()}")


@finmars_task(name="celery_tasks.auto_cancel_task_by_ttl")
def auto_cancel_task_by_ttl(*args, **kwargs):
    try:
        tasks = CeleryTask.objects.filter(
            status=CeleryTask.STATUS_PENDING, expiry_at__lte=now()
        )

        for task in tasks:
            if not task.notes:
                task.notes = ""

            task.notes = task.notes + "Task was cancelled by TTL \n"

            task.status = CeleryTask.STATUS_TIMEOUT
            task.save()

    except Exception as e:
        master_user = MasterUser.objects.all().first()

        send_system_message(
            master_user=master_user,
            action_status="required",
            type="warning",
            title="Could not cancel tasks by ttl",
            description=str(e),
        )

        _l.error(
            f"auto_cancel_task_by_ttl.exception {repr(e)} {traceback.format_exc()}"
        )


@finmars_task(name="celery_tasks.check_for_died_workers")
def check_for_died_workers(*args, **kwargs):
    # Create an inspect instance
    inspect_instance = app.control.inspect()

    tasks = CeleryTask.objects.filter(status=CeleryTask.STATUS_PENDING)

    _l.info(f"check_for_died_workers.pending_tasks {len(tasks)}")

    # Get the active workers
    active_workers = inspect_instance.active()
    if not active_workers:
        _l.info("check_for_died_workers.no_active_workers")

        for task in tasks:
            task.status = CeleryTask.STATUS_CANCELED
            task.error_message = "No active workers"
            task.save()

    for task in tasks:
        worker_name = task.worker_name

        # Get stats of the worker processing this task
        worker_stats = inspect_instance.stats().get(worker_name, {})
        uptime = worker_stats.get("uptime")  # This is in seconds

        if not uptime:
            continue

        worker_start_time = datetime.now(timezone.utc) - timedelta(seconds=uptime)

        # Compare worker start time with task's created time
        if task.modified > worker_start_time:
            # The task was created before the worker started (worker restarted after picking the task)
            task.error_message = "Worker probably died after picking the task"
            task.status = CeleryTask.STATUS_CANCELED
            task.save()
            _l.info(f"check_for_died_workers. Task {task.id} canceled due worker died")


@finmars_task(name="celery_tasks.bulk_delete", bind=True)
def bulk_delete(self, task_id, *args, **kwargs):
    # is_fake = bool(request.query_params.get('is_fake'))

    celery_task = CeleryTask.objects.get(id=task_id)
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    options_object = celery_task.options_object

    _l.info(
        f"bulk_delete: task_id {task_id} content_type {options_object['content_type']}"
        f" options_object {options_object}"
    )

    content_type_pieces = options_object["content_type"].split(".")

    content_type = ContentType.objects.get(
        app_label=content_type_pieces[0],
        model=content_type_pieces[1],
    )

    celery_task.update_progress(
        {
            "current": 0,
            "total": len(options_object["ids"]),
            "percent": 0,
            "description": "Bulk delete initialized",
        }
    )

    to_be_deleted_queryset = content_type.model_class().objects.filter(
        id__in=options_object["ids"]
    )

    last_exception = None
    for count, instance in enumerate(to_be_deleted_queryset, start=1):
        try:
            if hasattr(instance, "is_deleted") and hasattr(instance, "fake_delete") and not instance.is_deleted:
                instance.fake_delete()
            else:
                instance.delete()
            description = f"Instance {instance.id} was deleted"
        except Exception as e:
            last_exception = e
            description = f"Instance {instance.id} was not deleted"

        celery_task.update_progress({
            "current": count,
            "total": len(options_object["ids"]),
            "percent": round(count / (len(options_object["ids"]) / 100)),
            "description": description,
        })
    if last_exception:
        err_msg = f"bulk_delete exception {repr(last_exception)} {traceback.format_exception(last_exception)}"
        _l.info(err_msg)  # sentry detects it as error, but it maybe not
        _l.info(f'options_object["content_type"] {options_object["content_type"]}')
        raise RuntimeError(err_msg) from last_exception


@finmars_task(name="celery_tasks.bulk_restore", bind=True)
def bulk_restore(self, task_id, *args, **kwargs):
    celery_task = CeleryTask.objects.get(id=task_id)
    celery_task.celery_task_id = self.request.id

    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    options_object = celery_task.options_object

    _l.info(
        f"bulk_restore: task_id {task_id} content_type {options_object['content_type']}"
        f" options_object {options_object}"
    )

    celery_task.update_progress(
        {
            "current": 0,
            "total": len(options_object["ids"]),
            "percent": 0,
            "description": "Bulk restore initialized",
        }
    )

    content_type_pieces = options_object["content_type"].split(".")

    content_type = ContentType.objects.get(
        app_label=content_type_pieces[0],
        model=content_type_pieces[1],
    )

    queryset = content_type.model_class().objects.filter(id__in=options_object["ids"])

    try:
        if content_type.model_class()._meta.get_field("is_deleted"):
            for count, instance in enumerate(queryset, start=1):
                instance.restore()
                celery_task.update_progress(
                    {
                        "current": count,
                        "total": len(options_object["ids"]),
                        "percent": round(count / (len(options_object["ids"]) / 100)),
                        "description": f"Instance {instance.id} was restored",
                    }
                )

            celery_task.status = CeleryTask.STATUS_DONE
            celery_task.mark_task_as_finished()

    except Exception as e:
        err_msg = f"bulk_restore exception {repr(e)} {traceback.format_exc()}"
        _l.error(f"content_type={options_object['content_type']}: {err_msg}")

        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.error_message = err_msg
        raise RuntimeError(err_msg) from e

    finally:
        celery_task.save()


def import_item(item, context):
    from poms.common.utils import get_content_type_by_name, get_serializer
    from poms.transactions.handlers import TransactionTypeProcess
    from poms.transactions.models import TransactionType

    meta = item.get("meta", None)

    if not meta:
        raise ValueError("Meta is not found. Could not process JSON")

    if meta["content_type"] == "transactions.complextransaction":
        transaction_type = TransactionType.objects.get(
            user_code=item["transaction_type"]
        )

        values = {}

        for input in item["inputs"]:
            if input["value_type"] == 10 :
                values[input["transaction_type_input"]] = input["value_string"]

            elif input["value_type"] == 20:
                values[input["transaction_type_input"]] = input["value_float"]

            elif input["value_type"] == 40:
                values[input["transaction_type_input"]] = input["value_date"]

            elif input["value_type"] == 110:
                values[input["transaction_type_input"]] = input["value_string"]

            elif input["value_type"] == 100:
                content_type_key = input["content_type"]

                content_type = get_content_type_by_name(content_type_key)
                with contextlib.suppress(Exception):
                    values[
                        input["transaction_type_input"]
                    ] = content_type.model_class().objects.get(
                        user_code=input["value_relation"]
                    )

        process_instance = TransactionTypeProcess(
            transaction_type=transaction_type,
            default_values=values,
            context=context,
            member=context["member"],
            source=item["source"],
            linked_import_task=context.get("task"),
        )

        process_instance.process()

    else:
        serializer_class = get_serializer(meta["content_type"])

        serializer = serializer_class(data=item, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.save()


@finmars_task(name="celery_tasks.universal_input", bind=True)
def universal_input(self, task_id, *args, **kwargs):
    from poms.common.models import ProxyRequest, ProxyUser

    # is_fake = bool(request.query_params.get('is_fake'))

    _l.info(f"universal_input.task_id {task_id}")

    celery_task = CeleryTask.objects.get(id=task_id)
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    result = {}
    try:
        data = celery_task.options_object

        proxy_user = ProxyUser(celery_task.member, celery_task.master_user)

        proxy_request = ProxyRequest(proxy_user)

        context = {
            "master_user": celery_task.master_user,
            "member": celery_task.member,
            "request": proxy_request,
            "task": celery_task,
        }

        if isinstance(data, dict):
            data = [data]

        for i, item in enumerate(data, start=1):
            try:
                import_item(item, context)
                result[str(i)] = {"status": "success"}

            except Exception as e:
                result[str(i)] = {"status": "error", "error_message": str(e)}

            celery_task.update_progress(
                {
                    "current": i,
                    "total": len(data),
                    "percent": round(i / (len(data) / 100)),
                    "description": f"Going to import {i}",
                }
            )

        celery_task.result_object = result
        celery_task.status = CeleryTask.STATUS_DONE
        celery_task.mark_task_as_finished()
        celery_task.save()

    except Exception as e:
        err_msg = f"universal_input exception {repr(e)} {traceback.format_exc()}"
        celery_task.result_object = result
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.error_message = err_msg
        celery_task.save()
        raise RuntimeError(err_msg) from e
