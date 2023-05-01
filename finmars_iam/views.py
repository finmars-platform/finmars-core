from rest_framework.viewsets import ModelViewSet

from finmars_iam.filters import ObjectPermissionBackend
from finmars_iam.mixins import AccessViewSetMixin
from finmars_iam.permissions import FinmarsAccessPolicy


class AbstractFinmarsAccessPolicyViewSet(AccessViewSetMixin, ModelViewSet):
    access_policy = FinmarsAccessPolicy

    filter_backends = ModelViewSet.filter_backends + [
        ObjectPermissionBackend,
    ]
