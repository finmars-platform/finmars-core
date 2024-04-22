from logging import getLogger

import django_filters
from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from poms.common.filters import CharFilter, NoOpFilter
from poms.common.views import AbstractModelViewSet, AbstractReadOnlyModelViewSet
from poms.obj_attrs.filters import (
    AttributeTypeValueTypeFilter,
    OwnerByAttributeTypeFilter,
)
from poms.obj_attrs.models import (
    GenericAttribute,
    GenericAttributeType,
    GenericClassifier,
)
from poms.obj_attrs.serializers import (
    GenericAttributeTypeSerializer,
    GenericClassifierNodeSerializer,
    RecalculateAttributesSerializer,
)
from poms.obj_attrs.tasks import recalculate_attributes
from poms.users.filters import OwnerByMasterUserFilter

_l = getLogger("poms.obj_attrs")


class AbstractAttributeTypeViewSet(AbstractModelViewSet):
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
        "order",
    ]

    def get_queryset(self):
        qs = super(AbstractAttributeTypeViewSet, self).get_queryset()
        return qs.prefetch_related("options")

    def get_serializer(self, *args, **kwargs):
        return super().get_serializer(*args, **kwargs)


class AbstractClassifierViewSet(AbstractModelViewSet):
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByAttributeTypeFilter,
    ]
    ordering_fields = [
        "attribute_type",
        "attribute_type__user_code",
        "attribute_type__name",
        "attribute_type__short_name",
        "attribute_type__public_name",
        "name",
        "level",
    ]

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)


class AccountClassifierFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()
    level = django_filters.NumberFilter()

    class Meta:
        model = GenericClassifier
        fields = []


class GenericClassifierViewSet(AbstractReadOnlyModelViewSet):
    queryset = GenericClassifier.objects.select_related(
        "attribute_type", "parent"
    ).prefetch_related("children")
    filter_backends = AbstractReadOnlyModelViewSet.filter_backends + [
        OwnerByAttributeTypeFilter,
    ]
    serializer_class = GenericClassifierNodeSerializer
    target_model = None
    ordering_fields = [
        "attribute_type",
        "attribute_type__user_code",
        "attribute_type__name",
        "attribute_type__short_name",
        "attribute_type__public_name",
        "name",
        "level",
    ]
    filter_class = AccountClassifierFilterSet

    def get_queryset(self):
        return (
            super(GenericClassifierViewSet, self)
            .get_queryset()
            .filter(attribute_type__content_type=self.target_model_content_type)
        )

    @property
    def target_model_content_type(self):
        return ContentType.objects.get_for_model(self.target_model)


class GenericAttributeTypeFilterSet(FilterSet):
    id = NoOpFilter()
    user_code = CharFilter()
    kind = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    value_type = AttributeTypeValueTypeFilter()

    class Meta:
        model = GenericAttributeType
        fields = []


# class GenericAttributeTypeViewSet(AbstractWithObjectPermissionViewSet):
class GenericAttributeTypeViewSet(AbstractModelViewSet):
    queryset = GenericAttributeType.objects.select_related(
        "master_user", "content_type"
    ).prefetch_related(
        "options",
        "classifiers",
    )
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    serializer_class = GenericAttributeTypeSerializer
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
        "order",
    ]
    filter_class = GenericAttributeTypeFilterSet
    target_model = None
    target_model_serializer = None

    def get_queryset(self):
        return (
            super(GenericAttributeTypeViewSet, self)
            .get_queryset()
            .filter(content_type=self.target_model_content_type)
        )

    def get_serializer(self, *args, **kwargs):
        return super().get_serializer(*args, **kwargs)

    @property
    def target_model_content_type(self):
        # TODO important objects.get_for_model return cached value
        # from public scheme, it can lead to unexpected behavior
        # ContentType.objects.get_for_model(self.target_model)
        # Assuming 'self.target_model' is a Django model class
        app_label = self.target_model._meta.app_label
        model = self.target_model._meta.model_name  # 'model_name' is always lowercase

        content_type = ContentType.objects.get(app_label=app_label, model=model)
        return content_type

    def perform_create(self, serializer):
        serializer.save(content_type=ContentType.objects.get_for_model(self.target_model))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @action(detail=True, methods=["get"], url_path="objects-to-recalculate")
    def objects_to_recalculate(self, request, pk, realm_code=None, space_code=None):
        master_user = request.user.master_user

        attribute_type = GenericAttributeType.objects.get(
            id=pk, master_user=master_user
        )

        if attribute_type.can_recalculate is False:
            return Response({"count": 0})

        objs_count = GenericAttribute.objects.filter(
            attribute_type=attribute_type, content_type=self.target_model_content_type
        ).count()

        return Response({"count": objs_count})

    @action(
        detail=True,
        methods=["post"],
        url_path="recalculate",
        serializer_class=RecalculateAttributesSerializer,
    )
    def recalculate_attributes(self, request, pk, realm_code=None, space_code=None):
        context = {"request": request}

        serializer = RecalculateAttributesSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        task_id = instance.task_id

        print(f"instance {instance}")

        if not task_id:
            instance.attribute_type_id = pk
            instance.target_model = self.target_model
            instance.target_model_content_type = self.target_model_content_type
            instance.target_model_serializer = self.target_model_serializer

            res = recalculate_attributes.apply_async(kwargs={"instance": instance, 'context': {
                'space_code': request.space_code,
                'realm_code': request.realm_code
            }})

            instance.task_id = res.id
            instance.task_status = res.status

            print(f"instance.task_id {instance.task_id}")

            serializer = RecalculateAttributesSerializer(instance=instance, many=False)

        # TODO import-like status check chain someday
        # TODO Right now is not important because status showed at Active Processes page
        return Response(serializer.data, status=status.HTTP_200_OK)
