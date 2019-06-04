from functools import partial

import django_filters
from django.db.models import F
from rest_framework.filters import BaseFilterBackend, FilterSet

from poms.common.middleware import get_request
from poms.common.utils import force_qs_evaluation
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.obj_perms.utils import obj_perms_filter_objects_for_view

from django.db.models import Q

import time


# class ClassifierFilter(BaseFilterBackend):
#     def filter_queryset(self, request, queryset, view):
#         parent_id = request.query_params.get('parent', None)
#         if parent_id:
#             parent = queryset.get(id=parent_id)
#             return parent.get_family()
#         else:
#             return queryset.filter(parent__isnull=True)


def _model_choices(model, field_name, master_user_path):
    master_user = get_request().user.master_user
    qs = model.objects.filter(**{master_user_path: master_user}).order_by(field_name)
    for t in qs:
        yield t.id, getattr(t, field_name)


def _model_with_perms_choices(model, field_name, master_user_path):
    master_user = get_request().user.master_user
    member = get_request().user.member
    qs = model.objects.filter(**{master_user_path: master_user}).order_by(field_name)
    for t in obj_perms_filter_objects_for_view(member, qs, prefetch=False):
        yield t.id, getattr(t, field_name)


class ModelExtMultipleChoiceFilter(django_filters.MultipleChoiceFilter):
    model = None
    field_name = 'name'
    master_user_path = 'master_user'

    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', self.model)
        self.field_name = kwargs.pop('field_name', self.field_name)
        self.master_user_path = kwargs.pop('master_user_path', self.master_user_path)
        kwargs['choices'] = partial(_model_choices, model=self.model, field_name=self.field_name,
                                    master_user_path=self.master_user_path)
        super(ModelExtMultipleChoiceFilter, self).__init__(*args, **kwargs)


class ModelExtWithPermissionMultipleChoiceFilter(django_filters.MultipleChoiceFilter):
    model = None
    field_name = 'name'
    master_user_path = 'master_user'

    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', self.model)
        self.field_name = kwargs.pop('field_name', self.field_name)
        self.master_user_path = kwargs.pop('master_user_path', self.master_user_path)
        kwargs['choices'] = partial(_model_with_perms_choices, model=self.model, field_name=self.field_name,
                                    master_user_path=self.master_user_path)
        super(ModelExtWithPermissionMultipleChoiceFilter, self).__init__(*args, **kwargs)


class AbstractRelatedFilterBackend(BaseFilterBackend):
    source = None
    query_key = None

    def filter_queryset(self, request, queryset, view):
        pk_set = [int(pk) for pk in request.query_params.getlist(self.query_key) if pk]
        if pk_set:
            return queryset.filter(**{'%s__in' % self.query_key: pk_set})
        return queryset


class ByIdFilterBackend(AbstractRelatedFilterBackend):
    source = 'pk'
    query_key = 'id'


class ByIsDeletedFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if getattr(view, 'has_feature_is_deleted', False):
            if getattr(view, 'action', '') == 'list':
                value = request.query_params.get('is_deleted', None)
                if value is None:
                    is_deleted = value in (True, 'True', 'true', '1')
                    queryset = queryset.filter(is_deleted=is_deleted)
        return queryset


class NoOpFilter(django_filters.MethodFilter):
    # For UI only, real filtering in some AbstractRelatedFilterBackend
    def filter(self, qs, value):
        return qs


class CharFilter(django_filters.CharFilter):
    def __init__(self, *args, **kwargs):
        kwargs['lookup_expr'] = 'icontains'
        super(CharFilter, self).__init__(*args, **kwargs)


class GroupsAttributeFilter(BaseFilterBackend):

    def format_groups(self, group_type):
        if 'attributes.' in group_type:
            attribute_type = GenericAttributeType.objects.get(user_code__exact=group_type.split('attributes.')[1])

            return str(attribute_type.id)

        return group_type

    def filter_queryset(self, request, queryset, view):

        start_time = time.time()

        groups_types = request.query_params.getlist('groups_types')
        groups_values = request.query_params.getlist('groups_values')

        groups_types = list(map(self.format_groups, groups_types))

        # print('GroupsAttributeFilter init')

        print('GroupsAttributeFilter.group_types %s' % groups_types)
        # print('GroupsAttributeFilter.groups_values %s' % groups_values)

        # print('queryset len %s' % len(queryset))

        if len(groups_types) and len(groups_values):

            i = 0

            for attr in groups_types:

                if len(groups_values) > i:

                    if attr.isdigit():

                        attribute_type = GenericAttributeType.objects.get(id__exact=attr)

                        # print('attribute_type %s ' % attribute_type)
                        # print('attribute_type value_type %s' % attribute_type.value_type)

                        if attribute_type.value_type == 20:

                            if groups_values[i] == '-':

                                queryset = queryset.filter(attributes__value_float__isnull=True,
                                                           attributes__attribute_type=attribute_type)

                            else:
                                queryset = queryset.filter(attributes__value_float=groups_values[i],
                                                           attributes__attribute_type=attribute_type)

                        if attribute_type.value_type == 10:

                            if groups_values[i] == '-':
                                queryset = queryset.filter(attributes__value_string__isnull=True,
                                                           attributes__attribute_type=attribute_type)
                            else:

                                queryset = queryset.filter(attributes__value_string=groups_values[i],
                                                           attributes__attribute_type=attribute_type)

                        if attribute_type.value_type == 30:

                            if groups_values[i] == '-':
                                queryset = queryset.filter(attributes__classifier__isnull=True,
                                                           attributes__attribute_type=attribute_type)
                            else:
                                queryset = queryset.filter(attributes__classifier=groups_values[i],
                                                           attributes__attribute_type=attribute_type)

                        if attribute_type.value_type == 40:

                            if groups_values[i] == '-':
                                queryset = queryset.filter(attributes__value_date__isnull=True,
                                                           attributes__attribute_type=attribute_type)
                            else:
                                queryset = queryset.filter(attributes__value_date=groups_values[i],
                                                           attributes__attribute_type=attribute_type)

                        # print('iteration i %s' % i)
                        # print('iteration len %s' % len(queryset))

                    else:

                        params = {}

                        if groups_values[i] == '-':

                            queryset = queryset.filter(Q(**{attr + '__isnull': True}) | Q(**{attr: '-'}))

                        else:
                            params[attr] = groups_values[i]

                            queryset = queryset.filter(**params)

                    force_qs_evaluation(queryset)

                i = i + 1

        # print("GroupsAttributeFilter.filter_queryset %s seconds " % (time.time() - start_time))

        return queryset


class AttributeFilter(BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):

        start_time = time.time()

        groups_types = []
        groups_values = []

        for key in list(request.GET.keys()):

            key_formatted = key.split('___da_')

            if len(key_formatted) == 2:
                groups_types.append(key_formatted[1])
                groups_values.append(request.GET.getlist(key)[0])

        # print('AttributeFilter init')

        # print('AttributeFilter.groups_types %s' % groups_types)
        # print('AttributeFilter.groups_values %s' % groups_values)

        if len(groups_types) and len(groups_values):

            i = 0

            for attr in groups_types:

                if len(groups_values) > i:

                    if attr.isdigit():

                        attribute_type = GenericAttributeType.objects.get(id__exact=attr)

                        # print('AttributeFilter.attribute_type %s' % attribute_type)

                        if attribute_type.value_type == 20:

                            if groups_values[i] == '-':

                                queryset = queryset.filter(attributes__value_float__isnull=True,
                                                           attributes__attribute_type=attribute_type)
                            else:
                                queryset = queryset.filter(attributes__value_float=groups_values[i],
                                                           attributes__attribute_type=attribute_type)

                        if attribute_type.value_type == 10:

                            if groups_values[i] == '-':
                                queryset = queryset.filter(attributes__value_string__isnull=True,
                                                           attributes__attribute_type=attribute_type)
                            else:
                                queryset = queryset.filter(attributes__value_string=groups_values[i],
                                                           attributes__attribute_type=attribute_type)

                        if attribute_type.value_type == 30:

                            if groups_values[i] == '-':
                                queryset = queryset.filter(attributes__classifier__isnull=True,
                                                           attributes__attribute_type=attribute_type)
                            else:
                                queryset = queryset.filter(attributes__classifier=groups_values[i],
                                                           attributes__attribute_type=attribute_type)

                        if attribute_type.value_type == 40:

                            if groups_values[i] == '-':
                                queryset = queryset.filter(attributes__value_date__isnull=True,
                                                           attributes__attribute_type=attribute_type)
                            else:
                                queryset = queryset.filter(attributes__value_date=groups_values[i],
                                                           attributes__attribute_type=attribute_type)

                    else:

                        params = {}

                        if groups_values[i] == '-':

                            queryset = queryset.filter(Q(**{attr + '__isnull': True}) | Q(**{attr: '-'}))

                        else:
                            params[attr] = groups_values[i]

                            queryset = queryset.filter(**params)

                    force_qs_evaluation(queryset)

                i = i + 1

        # print('AttributeFilter qs len %s' % len(queryset))

        # print("AttributeFilter.filter_queryset %s seconds " % (time.time() - start_time))

        return queryset


class ClassifierFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # queryset = queryset.prefetch_related('parent', 'children')
        if view and view.action == 'list':
            return queryset.filter(parent__isnull=True)
        return queryset.prefetch_related('parent', 'children')


class ClassifierRootFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(parent__isnull=True)


class ClassifierPrefetchFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.prefetch_related('parent', 'children')


class AbstractClassifierFilterSet(FilterSet):
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()

    class Meta:
        fields = ['user_code', 'name', 'short_name']

    def parent_filter(self, qs, value):
        return qs


class IsDefaultFilter(django_filters.BooleanFilter):
    def __init__(self, *args, **kwargs):
        self.source = kwargs.pop('source')
        super(IsDefaultFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in ([], (), {}, None, ''):
            return qs
        if self.distinct:
            qs = qs.distinct()
        if value is None:
            return qs
        elif value:
            return qs.filter(**{'pk': F('master_user__%s__id' % self.source)})
        else:
            return qs.exclude(**{'pk': F('master_user__%s__id' % self.source)})
