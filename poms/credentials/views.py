from django_filters import FilterSet

from poms.common.filters import CharFilter
from poms.common.views import AbstractModelViewSet
from poms.credentials.models import Credentials
from poms.credentials.serializers import CredentialsSerializer


from poms.users.filters import OwnerByMasterUserFilter


from logging import getLogger

_l = getLogger('poms.credentials')


class CredentialsFilterSet(FilterSet):
    user_code = CharFilter()
    name = CharFilter()

    class Meta:
        model = Credentials
        fields = []


class CredentialsViewSet(AbstractModelViewSet):
    queryset = Credentials.objects
    serializer_class = CredentialsSerializer
    filter_class = CredentialsFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]

    permission_classes = []




