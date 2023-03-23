from __future__ import unicode_literals

import json
import logging
import time
from collections import OrderedDict
from os.path import getsize

from celery.result import AsyncResult
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.core.signing import TimestampSigner
from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, ViewSet

from poms.audit.mixins import HistoricalModelMixin
from poms.common.filtering_handlers import handle_filters, handle_global_table_search
from poms.common.filters import ByIdFilterBackend, ByIsDeletedFilterBackend, OrderingPostFilter, \
    ByIsEnabledFilterBackend
from poms.common.grouping_handlers import handle_groups, count_groups
from poms.common.mixins import BulkModelMixin, DestroyModelFakeMixin, UpdateModelMixinExt
from poms.common.sorting import sort_by_dynamic_attrs
from poms.history.mixins import HistoryMixin
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.users.utils import get_master_user_and_member

_l = logging.getLogger('poms.common')

from django.http import HttpResponse, Http404


class AbstractApiView(APIView):

    def perform_authentication(self, request):

        auth_st = time.perf_counter()

        super(AbstractApiView, self).perform_authentication(request)

        if request.user.is_authenticated:
            try:
                member, master_user = get_master_user_and_member(request)

                request.user.member = member
                request.user.master_user = master_user

            except Exception as e:

                request.user.member, request.user.master_user = None, None
                _l.debug("perform_authentication exception %s" % e)

        self.auth_time = float("{:3.3f}".format(time.perf_counter() - auth_st))

    # Possibly Deprecated
    # def initial(self, request, *args, **kwargs):
    #     super(AbstractApiView, self).initial(request, *args, **kwargs)
    #
    #     timezone.activate(settings.TIME_ZONE)
    #     if request.user.is_authenticated:
    #
    #         if hasattr(request.user, 'master_user'):
    #
    #             master_user = request.user.master_user
    #             if master_user and master_user.timezone:
    #                 timezone.activate(master_user.timezone)

    # Possibly Deprecated
    # def dispatch(self, request, *args, **kwargs):
    #     if request.method.upper() in permissions.SAFE_METHODS:
    #         response = super(AbstractApiView, self).dispatch(request, *args, **kwargs)
    #         return self._mini_if_need(request, response)
    #     else:
    #         with transaction.atomic():
    #             response = super(AbstractApiView, self).dispatch(request, *args, **kwargs)
    #             return self._mini_if_need(request, response)
    #
    # def _mini_if_need(self, request, response):
    #     if '_mini' in request.GET:
    #         self._remove_object(response.data)
    #     return response
    #
    # def _remove_object(self, data):
    #     if isinstance(data, (list, tuple)):
    #         for i, v in enumerate(data):
    #             data[i] = self._remove_object(v)
    #     elif isinstance(data, (dict, OrderedDict)):
    #         for k, v in list(data.items()):
    #             if k.endswith('_object') or k in ['user_object_permissions', 'group_object_permissions']:
    #                 del data[k]
    #             else:
    #                 data[k] = self._remove_object(v)
    #     return data


class AbstractViewSet(AbstractApiView, ViewSet):
    serializer_class = None
    permission_classes = [
        IsAuthenticated
    ]

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)

    def get_serializer_class(self):
        return self.serializer_class

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }


class AbstractEvGroupViewSet(AbstractApiView, UpdateModelMixinExt, DestroyModelFakeMixin,
                             BulkModelMixin, ModelViewSet):
    permission_classes = [
        IsAuthenticated
    ]
    filter_backends = [
        ByIdFilterBackend,
        ByIsDeletedFilterBackend,
        DjangoFilterBackend,
        OrderingFilter,
        OrderingPostFilter
    ]

    # DEPRECATED
    def list(self, request):

        if len(request.query_params.getlist('groups_types')) == 0:
            return Response({
                "status": status.HTTP_404_NOT_FOUND,
                "message": 'No groups provided.',
                "data": []
            })

        start_time = time.time()
        master_user = request.user.master_user

        qs = self.get_queryset()

        qs = self.filter_queryset(qs)

        filtered_qs = self.get_queryset()

        filtered_qs = filtered_qs.filter(id__in=qs)

        filtered_qs = filtered_qs.filter(master_user=master_user)

        content_type = ContentType.objects.get_for_model(self.serializer_class.Meta.model)

        # if content_type.model not in ['currencyhistory', 'pricehistory', 'pricingpolicy', 'transaction', 'currencyhistoryerror', 'pricehistoryerror']:
        #     filtered_qs = filtered_qs.filter(is_deleted=False)

        try:
            filtered_qs.model._meta.get_field('is_enabled')
        except FieldDoesNotExist:
            pass
        else:
            is_enabled = self.request.query_params.get('is_enabled', 'true')
            if is_enabled == 'true':
                filtered_qs = filtered_qs.filter(is_enabled=True)

        filtered_qs = handle_groups(filtered_qs, request, self.get_queryset(), content_type)

        page = self.paginate_queryset(filtered_qs)

        _l.debug("List %s seconds " % (time.time() - start_time))

        if page is not None:
            return self.get_paginated_response(page)

        return Response(filtered_qs)

    @action(detail=False, methods=['post'], url_path='filtered')
    def filtered_list(self, request, *args, **kwargs):

        start_time = time.time()

        groups_types = request.data.get('groups_types', None)
        groups_values = request.data.get('groups_values', None)
        groups_order = request.data.get('groups_order', None)
        master_user = request.user.master_user
        content_type = ContentType.objects.get_for_model(self.serializer_class.Meta.model)
        filter_settings = request.data.get('filter_settings', None)
        global_table_search = request.data.get('global_table_search', '')
        ev_options = request.data.get('ev_options', '')

        qs = self.get_queryset()

        qs = self.filter_queryset(qs)

        filtered_qs = self.get_queryset()

        filtered_qs = filtered_qs.filter(id__in=qs)

        # print('len before handle filters %s' % len(filtered_qs))

        filtered_qs = handle_filters(filtered_qs, filter_settings, master_user, content_type)

        if global_table_search:
            filtered_qs = handle_global_table_search(filtered_qs, global_table_search, self.serializer_class.Meta.model,
                                                     content_type)

        # print('len after handle filters %s' % len(filtered_qs))

        # filtered_qs = filtered_qs.filter(id__in=qs)

        # if content_type.model not in ['currencyhistory', 'pricehistory', 'pricingpolicy', 'transaction', 'currencyhistoryerror', 'pricehistoryerror']:
        #     filtered_qs = filtered_qs.filter(is_deleted=False)

        if content_type.model not in ['currencyhistory', 'pricehistory', 'currencyhistoryerror', 'pricehistoryerror']:

            is_enabled = request.data.get('is_enabled', 'true')

            if is_enabled == 'true':
                filtered_qs = filtered_qs.filter(is_enabled=True)

        filtered_qs = handle_groups(filtered_qs, groups_types, groups_values, groups_order, master_user,
                                    self.get_queryset(), content_type)

        filtered_qs = count_groups(filtered_qs, groups_types, groups_values, master_user, self.get_queryset(),
                                   content_type, filter_settings, ev_options, global_table_search)

        # print('len after handle groups %s' % len(filtered_qs))

        page = self.paginator.post_paginate_queryset(filtered_qs, request)

        _l.debug("Filtered EV Group List %s seconds " % str((time.time() - start_time)))

        if page is not None:
            return self.get_paginated_response(page)

        return Response(filtered_qs)


class AbstractModelViewSet(AbstractApiView, HistoricalModelMixin, HistoryMixin, UpdateModelMixinExt, DestroyModelFakeMixin,
                           BulkModelMixin, ModelViewSet):
    permission_classes = [
        IsAuthenticated
    ]
    filter_backends = [
        ByIdFilterBackend,
        ByIsDeletedFilterBackend,
        ByIsEnabledFilterBackend,
        DjangoFilterBackend,
        OrderingFilter,
        OrderingPostFilter,
    ]

    def list(self, request, *args, **kwargs):

        if not hasattr(request.user, 'master_user'):
            return Response([])

        queryset = self.filter_queryset(self.get_queryset())

        content_type = ContentType.objects.get_for_model(self.serializer_class.Meta.model)

        ordering = request.GET.get('ordering')
        master_user = request.user.master_user

        if ordering:
            queryset = sort_by_dynamic_attrs(queryset, ordering, master_user, content_type)

        try:
            queryset.model._meta.get_field('is_enabled')
        except FieldDoesNotExist:
            pass
        else:
            is_enabled = self.request.query_params.get('is_enabled', 'true')
            if is_enabled == 'true':
                queryset = queryset.filter(is_enabled=True)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post', 'get'], url_path='filtered')
    def filtered_list(self, request, *args, **kwargs):

        start_time = time.perf_counter()

        filter_settings = request.data.get('filter_settings', None)
        global_table_search = request.data.get('global_table_search', '')
        content_type = ContentType.objects.get_for_model(self.serializer_class.Meta.model)
        master_user = request.user.master_user

        filters_st = time.perf_counter()
        queryset = self.filter_queryset(self.get_queryset())

        if content_type.model not in ['currencyhistory', 'pricehistory', 'complextransaction', 'transaction',
                                      'currencyhistoryerror', 'pricehistoryerror']:

            is_enabled = request.data.get('is_enabled', 'true')

            if is_enabled == 'true':
                queryset = queryset.filter(is_enabled=True)

        if content_type.model in ['complextransaction']:
            queryset = queryset.filter(is_deleted=False)

        queryset = handle_filters(queryset, filter_settings, master_user, content_type)

        ordering = request.data.get('ordering', None)

        _l.debug('ordering %s' % ordering)

        if ordering:
            sort_st = time.perf_counter()
            queryset = sort_by_dynamic_attrs(queryset, ordering, master_user, content_type)
            # _l.debug('filtered_list sort done: %s', "{:3.3f}".format(time.perf_counter() - sort_st))

        # _l.debug('filtered_list apply filters done: %s', "{:3.3f}".format(time.perf_counter() - filters_st))

        page_st = time.perf_counter()

        if global_table_search:
            queryset = handle_global_table_search(queryset, global_table_search, self.serializer_class.Meta.model,
                                                  content_type)

        page = self.paginator.post_paginate_queryset(queryset, request)

        # _l.debug('filtered_list get page done: %s', "{:3.3f}".format(time.perf_counter() - page_st))

        serialize_st = time.perf_counter()

        serializer = self.get_serializer(page, many=True)

        result = self.get_paginated_response(serializer.data)

        # _l.debug('filtered_list serialize done: %s', "{:3.3f}".format(time.perf_counter() - serialize_st))

        # _l.debug('filtered_list done: %s', "{:3.3f}".format(time.perf_counter() - start_time))

        return result

        # serializer = self.get_serializer(queryset, many=True)
        #
        # print("Filtered List %s seconds " % (time.time() - start_time))
        #
        # return Response(serializer.data)

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)


class AbstractReadOnlyModelViewSet(AbstractApiView, ReadOnlyModelViewSet):
    permission_classes = [
        IsAuthenticated
    ]
    filter_backends = [
        ByIdFilterBackend,
        DjangoFilterBackend,
        OrderingFilter,
    ]


class AbstractClassModelViewSet(AbstractReadOnlyModelViewSet):
    ordering_fields = ['name']
    filter_fields = ['user_code', 'name']
    pagination_class = None


class AbstractAsyncViewSet(AbstractViewSet):
    serializer_class = None
    celery_task = None

    def get_serializer_context(self):
        context = super(AbstractAsyncViewSet, self).get_serializer_context()
        context['show_object_permissions'] = False
        return context

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        task_id = instance.task_id

        signer = TimestampSigner()

        if task_id:

            res = AsyncResult(signer.unsign(task_id))

            st = time.perf_counter()

            if res.ready():
                instance = res.result

                # print('TASK ITEMS LEN %s' % len(res.result.items))

            print('AsyncResult res.ready: %s' % (time.perf_counter() - st))

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            print('TASK RESULT %s' % res.result)
            print('TASK STATUS %s' % res.status)

            instance.task_id = task_id
            instance.task_status = res.status
            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:

            res = self.celery_task.apply_async(kwargs={'instance': instance})
            instance.task_id = signer.sign('%s' % res.id)

            print('CREATE CELERY TASK %s' % res.id)

            instance.task_status = res.status
            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)


class AbstractSyncViewSet(AbstractViewSet):
    serializer_class = None
    task = None

    def get_serializer_context(self):
        context = super(AbstractSyncViewSet, self).get_serializer_context()
        context['show_object_permissions'] = False
        return context

    def create(self, request, *args, **kwargs):
        print('AbstractSyncViewSet create')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        res = self.task(instance)

        res.task_id = 1
        res.task_status = "SUCCESS"

        print('res.task_id %s' % res.task_id)
        print('res.task_status %s' % res.task_status)

        serializer = self.get_serializer(instance=res, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ValuesForSelectViewSet(AbstractApiView, ViewSet):

    def list(self, request):

        results = []

        content_type_name = request.query_params.get('content_type', None)
        key = request.query_params.get('key', None)
        value_type = request.query_params.get('value_type', None)

        master_user = request.user.master_user

        if not content_type_name:
            return Response({
                "status": status.HTTP_404_NOT_FOUND,
                "message": 'No content type provided.',
                "results": []
            })

        if not key:
            return Response({
                "status": status.HTTP_404_NOT_FOUND,
                "message": 'No key provided.',
                "results": []
            })

        if not value_type:
            return Response({
                "status": status.HTTP_404_NOT_FOUND,
                "message": 'No value type provided.',
                "results": []
            })

        if value_type != 'field':

            try:
                value_type = int(value_type)
            except Exception as e:
                return Response({
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": 'Value type is invalid.',
                    "results": []
                })

        content_type_pieces = content_type_name.split('.')

        try:
            content_type = ContentType.objects.get(app_label=content_type_pieces[0], model=content_type_pieces[1])
        except ContentType.DoesNotExist:
            return Response({
                "status": status.HTTP_404_NOT_FOUND,
                "message": 'Content type does not exist.',
                "results": []
            })

        model = content_type.model_class()

        if 'attributes.' in key:

            attribute_type_user_code = key.split('attributes.')[1]

            try:
                attribute_type = GenericAttributeType.objects.get(master_user=master_user,
                                                                  user_code=attribute_type_user_code,
                                                                  content_type=content_type)
            except GenericAttributeType.DoesNotExist:

                return Response({
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": 'No content type provided.',
                    "results": []
                })

            if value_type == 10:
                results = GenericAttribute.objects.filter(content_type=content_type,
                                                          attribute_type=attribute_type).order_by(
                    'value_string').values_list('value_string', flat=True).distinct('value_string')
            if value_type == 20:
                results = GenericAttribute.objects.filter(content_type=content_type,
                                                          attribute_type=attribute_type).order_by(
                    'value_float').values_list('value_float', flat=True).distinct('value_float')
            if value_type == 30:
                results = GenericAttribute.objects.filter(content_type=content_type,
                                                          attribute_type=attribute_type).order_by(
                    'classifier__name').values_list('classifier__name', flat=True).distinct('classifier__name')
            if value_type == 40:
                results = GenericAttribute.objects.filter(content_type=content_type,
                                                          attribute_type=attribute_type).order_by(
                    'value_date').values_list('value_date', flat=True).distinct('value_date')

        else:

            if content_type_name == 'instruments.pricehistory':

                if value_type == 10:
                    results = model.objects.filter(instrument__master_user=master_user).order_by(key).values_list(key,
                                                                                                                  flat=True).distinct(
                        key)
                if value_type == 20:
                    results = model.objects.filter(instrument__master_user=master_user).order_by(key).values_list(key,
                                                                                                                  flat=True).distinct(
                        key)
                if value_type == 40:
                    results = model.objects.filter(instrument__master_user=master_user).order_by(key).values_list(key,
                                                                                                                  flat=True).distinct(
                        key)
                if value_type == 'field':
                    results = model.objects.filter(instrument__master_user=master_user).order_by(
                        key + '__user_code').values_list(key + '__user_code', flat=True).distinct(key + '__user_code')


            elif content_type_name == 'currencies.currencyhistory':

                if value_type == 10:
                    results = model.objects.filter(currency__master_user=master_user).order_by(key).values_list(key,
                                                                                                                flat=True).distinct(
                        key)
                if value_type == 20:
                    results = model.objects.filter(currency__master_user=master_user).order_by(key).values_list(key,
                                                                                                                flat=True).distinct(
                        key)
                if value_type == 40:
                    results = model.objects.filter(currency__master_user=master_user).order_by(key).values_list(key,
                                                                                                                flat=True).distinct(
                        key)
                if value_type == 'field':
                    results = model.objects.filter(currency__master_user=master_user).order_by(
                        key + '__user_code').values_list(key + '__user_code', flat=True).distinct(key + '__user_code')


            else:

                if value_type == 10:
                    results = model.objects.filter(master_user=master_user).order_by(key).values_list(key,
                                                                                                      flat=True).distinct(
                        key)
                if value_type == 20:
                    results = model.objects.filter(master_user=master_user).order_by(key).values_list(key,
                                                                                                      flat=True).distinct(
                        key)
                if value_type == 40:
                    results = model.objects.filter(master_user=master_user).order_by(key).values_list(key,
                                                                                                      flat=True).distinct(
                        key)
                if value_type == 'field':
                    results = model.objects.filter(master_user=master_user).order_by(key + '__user_code').values_list(
                        key + '__user_code', flat=True).distinct(key + '__user_code')

        _l.debug('model %s' % model)

        return Response({
            "results": results
        })


class DebugLogViewSet(AbstractViewSet):

    def iter_json(self, context):
        yield '{"starts": "%d",' \
              '"data": "' % context['starts']

        while True:
            line = context['log'].readline()
            if line:
                yield json.dumps(line).strip(u'"')
            else:
                yield '", "ends": "%d"}' % context['log'].tell()
                context['log'].close()
                return

    def list(self, request):

        log_file = '/var/log/finmars/backend/django.log'

        seek_to = request.query_params.get('seek_to', 0)

        seek_to = int(seek_to)

        try:
            file_length = getsize(log_file)
        except Exception as e:
            raise Http404('Cannot access file')

        context = {}

        if seek_to == 0:
            seek_to = file_length - 1000

            if seek_to < 0:
                seek_to = 0

        if seek_to > file_length:
            seek_to = file_length

        try:
            context['log'] = open(log_file, 'r')
            context['log'].seek(seek_to)
            context['starts'] = seek_to
        except IOError:
            raise Http404('Cannot access file')

        return HttpResponse(
            self.iter_json(context),
            content_type='application/json'
        )
