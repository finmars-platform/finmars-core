from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist, FieldDoesNotExist
from django.db.models import ProtectedError
from django.utils.translation import ugettext_lazy
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError, PermissionDenied
from rest_framework.mixins import UpdateModelMixin, DestroyModelMixin, CreateModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.settings import api_settings


# TODO: Permissions for method and per-object must be verified!!!!

class DestroyModelMixinExt(DestroyModelMixin):
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response({
                api_settings.NON_FIELD_ERRORS_KEY: ugettext_lazy(
                    'Cannot delete instance because they are referenced through a protected foreign key'),
            }, status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DestroyModelFakeMixin(DestroyModelMixinExt):
    def get_queryset(self):
        qs = super(DestroyModelFakeMixin, self).get_queryset()
        try:
            qs.model._meta.get_field('is_deleted')
        except FieldDoesNotExist:
            return qs
        else:
            is_deleted = self.request.query_params.get('is_deleted', None)
            if is_deleted is None:
                if getattr(self, 'action', '') == 'list':
                    qs = qs.filter(is_deleted=False)
            return qs

    def perform_destroy(self, instance):
        # if getattr(self, 'has_feature_is_deleted', False):
        if hasattr(instance, 'is_deleted') and hasattr(instance, 'fake_delete'):
            instance.fake_delete()
        else:
            super(DestroyModelFakeMixin, self).perform_destroy(instance)


class UpdateModelMixinExt(UpdateModelMixin):
    def update(self, request, *args, **kwargs):
        response = super(UpdateModelMixinExt, self).update(request, *args, **kwargs)
        # total reload object, due many to many don't correctly returned
        if response.status_code == status.HTTP_200_OK:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        return response

        # Incorrect
        # def perform_update(self, serializer):
        #     if hasattr(serializer.instance, 'is_deleted') and hasattr(serializer.instance, 'fake_delete'):
        #         if serializer.is_deleted:
        #             raise PermissionDenied()
        #     return super(UpdateModelMixinExt, self).perform_update(serializer)


class BulkCreateModelMixin(CreateModelMixin):
    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        data = request.data
        if not isinstance(data, list):
            raise ValidationError(ugettext_lazy('Required list'))

        has_error = False
        serializers = []
        for adata in data:
            serializer = self.get_serializer(data=adata)
            if not serializer.is_valid(raise_exception=False):
                has_error = True
            serializers.append(serializer)

        if has_error:
            errors = []
            for serializer in serializers:
                errors.append(serializer.errors)
            raise ValidationError(errors)
        else:
            instances = []
            for serializer in serializers:
                self.perform_create(serializer)
                instances.append(serializer.instance)
            ret_serializer = self.get_serializer(instance=instances, many=True)
            return Response(list(ret_serializer.data), status=status.HTTP_201_CREATED)


class BulkUpdateModelMixin(UpdateModelMixin):
    @action(detail=False, methods=['put', 'patch'], url_path='bulk-update')
    def bulk_update(self, request):
        data = request.data
        if not isinstance(data, list):
            raise ValidationError(ugettext_lazy('Required list'))

        partial = request.method.lower() == 'patch'
        # queryset = self.filter_queryset(self.get_queryset())
        queryset = self.get_queryset()

        has_error = False
        serializers = []
        for adata in data:
            pk = adata['id']
            try:
                instance = queryset.get(pk=pk)
            except ObjectDoesNotExist:
                has_error = True
                serializers.append(None)
            else:
                try:
                    self.check_object_permissions(request, instance)
                except PermissionDenied:
                    raise

                serializer = self.get_serializer(instance=instance, data=adata, partial=partial)
                if not serializer.is_valid(raise_exception=False):
                    has_error = True
                serializers.append(serializer)

        if has_error:
            errors = []
            for serializer in serializers:
                if serializer:
                    errors.append(serializer.errors)
                else:
                    errors.append({
                        api_settings.NON_FIELD_ERRORS_KEY: ugettext_lazy('Not Found')
                    })
            raise ValidationError(errors)
        else:
            instances = []
            for serializer in serializers:
                self.perform_update(serializer)
                instances.append(serializer.instance)

            ret_serializer = self.get_serializer(
                instance=queryset.filter(pk__in=(i.id for i in instances)), many=True)
            return Response(list(ret_serializer.data), status=status.HTTP_200_OK)


class BulkSaveModelMixin(CreateModelMixin, UpdateModelMixin):
    @action(detail=False, methods=['post', 'put', 'patch'], url_path='bulk-save')
    def bulk_save(self, request):
        data = request.data
        if not isinstance(data, list):
            raise ValidationError(ugettext_lazy('Required list'))

        partial = request.method.lower() == 'patch'
        queryset = self.filter_queryset(self.get_queryset())

        has_error = False
        serializers = []
        for adata in data:
            pk = adata.get('id', None)
            if pk is None:
                serializer = self.get_serializer(data=adata)
                if not serializer.is_valid(raise_exception=False):
                    has_error = True
                serializers.append(serializer)
            else:
                try:
                    instance = queryset.get(pk=pk)
                except ObjectDoesNotExist:
                    has_error = True
                    serializers.append(None)
                else:
                    try:
                        self.check_object_permissions(request, instance)
                    except PermissionDenied:
                        raise
                    serializer = self.get_serializer(instance=instance, data=adata, partial=partial)
                    if not serializer.is_valid(raise_exception=False):
                        has_error = True
                    serializers.append(serializer)

        if has_error:
            errors = []
            for serializer in serializers:
                if serializer:
                    errors.append(serializer.errors)
                else:
                    errors.append({
                        api_settings.NON_FIELD_ERRORS_KEY: ugettext_lazy('Not Found')
                    })
            raise ValidationError(errors)
        else:
            instances = []
            for serializer in serializers:
                if serializer.instance is None:
                    self.perform_create(serializer)
                else:
                    self.perform_update(serializer)
                instances.append(serializer.instance)

            ret_serializer = self.get_serializer(
                instance=queryset.filter(pk__in=(i.id for i in instances)), many=True)
            return Response(list(ret_serializer.data), status=status.HTTP_200_OK)


class BulkDestroyModelMixin(DestroyModelMixin):
    @action(detail=False, methods=['get', 'post'], url_path='bulk-delete')
    def bulk_delete(self, request):

        print('Bulk delelete here')

        if request.method.lower() == 'get':
            return self.list(request)

        data = request.data

        queryset = self.filter_queryset(self.get_queryset())
        # is_fake = bool(request.query_params.get('is_fake'))

        for pk in data['ids']:

            try:
                instance = queryset.get(pk=pk)

                try:
                    self.check_object_permissions(request, instance)
                except PermissionDenied:
                    raise
                self.perform_destroy(instance)

            except ObjectDoesNotExist:
                print("object does not exist")

        # if not is_fake:
        #     for instance in queryset:
        #         try:
        #             self.check_object_permissions(request, instance)
        #         except PermissionDenied:
        #             raise
        #         self.perform_destroy(instance)

        return Response(status=status.HTTP_204_NO_CONTENT)


# BulkSaveModelMixin have some problem with permissions
class BulkModelMixin(BulkCreateModelMixin, BulkUpdateModelMixin, BulkDestroyModelMixin):
    @action(detail=False, methods=['post', 'put', 'patch', 'delete'], url_path='bulk')
    def bulk_dispatch(self, request):
        method = request.method.lower()

        if method == 'post':
            return self.bulk_create(request)
        elif method in ['put', 'patch']:
            return self.bulk_update(request)
        elif method in ['delete']:
            return self.bulk_delete(request)

        raise MethodNotAllowed(request.method)
