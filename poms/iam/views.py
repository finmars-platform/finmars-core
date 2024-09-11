from drf_yasg.inspectors import SwaggerAutoSchema
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from poms.iam.filters import ObjectPermissionBackend
from poms.iam.mixins import AccessViewSetMixin
from poms.iam.models import AccessPolicy, Group, Role
from poms.iam.permissions import FinmarsAccessPolicy
from poms.iam.serializers import AccessPolicySerializer, GroupSerializer, RoleSerializer
from django_filters.rest_framework import FilterSet
import django_filters
from rest_framework import filters

class AbstractFinmarsAccessPolicyViewSet(AccessViewSetMixin, ModelViewSet):
    access_policy = FinmarsAccessPolicy

    filter_backends = ModelViewSet.filter_backends + [
        ObjectPermissionBackend,
    ]


class CustomSwaggerAutoSchema(SwaggerAutoSchema):
    def get_operation(self, operation_keys=None):
        operation = super().get_operation(operation_keys)

        splitted_dash_operation_keys = [
            word for item in operation_keys for word in item.split("-")
        ]
        splitted_underscore_operation_keys = [
            word for item in splitted_dash_operation_keys for word in item.split("_")
        ]

        capitalized_operation_keys = [
            word.capitalize() for word in splitted_underscore_operation_keys
        ]

        operation.operationId = " ".join(capitalized_operation_keys)

        # operation.operationId = f"{self.view.queryset.model._meta.verbose_name.capitalize()} {operation_keys[-1].capitalize()}"
        return operation

    def get_tags(self, operation_keys=None):
        tags = super().get_tags(operation_keys)

        splitted_tags = [word.split("-") for word in tags]

        result = []

        for splitted_tag in splitted_tags:
            capitalized_tag = [word.capitalize() for word in splitted_tag]

            result.append(" ".join(capitalized_tag))

        return result


class RoleFilterSet(FilterSet):

    name = django_filters.CharFilter()
    user_code = django_filters.CharFilter()

    class Meta:
        model = Role
        fields = {
            'name': ['exact', 'contains', 'icontains'],
            'user_code': ['exact', 'contains', 'icontains'],
        }


class RoleViewSet(ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    filter_class = RoleFilterSet
    permission_classes = ModelViewSet.permission_classes + [IsAuthenticated]

    filter_backends = ModelViewSet.filter_backends + [filters.OrderingFilter]

    swagger_schema = CustomSwaggerAutoSchema

    ordering_fields = [
        'id',
        'name',
        'user_code',
        'created_at'
    ]


class GroupFilterSet(FilterSet):

    name = django_filters.CharFilter()
    user_code = django_filters.CharFilter()

    class Meta:
        model = Group
        fields = {
            'name': ['exact', 'contains', 'icontains'],
            'user_code': ['exact', 'contains', 'icontains'],
        }


class GroupViewSet(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    filter_class = GroupFilterSet
    permission_classes = [IsAuthenticated]

    filter_backends = ModelViewSet.filter_backends + [filters.OrderingFilter]

    swagger_schema = CustomSwaggerAutoSchema

    ordering_fields = [
        'id',
        'name',
        'user_code',
        'created_at'
    ]


class AccessPolicyFilterSet(FilterSet):

    name = django_filters.CharFilter()
    user_code = django_filters.CharFilter()

    class Meta:
        model = AccessPolicy
        fields = {
            'name': ['exact', 'contains', 'icontains'],
            'user_code': ['exact', 'contains', 'icontains'],
        }


class AccessPolicyViewSet(ModelViewSet):
    queryset = AccessPolicy.objects.all()
    serializer_class = AccessPolicySerializer
    filter_class = AccessPolicyFilterSet
    permission_classes = [IsAuthenticated]
    filter_backends = ModelViewSet.filter_backends + [filters.OrderingFilter]

    swagger_schema = CustomSwaggerAutoSchema

    ordering_fields = [
        'id',
        'name',
        'user_code',
        'created_at'
    ]