import itertools
import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    UpdateModelMixin,
)
from rest_framework.response import Response
from rest_framework.settings import api_settings

from poms.common.exceptions import FinmarsBaseException
from poms.common.serializers import BulkSerializer
from poms.common.utils import FinmarsNestedObjects
from poms.currencies.constants import DASH

_l = logging.getLogger("poms.common.mixins")


class ListLightModelMixin(ListModelMixin):
    """
    Needs for when creating default IAM policies
    """


class ListEvModelMixin(ListModelMixin):
    """
    Needs for when creating default IAM policies
    """


# noinspection PyUnresolvedReferences
class DestroyModelMixinExt(DestroyModelMixin):
    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            raise FinmarsBaseException(
                error_key=api_settings.NON_FIELD_ERRORS_KEY,
                message="Cannot delete instance because they are referenced through a protected foreign key",
                status_code=409,
            )


# noinspection PyUnresolvedReferences
class DestroyModelFakeMixin(DestroyModelMixinExt):
    def get_queryset(self):
        qs = super().get_queryset()
        try:
            qs.model._meta.get_field("is_deleted")
        except FieldDoesNotExist:
            return qs
        else:
            is_deleted = self.request.query_params.get("is_deleted", None)
            if is_deleted is None and getattr(self, "action", "") == "list":
                qs = qs.filter(is_deleted=False)
            return qs

    def perform_destroy(self, instance):
        _l.info(f"{self.__class__.__name__}.perform_destroy instance={instance.__class__.__name__}")

        if hasattr(instance, "is_deleted") and hasattr(instance, "fake_delete") and not instance.is_deleted:
            instance.fake_delete()
        else:
            super().perform_destroy(instance)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if hasattr(instance, "user_code") and instance.user_code == DASH:
            return Response(
                {
                    "message": "Cannot delete instance because they are referenced through a protected foreign key",
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["get"], url_path="delete")
    def delete_preview(self, request, *args, **kwargs):
        instance = self.get_object()

        collector = FinmarsNestedObjects(instance)
        collector.collect([instance])

        # need to sort items by class name because collect() gets model name from 1st list item
        protected = sorted(list(collector.protected), key=lambda instance: str(instance.__class__))
        protected_groups = [
            list(items_group) for _, items_group in itertools.groupby(protected, lambda item: str(item.__class__))
        ]
        for protected_items in protected_groups:
            collector.collect(protected_items)

        results = collector.nested()
        model_count = {
            f"{model._meta.app_label}.{model._meta.model_name}": len(objs)
            for model, objs in collector.model_objs.items()
        }
        return Response({"results": results, "counts": model_count})


# noinspection PyUnresolvedReferences
class UpdateModelMixinExt(UpdateModelMixin):
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        # total reload object, due many to many don't correctly returned
        if response.status_code == status.HTTP_200_OK:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)

        return response


# TODO: may be delete later
class DestroySystemicModelMixin(DestroyModelMixinExt):
    def perform_destroy(self, instance):
        if hasattr(instance, "is_systemic") and instance.is_systemic:
            raise MethodNotAllowed(
                "DELETE",
                detail='Method "DELETE" not allowed. Can not delete entity with is_systemic == true',
            )
        else:
            super().perform_destroy(instance)


# noinspection PyUnresolvedReferences
class BulkDestroyModelMixin(DestroyModelMixin):
    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request, realm_code=None, space_code=None):
        from poms.celery_tasks.models import CeleryTask
        from poms_app import celery_app

        serializer = BulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        queryset = self.filter_queryset(self.get_queryset())

        content_type = ContentType.objects.get(
            app_label=queryset.model._meta.app_label, model=queryset.model._meta.model_name
        )
        content_type_key = f"{content_type.app_label}.{content_type.model}"

        options_object = {"content_type": content_type_key, "ids": data["ids"]}

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_name="Bulk Delete",
            type="bulk_delete",
        )

        celery_app.send_task(
            "celery_tasks.bulk_delete",
            kwargs={
                "task_id": celery_task.id,
                "context": {"realm_code": request.realm_code, "space_code": request.space_code},
            },
            queue="backend-background-queue",
        )
        return Response({"task_id": celery_task.id})


class BulkRestoreModelMixin(DestroyModelMixin):
    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, realm_code=None, space_code=None):
        from poms.celery_tasks.models import CeleryTask
        from poms.celery_tasks.tasks import bulk_restore

        serializer = BulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        queryset = self.queryset

        if getattr(queryset.model, "deleted_user_code", None):
            codes_to_restore = queryset.filter(id__in=data["ids"]).values_list("deleted_user_code", flat=True)
            if existing_codes := queryset.filter(user_code__in=codes_to_restore).values_list(
                "user_code", flat=True
            ):
                return Response(
                    status=409,
                    data={
                        "error": f"Codes '{', '.join(existing_codes)}' already exist",
                        "error_key": "field_unique_constraint_violation",
                    },
                )
            if missing_ids := [str(id) for id in data["ids"] if not queryset.filter(id=id).exists()]:
                return Response(
                    status=404,
                    data={
                        "error": f"IDs '{', '.join(missing_ids)}' don`t exist",
                        "error_key": "value_does_not_exist",
                    },
                )

        content_type = ContentType.objects.get(
            app_label=queryset.model._meta.app_label, model=queryset.model._meta.model_name
        )
        content_type_key = f"{content_type.app_label}.{content_type.model}"

        options_object = {"content_type": content_type_key, "ids": data["ids"]}

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_name="Bulk Restore",
            type="bulk_restore",
        )

        bulk_restore.apply_async(
            kwargs={
                "task_id": celery_task.id,
                "context": {
                    "realm_code": request.realm_code,
                    "space_code": request.space_code,
                },
            }
        )

        return Response({"task": celery_task.id})


class BulkCreateModelMixin(CreateModelMixin):
    pass


class BulkUpdateModelMixin(UpdateModelMixin):
    pass


class BulkModelMixin(BulkCreateModelMixin, BulkUpdateModelMixin, BulkDestroyModelMixin, BulkRestoreModelMixin):
    pass
