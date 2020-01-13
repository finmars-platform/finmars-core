from django.db.models import Case, When

from poms.obj_attrs.models import GenericAttributeType, GenericAttribute

from django.db.models import Value
from django.db.models.functions import Coalesce

import math

from django.db.models.functions import Lower

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

def sort_by_dynamic_attrs(queryset, ordering, master_user, content_type):
    print('sort_by_dynamic_attrs.ordering %s' % ordering)

    parts = ordering.split('attributes.')

    if parts and len(parts) == 2:

        order = parts[0]
        key = parts[1]

        print('order %s' % order)
        print('key %s' % key)

        attribute_type = GenericAttributeType.objects.get(user_code__exact=key, master_user=master_user,
                                                          content_type=content_type)

        attributes_queryset = GenericAttribute.objects.filter(attribute_type=attribute_type, object_id__in=queryset)

        print('attribute_type.value_type1 %s' % attribute_type.value_type)

        if order == '-':

            if attribute_type.value_type == 10:
                attributes_queryset = attributes_queryset.annotate(value_string_null=
                                                                   Coalesce('value_string', Value(''))).order_by(
                    '-value_string_null')
            if attribute_type.value_type == 20:
                attributes_queryset = attributes_queryset.annotate(value_float_null=
                                                                   Coalesce('value_float',
                                                                            Value(-math.inf))).order_by(
                    '-value_float_null')

            if attribute_type.value_type == 30:
                attributes_queryset = attributes_queryset.annotate(classifier__name_null=
                                                                   Coalesce('classifier__name',
                                                                            Value('-'))).order_by(
                    '-classifier__name_null')

            if attribute_type.value_type == 40:
                attributes_queryset = attributes_queryset.annotate(value_date_null=
                                                                   Coalesce('value_date',
                                                                            Value('0001-01-01'))).order_by(
                    '-value_date_null')

        else:

            if attribute_type.value_type == 10:
                attributes_queryset = attributes_queryset.annotate(value_string_null=
                                                                   Coalesce('value_string', Value(''))).order_by(
                    'value_string_null')

            if attribute_type.value_type == 20:
                attributes_queryset = attributes_queryset.annotate(value_float_null=
                                                                   Coalesce('value_float',
                                                                            Value(-math.inf))).order_by(
                    'value_float_null')

            if attribute_type.value_type == 30:
                attributes_queryset = attributes_queryset.annotate(classifier__name_null=
                                                                   Coalesce('classifier__name',
                                                                            Value('-'))).order_by(
                    'classifier__name_null')

            if attribute_type.value_type == 40:
                attributes_queryset = attributes_queryset.annotate(value_date_null=
                                                                   Coalesce('value_date',
                                                                            Value('0001-01-01'))).order_by(
                    'value_date_null')

        # print('attributes_queryset %s' % attributes_queryset)

        # TODO refactor!

        result = []
        result_ids = []

        for a in attributes_queryset:

            for i in queryset:

                if a.object_id == i.id and a.object_id not in result_ids:
                    result_ids.append(i.id)
                    result.append(i)

        queryset = result
    else:

        print("ordering in system attrs %s" % ordering)

        if '-' in ordering:
            field = ordering.split('-')[1]
        else :
            field = ordering

        print('ordering field %s' % field)

        if is_relation(field):

            queryset = queryset.order_by(ordering + '__name')

        else:
            queryset = queryset.order_by(ordering)


    return queryset
