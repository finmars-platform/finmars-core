import django_filters
from django.contrib.contenttypes.models import ContentType
from rest_framework.decorators import list_route, detail_route
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.filters import FilterSet

from poms.common.filters import NoOpFilter, CharFilter, ModelExtWithPermissionMultipleChoiceFilter
from poms.common.formula import safe_eval, ExpressionEvalError
from poms.common.views import AbstractModelViewSet, AbstractReadOnlyModelViewSet
from poms.obj_attrs.filters import OwnerByAttributeTypeFilter, AttributeTypeValueTypeFilter
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier, GenericAttribute
from poms.obj_attrs.serializers import GenericAttributeTypeSerializer, GenericClassifierSerializer, \
    GenericClassifierNodeSerializer
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionGroupFilter, \
    ObjectPermissionPermissionFilter
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet
from poms.users.filters import OwnerByMasterUserFilter

from rest_framework.response import Response

from rest_framework import viewsets, status


class AbstractAttributeTypeViewSet(AbstractWithObjectPermissionViewSet):
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
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
        kwargs['show_classifiers'] = (self.action != 'list') or self.request.query_params.get('show_classifiers', None)
        kwargs['read_only_value_type'] = (self.action != 'create')
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
    attribute_type = ModelExtWithPermissionMultipleChoiceFilter(model=GenericAttributeType)

    class Meta:
        model = GenericClassifier
        fields = []


class GenericClassifierViewSet(AbstractReadOnlyModelViewSet):
    queryset = GenericClassifier.objects.select_related(
        'attribute_type',
        'parent'
    ).prefetch_related(
        'children',
        *get_permissions_prefetch_lookups(
            ('attribute_type', GenericAttributeType),
        )
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
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    value_type = AttributeTypeValueTypeFilter()
    member = ObjectPermissionMemberFilter(object_permission_model=GenericAttributeType)
    member_group = ObjectPermissionGroupFilter(object_permission_model=GenericAttributeType)
    permission = ObjectPermissionPermissionFilter(object_permission_model=GenericAttributeType)

    class Meta:
        model = GenericAttributeType
        fields = []


class GenericAttributeTypeViewSet(AbstractWithObjectPermissionViewSet):
    queryset = GenericAttributeType.objects.select_related(
        'master_user',
        'content_type'
    ).prefetch_related(
        'options', 'classifiers',
        *get_permissions_prefetch_lookups(
            (None, GenericAttributeType),
        )
    )
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
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
        kwargs.setdefault('show_classifiers',
                          (self.action != 'list') or self.request.query_params.get('show_classifiers', None))
        kwargs['read_only_value_type'] = (self.action != 'create')
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

        print('Create attribute type for %s' % self.target_model)

        attrs = []

        content_type = ContentType.objects.get_for_model(self.target_model)

        master_user = request.user.master_user

        items = self.target_model.objects.filter(master_user=master_user)

        print('items len %s' % len(items))

        attr_type = GenericAttributeType.objects.get(pk=serializer.data['id'])

        for item in items:

            try:
                exists = GenericAttribute.objects.get(attribute_type=attr_type, content_type=content_type,
                                                      object_id=item.pk)

            except GenericAttribute.DoesNotExist:

                attrs.append(GenericAttribute(attribute_type=attr_type, content_type=content_type, object_id=item.pk))

        GenericAttribute.objects.bulk_create(attrs)

        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_attributes_as_obj(self, instance):

        result = {}

        attributes = GenericAttribute.objects.filter(object_id=instance.id, content_type=self.target_model_content_type)

        for attribute in attributes:

            attribute_type = attribute.attribute_type

            if attribute_type.value_type == 10:
                result[attribute_type.user_code] = attribute.value_string

            if attribute_type.value_type == 20:
                result[attribute_type.user_code] = attribute.float

            if attribute_type.value_type == 30:
                if attribute.classifier:
                    result[attribute_type.user_code] = attribute.classifier.name
                else:
                    result[attribute_type.user_code] = None

            if attribute_type.value_type == 40:
                result[attribute_type.user_code] = attribute.value_date

        return result

    def get_json_objs(self, master_user, context):

        result = {}

        instances = self.target_model.objects.filter(master_user=master_user)

        for instance in instances:

            serializer = self.target_model_serializer(instance=instance, context=context)

            result[instance.id] = serializer.data

            result[instance.id]['attributes'] = self.get_attributes_as_obj(instance)

        return result

    @detail_route(methods=['get'], url_path='objects-to-recalculate')
    def objects_to_recalculate(self, request, pk):

        master_user = request.user.master_user

        attribute_type = GenericAttributeType.objects.get(id=pk, master_user=master_user)

        if attribute_type.can_recalculate is False:
            return Response({'count': 0})

        objs_count = GenericAttribute.objects.filter(
            attribute_type=attribute_type,
            content_type=self.target_model_content_type).count()

        return Response({'count': objs_count})

    @detail_route(methods=['post'], url_path='recalculate')
    def recalculate_attributes(self, request, pk):

        master_user = request.user.master_user

        attribute_type = GenericAttributeType.objects.get(id=pk, master_user=master_user)

        attributes = GenericAttribute.objects.filter(
            attribute_type=attribute_type,
            content_type=self.target_model_content_type)

        context = {'request': request}

        json_objs = self.get_json_objs(master_user, context, )

        for attr in attributes:

            data = json_objs[attr.object_id]

            try:
                executed_expression = safe_eval(attribute_type.expr, names={'this': data}, context={})
            except (ExpressionEvalError, TypeError, Exception, KeyError):
                executed_expression = 'Invalid Expression'

            if attr.attribute_type.value_type == GenericAttributeType.STRING:

                if executed_expression == 'Invalid Expression':
                    attr.value_string = None
                else:
                    attr.value_string = executed_expression

            if attr.attribute_type.value_type == GenericAttributeType.NUMBER:

                if executed_expression == 'Invalid Expression':
                    attr.value_float = None
                else:
                    attr.value_float = executed_expression

            if attr.attribute_type.value_type == GenericAttributeType.DATE:

                if executed_expression == 'Invalid Expression':
                    attr.value_date = None
                else:
                    attr.value_date = executed_expression

            if attr.attribute_type.value_type == GenericAttributeType.CLASSIFIER:

                if executed_expression == 'Invalid Expression':
                    attr.classifier = None
                else:
                    attr.classifier = executed_expression

            attr.save()

        return Response({'status': 'ok'})
