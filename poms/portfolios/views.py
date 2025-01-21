from logging import getLogger

import django_filters
from django.conf import settings
from django_filters.rest_framework import FilterSet
from django_filters.filters import BaseInFilter
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from poms.celery_tasks.models import CeleryTask
from poms.common.filters import (
    AttributeFilter,
    CharFilter,
    EntitySpecificFilter,
    GroupsAttributeFilter,
    ModelExtUserCodeMultipleChoiceFilter,
    NoOpFilter,
)
from poms.common.utils import get_list_of_entity_attributes
from poms.common.views import AbstractClassModelViewSet, AbstractModelViewSet
from poms.currencies.models import Currency
from poms.instruments.models import PricingPolicy
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet, GenericClassifierViewSet
from poms.portfolios.models import (
    Portfolio,
    PortfolioBundle,
    PortfolioClass,
    PortfolioHistory,
    PortfolioReconcileGroup,
    PortfolioReconcileHistory,
    PortfolioRegister,
    PortfolioRegisterRecord,
    PortfolioType,
)
from poms.portfolios.serializers import (
    CalculatePortfolioHistorySerializer,
    CalculatePortfolioReconcileHistorySerializer,
    FirstTransactionDateRequestSerializer,
    FirstTransactionDateResponseSerializer,
    PortfolioBundleSerializer,
    PortfolioClassSerializer,
    PortfolioHistorySerializer,
    PortfolioLightSerializer,
    PortfolioReconcileGroupSerializer,
    PortfolioReconcileHistorySerializer,
    PortfolioRegisterRecordSerializer,
    PortfolioRegisterSerializer,
    PortfolioSerializer,
    PortfolioTypeLightSerializer,
    PortfolioTypeSerializer,
    PrCalculatePriceHistoryRequestSerializer,
    PrCalculateRecordsRequestSerializer,
)
from poms.portfolios.tasks import (
    calculate_portfolio_history,
    calculate_portfolio_reconcile_history,
    calculate_portfolio_register_price_history,
    calculate_portfolio_register_record,
)
from poms.users.filters import OwnerByMasterUserFilter

_l = getLogger("poms.portfolios")


class PortfolioClassViewSet(AbstractClassModelViewSet):
    queryset = PortfolioClass.objects
    serializer_class = PortfolioClassSerializer


class PortfolioTypeFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    show_transaction_details = django_filters.BooleanFilter()

    class Meta:
        model = PortfolioType
        fields = []


class PortfolioTypeViewSet(AbstractModelViewSet):
    queryset = PortfolioType.objects.select_related("master_user").prefetch_related(
        get_attributes_prefetch(),
    )
    serializer_class = PortfolioTypeSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter,
    ]
    filter_class = PortfolioTypeFilterSet
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
    ]

    @action(detail=False, methods=["get"], url_path="attributes")
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10,
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10,
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10,
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10,
            },
            {
                "key": "show_transaction_details",
                "name": "Show transaction details",
                "value_type": 50,
            },
            {
                "key": "transaction_details_expr",
                "name": "Transaction details expr",
                "value_type": 10,
            },
        ]

        items += get_list_of_entity_attributes("accounts.accounttype")

        result = {"count": len(items), "next": None, "previous": None, "results": items}

        return Response(result)

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=PortfolioTypeLightSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)


class PortfolioTypeAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = PortfolioType
    target_model_serializer = PortfolioTypeSerializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + []


class PortfolioAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Portfolio
    target_model_serializer = PortfolioSerializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + []


class PortfolioClassifierViewSet(GenericClassifierViewSet):
    target_model = Portfolio


class PortfolioFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    attribute_types = GroupsAttributeFilter()
    attribute_values = GroupsAttributeFilter()
    client = CharFilter(
        field_name="client__user_code", lookup_expr="icontains"
    )

    class Meta:
        model = Portfolio
        fields = []


class PortfolioViewSet(AbstractModelViewSet):
    queryset = Portfolio.objects.select_related(
        "master_user", "owner"
    ).prefetch_related(
        get_attributes_prefetch(),
    )
    serializer_class = PortfolioSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter,
    ]
    filter_class = PortfolioFilterSet
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
    ]

    def create(self, request, *args, **kwargs):
        # Probably pointless on portfolio create
        # Because you cannot book transaction without portfolio
        # calculate_portfolio_register_record.apply_async(
        #     link=[
        #         calculate_portfolio_register_price_history.s()
        #     ])

        _l.info(f"{self.__class__.__name__}.create data={request.data}")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def update(self, request, *args, **kwargs):
        # trigger recalc after book properly
        # calculate_portfolio_register_record.apply_async(
        #     link=[
        #         calculate_portfolio_register_price_history.s()
        #     ])

        _l.info(f"{self.__class__.__name__}.update data={request.data}")

        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=PortfolioLightSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], url_path="attributes")
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10,
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10,
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10,
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
            },
            {"key": "notes", "name": "Notes", "value_type": 10},
            {
                "key": "accounts",
                "name": "Accounts",
                "value_content_type": "accounts.account",
                "value_entity": "account",
                "code": "user_code",
                "value_type": "mc_field",
            },
            {
                "key": "responsibles",
                "name": "Responsibles",
                "value_content_type": "counterparties.responsible",
                "value_entity": "responsible",
                "code": "user_code",
                "value_type": "mc_field",
            },
            {
                "key": "counterparties",
                "name": "Counterparties",
                "value_content_type": "counterparties.counterparty",
                "value_entity": "counterparty",
                "code": "user_code",
                "value_type": "mc_field",
            },
            {
                "key": "transaction_types",
                "name": "Transaction types",
                "value_content_type": "transactions.transactiontype",
                "value_entity": "transaction-type",
                "code": "user_code",
                "value_type": "mc_field",
            },
        ]

        items += get_list_of_entity_attributes("portfolios.portfolio")

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items,
        }

        return Response(result)

    @action(
        detail=True,
        methods=["get"],
        url_path="get-inception-date",
    )
    def get_inception_date(self, request, *args, **kwargs):
        result = {"date": None}

        portfolio = self.get_object()

        first_record = (
            PortfolioRegisterRecord.objects.filter(portfolio=portfolio)
            .order_by("transaction_date")
            .first()
        )

        if first_record:
            result["date"] = first_record.transaction_date

        return Response(result)

    @action(
        detail=False,
        methods=["get"],
        url_path="get-inception-date",
    )
    def get_inception_date(self, request, *args, **kwargs):
        user_code = request.query_params.get("user_code", None)

        if not user_code:
            raise Exception("user_code is required")

        result = {"date": None}

        portfolio = Portfolio.objects.get(user_code=user_code)

        first_record = (
            PortfolioRegisterRecord.objects.filter(portfolio=portfolio)
            .order_by("transaction_date")
            .first()
        )

        if first_record:
            result["date"] = first_record.transaction_date

        return Response(result)


class PortfolioRegisterAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = PortfolioRegister
    target_model_serializer = PortfolioRegisterSerializer
    permission_classes = GenericAttributeTypeViewSet.permission_classes + []


class PortfolioRegisterFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()

    class Meta:
        model = PortfolioRegister
        fields = []


class PortfolioRegisterViewSet(AbstractModelViewSet):
    queryset = PortfolioRegister.objects.select_related(
        "master_user",
    ).prefetch_related(
        get_attributes_prefetch(),
    )
    serializer_class = PortfolioRegisterSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter,
    ]
    filter_class = PortfolioRegisterFilterSet
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
    ]

    @action(
        detail=False,
        methods=["post"],
        url_path="calculate-records",
        serializer_class=PrCalculateRecordsRequestSerializer,
    )
    def calculate_records(self, request, realm_code=None, space_code=None):
        _l.info(f"{self.__class__.__name__}.calculate_records data={request.data}")

        serializer = PrCalculateRecordsRequestSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)

        task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            verbose_name="Calculate Portfolio Register Records",
            type="calculate_portfolio_register_record",
            status=CeleryTask.STATUS_PENDING,
        )
        task.options_object = serializer.validated_data
        task.save()

        calculate_portfolio_register_record.apply_async(
            kwargs={
                "task_id": task.id,
                "context": {
                    "space_code": task.master_user.space_code,
                    "realm_code": task.master_user.realm_code,
                },
            },
        )

        return Response(
            {
                "task_id": task.id,
                "task_status": task.status,
                "task_type": task.type,
                "task_options": task.options_object,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="calculate-price-history",
        serializer_class=PrCalculatePriceHistoryRequestSerializer,
    )
    def calculate_price_history(self, request, realm_code=None, space_code=None):
        _l.info(
            f"{self.__class__.__name__}.calculate_price_history data={request.data}"
        )
        serializer = PrCalculatePriceHistoryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            verbose_name="Calculate Portfolio Register Prices",
            type="calculate_portfolio_register_price_history",
            status=CeleryTask.STATUS_PENDING,
        )
        task.options_object = {
            "portfolios": serializer.validated_data.get("portfolios"),
            "date_to": serializer.validated_data["date_to"].strftime(
                settings.API_DATE_FORMAT
            ),
            "date_from": serializer.validated_data["date_from"].strftime(
                settings.API_DATE_FORMAT
            )
            if serializer.validated_data.get("date_from")
            else None,
        }
        task.save()

        calculate_portfolio_register_price_history.apply_async(
            kwargs={
                "task_id": task.id,
                "context": {
                    "space_code": task.master_user.space_code,
                    "realm_code": task.master_user.realm_code,
                },
            },
        )

        return Response(
            {
                "task_id": task.id,
                "task_status": task.status,
                "task_type": task.type,
                "task_options": task.options_object,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        from poms.instruments.models import Instrument

        instance = self.get_object()

        keep_instrument = request.data.get("keep_instrument")

        linked_instrument_id = instance.linked_instrument_id

        _l.info(
            f"{self.__class__.__name__}.destroy portfolio_register={instance.user_code}"
            f"linked_instrument_id {linked_instrument_id} "
            f"keep_instrument {keep_instrument}"
        )

        self.perform_destroy(instance)

        if keep_instrument != "true" and linked_instrument_id:
            _l.info(f"{self.__class__.__name__} initiating fake delete for instrument")

            instrument = Instrument.objects.get(id=linked_instrument_id)
            instrument.fake_delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class PortfolioRegisterRecordFilterSet(FilterSet):
    id = NoOpFilter()
    portfolio__user_code = ModelExtUserCodeMultipleChoiceFilter(model=Portfolio)    

    class Meta:
        model = PortfolioRegisterRecord
        fields = []


class PortfolioRegisterRecordViewSet(AbstractModelViewSet):
    queryset = PortfolioRegisterRecord.objects.select_related(
        "master_user",
        "portfolio",
        "instrument",
        "transaction_class",
        "cash_currency",
        "valuation_currency",
        "previous_date_record",
        "transaction",
        "portfolio_register",
    )
    serializer_class = PortfolioRegisterRecordSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = PortfolioRegisterRecordFilterSet
    ordering_fields = []


class PortfolioBundleFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = PortfolioBundle
        fields = []


class PortfolioBundleViewSet(AbstractModelViewSet):
    queryset = PortfolioBundle.objects.select_related("master_user")
    serializer_class = PortfolioBundleSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [OwnerByMasterUserFilter]
    filter_class = PortfolioBundleFilterSet
    ordering_fields = []

    @action(detail=True, methods=["get"], url_path="portfolio-registers")
    def get_portfolio_registers(self, request, pk, realm_code=None, space_code=None):
        obj = self.get_object()
        queryset = obj.registers.all()
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = PortfolioRegisterSerializer(
            page, many=True, context=self.get_serializer_context()
        )
        return self.get_paginated_response(serializer.data)


class PortfolioFirstTransactionViewSet(AbstractModelViewSet):
    queryset = Portfolio.objects
    serializer_class = FirstTransactionDateRequestSerializer
    http_method_names = ["get"]
    response_serializer_class = FirstTransactionDateResponseSerializer

    def list(self, request, *args, **kwargs):
        request_serializer = self.serializer_class(
            data=request.query_params,
            context={"request": request, "member": request.user.member},
        )
        request_serializer.is_valid(raise_exception=True)

        portfolios: list = request_serializer.validated_data["portfolio"]
        date_field: str = request_serializer.validated_data["date_field"]
        response_data = []
        for portfolio in portfolios:
            first_date = portfolio.first_transaction_date
            response_data.append(
                {
                    "portfolio": portfolio,
                    "first_transaction": {
                        "date_field": date_field,
                        "date": first_date,
                    },
                }
            )

        response_serializer = self.response_serializer_class(response_data, many=True)
        return Response(response_serializer.data)

    def retrieve(self, request, *args, **kwargs):
        raise MethodNotAllowed("retrieve", "not allowed", "405")


class PortfolioHistoryFilterSet(FilterSet):
    id = NoOpFilter()

    user_code = CharFilter()
    status = CharFilter()

    period_type = CharFilter()

    portfolio__user_code = ModelExtUserCodeMultipleChoiceFilter(model=Portfolio)
    currency__user_code = ModelExtUserCodeMultipleChoiceFilter(model=Currency)
    pricing_policy__user_code = ModelExtUserCodeMultipleChoiceFilter(
        model=PricingPolicy
    )

    date = django_filters.DateFromToRangeFilter()

    class Meta:
        model = PortfolioHistory
        fields = []


class PortfolioHistoryViewSet(AbstractModelViewSet):
    queryset = PortfolioHistory.objects.select_related(
        "master_user", "portfolio", "currency", "cost_method", "pricing_policy"
    )
    serializer_class = PortfolioHistorySerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = PortfolioHistoryFilterSet
    ordering_fields = []

    @action(
        detail=False,
        methods=["post"],
        url_path="calculate",
        serializer_class=CalculatePortfolioHistorySerializer,
    )
    def calculate(self, request, realm_code=None, space_code=None):
        _l.info(f"{self.__class__.__name__}.calculate data={request.data}")
        serializer = CalculatePortfolioHistorySerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)

        task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            verbose_name="Calculate Portfolio History",
            type="calculate_portfolio_history",
            status=CeleryTask.STATUS_PENDING,
        )
        task.options_object = serializer.validated_data
        task.save()

        calculate_portfolio_history.apply_async(
            kwargs={
                "task_id": task.id,
                "context": {
                    "space_code": task.master_user.space_code,
                    "realm_code": task.master_user.realm_code,
                },
            },
        )

        return Response(
            {
                "task_id": task.id,
                "task_status": task.status,
                "task_type": task.type,
                "task_options": task.options_object,
            },
            status=status.HTTP_200_OK,
        )


class PortfolioReconcileGroupFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = PortfolioReconcileGroup
        fields = []


class PortfolioReconcileGroupViewSet(AbstractModelViewSet):
    queryset = PortfolioReconcileGroup.objects.select_related("master_user")
    serializer_class = PortfolioReconcileGroupSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [OwnerByMasterUserFilter]
    filter_class = PortfolioReconcileGroupFilterSet
    ordering_fields = []


class PortfolioReconcileHistoryFilterSet(FilterSet):
    id = NoOpFilter()

    user_code = CharFilter()
    status = CharFilter()

    portfolio_reconcile_group__user_code = ModelExtUserCodeMultipleChoiceFilter(
        model=PortfolioReconcileGroup
    )

    date = django_filters.DateFromToRangeFilter()

    class Meta:
        model = PortfolioReconcileHistory
        fields = []


class PortfolioReconcileHistoryViewSet(AbstractModelViewSet):
    queryset = PortfolioReconcileHistory.objects.select_related(
        "master_user",
        "portfolio_reconcile_group",
    )
    serializer_class = PortfolioReconcileHistorySerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = PortfolioReconcileHistoryFilterSet
    ordering_fields = []

    # TODO Refactor
    @action(
        detail=False,
        methods=["post"],
        url_path="calculate",
        serializer_class=CalculatePortfolioReconcileHistorySerializer,
    )
    def calculate(self, request, realm_code=None, space_code=None):
        _l.info(f"{self.__class__.__name__}.calculate data={request.data}")
        serializer = CalculatePortfolioReconcileHistorySerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)

        task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            verbose_name="Calculate Portfolio Reconcile History",
            type="calculate_portfolio_reconcile_history",
            status=CeleryTask.STATUS_PENDING,
        )
        task.options_object = serializer.validated_data
        task.save()

        calculate_portfolio_reconcile_history.apply_async(
            kwargs={
                "task_id": task.id,
                "context": {
                    "space_code": task.master_user.space_code,
                    "realm_code": task.master_user.realm_code,
                },
            },
        )

        return Response(
            {
                "task_id": task.id,
                "task_status": task.status,
                "task_type": task.type,
                "task_options": task.options_object,
            },
            status=status.HTTP_200_OK,
        )
