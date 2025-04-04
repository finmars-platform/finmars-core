from logging import getLogger

from django_filters import FilterSet

from poms.common.filters import CharFilter
from poms.common.renderers import FinmarsJSONRenderer
from poms.common.views import AbstractModelViewSet
from poms.credentials.models import Credentials
from poms.credentials.serializers import CredentialsSerializer
from poms.users.filters import OwnerByMasterUserFilter

_l = getLogger("poms.credentials")


class CredentialsFilterSet(FilterSet):
    user_code = CharFilter()
    name = CharFilter()

    class Meta:
        model = Credentials
        fields = []


class CredentialsViewSet(AbstractModelViewSet):
    queryset = Credentials.objects
    serializer_class = CredentialsSerializer
    renderer_classes = [FinmarsJSONRenderer]
    filter_class = CredentialsFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    permission_classes = []
