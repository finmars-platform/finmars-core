import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db.models import ProtectedError
from django.utils.translation import gettext_lazy
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
from poms.currencies.constants import DASH

_l = logging.getLogger("poms.common.mixins")


class ListLightModelMixin(ListModelMixin):
    """
    Needs for when creating default IAM policies
    """

    pass


class ListEvModelMixin(ListModelMixin):
    """
    Needs for when creating default IAM policies
    """

    pass


# noinspection PyUnresolvedReferences
class DestroyModelMixinExt(DestroyModelMixin):
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: gettext_lazy(
                        "Cannot delete instance because they are referenced through a protected foreign key"
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        _l.info(
            f"{self.__class__.__name__}.perform_destroy instance="
            f"{instance.__class__.__name__}"
        )

        if hasattr(instance, "is_deleted") and hasattr(instance, "fake_delete"):
            instance.fake_delete()
        else:
            super().perform_destroy(instance)
            
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if hasattr(instance, 'user_code'):
            if instance.user_code == DASH:
                return Response({
                    "message": "Cannot delete instance because they are referenced through a protected foreign key",
                },
                    status=status.HTTP_409_CONFLICT,
                )
        return super().destroy(request, *args, **kwargs)


# noinspection PyUnresolvedReferences
class UpdateModelMixinExt(UpdateModelMixin):
    def update(self, request, *args, **kwargs):
        response = super(UpdateModelMixinExt, self).update(request, *args, **kwargs)
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
            super(DestroySystemicModelMixin, self).perform_destroy(instance)


# noinspection PyUnresolvedReferences
class BulkDestroyModelMixin(DestroyModelMixin):
    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request):
        data = request.data

        from poms.celery_tasks.models import CeleryTask

        queryset = self.filter_queryset(self.get_queryset())

        content_type = ContentType.objects.get_for_model(queryset.model)
        content_type_key = f"{content_type.app_label}.{content_type.model}"

        options_object = {"content_type": content_type_key, "ids": data["ids"]}

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_name="Bulk Delete",
            type="bulk_delete",
        )

        from poms_app import celery_app

        celery_app.send_task(
            "celery_tasks.bulk_delete",
            kwargs={"task_id": celery_task.id},
            queue="backend-background-queue",
        )

        # queryset = self.filter_queryset(self.get_queryset())
        # # is_fake = bool(request.query_params.get('is_fake'))
        #
        # _l.info('bulk_delete %s' % data['ids'])
        #
        #
        # try:
        #     if queryset.model._meta.get_field('is_deleted'):
        #
        #         # _l.info('bulk delete %s'  % queryset.model._meta.get_field('is_deleted'))
        #
        #         queryset = queryset.filter(id__in=data['ids'])
        #
        #         for instance in queryset:
        #             # try:
        #             #     self.check_object_permissions(request, instance)
        #             # except PermissionDenied:
        #             #     raise
        #             self.perform_destroy(instance)
        # except Exception as e:
        #
        #         # mostly for prices
        #
        #         queryset.filter(id__in=data['ids']).delete()

        # for pk in data['ids']:
        #
        #     try:
        #         instance = queryset.get(pk=pk)
        #
        #         try:
        #             self.check_object_permissions(request, instance)
        #         except PermissionDenied:
        #             raise
        #         self.perform_destroy(instance)
        #
        #     except ObjectDoesNotExist:
        #         print("object does not exist")

        # if not is_fake:
        #     for instance in queryset:
        #         try:
        #             self.check_object_permissions(request, instance)
        #         except PermissionDenied:
        #             raise
        #         self.perform_destroy(instance)

        return Response({"task_id": celery_task.id})


class BulkCreateModelMixin(CreateModelMixin):
    pass
    # Now BulkCreate is not supported
    # @action(detail=False, methods=['post'], url_path='bulk-create')
    # def bulk_create(self, request):
    #     data = request.data
    #     if not isinstance(data, list):
    #         raise ValidationError(gettext_lazy('Required list'))
    #
    #     has_error = False
    #     serializers = []
    #     for adata in data:
    #         serializer = self.get_serializer(data=adata)
    #         if not serializer.is_valid(raise_exception=False):
    #             has_error = True
    #         serializers.append(serializer)
    #
    #     if has_error:
    #         errors = []
    #         for serializer in serializers:
    #             errors.append(serializer.errors)
    #         raise ValidationError(errors)
    #     else:
    #         instances = []
    #         for serializer in serializers:
    #             self.perform_create(serializer)
    #             instances.append(serializer.instance)
    #         ret_serializer = self.get_serializer(instance=instances, many=True)
    #         return Response(list(ret_serializer.data), status=status.HTTP_201_CREATED)


class BulkUpdateModelMixin(UpdateModelMixin):
    pass
    # Now BulkUpdate is not supported
    # @action(detail=False, methods=['put', 'patch'], url_path='bulk-update')
    # def bulk_update(self, request):
    #     data = request.data
    #     if not isinstance(data, list):
    #         raise ValidationError(gettext_lazy('Required list'))
    #
    #     partial = request.method.lower() == 'patch'
    #     # queryset = self.filter_queryset(self.get_queryset())
    #     queryset = self.get_queryset()
    #
    #     has_error = False
    #     serializers = []
    #     for adata in data:
    #         pk = adata['id']
    #         try:
    #             instance = queryset.get(pk=pk)
    #         except ObjectDoesNotExist:
    #             has_error = True
    #             serializers.append(None)
    #         else:
    #             try:
    #                 self.check_object_permissions(request, instance)
    #             except PermissionDenied:
    #                 raise
    #
    #             serializer = self.get_serializer(instance=instance, data=adata, partial=partial)
    #             if not serializer.is_valid(raise_exception=False):
    #                 has_error = True
    #             serializers.append(serializer)
    #
    #     if has_error:
    #         errors = []
    #         for serializer in serializers:
    #             if serializer:
    #                 errors.append(serializer.errors)
    #             else:
    #                 errors.append({
    #                     api_settings.NON_FIELD_ERRORS_KEY: gettext_lazy('Not Found')
    #                 })
    #         raise ValidationError(errors)
    #     else:
    #         instances = []
    #         for serializer in serializers:
    #             self.perform_update(serializer)
    #             instances.append(serializer.instance)
    #
    #         ret_serializer = self.get_serializer(
    #             instance=queryset.filter(pk__in=(i.id for i in instances)), many=True)
    #         return Response(list(ret_serializer.data), status=status.HTTP_200_OK)


class BulkSaveModelMixin(CreateModelMixin, UpdateModelMixin):
    pass
    # Now BulkSave is not supported
    # @action(detail=False, methods=['post', 'put', 'patch'], url_path='bulk-save')
    # def bulk_save(self, request):
    #     data = request.data
    #     if not isinstance(data, list):
    #         raise ValidationError(gettext_lazy('Required list'))
    #
    #     partial = request.method.lower() == 'patch'
    #     queryset = self.filter_queryset(self.get_queryset())
    #
    #     has_error = False
    #     serializers = []
    #     for adata in data:
    #         pk = adata.get('id', None)
    #         if pk is None:
    #             serializer = self.get_serializer(data=adata)
    #             if not serializer.is_valid(raise_exception=False):
    #                 has_error = True
    #             serializers.append(serializer)
    #         else:
    #             try:
    #                 instance = queryset.get(pk=pk)
    #             except ObjectDoesNotExist:
    #                 has_error = True
    #                 serializers.append(None)
    #             else:
    #                 try:
    #                     self.check_object_permissions(request, instance)
    #                 except PermissionDenied:
    #                     raise
    #                 serializer = self.get_serializer(instance=instance, data=adata, partial=partial)
    #                 if not serializer.is_valid(raise_exception=False):
    #                     has_error = True
    #                 serializers.append(serializer)
    #
    #     if has_error:
    #         errors = []
    #         for serializer in serializers:
    #             if serializer:
    #                 errors.append(serializer.errors)
    #             else:
    #                 errors.append({
    #                     api_settings.NON_FIELD_ERRORS_KEY: gettext_lazy('Not Found')
    #                 })
    #         raise ValidationError(errors)
    #     else:
    #         instances = []
    #         for serializer in serializers:
    #             if serializer.instance is None:
    #                 self.perform_create(serializer)
    #             else:
    #                 self.perform_update(serializer)
    #             instances.append(serializer.instance)
    #
    #         ret_serializer = self.get_serializer(
    #             instance=queryset.filter(pk__in=(i.id for i in instances)), many=True)
    #         return Response(list(ret_serializer.data), status=status.HTTP_200_OK)


# BulkSaveModelMixin have some problem with permissions
class BulkModelMixin(BulkCreateModelMixin, BulkUpdateModelMixin, BulkDestroyModelMixin):
    pass

    # Now BulkModelMixin is not used
    # @action(detail=False, methods=['post', 'put', 'patch', 'delete'], url_path='bulk')
    # def bulk_dispatch(self, request):
    #     method = request.method.lower()
    #
    #     if method == 'post':
    #         return self.bulk_create(request)
    #     elif method in ['put', 'patch']:
    #         return self.bulk_update(request)
    #     elif method in ['delete']:
    #         return self.bulk_delete(request)
    #
    #     raise MethodNotAllowed(request.method)
