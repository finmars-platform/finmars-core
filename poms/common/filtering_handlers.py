from poms.common.utils import force_qs_evaluation
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType

from django.db.models import Count, Sum, F, Value, Aggregate
from django.db.models.functions import Lower

from django.db.models import CharField, Case, When
from django.db.models.functions import Coalesce
from django.contrib.contenttypes.models import ContentType

from datetime import date, timedelta, datetime

from django.db.models import Q

import time


class ValueType:
    STRING = '10'
    NUMBER = '20'
    DATE = '40'
    FIELD = 'field'


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


def add_dynamic_attribute_filter(qs, filter_config, master_user, content_type):

    filter_type = filter_config['filter_type']
    value_type = int(filter_config['value_type'])
    value = None

    exclude_empty_cells = filter_config['exclude_empty_cells']

    source_key = filter_config['key']
    attribute_type_user_code = source_key.split('attributes.')[1]

    attribute_type = GenericAttributeType.objects.get(user_code=attribute_type_user_code, content_type=content_type,
                                                      master_user=master_user)

    attributes_qs = GenericAttribute.objects.filter(attribute_type=attribute_type)

    # STRING FILTERS START

    if filter_type == FilterType.CONTAINS and int(value_type) == ValueType.STRING:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            if attribute_type.value_type == GenericAttributeType.CLASSIFIER:

                options = {}
                options['classifier__name__icontains'] = value

                include_null_options = {}
                if not exclude_empty_cells:
                    include_null_options['classifier__isnull'] = True
                    include_null_options['value_string__isnull'] = True
                    include_null_options['value_float__isnull'] = True
                    include_null_options['value_date__isnull'] = True


                attributes_qs = attributes_qs.filter(Q(**options) | Q(**include_null_options))

            else:

                options = {}
                options['value_string__icontains'] = value

                include_null_options = {}
                include_empty_string_options = {}
                if not exclude_empty_cells:
                    include_null_options['value_string__isnull'] = True
                    include_empty_string_options['value_string'] = ''

                attributes_qs = attributes_qs.filter(Q(**options) | Q(**include_null_options) | Q(**include_empty_string_options))

    if filter_type == FilterType.DOES_NOT_CONTAINS and int(value_type) == ValueType.STRING:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            if attribute_type.value_type == GenericAttributeType.CLASSIFIER:

                options = {}
                options['classifier__name__icontains'] = value

                exclude_empty_cells_options = {}
                if exclude_empty_cells:
                    exclude_empty_cells_options['classifier__isnull'] = True

                attributes_qs = attributes_qs.exclude(Q(**options) | Q(**exclude_empty_cells_options))

            else:

                options = {}
                options['value_string__icontains'] = value

                exclude_empty_cells_options = {}
                exclude_null_options = {}
                if exclude_empty_cells:
                    exclude_null_options['classifier__isnull'] = True
                    exclude_empty_cells_options['value_string'] = ''

                attributes_qs = attributes_qs.exclude(Q(**options) | Q(**exclude_null_options) | Q(**exclude_empty_cells_options))

    if filter_type == FilterType.EMPTY and int(value_type) == ValueType.STRING:

        include_null_options = {}
        include_empty_string_options = {}

        include_null_options['value_string__isnull'] = True
        include_empty_string_options['value_string'] = ''

        attributes_qs = attributes_qs.filter(Q(**include_null_options) | Q(**include_empty_string_options))

    # STRING FILTERS END

    # NUMBER FILTERS START

    if filter_type == FilterType.EQUAL and value_type == ValueType.NUMBER:

        if len(filter_config['value']):
            value = int(filter_config['value'][0])

        if value:

            options = {}
            options['value_float__iexact'] = value

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options['value_float__isnull'] = True

            attributes_qs = attributes_qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.NOT_EQUAL and value_type == ValueType.NUMBER:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options['value_float__iexact'] = value

            exclude_empty_cells_options = {}
            if exclude_empty_cells:
                exclude_empty_cells_options['value_float__isnull'] = True

            attributes_qs = attributes_qs.exclude(Q(**options) | Q(**exclude_empty_cells_options))

    if filter_type == FilterType.GREATER and value_type == ValueType.NUMBER:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options['value_float__gt'] = value

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options['value_float__isnull'] = True

            attributes_qs = attributes_qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.GREATER_EQUAL and value_type == ValueType.NUMBER:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options['value_float__gte'] = value

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options['value_float__isnull'] = True

            attributes_qs = attributes_qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.LESS and value_type == ValueType.NUMBER:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options['value_float__lt'] = value

            include_null_options = {}

            if not exclude_empty_cells:
                include_null_options['value_float__isnull'] = True

            attributes_qs = attributes_qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.LESS_EQUAL and value_type == ValueType.NUMBER:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options['value_float__lte'] = value

            include_null_options = {}

            if not exclude_empty_cells:
                include_null_options['value_float__isnull'] = True

            attributes_qs = attributes_qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.FROM_TO and value_type == ValueType.NUMBER:

        max_value = filter_config['value']['max_value']
        min_value = filter_config['value']['min_value']

        if max_value is not None and min_value is not None:

            options = {}
            options['value_float__gte'] = min_value
            options['value_float__lte'] = max_value

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options['value_float__isnull'] = True

            attributes_qs = attributes_qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.EMPTY and int(value_type) == ValueType.NUMBER:
        include_null_options = {}

        include_null_options['value_float__isnull'] = True

        attributes_qs = attributes_qs.filter(Q(**include_null_options))

    # NUMBER FILTERS END

    # DATE FILTERS START

    if filter_type == FilterType.EQUAL and value_type == ValueType.DATE:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options['value_date'] = datetime.strptime(value, "%Y-%m-%d").date()

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options['value_date__isnull'] = True

            attributes_qs = attributes_qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.NOT_EQUAL and value_type == ValueType.DATE:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options['value_date'] = datetime.strptime(value, "%Y-%m-%d").date()

            exclude_empty_cells_options = {}
            if exclude_empty_cells:
                exclude_empty_cells_options['value_date__isnull'] = True

            attributes_qs = attributes_qs.exclude(Q(**options) | Q(**exclude_empty_cells_options))

    if filter_type == FilterType.GREATER and value_type == ValueType.DATE:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options['value_date__gt'] = datetime.strptime(value, "%Y-%m-%d").date()

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options['value_date__isnull'] = True

            attributes_qs = attributes_qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.GREATER_EQUAL and value_type == ValueType.DATE:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options['value_date__gte'] = datetime.strptime(value, "%Y-%m-%d").date()

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options['value_date__isnull'] = True

            attributes_qs = attributes_qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.LESS and value_type == ValueType.DATE:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options['value_date__lt'] = datetime.strptime(value, "%Y-%m-%d").date()

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options['value_date__isnull'] = True

            attributes_qs = attributes_qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.LESS_EQUAL and value_type == ValueType.DATE:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options['value_date__lte'] = datetime.strptime(value, "%Y-%m-%d").date()

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options['value_date__isnull'] = True

            attributes_qs = attributes_qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.FROM_TO and value_type == ValueType.DATE:

        max_value = filter_config['value']['max_value']
        min_value = filter_config['value']['min_value']

        if max_value and min_value:

            options = {}
            options['value_date__gte'] = datetime.strptime(min_value, "%Y-%m-%d").date()
            options['value_date__lte'] = datetime.strptime(max_value, "%Y-%m-%d").date()

            include_null_options = {}

            if not exclude_empty_cells:
                include_null_options['value_date__isnull'] = True

            attributes_qs = attributes_qs.filter(Q(**options) | Q(**include_null_options))

    if filter_type == FilterType.EMPTY and int(value_type) == ValueType.DATE:

        include_null_options = {}

        include_null_options['value_date__isnull'] = True

        attributes_qs = attributes_qs.filter(Q(**include_null_options))

    filtered_attributes_ids =  attributes_qs.values_list('object_id', flat=True)

    # print('filtered_attributes_ids %s ' % filtered_attributes_ids)

    qs = qs.filter(id__in=filtered_attributes_ids)

    return qs


def add_filter(qs, filter_config):
    # print('filter_config %s ' % filter_config)

    filter_type = filter_config['filter_type']
    value_type = str(filter_config['value_type'])
    key = filter_config['key']
    value = None

    # print('value_type %s' % value_type)
    # print('value_type %s' % type(value_type))

    exclude_empty_cells = filter_config['exclude_empty_cells']

    # FIELD FILTERS START

    if filter_type == FilterType.CONTAINS and value_type == ValueType.FIELD:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key + '__name__icontains'] = value

            include_null_options = {}
            include_empty_string_options = {}
            if not exclude_empty_cells:
                include_null_options[key + '__name__isnull'] = True
                include_empty_string_options[key + '__name'] = ''

            print('include_null_options %s' % include_null_options)
            print('options %s' % options)

            qs = qs.filter(Q(**options) | Q(**include_null_options) | Q(**include_empty_string_options))

    elif filter_type == FilterType.DOES_NOT_CONTAINS and value_type == ValueType.FIELD:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key + '__name__icontains'] = value

            exclude_nulls_options = {}
            exclude_empty_cells_options = {}
            if exclude_empty_cells:
                exclude_nulls_options[key + '__name__isnull'] = True
                exclude_empty_cells_options[key + '__name'] = ''

            qs = qs.exclude(Q(**options) | Q(**exclude_nulls_options) | Q(**exclude_empty_cells_options))

    elif filter_type == FilterType.EMPTY and value_type == ValueType.FIELD:
        include_null_options = {}
        include_empty_string_options = {}

        include_null_options[key + '__name__isnull'] = True
        include_empty_string_options[key + '__name'] = ''

        qs = qs.filter(Q(**include_null_options) | Q(**include_empty_string_options))

    # STRING FILTERS START

    elif filter_type == FilterType.CONTAINS and value_type == ValueType.STRING:

        # print('here?')

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key + '__icontains'] = value

            include_null_options = {}
            include_empty_string_options = {}
            if not exclude_empty_cells:
                include_null_options[key + '__isnull'] = True
                include_empty_string_options[key] = ''

            print('include_null_options %s' % include_null_options)
            print('options %s' % options)

            qs = qs.filter(Q(**options) | Q(**include_null_options) | Q(**include_empty_string_options))

    elif filter_type == FilterType.DOES_NOT_CONTAINS and value_type == ValueType.STRING:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key + '__icontains'] = value

            exclude_nulls_options = {}
            exclude_empty_cells_options = {}
            if exclude_empty_cells:
                exclude_nulls_options[key + '__isnull'] = True
                exclude_empty_cells_options[key] = ''

            qs = qs.exclude(Q(**options) | Q(**exclude_nulls_options) | Q(**exclude_empty_cells_options))

    elif filter_type == FilterType.EMPTY and value_type == ValueType.STRING:
        include_null_options = {}
        include_empty_string_options = {}

        include_null_options[key + '__isnull'] = True
        include_empty_string_options[key] = ''

        qs = qs.filter(Q(**include_null_options) | Q(**include_empty_string_options))

    # STRING FILTERS END

    # NUMBER FILTERS START

    elif filter_type == FilterType.EQUAL and value_type == ValueType.NUMBER:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key + '__iexact'] = value

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + '__isnull'] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.NOT_EQUAL and value_type == ValueType.NUMBER:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key + '__iexact'] = value

            exclude_empty_cells_options = {}
            if exclude_empty_cells:
                exclude_empty_cells_options[key + '__isnull'] = True

            print('exclude_empty_cells_options %s' % exclude_empty_cells_options)

            qs = qs.exclude(Q(**options) | Q(**exclude_empty_cells_options))

    elif filter_type == FilterType.GREATER and value_type == ValueType.NUMBER:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key + '__gt'] = value

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + '__isnull'] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.GREATER_EQUAL and value_type == ValueType.NUMBER:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key + '__gte'] = value

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + '__isnull'] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.LESS and value_type == ValueType.NUMBER:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key + '__lt'] = value

            include_null_options = {}

            if not exclude_empty_cells:
                include_null_options[key + '__isnull'] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.LESS_EQUAL and value_type == ValueType.NUMBER:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key + '__lte'] = value

            include_null_options = {}

            if not exclude_empty_cells:
                include_null_options[key + '__isnull'] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.FROM_TO and value_type == ValueType.NUMBER:

        max_value = filter_config['value']['max_value']
        min_value = filter_config['value']['min_value']

        if max_value is not None and min_value is not None:

            options = {}
            options[key + '__gte'] = min_value
            options[key + '__lte'] = max_value

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + '__isnull'] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.EMPTY and value_type == ValueType.NUMBER:

        include_null_options = {}
        include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**include_null_options) )

    # NUMBER FILTERS END

    # DATE FILTERS START

    elif filter_type == FilterType.EQUAL and value_type == ValueType.DATE:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key] = datetime.strptime(value, "%Y-%m-%d").date()

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + '__isnull'] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.NOT_EQUAL and value_type == ValueType.DATE:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key] = datetime.strptime(value, "%Y-%m-%d").date()

            exclude_empty_cells_options = {}
            if exclude_empty_cells:
                exclude_empty_cells_options[key + '__isnull'] = True

            qs = qs.exclude(Q(**options) | Q(**exclude_empty_cells_options))

    elif filter_type == FilterType.GREATER and value_type == ValueType.DATE:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key + '__gt'] = datetime.strptime(value, "%Y-%m-%d").date()

            print('options', options)

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + '__isnull'] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.GREATER_EQUAL and value_type == ValueType.DATE:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key + '__gte'] = datetime.strptime(value, "%Y-%m-%d").date()

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + '__isnull'] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.LESS and value_type == ValueType.DATE:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key + '__lt'] = datetime.strptime(value, "%Y-%m-%d").date()

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + '__isnull'] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.LESS_EQUAL and value_type == ValueType.DATE:

        if len(filter_config['value']):
            value = filter_config['value'][0]

        if value:

            options = {}
            options[key + '__lte'] = datetime.strptime(value, "%Y-%m-%d").date()

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + '__isnull'] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.FROM_TO and value_type == ValueType.DATE:

        max_value = filter_config['value']['max_value']
        min_value = filter_config['value']['min_value']

        if max_value and min_value:

            options = {}
            options[key + '__gte'] = datetime.strptime(min_value, "%Y-%m-%d").date()
            options[key + '__lte'] = datetime.strptime(max_value, "%Y-%m-%d").date()

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + '__isnull'] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.EMPTY and value_type == ValueType.DATE:
        include_null_options = {}

        include_null_options[key + '__isnull'] = True

        qs = qs.filter(Q(**include_null_options) )

    # DATE FILTERS END

    # print('qs len after filters %s' % len(list(qs)))

    return qs


def is_dynamic_attribute_filter(filter_config):
    key = filter_config['key']

    return 'attributes' in key


def handle_filters(qs, filter_settings, master_user, content_type):

    print('Handle filters %s' % filter_settings)

    start_time = time.time()

    if filter_settings:
        for filter_config in filter_settings:

            if is_dynamic_attribute_filter(filter_config):
                qs = add_dynamic_attribute_filter(qs, filter_config, master_user, content_type)
            else:
                qs = add_filter(qs, filter_config)

    print("handle_filters %s seconds " % (time.time() - start_time))

    return qs
