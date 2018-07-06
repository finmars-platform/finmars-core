from poms.common.utils import force_qs_evaluation
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType

from django.db.models import Count, Sum, F, Value, Aggregate
from django.db.models.functions import Lower

from django.db.models import CharField, Case, When
from django.db.models.functions import Coalesce


def get_root_dynamic_attr_group(qs, root_group, groups_order):
    attribute_type = GenericAttributeType.objects.get(id=root_group)

    attr_qs = GenericAttribute.objects.filter(attribute_type=attribute_type)

    qs = qs.filter(attributes__in=attr_qs)

    if attribute_type.value_type == 20:
        qs = qs.distinct('attributes__value_float') \
            .order_by('-attributes__value_float') \
            .annotate(group_name=F('attributes__value_float')) \
            .values('group_name')

    if attribute_type.value_type == 10:
        qs = qs.distinct('attributes__value_string') \
            .order_by('-attributes__value_string') \
            .annotate(group_name=F('attributes__value_string')) \
            .values('group_name')

    if attribute_type.value_type == 30:
        qs = qs.values('attributes__classifier') \
            .annotate(group_id=F('attributes__classifier')) \
            .distinct() \
            .annotate(group_name=F('attributes__classifier__name')) \
            .values('group_name', 'group_id')

    if attribute_type.value_type == 40:
        qs = qs.distinct('attributes__value_date') \
            .order_by('-attributes__value_date') \
            .annotate(group_name=F('attributes__value_date')) \
            .values('group_name')

    if groups_order == 'asc':
        qs = qs.order_by(F('group_name').asc())
    if groups_order == 'desc':
        qs = qs.order_by(F('group_name').desc())

    return qs


def get_root_system_attr_group(qs, root_group, groups_order):
    if root_group == 'type':

        qs = qs.values('type') \
            .annotate(group_id=F('type')) \
            .distinct() \
            .annotate(group_name=F('type__user_code')) \
            .values('group_name', 'group_id')
    else:

        qs = qs.distinct(root_group) \
            .annotate(group_name=F(root_group)) \
            .values('group_name') \
            .order_by(root_group)

    if groups_order == 'asc':
        qs = qs.order_by(F('group_name').asc())
    if groups_order == 'desc':
        qs = qs.order_by(F('group_name').desc())

    return qs


def get_last_dynamic_attr_group(qs, last_group, groups_order):
    attribute_type = GenericAttributeType.objects.get(id=last_group)

    attr_qs = GenericAttribute.objects.filter(attribute_type=attribute_type)

    qs = qs.filter(attributes__in=attr_qs)

    if attribute_type.value_type == 20:
        qs = qs.distinct('attributes__value_float') \
            .order_by('-attributes__value_float') \
            .annotate(group_name=F('attributes__value_float')) \
            .values('group_name')

    if attribute_type.value_type == 10:
        qs = qs.distinct('attributes__value_string') \
            .order_by('-attributes__value_string') \
            .annotate(group_name=F('attributes__value_string')) \
            .values('group_name')

    if attribute_type.value_type == 30:
        qs = qs.values('attributes__classifier') \
            .annotate(group_id=F('attributes__classifier')) \
            .distinct() \
            .annotate(group_name=F('attributes__classifier__name')) \
            .values('group_name', 'group_id')

    if attribute_type.value_type == 40:
        qs = qs.distinct('attributes__value_date') \
            .order_by('-attributes__value_date') \
            .annotate(group_name=F('attributes__value_date')) \
            .values('group_name')

    if groups_order == 'asc':
        qs = qs.order_by(F('group_name').asc())
    if groups_order == 'desc':
        qs = qs.order_by(F('group_name').desc())

    return qs


def get_last_system_attr_group(qs, last_group, groups_order):
    if last_group == 'type':

        qs = qs.values('type') \
            .annotate(group_id=F('type')) \
            .distinct() \
            .annotate(group_name=F('type__user_code')) \
            .values('group_name', 'group_id')
    else:

        qs = qs.distinct(last_group) \
            .annotate(group_name=F(last_group)) \
            .values('group_name')

    if groups_order == 'desc':
        qs = qs.order_by(F('group_name').desc())
    else:
        qs = qs.order_by(F('group_name').asc())

    return qs


def get_queryset_filters(qs, groups_types, groups_values):
    i = 0

    groups_values_count = len(groups_values)

    for attr in groups_types:

        if attr.isdigit():

            if groups_values_count > i:

                attribute_type = GenericAttributeType.objects.get(id=attr)

                if attribute_type.value_type == 20:

                    if groups_values[i] == '-':
                        qs = qs.filter(attributes__value_float__isnull=True,
                                       attributes__attribute_type=attribute_type)
                    else:
                        qs = qs.filter(attributes__value_float=groups_values[i],
                                       attributes__attribute_type=attribute_type)

                if attribute_type.value_type == 10:

                    if groups_values[i] == '-':
                        qs = qs.filter(attributes__value_string__isnull=True,
                                       attributes__attribute_type=attribute_type)
                    else:
                        qs = qs.filter(attributes__value_string=groups_values[i],
                                       attributes__attribute_type=attribute_type)

                if attribute_type.value_type == 30:

                    if groups_values[i] == '-':
                        qs = qs.filter(attributes__classifier__isnull=True,
                                       attributes__attribute_type=attribute_type)
                    else:
                        qs = qs.filter(attributes__classifier=groups_values[i],
                                       attributes__attribute_type=attribute_type)

                if attribute_type.value_type == 40:

                    if groups_values[i] == '-':
                        qs = qs.filter(attributes__value_date__isnull=True,
                                       attributes__attribute_type=attribute_type)
                    else:
                        qs = qs.filter(attributes__value_date=groups_values[i],
                                       attributes__attribute_type=attribute_type)

                force_qs_evaluation(qs)

        else:

            if groups_values_count > i:
                
                params = {}

                if groups_values[i] == '-':
                    params[attr + '_isnull'] = True
                else:
                    params[attr] = groups_values[i]

                qs = qs.filter(**params)

                force_qs_evaluation(qs)

        i = i + 1

    return qs


def is_dynamic_attribute(item):
    return item.isdigit()


def is_root_groups_configuration(groups_types, groups_values):
    return len(groups_types) == 1 and not len(groups_values)


def handle_groups(qs, request):
    groups_types = request.query_params.getlist('groups_types')
    groups_values = request.query_params.getlist('groups_values')
    groups_order = request.query_params.get('groups_order')

    print(groups_types)
    print(groups_values)
    print(groups_order)

    if is_root_groups_configuration(groups_types, groups_values):

        if is_dynamic_attribute(groups_types[0]):

            qs = get_root_dynamic_attr_group(qs, root_group=groups_types[0], groups_order=groups_order)

        else:

            qs = get_root_system_attr_group(qs, root_group=groups_types[0], groups_order=groups_order)

    else:

        qs = get_queryset_filters(qs, groups_types, groups_values)

        if is_dynamic_attribute(groups_types[-1]):

            qs = get_last_dynamic_attr_group(qs, last_group=groups_types[-1], groups_order=groups_order)

        else:

            qs = get_last_system_attr_group(qs, last_group=groups_types[-1], groups_order=groups_order)

    return qs
