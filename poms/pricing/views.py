from logging import getLogger

from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings

from poms.celery_tasks.models import CeleryTask
from poms.common.filters import GroupsAttributeFilter, NoOpFilter
from poms.common.pagination import CustomPaginationMixin
from poms.common.renderers import FinmarsJSONRenderer
from poms.common.views import (
    AbstractEvGroupViewSet,
    AbstractModelViewSet,
    AbstractViewSet,
)
from poms.pricing.models import CurrencyHistoryError, PriceHistoryError
from poms.pricing.serializers import (
    CurrencyHistoryErrorSerializer,
    PriceHistoryErrorSerializer,
    RunPricingSerializer,
)
from poms.pricing.tasks import run_pricing
from poms.users.filters import OwnerByMasterUserFilter

_l = getLogger("poms.pricing")


class RunPricingView(AbstractViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RunPricingSerializer
    renderer_classes = [FinmarsJSONRenderer]

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = CeleryTask(
            master_user=request.user.master_user,
            member=request.user.member,
            status=CeleryTask.STATUS_INIT,
            type="run_pricing",
        )
        task.options_object = serializer.validated_data
        task.save()

        run_pricing.apply_async(
            kwargs={
                "task_id": task.id,
                "context": {
                    "space_code": task.master_user.space_code,
                    "realm_code": task.master_user.realm_code,
                },
            }
        )
        return Response({"status": "ok", "task_id": task.id}, status=status.HTTP_201_CREATED)


class PriceHistoryErrorFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = PriceHistoryError
        fields = []


class PriceHistoryErrorViewSet(AbstractModelViewSet):
    queryset = PriceHistoryError.objects.select_related(
        "master_user",
        "instrument",
        "pricing_policy",
    )
    serializer_class = PriceHistoryErrorSerializer
    renderer_classes = [FinmarsJSONRenderer]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = PriceHistoryErrorFilterSet
    ordering_fields = ["date"]


class PriceHistoryErrorEvViewSet(AbstractModelViewSet):
    queryset = PriceHistoryError.objects.select_related(
        "master_user",
        "instrument",
        "pricing_policy",
    )
    serializer_class = PriceHistoryErrorSerializer
    renderer_classes = [FinmarsJSONRenderer]
    filter_backends = AbstractModelViewSet.filter_backends + [OwnerByMasterUserFilter, GroupsAttributeFilter]
    filter_class = PriceHistoryErrorFilterSet
    ordering_fields = ["date"]


class PriceHistoryErrorEvGroupViewSet(AbstractEvGroupViewSet, CustomPaginationMixin):
    queryset = PriceHistoryError.objects.select_related(
        "master_user",
        "instrument",
        "pricing_policy",
    )
    serializer_class = PriceHistoryErrorSerializer
    renderer_classes = [FinmarsJSONRenderer]
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = PriceHistoryErrorFilterSet

    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]


class CurrencyHistoryErrorFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = CurrencyHistoryError
        fields = []


class CurrencyHistoryErrorViewSet(AbstractModelViewSet):
    queryset = CurrencyHistoryError.objects.select_related(
        "master_user",
        "currency",
        "pricing_policy",
    )
    serializer_class = CurrencyHistoryErrorSerializer
    renderer_classes = [FinmarsJSONRenderer]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = CurrencyHistoryErrorFilterSet
    ordering_fields = ["date"]


class CurrencyHistoryErrorEvViewSet(AbstractModelViewSet):
    queryset = CurrencyHistoryError.objects.select_related(
        "master_user",
        "currency",
        "pricing_policy",
    )
    serializer_class = CurrencyHistoryErrorSerializer
    renderer_classes = [FinmarsJSONRenderer]
    filter_backends = AbstractModelViewSet.filter_backends + [OwnerByMasterUserFilter, GroupsAttributeFilter]
    filter_class = CurrencyHistoryErrorFilterSet
    ordering_fields = ["date"]


class CurrencyHistoryErrorEvGroupViewSet(AbstractEvGroupViewSet, CustomPaginationMixin):
    queryset = CurrencyHistoryError.objects.select_related(
        "master_user",
        "currency",
        "pricing_policy",
    )

    serializer_class = CurrencyHistoryErrorSerializer
    renderer_classes = [FinmarsJSONRenderer]
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = CurrencyHistoryErrorFilterSet

    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
