from __future__ import unicode_literals

import logging

import django_filters
import requests
from django_filters.rest_framework import FilterSet
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from rest_framework.decorators import action

from poms.common.filters import CharFilter, ModelExtMultipleChoiceFilter, NoOpFilter, AttributeFilter, \
    GroupsAttributeFilter, EntitySpecificFilter
from poms.common.jwt import encode_with_jwt
from poms.common.pagination import CustomPaginationMixin
from poms.common.views import AbstractModelViewSet
from poms.currencies.filters import OwnerByCurrencyFilter
from poms.currencies.models import Currency, CurrencyHistory
from poms.currencies.serializers import CurrencySerializer, CurrencyHistorySerializer, CurrencyLightSerializer, \
    CurrencyEvSerializer
from poms.instruments.models import PricingPolicy
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet
from poms.obj_perms.permissions import PomsConfigurationPermission
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractEvGroupWithObjectPermissionViewSet, AbstractWithObjectPermissionViewSet
from poms.users.filters import OwnerByMasterUserFilter

_l = logging.getLogger('poms.currencies')

from poms_app import settings


class CurrencyAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Currency
    target_model_serializer = CurrencySerializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


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


class CurrencyViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Currency.objects.select_related(
        'master_user',
    ).prefetch_related(
        get_attributes_prefetch()
    )
    serializer_class = CurrencySerializer
    # permission_classes = AbstractModelViewSet.permission_classes + [
    #     # SuperUserOrReadOnly,
    # ]
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    filter_class = CurrencyFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name', 'reference_for_pricing',
        'price_download_scheme', 'price_download_scheme__scheme_name',
    ]

    @action(detail=False, methods=['get'], url_path='light', serializer_class=CurrencyLightSerializer)
    def list_light(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        result = self.get_paginated_response(serializer.data)

        return result

    @action(detail=False, methods=['get'], url_path='attributes')
    def list_attributes(self, request, *args, **kwargs):

        items = [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10
            },
            {
                "key": "reference_for_pricing",
                "name": "Reference for pricing",
                "value_type": 10
            },
            {
                "key": "default_fx_rate",
                "name": "Default FX rate",
                "value_type": 20
            },
            {
                "key": "pricing_condition",
                "name": "Pricing Condition",
                "value_content_type": "instruments.pricingcondition",
                "value_entity": "pricing-condition",
                "code": "user_code",
                "value_type": "field"
            }
        ]

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items
        }

        return Response(result)



class CurrencyEvFilterSet(FilterSet):
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


class CurrencyEvViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Currency.objects.select_related(
        'master_user',
    ).prefetch_related(
        'attributes',
        'attributes__classifier',
        # get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Currency),
        )
    )
    serializer_class = CurrencyEvSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter
    ]
    filter_class = CurrencyEvFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name'
    ]


class CurrencyLightFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()

    class Meta:
        model = Currency
        fields = []

# DEPRECATED
class CurrencyLightViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Currency.objects.select_related(
        'master_user',
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Currency),
        )
    )
    serializer_class = CurrencyLightSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        EntitySpecificFilter
    ]
    filter_class = CurrencyLightFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name'
    ]


class CurrencyEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Currency.objects.select_related(
        'master_user',
    ).prefetch_related(
        get_attributes_prefetch()
    )
    serializer_class = CurrencySerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = CurrencyFilterSet

    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        EntitySpecificFilter
    ]


class CurrencyHistoryFilterSet(FilterSet):
    id = NoOpFilter()
    date = django_filters.DateFromToRangeFilter()
    currency = ModelExtMultipleChoiceFilter(model=Currency)
    pricing_policy = ModelExtMultipleChoiceFilter(model=PricingPolicy)
    fx_rate = django_filters.RangeFilter()

    class Meta:
        model = CurrencyHistory
        fields = []


class CurrencyHistoryViewSet(AbstractModelViewSet):
    queryset = CurrencyHistory.objects.select_related(
        'currency',
        'pricing_policy'
    ).prefetch_related(

    )
    serializer_class = CurrencyHistorySerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        # SuperUserOrReadOnly,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByCurrencyFilter,
        AttributeFilter,
        GroupsAttributeFilter
    ]
    filter_class = CurrencyHistoryFilterSet
    ordering_fields = [
        'date', 'fx_rate',
        'currency', 'currency__user_code', 'currency__name', 'currency__short_name', 'currency__public_name',
        'pricing_policy', 'pricing_policy__user_code', 'pricing_policy__name', 'pricing_policy__short_name',
        'pricing_policy__public_name',
    ]

    @action(detail=False, methods=['get'], url_path='attributes')
    def list_attributes(self, request, *args, **kwargs):

        items = [
            {
                "key": "currency",
                "name": "Currency",
                "value_type": "field",
                "value_entity": "currency",
                "value_content_type": "",
                "code": "currencies.currency"
            },
            {
                "key": "date",
                "name": "Date",
                "value_type": 40
            },
            {
                "key": "fx_rate",
                "name": "Fx rate",
                "value_type": 20
            },
            {
                "key": "pricing_policy",
                "name": "Pricing policy",
                "value_type": "field",
                "value_entity": "pricing_policy",
                "value_content_type": "instruments.pricingpolicy",
                "code": "user_code"
            },

            {
                "key": "procedure_modified_datetime",
                "name": "Modified Date And Time",
                "value_type": 40
            }
        ]

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items
        }

        return Response(result)


class CurrencyHistoryEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = CurrencyHistory.objects.select_related(
        'currency',
        'pricing_policy'
    ).prefetch_related(

    )
    serializer_class = CurrencyHistorySerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = CurrencyHistoryFilterSet

    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByCurrencyFilter,
        AttributeFilter
    ]


class CurrencyDatabaseSearchViewSet(APIView):
    permission_classes = []

    def get(self, request):

        headers = {'Content-type': 'application/json'}

        payload_jwt = {
            "sub": settings.BASE_API_URL,  # "user_id_or_name",
            "role": 0  # 0 -- ordinary user, 1 -- admin (access to /loadfi and /loadeq)
        }

        token = encode_with_jwt(payload_jwt)

        name = request.query_params.get('name', '')
        page = request.query_params.get('page', 1)

        headers['Authorization'] = 'Bearer %s' % token

        result = {}

        _l.info('headers %s' % headers)

        url = str(settings.CBONDS_BROKER_URL) + 'instr/find/currency/%s?page=%s' % (name, page)

        _l.info("Requesting URL %s" % url)

        response = None

        try:
            response = requests.get(url=url, headers=headers, verify=settings.VERIFY_SSL)
        except Exception as e:
            _l.info("Request error %s" % e)
            result = {}

        # _l.info("response.text %s" % response.text)

        try:
            result = response.json()
        except Exception as e:
            if response:
                _l.info('response %s' % response.text)
                _l.info("Response parse error %s" % e)
            result = {}

        return Response(result)
