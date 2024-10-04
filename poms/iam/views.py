import django_filters
from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import FilterSet
from drf_yasg.inspectors import SwaggerAutoSchema
from rest_framework import filters
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from poms.common.serializers import ContentTypeSerializer
from poms.iam.filters import ObjectPermissionBackend
from poms.iam.mixins import AccessViewSetMixin
from poms.iam.models import (
    AccessPolicy,
    Group,
    ResourceGroup,
    ResourceGroupAssignment,
    Role,
)
from poms.iam.permissions import AdminPermission, FinmarsAccessPolicy
from poms.iam.serializers import (
    AccessPolicySerializer,
    GroupSerializer,
    ResourceGroupAssignmentSerializer,
    ResourceGroupSerializer,
    RoleSerializer,
)

WRITABLE_ACTIONS = {
    "create",
    "destroy",
    "update",
    "partial_update",
}


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
            "name": ["exact", "contains", "icontains"],
            "user_code": ["exact", "contains", "icontains"],
        }


class RoleViewSet(ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    filter_class = RoleFilterSet
    permission_classes = ModelViewSet.permission_classes + [IsAuthenticated]

    filter_backends = ModelViewSet.filter_backends + [filters.OrderingFilter]

    swagger_schema = CustomSwaggerAutoSchema

    ordering_fields = ["id", "name", "user_code", "created_at"]


class GroupFilterSet(FilterSet):
    name = django_filters.CharFilter()
    user_code = django_filters.CharFilter()

    class Meta:
        model = Group
        fields = {
            "name": ["exact", "contains", "icontains"],
            "user_code": ["exact", "contains", "icontains"],
        }


class GroupViewSet(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    filter_class = GroupFilterSet
    permission_classes = [IsAuthenticated]

    filter_backends = ModelViewSet.filter_backends + [filters.OrderingFilter]

    swagger_schema = CustomSwaggerAutoSchema

    ordering_fields = ["id", "name", "user_code", "created_at"]


class AccessPolicyFilterSet(FilterSet):
    name = django_filters.CharFilter()
    user_code = django_filters.CharFilter()

    class Meta:
        model = AccessPolicy
        fields = {
            "name": ["exact", "contains", "icontains"],
            "user_code": ["exact", "contains", "icontains"],
        }


class AccessPolicyViewSet(ModelViewSet):
    queryset = AccessPolicy.objects.all()
    serializer_class = AccessPolicySerializer
    filter_class = AccessPolicyFilterSet
    permission_classes = [IsAuthenticated]
    filter_backends = ModelViewSet.filter_backends + [filters.OrderingFilter]

    swagger_schema = CustomSwaggerAutoSchema

    ordering_fields = ["id", "name", "user_code", "created_at"]


class IAMBaseViewSet(ModelViewSet):
    """
    A base viewset that enforces IAM policies based on user policies.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user_policy = getattr(self.request, "user_policy", {})

        allowed_resources = user_policy.get("Resource")

        if allowed_resources is None:
            # Admin user, no filtering
            return queryset

        if not allowed_resources:
            # No access to any resources
            return queryset.none()

        # Assuming models have 'user_code' field
        return queryset.filter(user_code__in=allowed_resources)

    def list(self, request, *args, **kwargs):
        # Check if user has access to the endpoint
        if not self.has_endpoint_access():
            raise PermissionDenied("You do not have access to this endpoint.")

        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        # Check if user has access to the specific resource
        instance = self.get_object()
        if not self.has_resource_access(instance):
            raise PermissionDenied("You do not have access to this resource.")

        return super().retrieve(request, *args, **kwargs)

    def has_endpoint_access(self):
        """
        Implement your logic to check if the user has access to the requested endpoint.
        For simplicity, return True. Customize as needed.
        """
        return True

    def has_resource_access(self, instance):
        """
        Check if the user has access to the specific resource based on 'user_code'.
        """
        user_policy = getattr(self.request, "user_policy", {})
        allowed_resources = user_policy.get("Resource")

        if allowed_resources is None:
            # Admin user
            return True

        return instance.user_code in allowed_resources


class ResourceGroupViewSet(ModelViewSet):
    """
    A viewset for viewing and editing ResourceGroup instances.
    """

    queryset = ResourceGroup.objects.all()
    serializer_class = ResourceGroupSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_permissions(self):
        # only admins can create, change & delete ResourceGroups
        if self.action in WRITABLE_ACTIONS:
            self.permission_classes.append(AdminPermission)

        return super().get_permissions()


class ResourceGroupAssignmentViewSet(ModelViewSet):
    """
    A viewset for viewing and editing ResourceGroupAssignment instances.
    """

    queryset = ResourceGroupAssignment.objects.all()
    serializer_class = ResourceGroupAssignmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_permissions(self):
        # only admins can create, change & delete ResourceGroups
        if self.action in WRITABLE_ACTIONS:
            self.permission_classes.append(AdminPermission)

        return super().get_permissions()


class ContentTypeViewSet(ModelViewSet):
    """
    A viewset for viewing all ContentTypes objects,which have 'user_code' field,
    but except ResourceGroup.
    """

    queryset = ContentType.objects.filter(
        app_label__isnull=False,
        model__isnull=False,
    ).exclude(
        model=ResourceGroup._meta.model_name,
        app_label=ResourceGroup._meta.app_label,
    )
    serializer_class = ContentTypeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    http_method_names = ["get"]

    def get_queryset(self) -> list[ContentType]:
        return [
            ct
            for ct in self.queryset
            if hasattr(ct.model_class(), "user_code")
            and ct.model_class != ResourceGroup
        ]

    def retrieve(self, request, *args, **kwargs):
        raise MethodNotAllowed("Action 'retrieve' is not allowed in this URI")
