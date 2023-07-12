import json
import logging
import time
from os.path import getsize

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.core.signing import TimestampSigner
from django.http import Http404, HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.inspectors import SwaggerAutoSchema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, ViewSet

from celery.result import AsyncResult

from poms.common.filtering_handlers import handle_filters, handle_global_table_search
from poms.common.filters import (
    ByIdFilterBackend,
    ByIsDeletedFilterBackend,
    ByIsEnabledFilterBackend,
    OrderingPostFilter,
)
from poms.common.grouping_handlers import count_groups, handle_groups
from poms.common.mixins import (
    BulkModelMixin,
    DestroyModelFakeMixin,
    ListEvModelMixin,
    ListLightModelMixin,
    UpdateModelMixinExt,
)
from poms.common.sorting import sort_by_dynamic_attrs
from poms.iam.views import AbstractFinmarsAccessPolicyViewSet
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.users.utils import get_master_user_and_member

_l = logging.getLogger("poms.common")


class CustomSwaggerAutoSchema(SwaggerAutoSchema):
    def get_operation(self, operation_keys=None):
        operation = super().get_operation(operation_keys)

        splitted_dash_operation_keys = [
            word for item in operation_keys for word in item.split("-")
        ]
        splitted_underscore_operation_keys = [
            word for item in splitted_dash_operation_keys for word in item.split("_")
        ]

        capitalized_operation_keys = [
            word.capitalize() for word in splitted_underscore_operation_keys
        ]

        operation.operationId = " ".join(capitalized_operation_keys)

        # operation.operationId = f"{self.view.queryset.model._meta.verbose_name.capitalize()} {operation_keys[-1].capitalize()}"
        return operation

    def get_tags(self, operation_keys=None):
        tags = super().get_tags(operation_keys)

        splitted_tags = [word.split("-") for word in tags]

        result = []

        for splitted_tag in splitted_tags:
            capitalized_tag = [word.capitalize() for word in splitted_tag]

            result.append(" ".join(capitalized_tag))

        return result


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
                _l.debug(f"perform_authentication exception {e}")

        self.auth_time = float("{:3.3f}".format(time.perf_counter() - auth_st))

    swagger_schema = CustomSwaggerAutoSchema


class AbstractViewSet(AbstractApiView, ViewSet):
    serializer_class = None
    permission_classes = [IsAuthenticated]

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs["context"] = self.get_serializer_context()
        return serializer_class(*args, **kwargs) if serializer_class else None

    def get_serializer_class(self):
        return self.serializer_class

    def get_serializer_context(self):
        return {"request": self.request, "format": self.format_kwarg, "view": self}


# DEPRECATED
class AbstractEvGroupViewSet(
    AbstractApiView,
    UpdateModelMixinExt,
    DestroyModelFakeMixin,
    BulkModelMixin,
    ModelViewSet,
):
    permission_classes = [IsAuthenticated]
    filter_backends = [
        ByIdFilterBackend,
        ByIsDeletedFilterBackend,
        DjangoFilterBackend,
        OrderingFilter,
        OrderingPostFilter,
    ]

    # DEPRECATED
    def list(self, request):
        if len(request.query_params.getlist("groups_types")) == 0:
            return Response(
                {
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": "No groups provided.",
                    "data": [],
                }
            )

        start_time = time.time()
        master_user = request.user.master_user

        qs = self.get_queryset()

        qs = self.filter_queryset(qs)

        filtered_qs = self.get_queryset()

        filtered_qs = filtered_qs.filter(id__in=qs)

        filtered_qs = filtered_qs.filter(master_user=master_user)

        content_type = ContentType.objects.get_for_model(
            self.serializer_class.Meta.model
        )

        try:
            filtered_qs.model._meta.get_field("is_enabled")
        except FieldDoesNotExist:
            pass
        else:
            is_enabled = self.request.query_params.get("is_enabled", "true")
            if is_enabled == "true":
                filtered_qs = filtered_qs.filter(is_enabled=True)

        try:
            filtered_qs.model._meta.get_field("is_deleted")
        except FieldDoesNotExist:
            pass
        else:
            is_deleted = self.request.query_params.get("is_deleted", "true")
            if is_deleted == "true":
                filtered_qs = filtered_qs.filter(is_deleted=True)
            else:
                filtered_qs = filtered_qs.filter(is_deleted=False)

        filtered_qs = handle_groups(
            filtered_qs, request, self.get_queryset(), content_type
        )

        page = self.paginate_queryset(filtered_qs)

        _l.debug(f"List {time.time() - start_time} seconds ")

        if page is not None:
            return self.get_paginated_response(page)

        return Response(filtered_qs)

    @action(detail=False, methods=["post"], url_path="filtered")
    def filtered_list(self, request, *args, **kwargs):
        start_time = time.time()

        groups_types = request.data.get("groups_types", None)
        groups_values = request.data.get("groups_values", None)
        groups_order = request.data.get("groups_order", None)
        master_user = request.user.master_user
        content_type = ContentType.objects.get_for_model(
            self.serializer_class.Meta.model
        )
        filter_settings = request.data.get("filter_settings", None)
        global_table_search = request.data.get("global_table_search", "")
        ev_options = request.data.get("ev_options", "")

        qs = self.get_queryset()

        qs = self.filter_queryset(qs)

        filtered_qs = self.get_queryset()

        filtered_qs = filtered_qs.filter(id__in=qs)

        # print('len before handle filters %s' % len(filtered_qs))

        filtered_qs = handle_filters(
            filtered_qs, filter_settings, master_user, content_type
        )

        if global_table_search:
            filtered_qs = handle_global_table_search(
                filtered_qs,
                global_table_search,
                self.serializer_class.Meta.model,
                content_type,
            )

        if content_type.model not in [
            "currencyhistory",
            "pricehistory",
            "currencyhistoryerror",
            "pricehistoryerror",
        ]:
            is_enabled = request.data.get("is_enabled", "true")

            if is_enabled == "true":
                filtered_qs = filtered_qs.filter(is_enabled=True)

        filtered_qs = handle_groups(
            filtered_qs,
            groups_types,
            groups_values,
            groups_order,
            master_user,
            self.get_queryset(),
            content_type,
        )

        filtered_qs = count_groups(
            filtered_qs,
            groups_types,
            groups_values,
            master_user,
            self.get_queryset(),
            content_type,
            filter_settings,
            ev_options,
            global_table_search,
        )

        # print('len after handle groups %s' % len(filtered_qs))

        page = self.paginator.post_paginate_queryset(filtered_qs, request)

        _l.debug(f"Filtered EV Group List {str(time.time() - start_time)} seconds ")

        if page is not None:
            return self.get_paginated_response(page)

        return Response(filtered_qs)


class AbstractModelViewSet(
    AbstractApiView,
    ListLightModelMixin,
    ListEvModelMixin,
    UpdateModelMixinExt,
    DestroyModelFakeMixin,
    BulkModelMixin,
    AbstractFinmarsAccessPolicyViewSet,
):
    permission_classes = AbstractFinmarsAccessPolicyViewSet.permission_classes + [
        IsAuthenticated
    ]
    filter_backends = AbstractFinmarsAccessPolicyViewSet.filter_backends + [
        ByIdFilterBackend,
        ByIsDeletedFilterBackend,
        ByIsEnabledFilterBackend,
        # DjangoFilterBackend, # Create duplicate error, possibly inheriths from AbstractFinmarsAccessPolicyViewSet
        OrderingFilter,
        OrderingPostFilter,
    ]

    def list(self, request, *args, **kwargs):
        if not hasattr(request.user, "master_user"):
            return Response([])

        queryset = self.filter_queryset(self.get_queryset())

        content_type = ContentType.objects.get_for_model(
            self.serializer_class.Meta.model
        )

        ordering = request.GET.get("ordering")
        master_user = request.user.master_user

        if ordering:
            queryset = sort_by_dynamic_attrs(
                queryset, ordering, master_user, content_type
            )

        try:
            queryset.model._meta.get_field("is_enabled")
        except FieldDoesNotExist:
            pass
        else:
            is_enabled = self.request.query_params.get("is_enabled", "true")
            if is_enabled == "true":
                queryset = queryset.filter(is_enabled=True)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="ev-item")
    def list_ev_item(self, request, *args, **kwargs):
        start_time = time.perf_counter()

        filter_settings = request.data.get("filter_settings", None)
        global_table_search = request.data.get("global_table_search", "")
        content_type = ContentType.objects.get_for_model(
            self.serializer_class.Meta.model
        )
        master_user = request.user.master_user

        filters_st = time.perf_counter()
        queryset = self.filter_queryset(self.get_queryset())

        if content_type.model not in [
            "currencyhistory",
            "pricehistory",
            "complextransaction",
            "transaction",
            "currencyhistoryerror",
            "pricehistoryerror",
        ]:
            is_enabled = request.data.get("is_enabled", "true")

            if is_enabled == "true":
                queryset = queryset.filter(is_enabled=True)

        if content_type.model in ["complextransaction"]:
            queryset = queryset.filter(is_deleted=False)

        queryset = handle_filters(queryset, filter_settings, master_user, content_type)

        ordering = request.data.get("ordering", None)

        _l.debug(f"ordering {ordering}")

        if ordering:
            sort_st = time.perf_counter()
            queryset = sort_by_dynamic_attrs(
                queryset, ordering, master_user, content_type
            )
            # _l.debug('filtered_list sort done: %s', "{:3.3f}".format(time.perf_counter() - sort_st))

        # _l.debug('filtered_list apply filters done: %s', "{:3.3f}".format(time.perf_counter() - filters_st))

        page_st = time.perf_counter()

        if global_table_search:
            queryset = handle_global_table_search(
                queryset,
                global_table_search,
                self.serializer_class.Meta.model,
                content_type,
            )

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

    @action(detail=False, methods=["post"], url_path="ev-group")
    def list_ev_group(self, request, *args, **kwargs):
        start_time = time.time()

        groups_types = request.data.get("groups_types", None)
        groups_values = request.data.get("groups_values", None)
        groups_order = request.data.get("groups_order", None)
        master_user = request.user.master_user
        content_type = ContentType.objects.get_for_model(
            self.serializer_class.Meta.model
        )
        filter_settings = request.data.get("filter_settings", None)
        global_table_search = request.data.get("global_table_search", "")
        ev_options = request.data.get("ev_options", "")

        qs = self.get_queryset()

        qs = self.filter_queryset(qs)

        filtered_qs = self.get_queryset()

        filtered_qs = filtered_qs.filter(id__in=qs)

        # print('len before handle filters %s' % len(filtered_qs))

        filtered_qs = handle_filters(
            filtered_qs, filter_settings, master_user, content_type
        )

        if global_table_search:
            filtered_qs = handle_global_table_search(
                filtered_qs,
                global_table_search,
                self.serializer_class.Meta.model,
                content_type,
            )

        # print('len after handle filters %s' % len(filtered_qs))

        # filtered_qs = filtered_qs.filter(id__in=qs)

        # if content_type.model not in ['currencyhistory', 'pricehistory', 'pricingpolicy', 'transaction', 'currencyhistoryerror', 'pricehistoryerror']:
        #     filtered_qs = filtered_qs.filter(is_deleted=False)

        if content_type.model not in [
            "currencyhistory",
            "pricehistory",
            "currencyhistoryerror",
            "pricehistoryerror",
        ]:
            is_enabled = request.data.get("is_enabled", "true")

            if is_enabled == "true":
                filtered_qs = filtered_qs.filter(is_enabled=True)

        if content_type.model in ["complextransaction"]:
            filtered_qs = filtered_qs.filter(is_deleted=False)

        filtered_qs = handle_groups(
            filtered_qs,
            groups_types,
            groups_values,
            groups_order,
            master_user,
            self.get_queryset(),
            content_type,
        )

        filtered_qs = count_groups(
            filtered_qs,
            groups_types,
            groups_values,
            master_user,
            self.get_queryset(),
            content_type,
            filter_settings,
            ev_options,
            global_table_search,
        )

        # print('len after handle groups %s' % len(filtered_qs))

        page = self.paginator.post_paginate_queryset(filtered_qs, request)

        _l.debug(f"Filtered EV Group List {str(time.time() - start_time)} seconds ")

        if content_type.model == "transactiontype":  # TODO refactor someday
            from poms.transactions.models import (  # TODO Really bad stuff here
                TransactionTypeGroup,
            )

            """It happens because we change TransactionTypeGroup relation to user_code,
                so its broke default relation group counting, and now we need to get group name separately
                maybe we need to refactor this whole module, or just provide user_codes and frontend app will get names of groups
            """

            for item in page:
                try:
                    # _l.info('group_identifier %s' % item['group_identifier'])

                    ttype_group = TransactionTypeGroup.objects.filter(
                        user_code=item["group_identifier"]
                    ).first()

                    # _l.info('short_name %s' % ttype_group.short_name)

                    item["group_name"] = ttype_group.short_name

                except Exception as e:
                    _l.info(f"e {e}")

        _l.info(f"page {page}")

        if page is not None:
            return self.get_paginated_response(page)

        return Response(filtered_qs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)


class AbstractReadOnlyModelViewSet(AbstractApiView, ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [
        ByIdFilterBackend,
        DjangoFilterBackend,
        OrderingFilter,
    ]


class AbstractClassModelViewSet(AbstractReadOnlyModelViewSet):
    ordering_fields = ["name"]
    filter_fields = ["user_code", "name"]
    pagination_class = None


class AbstractAsyncViewSet(AbstractViewSet):
    serializer_class = None
    celery_task = None

    def get_serializer_context(self):
        context = super(AbstractAsyncViewSet, self).get_serializer_context()
        context["show_object_permissions"] = False
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

            print(f"AsyncResult res.ready: {time.perf_counter() - st}")

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            print(f"TASK RESULT {res.result}")
            print(f"TASK STATUS {res.status}")

            instance.task_id = task_id
        else:
            res = self.celery_task.apply_async(kwargs={"instance": instance})
            instance.task_id = signer.sign(f"{res.id}")

            print(f"CREATE CELERY TASK {res.id}")

        instance.task_status = res.status
        serializer = self.get_serializer(instance=instance, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AbstractSyncViewSet(AbstractViewSet):
    serializer_class = None
    task = None

    def get_serializer_context(self):
        context = super(AbstractSyncViewSet, self).get_serializer_context()
        context["show_object_permissions"] = False
        return context

    def create(self, request, *args, **kwargs):
        print("AbstractSyncViewSet create")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        res = self.task(instance)

        res.task_id = 1
        res.task_status = "SUCCESS"

        print(f"res.task_id={res.task_id} res.task_status={res.task_status}")

        serializer = self.get_serializer(instance=res, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ValuesForSelectViewSet(AbstractApiView, ViewSet):
    def list(self, request):
        results = []

        content_type_name = request.query_params.get("content_type", None)
        key = request.query_params.get("key", None)
        value_type = request.query_params.get("value_type", None)

        master_user = request.user.master_user

        if not content_type_name:
            return Response(
                {
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": "No content type provided.",
                    "results": [],
                }
            )

        if not key:
            return Response(
                {
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": "No key provided.",
                    "results": [],
                }
            )

        if not value_type:
            return Response(
                {
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": "No value type provided.",
                    "results": [],
                }
            )

        if value_type != "field":
            try:
                value_type = int(value_type)
            except Exception as e:
                return Response(
                    {
                        "status": status.HTTP_404_NOT_FOUND,
                        "message": "Value type is invalid.",
                        "results": [],
                    }
                )

        content_type_pieces = content_type_name.split(".")

        try:
            content_type = ContentType.objects.get(
                app_label=content_type_pieces[0], model=content_type_pieces[1]
            )
        except ContentType.DoesNotExist:
            return Response(
                {
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": "Content type does not exist.",
                    "results": [],
                }
            )

        model = content_type.model_class()

        if "attributes." in key:
            attribute_type_user_code = key.split("attributes.")[1]

            try:
                attribute_type = GenericAttributeType.objects.get(
                    master_user=master_user,
                    user_code=attribute_type_user_code,
                    content_type=content_type,
                )
            except GenericAttributeType.DoesNotExist:
                return Response(
                    {
                        "status": status.HTTP_404_NOT_FOUND,
                        "message": "No content type provided.",
                        "results": [],
                    }
                )

            if value_type == 10:
                results = (
                    GenericAttribute.objects.filter(
                        content_type=content_type, attribute_type=attribute_type
                    )
                    .order_by("value_string")
                    .values_list("value_string", flat=True)
                    .distinct("value_string")
                )
            if value_type == 20:
                results = (
                    GenericAttribute.objects.filter(
                        content_type=content_type, attribute_type=attribute_type
                    )
                    .order_by("value_float")
                    .values_list("value_float", flat=True)
                    .distinct("value_float")
                )
            if value_type == 30:
                results = (
                    GenericAttribute.objects.filter(
                        content_type=content_type, attribute_type=attribute_type
                    )
                    .order_by("classifier__name")
                    .values_list("classifier__name", flat=True)
                    .distinct("classifier__name")
                )
            if value_type == 40:
                results = (
                    GenericAttribute.objects.filter(
                        content_type=content_type, attribute_type=attribute_type
                    )
                    .order_by("value_date")
                    .values_list("value_date", flat=True)
                    .distinct("value_date")
                )

        else:
            if content_type_name == "instruments.pricehistory":
                if value_type == 10:
                    results = (
                        model.objects.filter(instrument__master_user=master_user)
                        .order_by(key)
                        .values_list(key, flat=True)
                        .distinct(key)
                    )
                if value_type == 20:
                    results = (
                        model.objects.filter(instrument__master_user=master_user)
                        .order_by(key)
                        .values_list(key, flat=True)
                        .distinct(key)
                    )
                if value_type == 40:
                    results = (
                        model.objects.filter(instrument__master_user=master_user)
                        .order_by(key)
                        .values_list(key, flat=True)
                        .distinct(key)
                    )
                if value_type == "field":
                    results = (
                        model.objects.filter(instrument__master_user=master_user)
                        .order_by(key + "__user_code")
                        .values_list(key + "__user_code", flat=True)
                        .distinct(key + "__user_code")
                    )

            elif content_type_name == "currencies.currencyhistory":
                if value_type == 10:
                    results = (
                        model.objects.filter(currency__master_user=master_user)
                        .order_by(key)
                        .values_list(key, flat=True)
                        .distinct(key)
                    )
                if value_type == 20:
                    results = (
                        model.objects.filter(currency__master_user=master_user)
                        .order_by(key)
                        .values_list(key, flat=True)
                        .distinct(key)
                    )
                if value_type == 40:
                    results = (
                        model.objects.filter(currency__master_user=master_user)
                        .order_by(key)
                        .values_list(key, flat=True)
                        .distinct(key)
                    )
                if value_type == "field":
                    results = (
                        model.objects.filter(currency__master_user=master_user)
                        .order_by(key + "__user_code")
                        .values_list(key + "__user_code", flat=True)
                        .distinct(key + "__user_code")
                    )

            else:
                if value_type == 10:
                    results = (
                        model.objects.filter(master_user=master_user)
                        .order_by(key)
                        .values_list(key, flat=True)
                        .distinct(key)
                    )
                if value_type == 20:
                    results = (
                        model.objects.filter(master_user=master_user)
                        .order_by(key)
                        .values_list(key, flat=True)
                        .distinct(key)
                    )
                if value_type == 40:
                    results = (
                        model.objects.filter(master_user=master_user)
                        .order_by(key)
                        .values_list(key, flat=True)
                        .distinct(key)
                    )
                if value_type == "field":
                    results = (
                        model.objects.filter(master_user=master_user)
                        .order_by(key + "__user_code")
                        .values_list(key + "__user_code", flat=True)
                        .distinct(key + "__user_code")
                    )

        _l.debug(f"model {model}")

        return Response({"results": results})


class DebugLogViewSet(AbstractViewSet):
    def iter_json(self, context):
        yield '{"starts": "%d",' '"data": "' % context["starts"]

        while True:
            line = context["log"].readline()
            if line:
                yield json.dumps(line).strip('"')
            else:
                yield '", "ends": "%d"}' % context["log"].tell()
                context["log"].close()
                return

    def list(self, request):
        log_file = "/var/log/finmars/backend/django.log"

        seek_to = request.query_params.get("seek_to", 0)

        seek_to = int(seek_to)

        try:
            file_length = getsize(log_file)
        except Exception as e:
            raise Http404("Cannot access file") from e

        context = {}

        if seek_to == 0:
            seek_to = file_length - 1000

            if seek_to < 0:
                seek_to = 0

        if seek_to > file_length:
            seek_to = file_length

        try:
            context["log"] = open(log_file, "r")
            context["log"].seek(seek_to)
            context["starts"] = seek_to
        except IOError as exc:
            raise Http404("Cannot access file") from exc

        return HttpResponse(self.iter_json(context), content_type="application/json")
