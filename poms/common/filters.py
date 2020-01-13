from functools import partial

import django_filters
from django.db.models import F
from django_filters.rest_framework import FilterSet
from rest_framework.filters import BaseFilterBackend
from rest_framework.settings import api_settings

from poms.common.middleware import get_request
from poms.common.utils import force_qs_evaluation
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.obj_perms.utils import obj_perms_filter_objects_for_view

from django.db.models import Q

from django.contrib.contenttypes.models import ContentType

from django.utils.translation import ugettext_lazy as _
from django.utils import six
from django.core.exceptions import ImproperlyConfigured

import time


# class ClassifierFilter(BaseFilterBackend):
#     def filter_queryset(self, request, queryset, view):
#         parent_id = request.query_params.get('parent', None)
#         if parent_id:
#             parent = queryset.get(id=parent_id)
#             return parent.get_family()
#         else:
#             return queryset.filter(parent__isnull=True)


def is_relation(item):
    return item in ['type', 'currency', 'instrument',
                    'instrument_type', 'group',
                    'pricing_policy', 'portfolio',
                    'transaction_type', 'transaction_currency',
                    'settlement_currency', 'account_cash',
                    'account_interim', 'account_position',
                    'accrued_currency', 'pricing_currency',
                    'one_off_event', 'regular_event', 'factor_same',
                    'factor_up', 'factor_down',

                    'strategy1_position', 'strategy1_cash',
                    'strategy2_position', 'strategy2_cash',
                    'strategy3_position', 'strategy3_cash',

                    'counterparty', 'responsible',

                    'allocation_balance', 'allocation_pl',
                    'linked_instrument',

                    'subgroup'

                    ]


def is_system_relation(item):
    return item in ['instrument_class',
                    'transaction_class',
                    'daily_pricing_model',
                    'payment_size_detail']


def is_scheme(item):
    return item in ['price_download_scheme']

def _model_choices(model, field_name, master_user_path):
    master_user = get_request().user.master_user

    print('model %s' % model)
    print('field_name %s' % field_name)

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


class ByIsEnabledFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if getattr(view, 'has_feature_is_enabled', False):
            if getattr(view, 'action', '') == 'list':
                value = request.query_params.get('is_enabled', None)
                if value is None:
                    is_enabled = value in (True, 'True', 'true', '1')
                    queryset = queryset.filter(is_enabled=is_enabled)
        return queryset


class NoOpFilter(django_filters.Filter):
    # For UI only, real filtering in some AbstractRelatedFilterBackend
    def filter(self, qs, value):
        return qs


class CharFilter(django_filters.CharFilter):
    def __init__(self, *args, **kwargs):
        kwargs['lookup_expr'] = 'icontains'
        super(CharFilter, self).__init__(*args, **kwargs)


class GroupsAttributeFilter(BaseFilterBackend):

    def format_groups(self, group_type, master_user, content_type):
        if 'attributes.' in group_type:
            attribute_type = GenericAttributeType.objects.get(user_code__exact=group_type.split('attributes.')[1],
                                                              master_user=master_user, content_type=content_type)

            return str(attribute_type.id)

        return group_type

    def filter_queryset(self, request, queryset, view):

        print('GroupsAttributeFilter')

        start_time = time.time()

        # groups_types = request.query_params.getlist('groups_types')
        # groups_values = request.query_params.getlist('groups_values')

        groups_types = request.data.get('groups_types', [])
        groups_values = request.data.get('groups_values', [])

        master_user = request.user.master_user

        if hasattr(view.serializer_class, 'Meta'):
            model = view.serializer_class.Meta.model
        else:
            return queryset

        content_type = ContentType.objects.get_for_model(model, for_concrete_model=False)

        groups_types = list(map(lambda x: self.format_groups(x, master_user, content_type), groups_types))

        # print('GroupsAttributeFilter init')

        # print('GroupsAttributeFilter.group_types %s' % groups_types)
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

                            res_attr = attr

                            if is_relation(res_attr):
                                res_attr = res_attr + '__user_code'
                            elif is_system_relation(attr):
                                res_attr = res_attr + '__system_code'
                            elif is_scheme(attr):
                                res_attr = res_attr + '__scheme_name'

                            queryset = queryset.filter(Q(**{res_attr + '__isnull': True}) | Q(**{res_attr: '-'}))

                        else:

                            if is_relation(attr):
                                params[attr + '__user_code'] = groups_values[i]
                            elif is_system_relation(attr):
                                params[attr + '__system_code'] = groups_values[i]
                            elif is_scheme(attr):
                                params[attr + '__scheme_name'] = groups_values[i]
                            else:
                                params[attr] = groups_values[i]

                            # print(attr)
                            # print(params)

                            queryset = queryset.filter(**params)

                    force_qs_evaluation(queryset)

                i = i + 1

        print("GroupsAttributeFilter done in %s seconds " % (time.time() - start_time))

        return queryset


class AttributeFilter(BaseFilterBackend):

    def format_groups(self, group_type, master_user, content_type):
        if 'attributes.' in group_type:
            attribute_type = GenericAttributeType.objects.get(user_code__exact=group_type.split('attributes.')[1],
                                                              master_user=master_user, content_type=content_type)

            return str(attribute_type.id)

        return group_type

    def filter_queryset(self, request, queryset, view):

        print('Attributes Filter')

        start_time = time.time()

        groups_types = request.data.get('groups_types', [])
        groups_values = request.data.get('groups_values', [])

        # for key in list(request.GET.keys()):
        #
        #     key_formatted = key.split('___da_')
        #
        #     if len(key_formatted) == 2:
        #         groups_types.append(key_formatted[1])
        #         groups_values.append(request.GET.getlist(key)[0])

        # print('AttributeFilter init')

        # print('AttributeFilter.groups_types %s' % groups_types)
        # print('AttributeFilter.groups_values %s' % groups_values)

        master_user = request.user.master_user

        if hasattr(view.serializer_class, 'Meta'):
            model = view.serializer_class.Meta.model
        else:
            return queryset

        content_type = ContentType.objects.get_for_model(model, for_concrete_model=False)

        groups_types = list(map(lambda x: self.format_groups(x, master_user, content_type), groups_types))

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

                            res_attr = attr

                            if is_relation(res_attr):
                                res_attr = res_attr + '__user_code'
                            elif is_system_relation(attr):
                                res_attr = res_attr + '__system_code'
                            elif is_scheme(attr):
                                res_attr = res_attr + '__scheme_name'

                            queryset = queryset.filter(Q(**{res_attr + '__isnull': True}) | Q(**{res_attr: '-'}))

                        else:
                            if is_relation(attr):
                                params[attr + '__user_code'] = groups_values[i]
                            elif is_system_relation(attr):
                                params[attr + '__system_code'] = groups_values[i]
                            elif is_scheme(attr):
                                params[attr + '__scheme_name'] = groups_values[i]
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


class OrderingPostFilter(BaseFilterBackend):
    # The URL query parameter used for the ordering.
    ordering_param = api_settings.ORDERING_PARAM
    ordering_fields = None
    template = 'rest_framework/filters/ordering.html'

    def get_ordering(self, request, queryset, view):
        """
        Ordering is set by a comma delimited ?ordering=... query parameter.

        The `ordering` query parameter can be overridden by setting
        the `ordering_param` value on the OrderingFilter or by
        specifying an `ORDERING_PARAM` value in the API settings.
        """

        # print('request.data %s' % request.data)

        params = request.data.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(',')]
            ordering = self.remove_invalid_fields(queryset, fields, view)
            if ordering:
                return ordering

        # No ordering was included, or all the ordering fields were invalid
        return self.get_default_ordering(view)

    def get_default_ordering(self, view):
        ordering = getattr(view, 'ordering', None)
        if isinstance(ordering, six.string_types):
            return (ordering,)
        return ordering

    def get_default_valid_fields(self, queryset, view):
        # If `ordering_fields` is not specified, then we determine a default
        # based on the serializer class, if one exists on the view.
        if hasattr(view, 'get_serializer_class'):
            try:
                serializer_class = view.get_serializer_class()
            except AssertionError:
                # Raised by the default implementation if
                # no serializer_class was found
                serializer_class = None
        else:
            serializer_class = getattr(view, 'serializer_class', None)

        if serializer_class is None:
            msg = (
                "Cannot use %s on a view which does not have either a "
                "'serializer_class', an overriding 'get_serializer_class' "
                "or 'ordering_fields' attribute."
            )
            raise ImproperlyConfigured(msg % self.__class__.__name__)

        return [
            (field.source or field_name, field.label)
            for field_name, field in serializer_class().fields.items()
            if not getattr(field, 'write_only', False) and not field.source == '*'
        ]

    def get_valid_fields(self, queryset, view):
        valid_fields = getattr(view, '`ing_fields', self.ordering_fields)

        if valid_fields is None:
            # Default to allowing filtering on serializer fields
            return self.get_default_valid_fields(queryset, view)

        elif valid_fields == '__all__':
            # View explicitly allows filtering on any model field
            valid_fields = [
                (field.name, field.verbose_name) for field in queryset.model._meta.fields
            ]
            valid_fields += [
                (key, key.title().split('__'))
                for key in queryset.query.annotations.keys()
            ]
        else:
            valid_fields = [
                (item, item) if isinstance(item, six.string_types) else item
                for item in valid_fields
            ]

        return valid_fields

    def remove_invalid_fields(self, queryset, fields, view):
        valid_fields = [item[0] for item in self.get_valid_fields(queryset, view)]
        return [term for term in fields if term.lstrip('-') in valid_fields]

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)

        if ordering:
            return queryset.order_by(*ordering)

        return queryset

    def get_template_context(self, request, queryset, view):
        current = self.get_ordering(request, queryset, view)
        current = None if current is None else current[0]
        options = []
        for key, label in self.get_valid_fields(queryset, view):
            options.append((key, '%s - %s' % (label, _('ascending'))))
            options.append(('-' + key, '%s - %s' % (label, _('descending'))))
        return {
            'request': request,
            'current': current,
            'param': self.ordering_param,
            'options': options,
        }

    def get_fields(self, view):
        return [self.ordering_param]