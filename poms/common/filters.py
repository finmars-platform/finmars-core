import logging
from functools import partial

import django_filters
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import FilterSet
from rest_framework.filters import BaseFilterBackend
from rest_framework.settings import api_settings
from six import string_types

from poms.common.middleware import get_request
from poms.common.utils import attr_is_relation
from poms.obj_attrs.models import GenericAttributeType

_l = logging.getLogger("poms.common")


def is_system_relation(item):
    return item in [
        "instrument_class",
        "transaction_class",
        "daily_pricing_model",
        "payment_size_detail",
    ]


def is_scheme(item):
    return item in ["price_download_scheme"]


def _model_choices(model, field_name, master_user_path):
    master_user = get_request().user.master_user

    qs = model.objects.filter(**{master_user_path: master_user}).order_by(field_name)

    for t in qs:
        yield t.id, getattr(t, field_name)


class ModelExtMultipleChoiceFilter(django_filters.MultipleChoiceFilter):
    model = None
    field_name = "name"
    master_user_path = "master_user"

    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop("model", self.model)
        self.field_name = kwargs.pop("field_name", self.field_name)
        self.master_user_path = kwargs.pop("master_user_path", self.master_user_path)
        kwargs["choices"] = partial(
            _model_choices,
            model=self.model,
            field_name=self.field_name,
            master_user_path=self.master_user_path,
        )
        super(ModelExtMultipleChoiceFilter, self).__init__(*args, **kwargs)


class AbstractRelatedFilterBackend(BaseFilterBackend):
    source = None
    query_key = None

    def filter_queryset(self, request, queryset, view):
        pk_set = [int(pk) for pk in request.query_params.getlist(self.query_key) if pk]
        if pk_set:
            return queryset.filter(**{f"{self.query_key}__in": pk_set})

        return queryset


class ByIdFilterBackend(AbstractRelatedFilterBackend):
    source = "pk"
    query_key = "id"


class ByIsDeletedFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if (
                getattr(view, "has_feature_is_deleted", False)
                and getattr(view, "action", "") == "list"
        ):
            value = request.query_params.get("is_deleted", None)
            if value is None:
                is_deleted = value in (True, "True", "true", "1")
                queryset = queryset.filter(is_deleted=is_deleted)
        return queryset


def _user_code_model_choices(model, field_name, master_user_path):
    master_user = get_request().user.master_user

    qs = model.objects.filter(**{master_user_path: master_user}).order_by(field_name)

    for t in qs:
        yield t.user_code, getattr(t, field_name)


class ModelExtUserCodeMultipleChoiceFilter(django_filters.MultipleChoiceFilter):
    model = None
    field_name = 'user_code'
    master_user_path = 'master_user'

    def __init__(self, *args, **kwargs):
        kwargs['lookup_expr'] = 'exact'
        self.model = kwargs.pop('model', self.model)
        self.field_name = kwargs.pop('field_name', self.field_name)
        self.master_user_path = kwargs.pop('master_user_path', self.master_user_path)
        kwargs['choices'] = partial(_user_code_model_choices, model=self.model, field_name=self.field_name,
                                    master_user_path=self.master_user_path)
        super(ModelExtUserCodeMultipleChoiceFilter, self).__init__(*args, **kwargs)


class ByIsEnabledFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if (
                getattr(view, "has_feature_is_enabled", False)
                and getattr(view, "action", "") == "list"
        ):
            value = request.query_params.get("is_enabled", None)
            if value is None:
                is_enabled = value in (True, "True", "true", "1")
                queryset = queryset.filter(is_enabled=is_enabled)
        return queryset


class NoOpFilter(django_filters.Filter):
    # For UI only, real filtering in some AbstractRelatedFilterBackend
    def filter(self, qs, value):
        return qs


class CharFilter(django_filters.CharFilter):
    def __init__(self, *args, **kwargs):
        kwargs["lookup_expr"] = "icontains"
        super(CharFilter, self).__init__(*args, **kwargs)


class CharExactFilter(django_filters.CharFilter):
    def __init__(self, *args, **kwargs):
        kwargs["lookup_expr"] = "exact"
        super(CharExactFilter, self).__init__(*args, **kwargs)


def _is_date_or_number(field_type):
    for type_part in ['Date', 'Float', 'Integer']:
        if type_part in field_type:
            return True

    return False


def get_q_obj_for_group_dash(content_type_key, model, attribute_key):
    """

    :param content_type_key:
    :param model:
    :param attribute_key:
    :return: Q object with filtering conditions for '-' group
    """
    res_attr = attribute_key

    if attr_is_relation(content_type_key, res_attr):
        res_attr = f"{res_attr}__user_code"

    q = Q(**{f"{res_attr}__isnull": True})

    '''
    TODO: move rest of models from front end to backend
    use them to determine whether attribute
    contains number or date
    '''
    try:
        field = model._meta.get_field(attribute_key)
    except (FieldDoesNotExist, AttributeError) as e:
        raise e

    field_type = field.get_internal_type()
    value_type = None

    if 'Date' in field_type:
        value_type = 40
    else:
        for type_part in ['Float', 'Integer']:
            if type_part in field_type:
                value_type = 20
                break

    # TODO: remove block bellow after separating 0 and '-'
    if value_type == 20:
        q = Q(q | Q(**{res_attr: 0}))

    elif value_type != 40:
        # value_type is 10 or 30
        q = Q(q | Q(**{res_attr: '-'}))

    return q


def get_q_obj_for_attribute_type(attribute_type, group_value):
    """

    :param attribute_type:
    :param group_value:
    :return: Q object with filtering conditions for grouping by GenericAttribute
    """
    q = Q()

    if attribute_type.value_type in {10, 20, 30, 40}:
        q = Q(attributes__attribute_type=attribute_type)
    else:
        _l.error(f"Attribute with invalid value_type passed: {attribute_type.value_type}")
        return q

    if attribute_type.value_type == 20:

        if group_value == "-":
            # TODO: remove Q(attributes__value_float=0) after separating 0 and '-'
            q = q & Q(Q(attributes__value_float__isnull=True) | Q(attributes__value_float=0))

        else:
            q = q & Q(attributes__value_float=group_value)

    elif attribute_type.value_type == 10:

        if group_value == '-':
            q = q & Q(Q(attributes__value_string__isnull=True) | Q(attributes__value_string='-'))

        else:
            q = q & Q(Q(attributes__value_string=group_value))

    elif attribute_type.value_type == 30:

        if group_value == '-':
            q = q & Q(Q(attributes__classifier__isnull=True) | Q(attributes__classifier__name='-'))

        else:
            q = q & Q(Q(attributes__classifier=group_value))


    elif attribute_type.value_type == 40:

        if group_value == '-':
            q = q & Q(attributes__value_date__isnull=True)
        else:
            q = q & Q(attributes__value_date=group_value)

    return q


def filter_items_for_group(queryset, groups_types, groups_values, content_type_key, model=None):
    """
    :param queryset:
    :type queryset: object
    :param groups_types: List of attribute types that are used for grouping
    :type groups_types: list
    :param groups_values: List of group names
    :type groups_values: list
    :param model:
    :type model: object|None
    :param content_type_key:
    :type content_type_key: str
    :return object: filtered queryset
    """
    if len(groups_types) and len(groups_values):
        for i, attr in enumerate(groups_types):
            if len(groups_values) > i:
                if attr.isdigit():

                    attribute_type = GenericAttributeType.objects.get(id__exact=attr)

                    q = get_q_obj_for_attribute_type(attribute_type, groups_values[i])

                    if q != Q():
                        queryset = queryset.filter(q)

                elif groups_values[i] == "-":

                    q = get_q_obj_for_group_dash(
                        content_type_key,
                        model,
                        attr
                    )

                    queryset = queryset.filter(q)

                else:
                    params = {}

                    if attr_is_relation(content_type_key, attr):
                        params[f"{attr}__user_code"] = groups_values[i]
                    else:
                        params[attr] = groups_values[i]

                    queryset = queryset.filter(**params)

    return queryset


def _filter_queryset_for_attribute(self_obj, request, queryset, view):
    groups_types = request.data.get("groups_types", [])
    groups_values = request.data.get("groups_values", [])

    master_user = request.user.master_user

    if hasattr(view.serializer_class, "Meta"):
        model = view.serializer_class.Meta.model
    else:
        return queryset

    content_type = ContentType.objects.get(
        app_label=model._meta.app_label, model=model._meta.model_name
    )

    content_type_key = f"{content_type.app_label}.{content_type.model}"

    groups_types = list(
        map(
            lambda x: self_obj.format_groups(x, master_user, content_type), groups_types
        )
    )

    return filter_items_for_group(
        queryset,
        groups_types,
        groups_values,
        content_type_key,
        model
    )


class GroupsAttributeFilter(BaseFilterBackend):
    def format_groups(self, group_type, master_user, content_type):
        if "attributes." in group_type:
            attribute_type = GenericAttributeType.objects.get(
                user_code__exact=group_type.split("attributes.")[1],
                master_user=master_user,
                content_type=content_type,
            )

            return str(attribute_type.id)

        return group_type

    def filter_queryset(self, request, queryset, view):
        return _filter_queryset_for_attribute(self, request, queryset, view)


class AttributeFilter(BaseFilterBackend):
    def format_groups(self, group_type, master_user, content_type):
        if "attributes." in group_type:
            attribute_type = GenericAttributeType.objects.get(
                user_code__exact=group_type.split("attributes.")[1],
                master_user=master_user,
                content_type=content_type,
            )

            return str(attribute_type.id)

        return group_type

    def filter_queryset(self, request, queryset, view):
        return _filter_queryset_for_attribute(self, request, queryset, view)


class ClassifierFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # queryset = queryset.prefetch_related('parent', 'children')
        if view and view.action == "list":
            return queryset.filter(parent__isnull=True)
        return queryset.prefetch_related("parent", "children")


class ClassifierRootFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(parent__isnull=True)


class ClassifierPrefetchFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.prefetch_related("parent", "children")


class AbstractClassifierFilterSet(FilterSet):
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()

    class Meta:
        fields = ["user_code", "name", "short_name"]

    def parent_filter(self, qs, value):
        return qs


class IsDefaultFilter(django_filters.BooleanFilter):
    def __init__(self, *args, **kwargs):
        self.source = kwargs.pop("source")
        super(IsDefaultFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in ([], (), {}, None, ""):
            return qs
        if self.distinct:
            qs = qs.distinct()
        if value is None:
            return qs
        elif value:
            return qs.filter(**{"pk": F(f"master_user__{self.source}__id")})
        else:
            return qs.exclude(**{"pk": F(f"master_user__{self.source}__id")})


class OrderingPostFilter(BaseFilterBackend):
    # The URL query parameter used for the ordering.
    ordering_param = api_settings.ORDERING_PARAM
    ordering_fields = None
    template = "rest_framework/filters/ordering.html"

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
            fields = [param.strip() for param in params.split(",")]
            ordering = self.remove_invalid_fields(queryset, fields, view)
            if ordering:
                return ordering

        # No ordering was included, or all the ordering fields were invalid
        return self.get_default_ordering(view)

    def get_default_ordering(self, view):
        ordering = getattr(view, "ordering", None)
        return (ordering,) if isinstance(ordering, string_types) else ordering

    def get_default_valid_fields(self, queryset, view):
        # If `ordering_fields` is not specified, then we determine a default
        # based on the serializer class, if one exists on the view.
        if hasattr(view, "get_serializer_class"):
            try:
                serializer_class = view.get_serializer_class()
            except AssertionError:
                # Raised by the default implementation if
                # no serializer_class was found
                serializer_class = None
        else:
            serializer_class = getattr(view, "serializer_class", None)

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
            if not getattr(field, "write_only", False) and field.source != "*"
        ]

    def get_valid_fields(self, queryset, view):
        valid_fields = getattr(view, "`ing_fields", self.ordering_fields)

        if valid_fields is None:
            # Default to allowing filtering on serializer fields
            return self.get_default_valid_fields(queryset, view)

        elif valid_fields == "__all__":
            # View explicitly allows filtering on any model field
            valid_fields = [
                (field.name, field.verbose_name)
                for field in queryset.model._meta.fields
            ]
            valid_fields += [
                (key, key.title().split("__"))
                for key in queryset.query.annotations.keys()
            ]
        else:
            valid_fields = [
                (item, item) if isinstance(item, string_types) else item
                for item in valid_fields
            ]

        return valid_fields

    def remove_invalid_fields(self, queryset, fields, view):
        valid_fields = [item[0] for item in self.get_valid_fields(queryset, view)]
        return [term for term in fields if term.lstrip("-") in valid_fields]

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)

        return queryset.order_by(*ordering) if ordering else queryset

    def get_template_context(self, request, queryset, view):
        current = self.get_ordering(request, queryset, view)
        current = None if current is None else current[0]
        options = []
        for key, label in self.get_valid_fields(queryset, view):
            options.extend(
                [
                    (key, f'{label} - {_("ascending")}'),
                    (f"-{key}", f'{label} - {_("descending")}'),
                ]
            )
        return {
            "request": request,
            "current": current,
            "param": self.ordering_param,
            "options": options,
        }

    def get_fields(self, view):
        return [self.ordering_param]


class EntitySpecificFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if not view.detail:
            is_disabled = False
            is_deleted = False
            is_inactive = False
            is_active = False

            if (
                    "ev_options" in request.data
                    and "entity_filters" in request.data["ev_options"]
            ):
                if "disabled" in request.data["ev_options"]["entity_filters"]:
                    is_disabled = True

                if "deleted" in request.data["ev_options"]["entity_filters"]:
                    is_deleted = True

                if "inactive" in request.data["ev_options"]["entity_filters"]:
                    is_inactive = True

                if "active" in request.data["ev_options"]["entity_filters"]:
                    is_active = True

            # Show Disabled
            if not is_disabled:
                queryset = queryset.filter(is_enabled=True)

            # Show Deleted
            if not is_deleted:
                queryset = queryset.filter(is_deleted=False)

            if is_inactive == False and is_active == True:
                try:
                    field = queryset.model._meta.get_field("is_active")

                    queryset = queryset.filter(is_active=True)
                except FieldDoesNotExist:
                    pass

            if not is_active and is_inactive:
                try:
                    field = queryset.model._meta.get_field("is_active")

                    queryset = queryset.filter(is_active=False)
                except FieldDoesNotExist:
                    pass

        return queryset


class ComplexTransactionStatusFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        from poms.transactions.models import ComplexTransaction

        if not view.detail:
            show_booked = False
            show_ignored = False

            if (
                    "ev_options" in request.data
                    and "complex_transaction_filters" in request.data["ev_options"]
            ):
                if (
                        "booked"
                        in request.data["ev_options"]["complex_transaction_filters"]
                ):
                    show_booked = True

                if (
                        "ignored"
                        in request.data["ev_options"]["complex_transaction_filters"]
                ):
                    show_ignored = True

            if show_booked == False and show_ignored == True:
                try:
                    queryset = queryset.filter(status=ComplexTransaction.IGNORE)
                except FieldDoesNotExist:
                    pass

            if show_booked and not show_ignored:
                try:
                    queryset = queryset.filter(
                        status__in=[
                            ComplexTransaction.PRODUCTION,
                            ComplexTransaction.PENDING,
                        ]
                    )
                except FieldDoesNotExist:
                    pass

        # Important, we could find deleted transactions only via recycle bin
        queryset = queryset.filter(is_deleted=False)

        return queryset


class GlobalTableSearchFilter(django_filters.CharFilter):
    def filter(self, qs, value):
        if not value:
            return qs

        # Create a Q object for each text field you want to search in
        queries = [Q(**{f"{field_name}__icontains": value}) for field_name in self.get_text_fields(qs.model)]

        # Combine the Q objects using OR operator
        query = queries.pop()

        for item in queries:
            query |= item

        # Filter the queryset
        return qs.filter(query).distinct()

    def get_text_fields(self, model):
        # This method should return the list of text field names that you want to search in
        text_fields = [f.name for f in model._meta.fields if
                       isinstance(f, (models.CharField, models.TextField, models.DateField, models.IntegerField))]
        return text_fields
