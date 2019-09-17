from django_filters.rest_framework import FilterSet, DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.viewsets import  ModelViewSet

from poms.common.views import AbstractApiView
from .models import CeleryTask
from .serializers import CeleryTaskSerializer
from poms.common.filters import CharFilter
from poms.users.filters import OwnerByMasterUserFilter


class CeleryTaskFilterSet(FilterSet):

    task_id = CharFilter()
    task_status = CharFilter()
    task_type = CharFilter()

    class Meta:
        model = CeleryTask
        fields = []


class CeleryTaskViewSet(AbstractApiView, ModelViewSet):
    queryset = CeleryTask.objects.select_related(
        'master_user'
    )
    serializer_class = CeleryTaskSerializer
    filter_class = CeleryTaskFilterSet
    filter_backends = [
        DjangoFilterBackend,
        OwnerByMasterUserFilter,
    ]
