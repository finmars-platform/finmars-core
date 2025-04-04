import contextlib
import json
import logging
import time
import traceback
from os.path import getsize

from celery.result import AsyncResult

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.core.signing import TimestampSigner
from django.http import Http404, HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.inspectors import SwaggerAutoSchema
from rest_framework import parsers, renderers, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, ViewSet

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
from poms.common.serializers import RealmMigrateSchemeSerializer
from poms.common.sorting import sort_by_dynamic_attrs
from poms.common.renderers import FinmarsJSONRenderer
from poms.common.tasks import apply_migration_to_space
from poms.iam.views import AbstractFinmarsAccessPolicyViewSet
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.users.utils import get_master_user_and_member

_l = logging.getLogger("poms.common")


class CustomSwaggerAutoSchema(SwaggerAutoSchema):
    def get_operation(self, operation_keys=None):
        operation = super().get_operation(operation_keys)

        # e.g. operation_keys might be ("api", "v1", "accounts", "account-attribute-type", "list")
        # We skip the first two:
        relevant = operation_keys[2:]  # e.g. ("accounts", "account-attribute-type", "list")
        summary_words = operation_keys[4:]  # e.g. ("accounts", "account-attribute-type", "list")

        # split on dashes and underscores
        splitted = []
        for item in relevant:
            # split on dashes first
            for part in item.split("-"):
                # then split on underscores
                splitted.extend(part.split("_"))

        # capitalize each piece: e.g. "accounts" -> "Accounts", "list" -> "List"
        capitalized = [word.capitalize() for word in splitted]

        summary_capitalized = [" ".join(word.capitalize().split("_")) for word in summary_words]

        # join with underscores so we get "Accounts_Account_Attribute_Type_List"
        operation.operationId = "_".join(capitalized)
        operation.summary = " ".join(summary_capitalized)

        return operation

    def get_tags(self, operation_keys=None):
        if not operation_keys:
            return []
        # The viewset name is one before last, e.g. in ("api", "v1", "accounts", "account-attribute-type", "list")
        # it's "account-attribute-type"
        viewset = operation_keys[-2]
        # Split the viewset name on dashes and underscores, then capitalize each word
        parts = []
        for part in viewset.split("-"):
            parts.extend(part.split("_"))
        tag = " ".join(word.capitalize() for word in parts)
        return [tag]


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
    def list(self, request, *args, **kwargs):
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

        content_type = ContentType.objects.get(
            app_label=self.serializer_class.Meta.model._meta.app_label,
            model=self.serializer_class.Meta.model._meta.model_name,
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

        filtered_qs = handle_groups(filtered_qs, request, self.get_queryset(), content_type)

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
        content_type = ContentType.objects.get(
            app_label=self.serializer_class.Meta.model._meta.app_label,
            model=self.serializer_class.Meta.model._meta.model_name,
        )
        filter_settings = request.data.get("filter_settings", None)
        global_table_search = request.data.get("global_table_search", "")
        ev_options = request.data.get("ev_options", "")

        qs = self.get_queryset()

        qs = self.filter_queryset(qs)

        filtered_qs = self.get_queryset()

        filtered_qs = filtered_qs.filter(id__in=qs)

        # print('len before handle filters %s' % len(filtered_qs))

        filtered_qs = handle_filters(filtered_qs, filter_settings, master_user, content_type)

        if global_table_search:
            filtered_qs = handle_global_table_search(
                filtered_qs,
                global_table_search,
                self.serializer_class.Meta.model,
                content_type,
            )

        if content_type.model not in {
            "currencyhistory",
            "pricehistory",
            "currencyhistoryerror",
            "pricehistoryerror",
        }:
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
    # Seems order matters, szhitenev
    # 2024-10-21
    permission_classes = [IsAuthenticated, *AbstractFinmarsAccessPolicyViewSet.permission_classes]
    filter_backends = AbstractFinmarsAccessPolicyViewSet.filter_backends + [
        ByIdFilterBackend,
        ByIsDeletedFilterBackend,
        ByIsEnabledFilterBackend,
        OrderingFilter,
        OrderingPostFilter,
    ]

    def list(self, request, *args, **kwargs):
        if not hasattr(request.user, "master_user"):
            return Response([])

        queryset = self.filter_queryset(self.get_queryset())

        content_type = ContentType.objects.get_for_model(self.serializer_class.Meta.model)

        ordering = request.GET.get("ordering")
        master_user = request.user.master_user

        if ordering:
            queryset = sort_by_dynamic_attrs(queryset, ordering, master_user, content_type)

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
        filter_settings = request.data.get("filter_settings", None)
        global_table_search = request.data.get("global_table_search", "")
        content_type = ContentType.objects.get(
            app_label=self.serializer_class.Meta.model._meta.app_label,
            model=self.serializer_class.Meta.model._meta.model_name,
        )
        master_user = request.user.master_user

        queryset = self.filter_queryset(self.get_queryset())

        if content_type.model not in {
            "currencyhistory",
            "pricehistory",
            "complextransaction",
            "transaction",
            "currencyhistoryerror",
            "pricehistoryerror",
        }:
            is_enabled = request.data.get("is_enabled", "true")

            if is_enabled == "true":
                queryset = queryset.filter(is_enabled=True)

        if content_type.model == "complextransaction":
            queryset = queryset.filter(is_deleted=False)

        queryset = handle_filters(queryset, filter_settings, master_user, content_type)

        ordering = request.data.get("ordering", None)

        _l.debug(f"ordering {ordering}")

        if ordering:
            queryset = sort_by_dynamic_attrs(queryset, ordering, master_user, content_type)

        if global_table_search:
            queryset = handle_global_table_search(
                queryset,
                global_table_search,
                self.serializer_class.Meta.model,
                content_type,
            )

        page = self.paginator.post_paginate_queryset(queryset, request)

        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["post"], url_path="ev-group")
    def list_ev_group(self, request, *args, **kwargs):
        start_time = time.time()

        groups_types = request.data.get("groups_types", None)
        groups_values = request.data.get("groups_values", None)
        groups_order = request.data.get("groups_order", None)
        master_user = request.user.master_user
        content_type = ContentType.objects.get_for_model(self.serializer_class.Meta.model)
        filter_settings = request.data.get("filter_settings", None)
        global_table_search = request.data.get("global_table_search", "")
        ev_options = request.data.get("ev_options", "")

        qs = self.get_queryset()

        qs = self.filter_queryset(qs)

        filtered_qs = self.get_queryset()

        filtered_qs = filtered_qs.filter(id__in=qs)

        filtered_qs = handle_filters(filtered_qs, filter_settings, master_user, content_type)

        if global_table_search:
            filtered_qs = handle_global_table_search(
                filtered_qs,
                global_table_search,
                self.serializer_class.Meta.model,
                content_type,
            )

        if content_type.model not in {
            "currencyhistory",
            "pricehistory",
            "currencyhistoryerror",
            "pricehistoryerror",
        }:
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

        page = self.paginator.post_paginate_queryset(filtered_qs.order_by("id"), request)

        _l.debug(f"Filtered EV Group List {str(time.time() - start_time)} seconds ")

        if content_type.model == "transactiontype":  # FIXME refactor someday
            from poms.transactions.models import TransactionTypeGroup

            # It happens because we change TransactionTypeGroup relation to user_code,
            # so its broke default relation group counting, and now we need to get group name separately
            # maybe we need to refactor this whole module, or just provide user_codes and frontend app will

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

        # _l.info(f"page {page}")

        if page is not None:
            return self.get_paginated_response(page)

        return Response(filtered_qs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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
            res = self.celery_task.apply_async(
                kwargs={
                    "instance": instance,
                    "context": {
                        "space_code": request.space_code,
                        "realm_code": request.realm_code,
                    },
                }
            )
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


def _get_values_for_select(model, value_type, key, filter_kw, include_deleted=False):
    """
    :param model:
    :param value_type: Allowed values: 10, 20, 30, 40, 'field'
    :param key:
    :param filter_kw: Keyword arguments for method .filter()
    :type filter_kw: dict
    :param include_deleted:
    """
    filter_kw[f"{key}__isnull"] = False

    if value_type not in {10, 20, 40, "field"}:
        return Response(
            {
                "status": status.HTTP_404_NOT_FOUND,
                "message": "Invalid value_type for content_type.",
                "results": [],
            }
        )

    with contextlib.suppress(FieldDoesNotExist):
        if model._meta.get_field("is_deleted") and not include_deleted:
            filter_kw["is_deleted"] = False

    if value_type in {10, 20, 40}:
        return model.objects.filter(**filter_kw).order_by(key).values_list(key, flat=True).distinct(key)

    elif value_type == "field":
        return (
            model.objects.filter(**filter_kw)
            .order_by(key + "__user_code")
            .values_list(key + "__user_code", flat=True)
            .distinct(key + "__user_code")
        )


def _get_values_of_generic_attribute(master_user, value_type, content_type, key):
    """
    :param master_user:
    :param value_type: Allowed values: 10, 20, 30, 40, 'field'
    :param content_type:
    :param key:
    :return list:
    """

    results = []
    attribute_type_user_code = key.split("attributes.")[1]

    attribute_type = GenericAttributeType.objects.get(
        master_user=master_user,
        user_code=attribute_type_user_code,
        content_type=content_type,
    )

    if value_type == 10:
        results = (
            GenericAttribute.objects.filter(
                content_type=content_type,
                attribute_type=attribute_type,
                value_string__isnull=False,
            )
            .order_by("value_string")
            .values_list("value_string", flat=True)
            .distinct("value_string")
        )
    elif value_type == 20:
        results = (
            GenericAttribute.objects.filter(
                content_type=content_type,
                attribute_type=attribute_type,
                value_float__isnull=False,
            )
            .order_by("value_float")
            .values_list("value_float", flat=True)
            .distinct("value_float")
        )
    elif value_type == 30:
        results = (
            GenericAttribute.objects.filter(
                content_type=content_type,
                attribute_type=attribute_type,
                classifier__name__isnull=False,
            )
            .order_by("classifier__name")
            .values_list("classifier__name", flat=True)
            .distinct("classifier__name")
        )
    elif value_type == 40:
        results = (
            GenericAttribute.objects.filter(
                content_type=content_type,
                attribute_type=attribute_type,
                value_date__isnull=False,
            )
            .order_by("value_date")
            .values_list("value_date", flat=True)
            .distinct("value_date")
        )

    return list(results)


def _get_values_from_report(content_type, report_instance_id, key):
    """
    Returns unique value from items for custom field or system attribute
    of report

    :param content_type:
    :param report_instance_id:
    :type report_instance_id: int
    :param key:
    :return list:
    """

    report_instance_model = apps.get_model(f"{content_type}instance")

    report_instance = report_instance_model.objects.get(id=report_instance_id)

    full_items = report_instance.data["items"]

    # for item in full_items:
    #     if key in item and item[key] not in (None, ''):
    #         values.add(item[key])
    values = {item[key] for item in full_items if key in item and item[key] not in (None, "")}

    values = sorted(values)
    return values


class ValuesForSelectViewSet(AbstractApiView, ViewSet):
    renderer_classes = [FinmarsJSONRenderer]

    def list(self, request, *args, **kwargs):
        content_type_name = request.query_params.get("content_type", None)
        key = request.query_params.get("key", None)
        value_type = request.query_params.get("value_type", None)
        include_deleted = request.query_params.get("include_deleted", None)
        report_instance_id = request.query_params.get("report_instance_id", None)

        master_user = request.user.master_user

        # keys of attributes that are not relations (e.g. not: instrument.name, currency.user_code etc.)
        report_system_attrs_keys_list = []

        # region Exceptions
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

        # endregion Exceptions

        # report_instance_id is required only in some cases
        if report_instance_id is not None:
            report_instance_id = int(report_instance_id)

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

        is_report = content_type_name in (
            "reports.balancereport",
            "reports.plreport",
            "reports.transactionreport",
        )

        if is_report:
            report_system_attrs_keys_list = [
                item["key"] for item in model.get_system_attrs() if item["value_type"] != "field"
            ]

        if "attributes." in key:
            try:
                results = _get_values_of_generic_attribute(master_user, value_type, content_type, key)

                if "Cash & Equivalents" not in results:
                    results.append("Cash & Equivalents")

            except GenericAttributeType.DoesNotExist:
                return Response(
                    {
                        "status": status.HTTP_404_NOT_FOUND,
                        "message": "No content type provided.",
                        "results": [],
                    }
                )

        elif is_report and (key in report_system_attrs_keys_list or "custom_fields." in key):
            if report_instance_id is None:
                return Response(
                    {
                        "status": status.HTTP_404_NOT_FOUND,
                        "message": "report_instance_id needed for such combination of a content_type and a key",
                        "results": [],
                    }
                )

            results = _get_values_from_report(content_type_name, report_instance_id, key)

        elif content_type_name == "instruments.pricehistory":
            results = _get_values_for_select(
                model,
                value_type,
                key,
                {"instrument__master_user": master_user},
                include_deleted,
            )

        elif content_type_name == "currencies.currencyhistory":
            results = _get_values_for_select(
                model,
                value_type,
                key,
                {"currency__master_user": master_user},
                include_deleted,
            )

        elif content_type_name in [
            "transactions.transactionclass",
            "instruments.country",
        ]:
            results = model.objects.all().order_by(key).values_list(key, flat=True).distinct(key)

        else:
            results = _get_values_for_select(
                model,
                value_type,
                key,
                {"master_user": master_user},
                include_deleted,
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

    def list(self, request, *args, **kwargs):
        log_file = "/var/log/finmars/backend/django.log"

        seek_to = request.query_params.get("seek_to", 0)

        seek_to = int(seek_to)

        try:
            file_length = getsize(log_file)
        except Exception as e:
            raise Http404("Cannot access file") from e

        if seek_to == 0:
            seek_to = file_length - 1000

        elif seek_to < 0:
            seek_to = 0

        elif seek_to > file_length:
            seek_to = file_length

        context = {}
        try:
            context["log"] = open(log_file, "r")
            context["log"].seek(seek_to)
            context["starts"] = seek_to
        except IOError as exc:
            raise Http404("Cannot access file") from exc

        return HttpResponse(self.iter_json(context), content_type="application/json")


class RealmMigrateSchemeView(APIView):
    throttle_classes = []
    permission_classes = []
    authentication_classes = []  # no auth neede
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.JSONParser,
    )
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = RealmMigrateSchemeSerializer

    def get_serializer_context(self):
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            space_code = serializer.validated_data.get("space_code")
            realm_code = serializer.validated_data.get("realm_code")

            apply_migration_to_space.apply_async(kwargs={"space_code": space_code, "realm_code": realm_code})

            # Optionally, reset the search path to default after migrating
            # with connection.cursor() as cursor:
            #     cursor.execute("SET search_path TO public;")

            return Response({"status": "ok"})

        except Exception as e:
            _l.error(f"RealmMigrateSchemeView.exception: {str(e)} " f"trace: {traceback.format_exc()}")

            return Response({"status": "error", "message": str(e)})
