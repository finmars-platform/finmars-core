from poms.common.utils import force_qs_evaluation
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType

from django.db.models import Count, Sum, F, Value, Aggregate
from django.db.models.functions import Lower

from django.db.models import CharField, Case, When
from django.db.models.functions import Coalesce
from django.contrib.contenttypes.models import ContentType

from django.db.models import Q

import time


class ValueType:
    STRING = 10
    NUMBER = 20
    DATE = 40


class FilterType:
    EMPTY = 'empty'
    CONTAINS = 'contains'
    DOES_NOT_CONTAINS = 'does_not_contains'
    FROM_TO = 'from_to'
    EQUAL = 'equal'
    NOT_EQUAL = 'not_equal'
    GREATER = 'greater'
    GREATER_EQUAL = 'greater_equal'
    LESS = 'less'
    LESS_EQUAL = 'less_equal'


def add_filter(qs, filter_config):
    print('filter_config %s ' % filter_config)

    filter_type = filter_config['filter_type']
    value_type = int(filter_config['value_type'])
    key = filter_config['key']

    exclude_empty_cells = filter_config['exclude_empty_cells']

    print('filter_type %s' % filter_type)
    print('value_type %s' % value_type)
    print('exclude_empty_cells %s' % exclude_empty_cells)

    print('qs len before filters %s' % len(list(qs)))

    # STRING FILTERS START

    if filter_type == FilterType.CONTAINS and int(value_type) == ValueType.STRING:

        value = filter_config['value'][0]

        options = {}
        options[key + '__contains'] = value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.DOES_NOT_CONTAINS and int(value_type) == ValueType.STRING:

        value = filter_config['value'][0]

        options = {}
        options[key + '__contains'] =  value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.exclude(Q(**options)).filter(Q(**include_null_options))

    if filter_type == FilterType.EMPTY and int(value_type) == ValueType.STRING:

        options = {}
        options[key + '__isnull'] = True

        qs = qs.filter(Q(**options))

    # STRING FILTERS END

    # NUMBER FILTERS START

    if filter_type == FilterType.EQUAL and value_type == ValueType.NUMBER:

        value = filter_config['value'][0]

        options = {}
        options[key] = value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.NOT_EQUAL and value_type == ValueType.NUMBER:

        value = filter_config['value'][0]

        options = {}
        options[key] = value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.exclude(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.GREATER and value_type == ValueType.NUMBER:

        value = filter_config['value'][0]

        options = {}
        options[key + '__gt'] = value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.GREATER_EQUAL and value_type == ValueType.NUMBER:

        value = filter_config['value'][0]

        options = {}
        options[key + '__gte'] = value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.LESS and value_type == ValueType.NUMBER:

        value = filter_config['value'][0]

        options = {}
        options[key + '__lt'] = value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.LESS_EQUAL and value_type == ValueType.NUMBER:

        value = filter_config['value'][0]

        options = {}
        options[key + '__lte'] = value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.FROM_TO and value_type == ValueType.NUMBER:

        max_value = filter_config['value']['max_value']
        min_value = filter_config['value']['min_value']

        options = {}
        options[key + '__gte'] =  min_value
        options[key + '__lte'] =  max_value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.EMPTY and int(value_type) == ValueType.NUMBER:

        options = {}
        options[key + '__isnull'] = True

        qs = qs.filter(Q(**options))

    # NUMBER FILTERS END

    # DATE FILTERS START

    if filter_type == FilterType.EQUAL and value_type == ValueType.DATE:

        value = filter_config['value'][0]

        options = {}
        options[key] = value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.NOT_EQUAL and value_type == ValueType.DATE:

        value = filter_config['value'][0]

        options = {}
        options[key] = value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.exclude(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.GREATER and value_type == ValueType.DATE:

        value = filter_config['value'][0]

        options = {}
        options[key + '__gt'] = value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.GREATER_EQUAL and value_type == ValueType.DATE:

        value = filter_config['value'][0]

        options = {}
        options[key + '__gte'] = value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.LESS and value_type == ValueType.DATE:

        value = filter_config['value'][0]

        options = {}
        options[key + '__lt'] = value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.LESS_EQUAL and value_type == ValueType.DATE:

        value = filter_config['value'][0]

        options = {}
        options[key + '__lte'] = value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.FROM_TO and value_type == ValueType.DATE:

        max_value = filter_config['value']['max_value']
        min_value = filter_config['value']['min_value']

        options = {}
        options[key + '__gte'] =  min_value
        options[key + '__lte'] =  max_value

        include_null_options = {}
        if not exclude_empty_cells:
            include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.EMPTY and int(value_type) == ValueType.DATE:

        options = {}
        options[key + '__isnull'] = True

        qs = qs.filter(Q(**options))

    # DATE FILTERS END

    print('qs len after filters %s' % len(list(qs)))

    return qs


def handle_filters(qs, filter_settings):
    start_time = time.time()

    if filter_settings:
        for filter_config in filter_settings:
            qs = add_filter(qs, filter_config)

    print("handle_filters %s seconds " % (time.time() - start_time))

    return qs
