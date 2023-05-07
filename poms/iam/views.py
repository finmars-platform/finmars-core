from rest_framework.viewsets import ModelViewSet

from poms.iam.filters import ObjectPermissionBackend
from poms.iam.mixins import AccessViewSetMixin
from poms.iam.models import Role, Group, AccessPolicy
from poms.iam.permissions import FinmarsAccessPolicy
from rest_framework.permissions import IsAuthenticated
from drf_yasg.inspectors import SwaggerAutoSchema

from poms.iam.serializers import RoleSerializer, GroupSerializer, AccessPolicySerializer


class AbstractFinmarsAccessPolicyViewSet(AccessViewSetMixin, ModelViewSet):
    access_policy = FinmarsAccessPolicy

    filter_backends = ModelViewSet.filter_backends + [
        ObjectPermissionBackend,
    ]


class CustomSwaggerAutoSchema(SwaggerAutoSchema):
    def get_operation(self, operation_keys=None):
        operation = super().get_operation(operation_keys)

        splitted_dash_operation_keys = [word for item in operation_keys for word in item.split('-')]
        splitted_underscore_operation_keys = [word for item in splitted_dash_operation_keys for word in item.split('_')]

        capitalized_operation_keys = [word.capitalize() for word in splitted_underscore_operation_keys]

        operation.operationId = ' '.join(capitalized_operation_keys)

        # operation.operationId = f"{self.view.queryset.model._meta.verbose_name.capitalize()} {operation_keys[-1].capitalize()}"
        return operation

    def get_tags(self, operation_keys=None):
        tags = super().get_tags(operation_keys)

        splitted_tags = [word.split('-') for word in tags]

        result = []

        for splitted_tag in splitted_tags:
            capitalized_tag = [word.capitalize() for word in splitted_tag]

            result.append(' '.join(capitalized_tag))

        return result



class RoleViewSet(ModelViewSet):

    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = ModelViewSet.permission_classes + [
        IsAuthenticated
    ]

    swagger_schema = CustomSwaggerAutoSchema


class GroupViewSet(ModelViewSet):

    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [
        IsAuthenticated
    ]

    swagger_schema = CustomSwaggerAutoSchema

class AccessPolicyViewSet(ModelViewSet):

    queryset = AccessPolicy.objects.all()
    serializer_class = AccessPolicySerializer
    permission_classes = [
        IsAuthenticated
    ]

    swagger_schema = CustomSwaggerAutoSchema

