from logging import getLogger

import django_filters
from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from poms.common.filters import NoOpFilter, CharFilter
from poms.common.views import AbstractModelViewSet, AbstractReadOnlyModelViewSet
from poms.obj_attrs.filters import OwnerByAttributeTypeFilter, AttributeTypeValueTypeFilter
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier, GenericAttribute
from poms.obj_attrs.serializers import GenericAttributeTypeSerializer, GenericClassifierNodeSerializer, \
    RecalculateAttributesSerializer
from poms.obj_attrs.tasks import recalculate_attributes
from poms.users.filters import OwnerByMasterUserFilter

_l = getLogger('poms.obj_attrs')


class AbstractAttributeTypeViewSet(AbstractModelViewSet):
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name', 'order',
    ]

    def get_queryset(self):
        qs = super(AbstractAttributeTypeViewSet, self).get_queryset()
        return qs.prefetch_related('options')

    def get_serializer(self, *args, **kwargs):
        # TODO: remove objects_permissions
        # if self.action != 'objects_permissions':
        # kwargs['show_classifiers'] = (self.action != 'list') or self.request.query_params.get('show_classifiers', None)
        # kwargs['read_only_value_type'] = (self.action != 'create')
        return super(AbstractAttributeTypeViewSet, self).get_serializer(*args, **kwargs)


class AbstractClassifierViewSet(AbstractModelViewSet):
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByAttributeTypeFilter,
    ]
    ordering_fields = [
        'attribute_type', 'attribute_type__user_code', 'attribute_type__name', 'attribute_type__short_name',
        'attribute_type__public_name',
        'name', 'level',
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
        'attribute_type',
        'parent'
    ).prefetch_related(
        'children'
    )
    filter_backends = AbstractReadOnlyModelViewSet.filter_backends + [
        OwnerByAttributeTypeFilter,
    ]
    serializer_class = GenericClassifierNodeSerializer
    target_model = None
    ordering_fields = [
        'attribute_type', 'attribute_type__user_code', 'attribute_type__name', 'attribute_type__short_name',
        'attribute_type__public_name',
        'name', 'level',
    ]
    filter_class = AccountClassifierFilterSet

    def get_queryset(self):
        return super(GenericClassifierViewSet, self).get_queryset().filter(
            attribute_type__content_type=self.target_model_content_type)

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
        'master_user',
        'content_type'
    ).prefetch_related(
        'options', 'classifiers',
    )
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    serializer_class = GenericAttributeTypeSerializer
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name', 'order',
    ]
    filter_class = GenericAttributeTypeFilterSet
    target_model = None
    target_model_serializer = None

    def get_queryset(self):
        return super(GenericAttributeTypeViewSet, self).get_queryset().filter(
            content_type=self.target_model_content_type)

    def get_serializer(self, *args, **kwargs):
        # kwargs.setdefault('show_classifiers',
        #                   (self.action != 'list') or self.request.query_params.get('show_classifiers', None))
        # kwargs['read_only_value_type'] = (self.action != 'create')
        return super(GenericAttributeTypeViewSet, self).get_serializer(*args, **kwargs)

    @property
    def target_model_content_type(self):
        return ContentType.objects.get_for_model(self.target_model)

    def perform_create(self, serializer):
        serializer.save(content_type=self.target_model_content_type)

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        # attrs = []
        #
        # content_type = ContentType.objects.get_for_model(self.target_model)
        #
        # master_user = request.user.master_user
        #
        # items = self.target_model.objects.filter(master_user=master_user)
        #
        # print('items len %s' % len(items))
        #
        # attr_type = GenericAttributeType.objects.get(pk=serializer.data['id'])
        #
        # for item in items:
        #
        #     try:
        #         exists = GenericAttribute.objects.get(attribute_type=attr_type, content_type=content_type,
        #                                               object_id=item.pk)
        #
        #     except GenericAttribute.DoesNotExist:
        #
        #         attrs.append(GenericAttribute(attribute_type=attr_type, content_type=content_type, object_id=item.pk))
        #
        # GenericAttribute.objects.bulk_create(attrs)

        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['get'], url_path='objects-to-recalculate')
    def objects_to_recalculate(self, request, pk):

        master_user = request.user.master_user

        attribute_type = GenericAttributeType.objects.get(id=pk, master_user=master_user)

        if attribute_type.can_recalculate is False:
            return Response({'count': 0})

        objs_count = GenericAttribute.objects.filter(
            attribute_type=attribute_type,
            content_type=self.target_model_content_type).count()

        return Response({'count': objs_count})

    @action(detail=True, methods=['post'], url_path='recalculate', serializer_class=RecalculateAttributesSerializer)
    def recalculate_attributes(self, request, pk):

        context = {'request': request}

        serializer = RecalculateAttributesSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        task_id = instance.task_id

        # signer = TimestampSigner()

        print('instance %s' % instance)

        if task_id:

            # TODO import-like status check chain someday
            # TODO Right now is not important because status showed at Active Processes page
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:

            instance.attribute_type_id = pk
            instance.target_model = self.target_model
            instance.target_model_content_type = self.target_model_content_type
            instance.target_model_serializer = self.target_model_serializer

            res = recalculate_attributes.apply_async(kwargs={'instance': instance})

            # instance.task_id = signer.sign('%s' % res.id)
            instance.task_id = res.id
            instance.task_status = res.status

            print('instance.task_id %s' % instance.task_id)

            serializer = RecalculateAttributesSerializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
