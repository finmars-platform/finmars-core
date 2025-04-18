import logging
import time
import traceback

import django_filters
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import Http404
from django.utils.translation import gettext_lazy
from django_filters.rest_framework import FilterSet
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings

from poms.accounts.models import Account
from poms.celery_tasks.models import CeleryTask
from poms.common.filters import (
    AttributeFilter,
    CharExactFilter,
    CharFilter,
    GlobalTableSearchFilter,
    GroupsAttributeFilter,
    ModelExtMultipleChoiceFilter,
    ModelExtUserCodeMultipleChoiceFilter,
    NoOpFilter,
)
from poms.common.utils import get_list_of_entity_attributes
from poms.common.views import (
    AbstractAsyncViewSet,
    AbstractClassModelViewSet,
    AbstractModelViewSet,
)
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, InstrumentType, PricingPolicy
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet, GenericClassifierViewSet
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.transactions.filters import (
    ComplexTransactionPermissionFilter,
    TransactionObjectPermissionFilter,
)
from poms.transactions.handlers import TransactionTypeProcess
from poms.transactions.models import (
    ComplexTransaction,
    EventClass,
    NotificationClass,
    Transaction,
    TransactionClass,
    TransactionType,
    TransactionTypeGroup,
)
from poms.transactions.serializers import (
    ComplexTransactionEvItemSerializer,
    ComplexTransactionLightSerializer,
    ComplexTransactionSerializer,
    ComplexTransactionSimpleSerializer,
    ComplexTransactionViewOnly,
    ComplexTransactionViewOnlySerializer,
    EventClassSerializer,
    NotificationClassSerializer,
    RecalculatePermissionComplexTransactionSerializer,
    RecalculatePermissionTransactionSerializer,
    RecalculateUserFieldsSerializer,
    TransactionClassSerializer,
    TransactionSerializer,
    TransactionTypeGroupSerializer,
    TransactionTypeLightSerializer,
    TransactionTypeLightSerializerWithInputs,
    TransactionTypeProcessSerializer,
    TransactionTypeRecalculateSerializer,
    TransactionTypeSerializer,
)
from poms.transactions.tasks import (
    recalculate_permissions_complex_transaction,
    recalculate_permissions_transaction,
    recalculate_user_fields,
)
from poms.users.filters import OwnerByMasterUserFilter

_l = logging.getLogger("poms.transactions")


class EventClassViewSet(AbstractClassModelViewSet):
    queryset = EventClass.objects
    serializer_class = EventClassSerializer


class NotificationClassViewSet(AbstractClassModelViewSet):
    queryset = NotificationClass.objects
    serializer_class = NotificationClassSerializer


class TransactionClassViewSet(AbstractClassModelViewSet):
    queryset = TransactionClass.objects
    serializer_class = TransactionClassSerializer


class TransactionTypeGroupFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()

    class Meta:
        model = TransactionTypeGroup
        fields = []


class TransactionTypeGroupViewSet(AbstractModelViewSet):
    queryset = TransactionTypeGroup.objects
    serializer_class = TransactionTypeGroupSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = TransactionTypeGroupFilterSet
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
    ]


class ModelExtWithAllWithPermissionMultipleChoiceFilter(ModelExtMultipleChoiceFilter):
    all_field_name = None

    def __init__(self, *args, **kwargs):
        self.all_field_name = kwargs.pop("all_field_name")
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if not value:
            return qs

        if self.is_noop(qs, value):
            return qs

        q = Q()
        for v in set(value):
            predicate = self.get_filter_predicate(v)
            q |= Q(**predicate)

        qs = self.get_method(qs)(q | Q(**{self.all_field_name: True}))

        return qs.distinct() if self.distinct else qs


class ModelExtWithAllWithMultipleChoiceFilter(ModelExtMultipleChoiceFilter):
    all_field_name = None

    def __init__(self, *args, **kwargs):
        self.all_field_name = kwargs.pop("all_field_name")
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if not value:
            return qs

        if self.is_noop(qs, value):
            return qs

        q = Q()
        for v in set(value):
            predicate = self.get_filter_predicate(v)

            print(f"predicate {predicate}")

            q |= Q(**predicate)

        qs = self.get_method(qs)(q | Q(**{self.all_field_name: True}))

        return qs.distinct() if self.distinct else qs


class TransactionTypeFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    user_code__exact = CharExactFilter(field_name="user_code")
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    group = ModelExtMultipleChoiceFilter(model=TransactionTypeGroup)
    portfolios = ModelExtWithAllWithMultipleChoiceFilter(
        model=Portfolio, all_field_name="is_valid_for_all_portfolios"
    )
    instrument_types = ModelExtWithAllWithMultipleChoiceFilter(
        model=InstrumentType, all_field_name="is_valid_for_all_instruments"
    )
    is_valid_for_all_portfolios = django_filters.BooleanFilter()
    is_valid_for_all_instruments = django_filters.BooleanFilter()

    class Meta:
        model = TransactionType
        fields = []


class TransactionTypeAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = TransactionType
    target_model_serializer = TransactionTypeSerializer
    permission_classes = GenericAttributeTypeViewSet.permission_classes + []


class TransactionTypeEvFilterSet(FilterSet):
    id = NoOpFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    is_valid_for_all_portfolios = django_filters.BooleanFilter()
    is_valid_for_all_instruments = django_filters.BooleanFilter()

    class Meta:
        model = TransactionType
        fields = []


class TransactionTypeViewSet(AbstractModelViewSet):
    queryset = TransactionType.objects.select_related(
        "master_user",
        "owner",
    ).prefetch_related("instrument_types", "attributes", "portfolios")
    serializer_class = TransactionTypeSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = TransactionTypeFilterSet
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
    ]

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=TransactionTypeLightSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=["post"],
        url_path="ev-item",
        serializer_class=TransactionTypeLightSerializer,
    )
    def list_ev_item(self, request, *args, **kwargs):
        return super().list_ev_item(request, *args, **kwargs)

    @action(
        detail=False,
        methods=["get"],
        url_path="light-with-inputs",
        serializer_class=TransactionTypeLightSerializerWithInputs,
    )
    def list_light_with_inputs(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], url_path="attributes")
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {"key": "name", "name": "Name", "value_type": 10},
            {"key": "short_name", "name": "Short name", "value_type": 10},
            {"key": "user_code", "name": "User code", "value_type": 10},
            {"key": "public_name", "name": "Public name", "value_type": 10},
            {"key": "notes", "name": "Notes", "value_type": 10},
            {"key": "group", "name": "Group", "value_type": "field"},
            {"key": "display_expr", "name": "Display Expression", "value_type": 10},
            {
                "key": "instrument_types",
                "name": "Instrument types",
                "value_content_type": "instruments.instrumenttype",
                "value_entity": "instrument-type",
                "code": "user_code",
                "value_type": "mc_field",
            },
            {
                "key": "portfolios",
                "name": "Portfolios",
                "value_content_type": "portfolios.portfolio",
                "value_entity": "portfolio",
                "code": "user_code",
                "value_type": "mc_field",
            },
            {"key": "user_text_1", "name": "User Text 1", "value_type": 10},
            {"key": "user_text_2", "name": "User Text 2", "value_type": 10},
            {"key": "user_text_3", "name": "User Text 3", "value_type": 10},
            {"key": "user_text_4", "name": "User Text 4", "value_type": 10},
            {"key": "user_text_5", "name": "User Text 5", "value_type": 10},
            {"key": "user_text_6", "name": "User Text 6", "value_type": 10},
            {"key": "user_text_7", "name": "User Text 7", "value_type": 10},
            {"key": "user_text_8", "name": "User Text 8", "value_type": 10},
            {"key": "user_text_9", "name": "User Text 9", "value_type": 10},
            {"key": "user_text_10", "name": "User Text 10", "value_type": 10},
            {"key": "user_text_11", "name": "User Text 11", "value_type": 10},
            {"key": "user_text_12", "name": "User Text 12", "value_type": 10},
            {"key": "user_text_13", "name": "User Text 13", "value_type": 10},
            {"key": "user_text_14", "name": "User Text 14", "value_type": 10},
            {"key": "user_text_15", "name": "User Text 15", "value_type": 10},
            {"key": "user_text_16", "name": "User Text 16", "value_type": 10},
            {"key": "user_text_17", "name": "User Text 17", "value_type": 10},
            {"key": "user_text_18", "name": "User Text 18", "value_type": 10},
            {"key": "user_text_19", "name": "User Text 19", "value_type": 10},
            {"key": "user_text_20", "name": "User Text 20", "value_type": 10},
            {"key": "user_text_21", "name": "User Text 21", "value_type": 10},
            {"key": "user_text_22", "name": "User Text 22", "value_type": 10},
            {"key": "user_text_23", "name": "User Text 23", "value_type": 10},
            {"key": "user_text_24", "name": "User Text 24", "value_type": 10},
            {"key": "user_text_25", "name": "User Text 25", "value_type": 10},
            {"key": "user_text_26", "name": "User Text 26", "value_type": 10},
            {"key": "user_text_27", "name": "User Text 27", "value_type": 10},
            {"key": "user_text_28", "name": "User Text 28", "value_type": 10},
            {"key": "user_text_29", "name": "User Text 29", "value_type": 10},
            {"key": "user_text_30", "name": "User Text 30", "value_type": 10},
            {"key": "user_number_1", "name": "User Number 1", "value_type": 10},
            {"key": "user_number_2", "name": "User Number 2", "value_type": 10},
            {"key": "user_number_3", "name": "User Number 3", "value_type": 10},
            {"key": "user_number_4", "name": "User Number 4", "value_type": 10},
            {"key": "user_number_5", "name": "User Number 5", "value_type": 10},
            {"key": "user_number_6", "name": "User Number 6", "value_type": 10},
            {"key": "user_number_7", "name": "User Number 7", "value_type": 10},
            {"key": "user_number_8", "name": "User Number 8", "value_type": 10},
            {"key": "user_number_9", "name": "User Number 9", "value_type": 10},
            {"key": "user_number_10", "name": "User Number 10", "value_type": 10},
            {"key": "user_number_11", "name": "User Number 11", "value_type": 10},
            {"key": "user_number_12", "name": "User Number 12", "value_type": 10},
            {"key": "user_number_13", "name": "User Number 13", "value_type": 10},
            {"key": "user_number_14", "name": "User Number 14", "value_type": 10},
            {"key": "user_number_15", "name": "User Number 15", "value_type": 10},
            {"key": "user_number_16", "name": "User Number 16", "value_type": 10},
            {"key": "user_number_17", "name": "User Number 17", "value_type": 10},
            {"key": "user_number_18", "name": "User Number 18", "value_type": 10},
            {"key": "user_number_19", "name": "User Number 19", "value_type": 10},
            {"key": "user_number_20", "name": "User Number 20", "value_type": 10},
            {"key": "user_date_1", "name": "User Date 1", "value_type": 10},
            {"key": "user_date_2", "name": "User Date 2", "value_type": 10},
            {"key": "user_date_3", "name": "User Date 3", "value_type": 10},
            {"key": "user_date_4", "name": "User Date 4", "value_type": 10},
            {"key": "user_date_5", "name": "User Date 5", "value_type": 10},
        ]

        items += get_list_of_entity_attributes("transactions.transactiontype")

        result = {"count": len(items), "next": None, "previous": None, "results": items}

        return Response(result)

    def get_context_for_book(self, request):
        master_user = request.user.master_user
        instrument_id = request.query_params.get("context_instrument", None)
        pricing_currency_id = request.query_params.get("context_pricing_currency", None)
        accrued_currency_id = request.query_params.get("context_accrued_currency", None)
        portfolio_id = request.query_params.get("context_portfolio", None)
        account_id = request.query_params.get("context_account", None)
        strategy1_id = request.query_params.get("context_strategy1", None)
        strategy2_id = request.query_params.get("context_strategy2", None)
        strategy3_id = request.query_params.get("context_strategy3", None)

        currency_id = request.query_params.get("context_currency", None)
        pricing_policy_id = request.query_params.get("context_pricing_policy", None)
        allocation_balance_id = request.query_params.get("context_allocation_balance", None)
        allocation_pl_id = request.query_params.get("context_allocation_pl", None)

        context_instrument = None
        context_pricing_currency = None
        context_accrued_currency = None
        context_portfolio = None
        context_account = None
        context_strategy1 = None
        context_strategy2 = None
        context_strategy3 = None

        context_currency = None
        context_pricing_policy = None
        context_allocation_balance = None
        context_allocation_pl = None

        context_position_size = request.query_params.get("context_position_size", None)

        if context_position_size:
            try:
                context_position_size = float(context_position_size)
            except Exception:
                context_position_size = None

        context_effective_date = request.query_params.get("context_effective_date", None)
        context_report_date = request.query_params.get("context_report_date", None)
        context_report_start_date = request.query_params.get("context_report_start_date", None)

        # context_notification_date = request.query_params.get(
        #     "context_notification_date"
        # )
        # context_final_date = request.query_params.get("context_final_date")
        # context_maturity_date = request.query_params.get("context_maturity_date")

        if pricing_policy_id:  # could be user_code
            try:
                context_pricing_policy = PricingPolicy.objects.get(
                    master_user=master_user, id=pricing_policy_id
                )
            except Exception:
                try:
                    context_pricing_policy = PricingPolicy.objects.get(
                        master_user=master_user, user_code=pricing_policy_id
                    )
                except Exception:
                    context_pricing_policy = None

        if currency_id:
            try:
                context_currency = Currency.objects.get(master_user=master_user, id=currency_id)
            except Currency.DoesNotExist:
                context_currency = None

        if allocation_balance_id:
            try:
                context_allocation_balance = Instrument.objects.get(
                    master_user=master_user, id=allocation_balance_id
                )
            except Instrument.DoesNotExist:
                context_allocation_balance = None

        if allocation_pl_id:
            try:
                context_allocation_pl = Instrument.objects.get(master_user=master_user, id=allocation_pl_id)
            except Instrument.DoesNotExist:
                context_allocation_pl = None

        if instrument_id:
            try:
                context_instrument = Instrument.objects.get(master_user=master_user, id=instrument_id)
            except Instrument.DoesNotExist:
                context_instrument = None

        if portfolio_id:
            try:
                context_portfolio = Portfolio.objects.get(master_user=master_user, id=portfolio_id)
            except Portfolio.DoesNotExist:
                context_portfolio = None

        if account_id:
            try:
                context_account = Account.objects.get(master_user=master_user, id=account_id)
            except Account.DoesNotExist:
                context_account = None

        if strategy1_id:
            try:
                context_strategy1 = Strategy1.objects.get(master_user=master_user, id=strategy1_id)
            except Strategy1.DoesNotExist:
                context_strategy1 = None

        if strategy2_id:
            try:
                context_strategy2 = Strategy2.objects.get(master_user=master_user, id=strategy2_id)
            except Strategy2.DoesNotExist:
                context_strategy2 = None

        if strategy3_id:
            try:
                context_strategy3 = Strategy3.objects.get(master_user=master_user, id=strategy3_id)
            except Strategy3.DoesNotExist:
                context_strategy3 = None

        if pricing_currency_id:
            try:
                context_pricing_currency = Currency.objects.get(
                    master_user=master_user, id=pricing_currency_id
                )
            except Currency.DoesNotExist:
                context_pricing_currency = None

        if accrued_currency_id:
            try:
                context_accrued_currency = Currency.objects.get(
                    master_user=master_user, id=pricing_currency_id
                )
            except Currency.DoesNotExist:
                context_accrued_currency = None

        context_values = {
            "context_instrument": context_instrument,
            "context_pricing_currency": context_pricing_currency,
            "context_accrued_currency": context_accrued_currency,
            "context_portfolio": context_portfolio,
            "context_account": context_account,
            "context_strategy1": context_strategy1,
            "context_strategy2": context_strategy2,
            "context_strategy3": context_strategy3,
            "context_position_size": context_position_size,
            "context_effective_date": context_effective_date,
            "context_currency": context_currency,
            "context_report_date": context_report_date,
            "context_report_start_date": context_report_start_date,
            "context_pricing_policy": context_pricing_policy,
            "context_allocation_balance": context_allocation_balance,
            "context_allocation_pl": context_allocation_pl,
            "context_parameter": request.query_params.get("context_parameter"),
        }

        context_parameter_exist = True
        increment = 1
        while context_parameter_exist:
            try:
                parameter = request.query_params.get(f"context_parameter{str(increment)}", None)

                if parameter:
                    context_values[f"context_parameter{str(increment)}"] = parameter
                    increment = increment + 1
                else:
                    context_parameter_exist = False
            except Exception:
                context_parameter_exist = False

        return context_values

    @action(
        detail=True,
        methods=["get", "put"],
        url_path="book",
        serializer_class=TransactionTypeProcessSerializer,
    )
    def book(self, request, pk=None, realm_code=None, space_code=None):
        with transaction.atomic():
            # Some Inputs can choose from which context variable it will take value
            # But by default Context Variables overwrites default value

            context_values = self.get_context_for_book(request)

            print(f"context_values={context_values}  pk={pk}")

            transaction_type = TransactionType.objects.get(pk=pk)

            if request.method == "GET":
                instance = TransactionTypeProcess(
                    process_mode="book",
                    transaction_type=transaction_type,
                    context=self.get_serializer_context(),
                    context_values=context_values,
                    member=request.user.member,
                )

                instance.complex_transaction.id = 0

                serializer = self.get_serializer(instance=instance)
                return Response(serializer.data)
            else:
                # PUT method
                complex_transaction_status = request.data["complex_transaction_status"]

                uniqueness_reaction = request.data.get("uniqueness_reaction", None)

                instance = TransactionTypeProcess(
                    process_mode=request.data["process_mode"],
                    transaction_type=transaction_type,
                    context=self.get_serializer_context(),
                    context_values=context_values,
                    complex_transaction_status=complex_transaction_status,
                    uniqueness_reaction=uniqueness_reaction,
                    member=request.user.member,
                )

                try:
                    serializer = self.get_serializer(instance=instance, data=request.data)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    return Response(serializer.data)

                finally:
                    if instance.has_errors:
                        transaction.set_rollback(True)

    @action(
        detail=True,
        methods=["get", "put"],
        url_path="book-pending",
        serializer_class=TransactionTypeProcessSerializer,
    )
    def book_pending(self, request, pk=None, realm_code=None, space_code=None):
        with transaction.atomic():
            complex_transaction_status = ComplexTransaction.PENDING

            transaction_type = TransactionType.objects.get(pk=pk)

            instance = TransactionTypeProcess(
                process_mode="book",
                transaction_type=transaction_type,
                context=self.get_serializer_context(),
                complex_transaction_status=complex_transaction_status,
                member=request.user.member,
            )

            if request.method == "GET":
                serializer = self.get_serializer(instance=instance)
                return Response(serializer.data)
            else:
                try:
                    serializer = self.get_serializer(instance=instance, data=request.data)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    return Response(serializer.data)
                finally:
                    if instance.has_errors:
                        transaction.set_rollback(True)

    @action(
        detail=True,
        methods=["put"],
        url_path="recalculate",
        serializer_class=TransactionTypeRecalculateSerializer,
        permission_classes=[IsAuthenticated],
    )
    def recalculate(self, request, pk=None, realm_code=None, space_code=None):
        process_mode = request.data.get("process_mode")
        if not process_mode:
            raise ValidationError("mandatory process_mode param is missing!")

        recalculate_inputs = request.data.get("recalculate_inputs")
        if not recalculate_inputs:
            raise ValidationError("mandatory recalculate_inputs param is missing!")

        transaction_type = TransactionType.objects.filter(pk=pk).first()
        if not transaction_type:
            raise Http404(f"TransactionType {pk} doesn't exists")

        context_values = self.get_context_for_book(request)
        # But by default Context Variables overwrites default value
        # default_values = self.get_context_for_book(request)

        process_st = time.perf_counter()

        instance = TransactionTypeProcess(
            transaction_type=transaction_type,
            process_mode=process_mode,
            recalculate_inputs=recalculate_inputs,
            uniqueness_reaction=request.data.get("uniqueness_reaction"),
            values=request.data.get("values"),
            #
            context=self.get_serializer_context(),
            context_values=context_values,
            complex_transaction_status=ComplexTransaction.PRODUCTION,
            member=request.user.member,
        )

        _l.debug(
            "TransactionTypeProcess recalculate mode instance created: %s",
            "{:3.3f}".format(time.perf_counter() - process_st),
        )

        serializer = self.get_serializer(instance=instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="recalculate-user-fields",
        serializer_class=RecalculateUserFieldsSerializer,
    )
    def recalculate_user_fields(self, request, pk, realm_code=None, space_code=None):
        print(f"pk={pk} request.data={request.data}")

        serializer = RecalculateUserFieldsSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        print(f"instance={instance}")

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            status="P",
            type="complex_transaction_user_field_recalculation",
        )

        celery_task.options_object = {
            "transaction_type_id": pk,
            "target_key": request.data.get("key", None),
        }

        celery_task.save()

        recalculate_user_fields.apply_async(
            kwargs={
                "task_id": celery_task.id,
                "context": {
                    "space_code": celery_task.master_user.space_code,
                    "realm_code": celery_task.master_user.realm_code,
                },
            }
        )

        instance.task_id = celery_task.id
        instance.task_status = "P"

        print(f"celery_task.id={celery_task.id} status={celery_task.status}")

        deserializer = RecalculateUserFieldsSerializer(instance=instance)

        # import-like status check chain someday, now is not important
        # because status showed at Active Processes page
        return Response(deserializer.data, status=status.HTTP_200_OK)


class TransactionAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Transaction
    target_model_serializer = TransactionSerializer


class TransactionClassifierViewSet(GenericClassifierViewSet):
    target_model = Transaction


class TransactionFilterSet(FilterSet):
    id = NoOpFilter()

    complex_transaction__code = django_filters.RangeFilter()
    complex_transaction__date = django_filters.DateFromToRangeFilter()
    complex_transaction__transaction_type = django_filters.Filter(
        field_name="complex_transaction__transaction_type"
    )
    complex_transaction = ModelExtMultipleChoiceFilter(
        model=ComplexTransaction,
        field_name="id",
        master_user_path="transaction_type__master_user",
    )
    transaction_class = django_filters.ModelMultipleChoiceFilter(queryset=TransactionClass.objects)
    transaction_code = django_filters.NumberFilter()
    transaction_currency = ModelExtMultipleChoiceFilter(model=Currency)
    position_size_with_sign = django_filters.RangeFilter()
    settlement_currency = ModelExtMultipleChoiceFilter(model=Currency)
    cash_consideration = django_filters.RangeFilter()
    principal_with_sign = django_filters.RangeFilter()
    carry_with_sign = django_filters.RangeFilter()
    overheads_with_sign = django_filters.RangeFilter()
    transaction_date = django_filters.DateFromToRangeFilter()
    accounting_date = django_filters.DateFromToRangeFilter()
    cash_date = django_filters.DateFromToRangeFilter()
    reference_fx_rate = django_filters.RangeFilter()
    is_locked = django_filters.BooleanFilter()
    is_deleted = django_filters.BooleanFilter()
    factor = django_filters.RangeFilter()
    trade_price = django_filters.RangeFilter()
    principal_amount = django_filters.RangeFilter()
    carry_amount = django_filters.RangeFilter()
    overheads = django_filters.RangeFilter()

    class Meta:
        model = Transaction
        fields = []


def get_transaction_queryset(select_related=True, complex_transaction_transactions=False):
    qs = Transaction.objects

    fields1 = (
        "master_user",
        "complex_transaction",
        "complex_transaction__transaction_type",
        # 'complex_transaction__transaction_type__group',
        "transaction_class",
        "instrument",
        "instrument__instrument_type",
        "instrument__instrument_type__instrument_class",
        "transaction_currency",
        "settlement_currency",
        "portfolio",
        "account_cash",
        "account_cash__type",
        "account_position",
        "account_position__type",
        "account_interim",
        "account_interim__type",
        "strategy1_position",
        "strategy1_position__subgroup",
        "strategy1_position__subgroup__group",
        "strategy1_cash",
        "strategy1_cash__subgroup",
        "strategy1_cash__subgroup__group",
        "strategy2_position",
        "strategy2_position__subgroup",
        "strategy2_position__subgroup__group",
        "strategy2_cash",
        "strategy2_cash__subgroup",
        "strategy2_cash__subgroup__group",
        "strategy3_position",
        "strategy3_position__subgroup",
        "strategy3_position__subgroup__group",
        "strategy3_cash",
        "strategy3_cash__subgroup",
        "strategy3_cash__subgroup__group",
        "responsible",
        "responsible__group",
        "counterparty",
        "counterparty__group",
        "linked_instrument",
        "linked_instrument__instrument_type",
        "linked_instrument__instrument_type__instrument_class",
        "allocation_balance",
        "allocation_balance__instrument_type",
        "allocation_balance__instrument_type__instrument_class",
        "allocation_pl",
        "allocation_pl__instrument_type",
        "allocation_pl__instrument_type__instrument_class",
    )
    if select_related:
        qs = qs.select_related(*fields1)
    else:
        qs = qs.prefetch_related(*fields1)

    qs = qs.prefetch_related(
        get_attributes_prefetch(),
    )

    if complex_transaction_transactions:
        qs = qs.prefetch_related(
            Prefetch(
                "complex_transaction__transactions",
                queryset=get_transaction_queryset(select_related=select_related).order_by(
                    "complex_transaction_order", "transaction_date"
                ),
            )
        )

    return qs


def get_complex_transaction_queryset(select_related=True, transactions=False):
    fields1 = (
        "transaction_type",
        # 'transaction_type__group',
    )
    qs = ComplexTransaction.objects

    if select_related:
        qs = qs.select_related(*fields1)
    else:
        qs = qs.prefetch_related(*fields1)

    qs = qs.prefetch_related(
        get_attributes_prefetch(),
    )

    if transactions:
        qs = qs.prefetch_related(
            Prefetch(
                "transactions",
                queryset=get_transaction_queryset(select_related=select_related).order_by(
                    "transaction_date",
                    "complex_transaction_order",
                ),
            )
        )

    return qs


class TransactionViewSet(AbstractModelViewSet):
    queryset = get_transaction_queryset(select_related=False, complex_transaction_transactions=True)
    serializer_class = TransactionSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        TransactionObjectPermissionFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + []
    filter_class = TransactionFilterSet
    ordering_fields = [
        "complex_transaction",
        "complex_transaction__code",
        "complex_transaction__date",
        "complex_transaction_order",
        "transaction_code",
        "portfolio",
        "portfolio__user_code",
        "portfolio__name",
        "portfolio__short_name",
        "portfolio__public_name",
        "instrument",
        "instrument__user_code",
        "instrument__name",
        "instrument__short_name",
        "instrument__public_name",
        "transaction_currency",
        "transaction_currency__user_code",
        "transaction_currency__name",
        "transaction_currency__short_name",
        "transaction_currency__public_name",
        "position_size_with_sign",
        "settlement_currency",
        "settlement_currency__user_code",
        "settlement_currency__name",
        "settlement_currency__short_name",
        "settlement_currency__public_name",
        "cash_consideration",
        "principal_with_sign",
        "carry_with_sign",
        "overheads_with_sign",
        "transaction_date",
        "accounting_date",
        "cash_date",
        "account_cash",
        "account_cash__user_code",
        "account_cash__name",
        "account_cash__short_name",
        "account_cash__public_name",
        "account_cash",
        "account_cash__user_code",
        "account_position__name",
        "account_position__short_name",
        "account_position__public_name",
        "account_interim",
        "account_interim__user_code",
        "account_interim__name",
        "account_interim__short_name",
        "account_interim__public_name",
        "strategy1_position",
        "strategy1_position__user_code",
        "strategy1_position__name",
        "strategy1_position__short_name",
        "strategy1_position__public_name",
        "strategy1_cash",
        "strategy1_cash__user_code",
        "strategy1_cash__name",
        "strategy1_cash__short_name",
        "strategy1_cash__public_name",
        "strategy2_position",
        "strategy2_position__user_code",
        "strategy2_position__name",
        "strategy2_position__short_name",
        "strategy2_position__public_name",
        "strategy2_cash",
        "strategy2_cash__user_code",
        "strategy2_cash__name",
        "strategy2_cash__short_name",
        "strategy2_cash__public_name",
        "strategy3_position",
        "strategy3_position__user_code",
        "strategy3_position__name",
        "strategy3_position__short_name",
        "strategy3_position__public_name",
        "strategy3_cash",
        "strategy3_cash__user_code",
        "strategy3_cash__name",
        "strategy3_cash__short_name",
        "strategy3_cash__public_name",
        "reference_fx_rate",
        "is_locked",
        "is_deleted",
        "factor",
        "trade_price",
        "principal_amount",
        "carry_amount",
        "overheads",
        "responsible",
        "responsible__user_code",
        "responsible__name",
        "responsible__short_name",
        "responsible__public_name",
        "counterparty",
        "counterparty__user_code",
        "counterparty__name",
        "counterparty__short_name",
        "counterparty__public_name",
        "linked_instrument",
        "linked_instrument__user_code",
        "linked_instrument__name",
        "linked_instrument__short_name",
        "linked_instrument__public_name",
        "allocation_balance",
        "allocation_balance__user_code",
        "allocation_balance__name",
        "allocation_balance__short_name",
        "allocation_balance__public_name",
        "allocation_pl",
        "allocation_pl__user_code",
        "allocation_pl__name",
        "allocation_pl__short_name",
        "allocation_pl__public_name",
    ]

    def perform_update(self, serializer):
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)

    @action(detail=False, methods=["get"], url_path="attributes")
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {"key": "notes", "name": "Notes", "value_type": 10},
            {"key": "transaction_code", "name": "Transaction Code", "value_type": 20},
            {
                "key": "transaction_class",
                "name": "Transaction class",
                "value_content_type": "transactions.transactionclass",
                "value_entity": "transaction_class",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "portfolio",
                "name": "Portfolio",
                "value_content_type": "portfolios.portfolio",
                "value_entity": "portfolio",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "transaction_currency",
                "name": "Transaction currency",
                "value_type": "field",
            },
            {
                "key": "instrument",
                "name": "Instrument",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "position_size_with_sign",
                "name": "Position Size with sign",
                "value_type": 20,
            },
            {
                "key": "settlement_currency",
                "name": "Settlement currency",
                "value_type": "field",
            },
            {
                "key": "cash_consideration",
                "name": "Cash consideration",
                "value_type": 20,
            },
            {
                "key": "principal_with_sign",
                "name": "Principal with sign",
                "value_type": 20,
            },
            {"key": "carry_with_sign", "name": "Carry with sign", "value_type": 20},
            {
                "key": "overheads_with_sign",
                "name": "Overheads with sign",
                "value_type": 20,
            },
            {"key": "accounting_date", "name": "Accounting date", "value_type": 40},
            {"key": "cash_date", "name": "Cash date", "value_type": 40},
            {"key": "account_cash", "name": "Account cash", "value_type": "field"},
            {
                "key": "account_position",
                "name": "Account position",
                "value_type": "field",
            },
            {
                "key": "account_interim",
                "name": "Account interim",
                "value_type": "field",
            },
            {
                "key": "strategy1_position",
                "name": "Strategy1 position",
                "value_type": "field",
            },
            {"key": "strategy1_cash", "name": "Strategy1 cash", "value_type": "field"},
            {
                "key": "strategy2_position",
                "name": "Strategy2 position",
                "value_type": "field",
            },
            {"key": "strategy2_cash", "name": "Strategy2 cash", "value_type": "field"},
            {
                "key": "strategy3_position",
                "name": "Strategy3 position",
                "value_type": "field",
            },
            {"key": "strategy3_cash", "name": "Strategy3 cash", "value_type": "field"},
            {"key": "reference_fx_rate", "name": "Reference fx rate", "value_type": 20},
            {"key": "is_locked", "name": "Is locked", "value_type": 50},
            {"key": "is_canceled", "name": "Is canceled", "value_type": 50},
            {"key": "factor", "name": "Factor", "value_type": 20},
            {"key": "principal_amount", "name": "Principal amount", "value_type": 20},
            {"key": "carry_amount", "name": "Carry amount", "value_type": 20},
            {"key": "overheads", "name": "overheads", "value_type": 20},
            {
                "key": "responsible",
                "name": "Responsible",
                "value_content_type": "counterparties.responsible",
                "value_entity": "responsible",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "counterparty",
                "name": "Counterparty",
                "value_content_type": "counterparties.counterparty",
                "value_entity": "counterparty",
                "code": "user_code",
                "value_type": "field",
            },
            {"key": "trade_price", "name": "Trade price", "value_type": 20},
            {
                "key": "allocation_balance",
                "name": "Allocation Balance",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "allocation_pl",
                "name": "Allocation P&L",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "linked_instrument",
                "name": "Linked instrument",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "code": "user_code",
                "value_type": "field",
            },
        ]

        result = {"count": len(items), "next": None, "previous": None, "results": items}

        return Response(result)


class ComplexTransactionAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = ComplexTransaction
    target_model_serializer = ComplexTransactionSerializer


class ComplexTransactionFilterSet(FilterSet):
    id = NoOpFilter()
    code = django_filters.NumberFilter()
    date = django_filters.DateFromToRangeFilter()
    is_deleted = django_filters.BooleanFilter()
    transactions__accounting_date = django_filters.DateFromToRangeFilter()
    transactions__portfolio__user_code = ModelExtUserCodeMultipleChoiceFilter(model=Portfolio)
    global_table_search = GlobalTableSearchFilter(label="Global table search")

    class Meta:
        model = ComplexTransaction
        fields = []


class ComplexTransactionViewSet(AbstractModelViewSet):
    queryset = get_complex_transaction_queryset(select_related=False, transactions=True)
    serializer_class = ComplexTransactionSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        ComplexTransactionPermissionFilter,
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = ComplexTransactionFilterSet
    ordering_fields = ["date", "code", "is_deleted", "transactions__accounting_date"]

    def create(self, request, *args, **kwargs):
        raise ValidationError("Not allowed!")

    @action(
        detail=False,
        methods=["post"],
        url_path="ev-item",
        serializer_class=ComplexTransactionEvItemSerializer,
    )
    def list_ev_item(self, request, *args, **kwargs):
        return super().list_ev_item(request, *args, **kwargs)

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=ComplexTransactionLightSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], url_path="attributes")
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {"key": "code", "name": "Code", "value_type": 20},
            {"key": "date", "name": "Date", "value_type": 40},
            {
                "key": "status",
                "name": "Status",
                "value_type": "field",
                "value_entity": "complex-transaction-status",
                "code": "user_code",
                "value_content_type": "transactions.complextransactionstatus",
            },
            {"key": "is_locked", "name": "Is locked", "value_type": 50},
            {"key": "is_canceled", "name": "Is canceled", "value_type": 50},
            {
                "key": "transaction_unique_code",
                "name": "Transaction Unique Code",
                "value_type": 10,
            },
            {"key": "text", "name": "Description", "value_type": 10},
            {
                "key": "transaction_type",
                "name": "Transaction Type",
                "value_type": "field",
                "value_entity": "transaction-type",
                "code": "user_code",
                "value_content_type": "transactions.transactiontype",
            },
            {"key": "user_text_1", "name": "User Text 1", "value_type": 10},
            {"key": "user_text_2", "name": "User Text 2", "value_type": 10},
            {"key": "user_text_3", "name": "User Text 3", "value_type": 10},
            {"key": "user_text_4", "name": "User Text 4", "value_type": 10},
            {"key": "user_text_5", "name": "User Text 5", "value_type": 10},
            {"key": "user_text_6", "name": "User Text 6", "value_type": 10},
            {"key": "user_text_7", "name": "User Text 7", "value_type": 10},
            {"key": "user_text_8", "name": "User Text 8", "value_type": 10},
            {"key": "user_text_9", "name": "User Text 9", "value_type": 10},
            {"key": "user_text_10", "name": "User Text 10", "value_type": 10},
            {"key": "user_text_11", "name": "User Text 11", "value_type": 10},
            {"key": "user_text_12", "name": "User Text 12", "value_type": 10},
            {"key": "user_text_13", "name": "User Text 13", "value_type": 10},
            {"key": "user_text_14", "name": "User Text 14", "value_type": 10},
            {"key": "user_text_15", "name": "User Text 15", "value_type": 10},
            {"key": "user_text_16", "name": "User Text 16", "value_type": 10},
            {"key": "user_text_17", "name": "User Text 17", "value_type": 10},
            {"key": "user_text_18", "name": "User Text 18", "value_type": 10},
            {"key": "user_text_19", "name": "User Text 19", "value_type": 10},
            {"key": "user_text_20", "name": "User Text 20", "value_type": 10},
            {"key": "user_text_21", "name": "User Text 21", "value_type": 10},
            {"key": "user_text_22", "name": "User Text 22", "value_type": 10},
            {"key": "user_text_23", "name": "User Text 23", "value_type": 10},
            {"key": "user_text_24", "name": "User Text 24", "value_type": 10},
            {"key": "user_text_25", "name": "User Text 25", "value_type": 10},
            {"key": "user_text_26", "name": "User Text 26", "value_type": 10},
            {"key": "user_text_27", "name": "User Text 27", "value_type": 10},
            {"key": "user_text_28", "name": "User Text 28", "value_type": 10},
            {"key": "user_text_29", "name": "User Text 29", "value_type": 10},
            {"key": "user_text_30", "name": "User Text 30", "value_type": 10},
            {"key": "user_number_1", "name": "User Number 1", "value_type": 20},
            {"key": "user_number_2", "name": "User Number 2", "value_type": 20},
            {"key": "user_number_3", "name": "User Number 3", "value_type": 20},
            {"key": "user_number_4", "name": "User Number 4", "value_type": 20},
            {"key": "user_number_5", "name": "User Number 5", "value_type": 20},
            {"key": "user_number_6", "name": "User Number 6", "value_type": 20},
            {"key": "user_number_7", "name": "User Number 7", "value_type": 20},
            {"key": "user_number_8", "name": "User Number 8", "value_type": 20},
            {"key": "user_number_9", "name": "User Number 9", "value_type": 20},
            {"key": "user_number_10", "name": "User Number 10", "value_type": 20},
            {"key": "user_number_11", "name": "User Number 11", "value_type": 20},
            {"key": "user_number_12", "name": "User Number 12", "value_type": 20},
            {"key": "user_number_13", "name": "User Number 13", "value_type": 20},
            {"key": "user_number_14", "name": "User Number 14", "value_type": 20},
            {"key": "user_number_15", "name": "User Number 15", "value_type": 20},
            {"key": "user_number_16", "name": "User Number 16", "value_type": 20},
            {"key": "user_number_17", "name": "User Number 17", "value_type": 20},
            {"key": "user_number_18", "name": "User Number 18", "value_type": 20},
            {"key": "user_number_19", "name": "User Number 19", "value_type": 20},
            {"key": "user_number_20", "name": "User Number 20", "value_type": 20},
            {"key": "user_date_1", "name": "User Date 1", "value_type": 40},
            {"key": "user_date_2", "name": "User Date 2", "value_type": 40},
            {"key": "user_date_3", "name": "User Date 3", "value_type": 40},
            {"key": "user_date_4", "name": "User Date 4", "value_type": 40},
            {"key": "user_date_5", "name": "User Date 5", "value_type": 40},
        ]

        result = {"count": len(items), "next": None, "previous": None, "results": items}

        return Response(result)

    @action(
        detail=True,
        methods=["get", "put"],
        url_path="rebook",
        serializer_class=TransactionTypeProcessSerializer,
        permission_classes=[IsAuthenticated],
    )
    def rebook(self, request, pk=None, realm_code=None, space_code=None):
        complex_transaction = self.get_object()

        if request.method == "GET":
            instance = TransactionTypeProcess(
                transaction_type=complex_transaction.transaction_type,
                process_mode="rebook",
                complex_transaction=complex_transaction,
                clear_execution_log=False,
                record_execution_log=False,
                context=self.get_serializer_context(),
                member=request.user.member,
            )

            serializer = self.get_serializer(instance=instance)
            return Response(serializer.data)
        else:
            with transaction.atomic():
                savepoint = transaction.savepoint()

                _l.info(f'complex tt status {request.data["complex_transaction_status"]}')

                uniqueness_reaction = request.data.get("uniqueness_reaction", None)

                instance = TransactionTypeProcess(
                    transaction_type=complex_transaction.transaction_type,
                    process_mode=request.data["process_mode"],
                    complex_transaction=complex_transaction,
                    complex_transaction_status=request.data["complex_transaction_status"],
                    context=self.get_serializer_context(),
                    uniqueness_reaction=uniqueness_reaction,
                    member=request.user.member,
                )

                _l.info("==== INIT REBOOK ====")

                try:
                    if (
                        request.data["complex_transaction"]
                        and not request.data["complex_transaction"]["status"]
                    ):
                        request.data["complex_transaction"]["status"] = ComplexTransaction.PRODUCTION

                    serializer = self.get_serializer(instance=instance, data=request.data)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()

                    if instance.has_errors:
                        transaction.savepoint_rollback(savepoint)

                        errors = [
                            instance.general_errors,
                            instance.transactions_errors,
                            instance.complex_transaction_errors,
                            instance.value_errors,
                            instance.instruments_errors,
                        ]

                        return Response(errors, status=400)

                    else:
                        transaction.savepoint_commit(savepoint)

                    return Response(serializer.data)

                except Exception as e:
                    _l.error(f"rebook error {repr(e)}\n {traceback.format_exc()}")
                    raise e

    @action(
        detail=True,
        methods=["get", "put"],
        url_path="recalculate",
        serializer_class=TransactionTypeRecalculateSerializer,
        permission_classes=[IsAuthenticated],
    )
    def recalculate(self, request, pk=None, realm_code=None, space_code=None):
        complex_transaction = self.get_object()

        uniqueness_reaction = request.data.get("uniqueness_reaction", None)

        process_st = time.perf_counter()

        instance = TransactionTypeProcess(
            transaction_type=complex_transaction.transaction_type,
            process_mode=request.data["process_mode"],
            complex_transaction=complex_transaction,
            context=self.get_serializer_context(),
            uniqueness_reaction=uniqueness_reaction,
            member=request.user.member,
        )

        _l.debug(
            "rebook TransactionTypeProcess done: %s",
            "{:3.3f}".format(time.perf_counter() - process_st),
        )

        if request.data["complex_transaction"]:
            request.data["complex_transaction"]["status"] = ComplexTransaction.PRODUCTION

        serialize_st = time.perf_counter()

        serializer = self.get_serializer(instance=instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        _l.debug(
            "rebook serialize done: %s",
            "{:3.3f}".format(time.perf_counter() - serialize_st),
        )

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get", "put"],
        url_path="rebook-pending",
        serializer_class=TransactionTypeProcessSerializer,
        permission_classes=[IsAuthenticated],
    )
    def rebook_pending(self, request, pk=None, realm_code=None, space_code=None):
        with transaction.atomic():
            complex_transaction = self.get_object()

            complex_transaction.status_id = ComplexTransaction.PENDING

            instance = TransactionTypeProcess(
                transaction_type=complex_transaction.transaction_type,
                process_mode="rebook",
                complex_transaction=complex_transaction,
                context=self.get_serializer_context(),
                member=request.user.member,
            )
            if request.method == "GET":
                serializer = self.get_serializer(instance=instance)
                return Response(serializer.data)
            else:
                try:
                    serializer = self.get_serializer(instance=instance, data=request.data)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()

                    return Response(serializer.data)
                finally:
                    if instance.has_errors:
                        transaction.set_rollback(True)

    @action(
        detail=True,
        methods=["put"],
        url_path="update-properties",
        serializer_class=ComplexTransactionSimpleSerializer,
    )
    def update_properties(self, request, pk=None, realm_code=None, space_code=None):
        complex_transaction = self.get_object()

        print("detail_route: /update_properties: process update_properties")

        serializer = self.get_serializer(instance=complex_transaction, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @action(
        detail=False,
        methods=["put", "patch"],
        url_path="bulk-update-properties",
        serializer_class=ComplexTransactionSimpleSerializer,
    )
    def bulk_update_properties(self, request, realm_code=None, space_code=None):
        data = request.data
        if not isinstance(data, list):
            raise ValidationError(gettext_lazy("Required list"))

        partial = request.method.lower() == "patch"

        queryset = self.get_queryset()

        has_error = False
        serializers = []
        for adata in data:
            pk = adata["id"]
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
                    errors.append({api_settings.NON_FIELD_ERRORS_KEY: gettext_lazy("Not Found")})
            raise ValidationError(errors)
        else:
            instances = []
            for serializer in serializers:
                self.perform_update(serializer)
                instances.append(serializer.instance)

            ret_serializer = self.get_serializer(
                instance=queryset.filter(pk__in=(i.id for i in instances)), many=True
            )
            return Response(list(ret_serializer.data), status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["get"],
        url_path="view",
        serializer_class=ComplexTransactionViewOnlySerializer,
        permission_classes=[IsAuthenticated],
    )
    def view(self, request, pk=None, realm_code=None, space_code=None):
        _st = time.perf_counter()

        complex_transaction = ComplexTransaction.objects.get(id=pk)
        transaction_type = TransactionType.objects.get(id=complex_transaction.transaction_type_id)

        instance = ComplexTransactionViewOnly(complex_transaction, transaction_type=transaction_type)

        _serialize_st = time.perf_counter()
        serializer = self.get_serializer(instance=instance)
        response = Response(serializer.data)
        result_time = "{:3.3f}".format(time.perf_counter() - _serialize_st)
        _l.debug(f"ComplexTransactionViewOnly.serialize total {result_time}")

        result_time = "{:3.3f}".format(time.perf_counter() - _st)
        _l.debug(f"ComplexTransactionViewOnly.response total {result_time}")

        return response

    @action(detail=False, methods=["get", "post"], url_path="bulk-restore")
    def bulk_restore(self, request, realm_code=None, space_code=None):
        if request.method.lower() == "get":
            return self.list(request)

        ids = request.data.get("ids")
        if not ids:
            raise ValidationError("'ids' parameter is empty or missing")

        _l.info(f"bulk_restore {ids}")

        complex_transactions = ComplexTransaction.objects.filter(id__in=ids)
        for complex_transaction in complex_transactions:
            if complex_transaction.deleted_transaction_unique_code:
                used = ComplexTransaction.objects.filter(
                    transaction_unique_code=complex_transaction.deleted_transaction_unique_code
                )

                if not len(used):
                    complex_transaction.transaction_unique_code = (
                        complex_transaction.deleted_transaction_unique_code
                    )
                    complex_transaction.deleted_transaction_unique_code = None
                    complex_transaction.is_deleted = False
                    complex_transaction.save()

            else:
                complex_transaction.is_deleted = False
                complex_transaction.save()

            for trans in complex_transaction.transactions.all():
                trans.is_deleted = False
                trans.save()

        return Response({"message": "ok"})


class RecalculatePermissionTransactionViewSet(AbstractAsyncViewSet):
    serializer_class = RecalculatePermissionTransactionSerializer
    celery_task = recalculate_permissions_transaction


class RecalculatePermissionComplexTransactionViewSet(AbstractAsyncViewSet):
    serializer_class = RecalculatePermissionComplexTransactionSerializer
    celery_task = recalculate_permissions_complex_transaction
