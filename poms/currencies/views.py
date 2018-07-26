from __future__ import unicode_literals

import django_filters
from rest_framework.filters import FilterSet
from rest_framework.settings import api_settings

from poms.common.filters import CharFilter, ModelExtMultipleChoiceFilter, NoOpFilter, AttributeFilter, \
    GroupsAttributeFilter
from poms.common.pagination import CustomPaginationMixin
from poms.common.views import AbstractModelViewSet
from poms.currencies.filters import OwnerByCurrencyFilter
from poms.currencies.models import Currency, CurrencyHistory
from poms.currencies.serializers import CurrencySerializer, CurrencyHistorySerializer
from poms.instruments.models import PricingPolicy, DailyPricingModel
from poms.integrations.models import PriceDownloadScheme
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet
from poms.obj_perms.views import AbstractEvGroupWithObjectPermissionViewSet
from poms.tags.filters import TagFilter
from poms.tags.utils import get_tag_prefetch
from poms.users.filters import OwnerByMasterUserFilter
from poms.users.permissions import SuperUserOrReadOnly


class CurrencyAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Currency


class CurrencyFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    reference_for_pricing = CharFilter()
    daily_pricing_model = django_filters.ModelMultipleChoiceFilter(queryset=DailyPricingModel.objects)
    price_download_scheme = ModelExtMultipleChoiceFilter(model=PriceDownloadScheme, field_name='scheme_name')
    tag = TagFilter(model=Currency)

    class Meta:
        model = Currency
        fields = []


class CurrencyViewSet(AbstractModelViewSet):
    queryset = Currency.objects.select_related(
        'master_user',
        'daily_pricing_model',
        'price_download_scheme',
        'price_download_scheme__provider',
    ).prefetch_related(
        get_attributes_prefetch(),
        get_tag_prefetch()
    )
    serializer_class = CurrencySerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        # SuperUserOrReadOnly,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = CurrencyFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name', 'reference_for_pricing',
        'price_download_scheme', 'price_download_scheme__scheme_name',
    ]

class CurrencyEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Currency.objects.select_related(
        'master_user',
        'daily_pricing_model',
        'price_download_scheme',
        'price_download_scheme__provider',
    ).prefetch_related(
        get_attributes_prefetch(),
        get_tag_prefetch()
    )
    serializer_class = CurrencySerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = CurrencyFilterSet

    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
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
        GroupsAttributeFilter,
    ]
    filter_class = CurrencyHistoryFilterSet
    ordering_fields = [
        'date', 'fx_rate',
        'currency', 'currency__user_code', 'currency__name', 'currency__short_name', 'currency__public_name',
        'pricing_policy', 'pricing_policy__user_code', 'pricing_policy__name', 'pricing_policy__short_name',
        'pricing_policy__public_name',
    ]

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
