from poms.obj_attrs.models import GenericAttribute, GenericAttributeType

from django.db.models import Count, Sum, F, Value
from django.db.models.functions import Lower


def get_root_dynamic_attr_group(qs, root_group, groups_order):
    attribute_type = GenericAttributeType.objects.get(id=root_group)

    attr_qs = GenericAttribute.objects.filter(attribute_type=attribute_type)

    print(attribute_type.value_type)

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

    # if attribute_type.value_type == 30:
    #     qs = qs.order_by('attributes__classifier') \
    #         .distinct('attributes__classifier', 'attributes__attribute_type__name') \
    #         .annotate(group_name=F('attributes__classifier')) \
    #         .values('group_name')

    if attribute_type.value_type == 40:
        qs = qs.distinct('attributes__value_date') \
            .order_by('-attributes__value_date') \
            .annotate(group_name=F('attributes__value_date')) \
            .values('group_name')

    print(qs)

    if groups_order == 'asc':
        qs = qs.order_by(F('group_name').asc())
    if groups_order == 'desc':
        qs = qs.order_by(F('group_name').desc())

    return qs


def get_root_system_attr_group(qs, root_group, groups_order):
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

    # print('get_last_dynamic_attr_group %s' % attribute_type.name)

    qs = qs.filter(attributes__attribute_type=attribute_type)

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

    # if attribute_type.value_type == 30:
    #     qs = qs.order_by('attributes__classifier') \
    #         .distinct('attributes__classifier', 'attributes__attribute_type__name') \
    #         .annotate(group_name=F('attributes__classifier')) \
    #         .values('group_name')

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
    print('last group %s' % last_group)
    print(qs)

    qs = qs.distinct(last_group) \
        .annotate(group_name=F(last_group)) \
        .values('group_name')

    if groups_order == 'desc':
        qs = qs.order_by(F('group_name').desc())
    else :
        qs = qs.order_by(F('group_name').asc())

    return qs


def get_queryset_filters(qs, groups_types, groups_values):
    print('groups_values %s ' % groups_values)

    i = 0

    for attr in groups_types:

        if attr.isdigit():

            attribute_type = GenericAttributeType.objects.get(id=attr)

            print('attribute_type.value_type %s' % attribute_type.value_type)

            qs = qs.filter(attributes__attribute_type=attribute_type)

            # print(attribute_type.value_type)
            # print('i %s' % i)
            # print('groups_values %s' % len(groups_values))

            if attribute_type.value_type == 20 and len(groups_values) > i:
                qs = qs.filter(attributes__value_float=groups_values[i])

            if attribute_type.value_type == 10 and len(groups_values) > i:
                qs = qs.filter(attributes__value_string=groups_values[i])

            if attribute_type.value_type == 30 and len(groups_values) > i:
                qs = qs.filter(attributes__classifier=groups_values[i])

            if attribute_type.value_type == 40 and len(groups_values) > i:
                print(groups_values[i])
                qs = qs.filter(attributes__value_date=groups_values[i])

        else:

            if len(groups_values) > i:

                params = {}

                params[attr] = groups_values[i]

                qs = qs.filter(**params)

        i = i + 1

    print('i %s' % i)
    print('qs11 %s' % qs)

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

        print(qs)

        print('here ')

        qs = get_queryset_filters(qs, groups_types, groups_values)

        if is_dynamic_attribute(groups_types[-1]):

            qs = get_last_dynamic_attr_group(qs, last_group=groups_types[-1], groups_order=groups_order)

        else:

            qs = get_last_system_attr_group(qs, last_group=groups_types[-1], groups_order=groups_order)

    return qs
