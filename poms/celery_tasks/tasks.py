import contextlib
import logging
import traceback
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now

from poms.celery_tasks import finmars_task
from celery import shared_task
from celery.utils.log import get_task_logger
from poms_app import settings

from poms.celery_tasks.models import CeleryTask
from poms.system_messages.handlers import send_system_message
from poms.users.models import MasterUser

celery_logger = get_task_logger(__name__)
_l = logging.getLogger("poms.celery_tasks")


# TODO Refactor to task_id
@finmars_task(name='celery_tasks.remove_old_tasks', bind=True)
def remove_old_tasks(self, *args, **kwargs):
    try:
        tasks = CeleryTask.objects.filter(created__lte=now() - timedelta(days=30))

        count = tasks.count()

        _l.info(f"Delete {count} tasks")
        master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)
        tasks.delete()

        send_system_message(
            master_user=master_user,
            type="info",
            title="Old Task Clearance",
            description=f"Finmars removed {count} tasks",
        )

    except Exception as e:
        master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

        send_system_message(
            master_user=master_user,
            action_status="required",
            type="warning",
            title="Could not delete old Tasks",
            description=str(e),
        )

        _l.error(f"remove_old_tasks.exception {repr(e)} {traceback.format_exc()}")


@finmars_task(name="celery_tasks.auto_cancel_task_by_ttl")
def auto_cancel_task_by_ttl():
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
        master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

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


@finmars_task(name="celery_tasks.bulk_delete", bind=True)
def bulk_delete(self, task_id):
    # is_fake = bool(request.query_params.get('is_fake'))

    _l.info(f"bulk_delete.task_id {task_id}")

    celery_task = CeleryTask.objects.get(id=task_id)
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    options_object = celery_task.options_object

    _l.info(f"bulk_delete.options_object {options_object}")

    content_type_pieces = options_object["content_type"].split(".")

    content_type = ContentType.objects.get(
        app_label=content_type_pieces[0], model=content_type_pieces[1]
    )

    queryset = content_type.model_class().objects.all()

    _l.info(f'bulk_delete {options_object["ids"]}')

    celery_task.update_progress(
        {
            "current": 0,
            "total": len(options_object["ids"]),
            "percent": 0,
            "description": "Bulk delete initialized",
        }
    )

    try:
        if content_type.model_class()._meta.get_field("is_deleted"):
            # _l.info('bulk delete %s'  % queryset.model._meta.get_field('is_deleted'))

            queryset = queryset.filter(id__in=options_object["ids"])

            count = 0

            items = list(queryset)

            for instance in items:
                # try:
                #     self.check_object_permissions(request, instance)
                # except PermissionDenied:
                #     raise
                instance.fake_delete()

                count = count + 1

                celery_task.update_progress(
                    {
                        "current": count,
                        "total": len(options_object["ids"]),
                        "percent": round(count / (len(options_object["ids"]) / 100)),
                        "description": f"Instance {instance.id} was deleted",
                    }
                )

    except Exception as e:
        _l.error(f"bulk_delete exception {repr(e)} {traceback.format_exc()}")

        if options_object["content_type"] in (
            "instruments.pricehistory",
            "currencies.currencyhistory",
        ):
            _l.info("Going to permanent delete.")
            queryset.filter(id__in=options_object["ids"]).delete()

    celery_task.status = CeleryTask.STATUS_DONE
    celery_task.mark_task_as_finished()
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
            if input["value_type"] == 10:
                values[input["transaction_type_input"]] = input["value_string"]

            if input["value_type"] == 20:
                values[input["transaction_type_input"]] = input["value_float"]

            if input["value_type"] == 40:
                values[input["transaction_type_input"]] = input["value_date"]

            if input["value_type"] == 110:
                values[input["transaction_type_input"]] = input["value_string"]

            if input["value_type"] == 100:
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
            execution_context="manual",
        )

        process_instance.process()

    else:
        serializer_class = get_serializer(meta["content_type"])

        serializer = serializer_class(data=item, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.save()


@finmars_task(name="celery_tasks.universal_input", bind=True)
def universal_input(self, task_id):
    # is_fake = bool(request.query_params.get('is_fake'))

    _l.info(f"universal_input.task_id {task_id}")

    celery_task = CeleryTask.objects.get(id=task_id)
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    result = {}

    try:
        data = celery_task.options_object

        from poms.common.models import ProxyUser

        proxy_user = ProxyUser(celery_task.member, celery_task.master_user)
        from poms.common.models import ProxyRequest

        proxy_request = ProxyRequest(proxy_user)

        context = {
            "master_user": celery_task.master_user,
            "member": celery_task.member,
            "request": proxy_request,
        }

        if isinstance(data, dict):
            data = [data]

        i = 1

        for item in data:
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

            i = i + 1

        celery_task.result_object = result
        celery_task.status = CeleryTask.STATUS_DONE
        celery_task.mark_task_as_finished()
        celery_task.save()

    except Exception as e:
        celery_task.result_object = result
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.error_message = str(e)
        celery_task.save()
