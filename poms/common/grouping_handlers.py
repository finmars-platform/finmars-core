from poms.common.utils import force_qs_evaluation
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType

from django.db.models import Count, Sum, F, Value, Aggregate
from django.db.models.functions import Lower

from django.db.models import CharField, Case, When
from django.db.models.functions import Coalesce
from django.contrib.contenttypes.models import ContentType

from django.db.models import Q

import time

import logging

_l = logging.getLogger('poms.common')


def get_root_dynamic_attr_group(qs, root_group, groups_order):
    start_time = time.time()

    attribute_type = GenericAttributeType.objects.get(id__exact=root_group)

    # attr_qs = GenericAttribute.objects.filter(attribute_type=attribute_type)

    # force_qs_evaluation(qs)

    qs = qs.filter(attributes__attribute_type=attribute_type)

    force_qs_evaluation(qs)

    # print('get_root_dynamic_attr_group len qs %s' % len(qs))

    # print('attribute_type.value_type %s' % attribute_type.value_type)

    if attribute_type.value_type == 20:
        qs = qs \
            .distinct('attributes__value_float') \
            .order_by('-attributes__value_float') \
            .annotate(group_name=F('attributes__value_float'), group_identifier=F('attributes__value_float')) \
            .values('group_name', 'group_identifier')

    if attribute_type.value_type == 10:
        qs = qs \
            .order_by('attributes__value_string') \
            .distinct('attributes__value_string') \
            .order_by('-attributes__value_string') \
            .annotate(group_name=F('attributes__value_string'), group_identifier=F('attributes__value_string')) \
            .values('group_name', 'group_identifier')

    if attribute_type.value_type == 30:
        qs = qs \
            .values('attributes__classifier') \
            .annotate(group_identifier=F('attributes__classifier')) \
            .distinct() \
            .annotate(group_name=F('attributes__classifier__name'), group_identifier=F('attributes__classifier')) \
            .values('group_name', 'group_identifier')

    if attribute_type.value_type == 40:
        qs = qs \
            .distinct('attributes__value_date') \
            .order_by('-attributes__value_date') \
            .annotate(group_name=F('attributes__value_date'), group_identifier=F('attributes__value_date')) \
            .values('group_name', 'group_identifier')

    force_qs_evaluation(qs)

    if groups_order == 'asc':
        qs = qs.order_by(F('group_name').asc())
    if groups_order == 'desc':
        qs = qs.order_by(F('group_name').desc())

    _l.debug("get_root_dynamic_attr_group %s seconds " % (time.time() - start_time))

    return qs


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


def get_root_system_attr_group(qs, root_group, groups_order):
    if is_relation(root_group):
        qs = qs.values(root_group) \
            .annotate(group_identifier=F(root_group + '__user_code')) \
            .distinct() \
            .annotate(group_name=F(root_group + '__short_name')) \
            .values('group_name', 'group_identifier')
    elif is_system_relation(root_group):
        qs = qs.values(root_group) \
            .annotate(group_identifier=F(root_group + '__system_code')) \
            .distinct() \
            .annotate(group_name=F(root_group + '__name')) \
            .values('group_name', 'group_identifier')
    elif is_scheme(root_group):
        qs = qs.values(root_group) \
            .annotate(group_identifier=F(root_group + '__scheme_name')) \
            .distinct() \
            .annotate(group_name=F(root_group + '__scheme_name')) \
            .values('group_name', 'group_identifier')
    else:
        qs = qs.distinct(root_group) \
            .annotate(group_name=F(root_group), group_identifier=F(root_group)) \
            .values('group_name', 'group_identifier') \
            .order_by(root_group)

    if groups_order == 'asc':
        qs = qs.order_by(F('group_name').asc())
    if groups_order == 'desc':
        qs = qs.order_by(F('group_name').desc())

    return qs


def get_last_dynamic_attr_group(qs, last_group, groups_order):
    start_time = time.time()

    # print('get_last_dynamic_attr_group qs len %s' % len(qs))
    # print("get_last_dynamic_attr_group dynamic attr id %s " % last_group)

    # force_qs_evaluation(qs)

    attribute_type = GenericAttributeType.objects.get(id__exact=last_group)

    qs = qs.filter(attributes__attribute_type=attribute_type)

    # print('get_last_dynamic_attr_group.attribute_type %s ' % attribute_type)
    # print('get_last_dynamic_attr_group.attribute_type.value_type %s ' % attribute_type.value_type)

    # print('get_last_dynamic_attr_group len %s' % len(qs))

    force_qs_evaluation(qs)

    if attribute_type.value_type == 20:
        qs = qs \
            .distinct('attributes__value_float') \
            .order_by('-attributes__value_float') \
            .annotate(group_name=F('attributes__value_float'), group_identifier=F('attributes__value_float')) \
            .values('group_name', 'group_identifier')

    if attribute_type.value_type == 10:
        qs = qs \
            .distinct('attributes__value_string') \
            .order_by('-attributes__value_string') \
            .annotate(group_name=F('attributes__value_string'), group_identifier=F('attributes__value_string')) \
            .values('group_name', 'group_identifier')

    if attribute_type.value_type == 30:
        qs = qs \
            .values('attributes__classifier') \
            .annotate(group_identifier=F('attributes__classifier')) \
            .distinct() \
            .annotate(group_name=F('attributes__classifier__name')) \
            .values('group_name', 'group_identifier')

    if attribute_type.value_type == 40:
        qs = qs \
            .distinct('attributes__value_date') \
            .order_by('-attributes__value_date') \
            .annotate(group_name=F('attributes__value_date'), group_identifier=F('attributes__value_date')) \
            .values('group_name', 'group_identifier')

    force_qs_evaluation(qs)

    if groups_order == 'asc':
        qs = qs.order_by(F('group_name').asc())
    if groups_order == 'desc':
        qs = qs.order_by(F('group_name').desc())

    _l.debug("get_last_dynamic_attr_group %s seconds " % (time.time() - start_time))

    return qs


def get_last_system_attr_group(qs, last_group, groups_order):
    print('last_group %s ' % last_group)

    if is_relation(last_group):
        qs = qs.values(last_group) \
            .annotate(group_identifier=F(last_group + '__user_code')) \
            .distinct() \
            .annotate(group_name=F(last_group + '__short_name')) \
            .values('group_name', 'group_identifier')

    elif is_system_relation(last_group):
        qs = qs.values(last_group) \
            .annotate(group_identifier=F(last_group + '__system_code')) \
            .distinct() \
            .annotate(group_name=F(last_group + '__name')) \
            .values('group_name', 'group_identifier')
    elif is_scheme(last_group):
        qs = qs.values(last_group) \
            .annotate(group_identifier=F(last_group + '__scheme_name')) \
            .distinct() \
            .annotate(group_name=F(last_group + '__scheme_name')) \
            .values('group_name', 'group_identifier')
    else:

        qs = qs.distinct(last_group) \
            .annotate(group_name=F(last_group), group_identifier=F(last_group)) \
            .values('group_name', 'group_identifier')

    if groups_order == 'desc':
        qs = qs.order_by(F('group_name').desc())
    else:
        qs = qs.order_by(F('group_name').asc())

    return qs


def get_queryset_filters(qs, groups_types, groups_values, original_qs):
    start_time = time.time()

    i = 0

    # print('get_queryset_filters len %s' % len(qs    ))

    force_qs_evaluation(qs)

    groups_values_count = len(groups_values)

    for attr in groups_types:

        if attr.isdigit():

            if groups_values_count > i:

                attribute_type = GenericAttributeType.objects.get(id__exact=attr)

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

        else:

            if groups_values_count > i:

                params = {}

                if groups_values[i] == '-':

                    res_attr = attr

                    if is_relation(res_attr):
                        res_attr = res_attr + '__user_code'
                    elif is_system_relation(attr):
                        res_attr = res_attr + '__system_code'
                    elif is_scheme(attr):
                        res_attr = res_attr + '__scheme_name'

                    qs = qs.filter(Q(**{res_attr + '__isnull': True}) | Q(**{res_attr: '-'}))

                else:
                    if is_relation(attr):
                        params[attr + '__user_code'] = groups_values[i]
                    elif is_system_relation(attr):
                        params[attr + '__system_code'] = groups_values[i]
                    elif is_scheme(attr):
                        params[attr + '__scheme_name'] = groups_values[i]
                    else:
                        params[attr] = groups_values[i]

                    qs = qs.filter(**params)

        force_qs_evaluation(qs)

        i = i + 1

    _l.debug("get_queryset_filters %s seconds " % (time.time() - start_time))

    # original_qs = original_qs.filter(id__in=qs)

    return qs


def is_dynamic_attribute(item):
    return item.isdigit()


def is_root_groups_configuration(groups_types, groups_values):
    return len(groups_types) == 1 and not len(groups_values)


def format_groups(group_type, master_user, content_type):
    if 'attributes.' in group_type:
        attribute_type = GenericAttributeType.objects.get(user_code__exact=group_type.split('attributes.')[1],
                                                          master_user=master_user, content_type=content_type)

        return str(attribute_type.id)

    return group_type


def handle_groups(qs, groups_types, groups_values, groups_order, master_user, original_qs, content_type):
    start_time = time.time()

    groups_types = list(map(lambda x: format_groups(x, master_user, content_type), groups_types))

    # print('handle_groups.group_types %s' % groups_types)
    # print('handle_groups.groups_values %s' % groups_values)
    # print('handle_groups.groups_order %s' % groups_order)
    # print('handle_groups.queryset len %s' % len(qs))

    if is_root_groups_configuration(groups_types, groups_values):

        if is_dynamic_attribute(groups_types[0]):

            qs = get_root_dynamic_attr_group(qs, root_group=groups_types[0], groups_order=groups_order)


        else:

            qs = get_root_system_attr_group(qs, root_group=groups_types[0], groups_order=groups_order)

    else:

        qs = get_queryset_filters(qs, groups_types, groups_values, original_qs)

        # print('handle groups after filters qs len %s' % len(qs))
        # print('handle groups after filters qs len %s' % qs)

        if is_dynamic_attribute(groups_types[-1]):

            qs = get_last_dynamic_attr_group(qs, last_group=groups_types[-1], groups_order=groups_order)

        else:

            qs = get_last_system_attr_group(qs, last_group=groups_types[-1], groups_order=groups_order)

    # print('handle_groups  %s' % qs)

    _l.debug("handle_groups %s seconds " % (time.time() - start_time))

    return qs
