import logging

import django_filters
from django_filters.rest_framework import FilterSet

# from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from poms.common.database_client import DatabaseService
from poms.common.filters import (
    AttributeFilter,
    CharFilter,
    EntitySpecificFilter,
    GroupsAttributeFilter,
    ModelExtMultipleChoiceFilter,
    NoOpFilter,
)
from poms.common.monad import Monad, MonadStatus
from poms.common.views import AbstractModelViewSet
from poms.currencies.filters import OwnerByCurrencyFilter
from poms.currencies.models import Currency, CurrencyHistory
from poms.currencies.serializers import (
    CurrencyHistorySerializer,
    CurrencyLightSerializer,
    CurrencySerializer,
    CurrencyDatabaseSearchRequestSerializer,
    CurrencyDatabaseSearchResponseSerializer,
)
from poms.instruments.models import PricingPolicy
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet
from poms.users.filters import OwnerByMasterUserFilter

_l = logging.getLogger("poms.currencies")


class CurrencyAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Currency
    target_model_serializer = CurrencySerializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + []


class CurrencyFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    reference_for_pricing = CharFilter()

    class Meta:
        model = Currency
        fields = []


class CurrencyViewSet(AbstractModelViewSet):
    queryset = Currency.objects.select_related(
        "master_user",
    ).prefetch_related(get_attributes_prefetch())
    serializer_class = CurrencySerializer
    # permission_classes = AbstractModelViewSet.permission_classes + [
    #     # SuperUserOrReadOnly,
    # ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter,
    ]
    filter_class = CurrencyFilterSet
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
        "reference_for_pricing",
        "price_download_scheme",
        "price_download_scheme__scheme_name",
    ]

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=CurrencyLightSerializer,
    )
    def list_light(self, request, *args, **kwargs):
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
            {
                "key": "reference_for_pricing",
                "name": "Reference for pricing",
                "value_type": 10,
            },
            {
                "key": "default_fx_rate",
                "name": "Default FX rate",
                "value_type": 20,
            },
            {
                "key": "pricing_condition",
                "name": "Pricing Condition",
                "value_content_type": "instruments.pricingcondition",
                "code": "user_code",
                "value_type": "field",
            },
        ]

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items,
        }

        return Response(result)


class CurrencyHistoryFilterSet(FilterSet):
    id = NoOpFilter()
    date = django_filters.DateFromToRangeFilter()
    currency = ModelExtMultipleChoiceFilter(model=Currency)
    # pricing_policy = ModelExtMultipleChoiceFilter(model=PricingPolicy)
    pricing_policy = CharFilter(field_name="pricing_policy__user_code", lookup_expr="icontains")
    fx_rate = django_filters.RangeFilter()

    class Meta:
        model = CurrencyHistory
        fields = []


class CurrencyHistoryViewSet(AbstractModelViewSet):
    queryset = CurrencyHistory.objects.select_related(
        "currency", "pricing_policy"
    ).prefetch_related()
    serializer_class = CurrencyHistorySerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        # SuperUserOrReadOnly,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByCurrencyFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = CurrencyHistoryFilterSet
    ordering_fields = [
        "date",
        "fx_rate",
        "currency",
        "currency__user_code",
        "currency__name",
        "currency__short_name",
        "currency__public_name",
        "pricing_policy",
        "pricing_policy__user_code",
        "pricing_policy__name",
        "pricing_policy__short_name",
        "pricing_policy__public_name",
    ]

    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request, *args, **kwargs):

        valid_data = []
        errors = []

        for item in request.data:
            serializer = self.get_serializer(data=item)
            if serializer.is_valid():
                valid_data.append(CurrencyHistory(**serializer.validated_data))
            else:
                errors.append(serializer.errors)

        _l.info('CurrencyHistoryViewSet.valid_data %s' % len(valid_data))

        CurrencyHistory.objects.bulk_create(valid_data, ignore_conflicts=True)

        if errors:
            _l.info('CurrencyHistoryViewSet.bulk_create.errors %s' % errors)
        #     # Here we just return the errors as part of the response.
        #     # You may want to log them or handle them differently depending on your needs.
        #     return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


    @action(detail=False, methods=["get"], url_path="attributes")
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {
                "key": "currency",
                "name": "Currency",
                "value_type": "field",
                "value_entity": "currency",
                "value_content_type": "",
                "code": "currencies.currency",
            },
            {
                "key": "date",
                "name": "Date",
                "value_type": 40,
            },
            {
                "key": "fx_rate",
                "name": "Fx rate",
                "value_type": 20,
            },
            {
                "key": "pricing_policy",
                "name": "Pricing policy",
                "value_type": "field",
                "value_entity": "pricing_policy",
                "value_content_type": "instruments.pricingpolicy",
                "code": "user_code",
            },
            {
                "key": "procedure_modified_datetime",
                "name": "Modified Date And Time",
                "value_type": 40,
            },
        ]

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items,
        }

        return Response(result)


class CurrencyDatabaseSearchViewSet(APIView):
    """
    Provides Currency info from Finmars-Database API based on CBOND's data
    """

    permission_classes = []

    # @swagger_auto_schema(
    #     tags=["Currencies"],
    #     operation_description="Provides Currency info based on CBOND's data",
    #     request_body=CurrencyDatabaseSearchRequestSerializer,
    #     responses={200: CurrencyDatabaseSearchResponseSerializer()},
    # )

    def _empty_response(self) -> Response:
        return Response(
            {
                "results": [],
                "next": None,
                "previous": None,
                "count": 0,
            }
        )

    def get(self, request):
        log = f"{self.__class__.__name__}"

        serializer = CurrencyDatabaseSearchRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = dict(serializer.validated_data)

        _l.info(f"{log} request params={params}")

        if not serializer.params_has_name(params):
            return self._empty_response()

        monad: Monad = DatabaseService().get_results("currency", params)

        _l.info(f"{log} monad.status={monad.status} monad.data={monad.data}")

        if monad.status != MonadStatus.DATA_READY:
            _l.error(f"{log} error, monad.message={monad.message}")
            return self._empty_response()

        return Response(CurrencyDatabaseSearchResponseSerializer(monad.data).data)
