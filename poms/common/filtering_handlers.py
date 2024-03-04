"""
Filtering of rows and groups for entity viewer
"""

import logging
import operator
import time
from datetime import datetime
from functools import reduce

from django.conf import settings
from django.db.models import (
    CharField,
    DateField,
    FloatField,
    ForeignKey,
    IntegerField,
    Q,
    TextField,
)

from dateutil.parser import parse

from poms.obj_attrs.models import GenericAttribute, GenericAttributeType

_l = logging.getLogger("poms.common")

DATE_FORMAT = settings.API_DATE_FORMAT


class ValueType:
    STRING = "10"
    NUMBER = "20"
    CLASSIFIER = "30"
    DATE = "40"
    BOOLEAN = "50"
    FIELD = "field"


class FilterType:
    EMPTY = "empty"
    CONTAINS = "contains"
    DOES_NOT_CONTAINS = "does_not_contains"
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    HAS_SUBSTRING = "contains_has_substring"
    FROM_TO = "from_to"
    OUT_OF_RANGE = "out_of_range"
    GREATER = "greater"
    GREATER_EQUAL = "greater_equal"
    LESS = "less"
    LESS_EQUAL = "less_equal"
    MULTISELECTOR = "multiselector"
    SELECTOR = "selector"
    DATE_TREE = "date_tree"

def _get_equal_q(field_key, value, exclude_empty_cells):
    """

    :param field_key:
    :param value:
    :param exclude_empty_cells:
    :return: Q object for filter type "equal"
    """
    q = Q(**{f"{field_key}__iexact": value})

    if not exclude_empty_cells:
        q = q | Q(**{f"{field_key}__isnull": True})

    return q

def _get_has_substring_q(field_key, value, exclude_empty_cells):
    """

    :param field_key:
    :param value:
    :param exclude_empty_cells:
    :return: Q object for filter type "contains_has_substring"
    """
    q = Q()
    substrings = value.split(" ")

    for text in substrings:
        q = q | Q(**{f"{field_key}__icontains": text})

    if not exclude_empty_cells:
        q = q | Q(**{f"{field_key}__isnull": True}) | Q(**{f"{field_key}": ""})

    return q

def _get_classifier_include_null_q(exclude_empty_cells):
    if exclude_empty_cells:
        return Q()

    return (
        Q(classifier__isnull=True) |
        Q(value_string__isnull=True) |
        Q(value_float__isnull=True) |
        Q(value_date__isnull=True)
    )

def add_dynamic_attribute_filter(qs, filter_config, master_user, content_type):
    filter_type = filter_config["filter_type"]
    value_type = str(filter_config["value_type"])
    value = None

    exclude_empty_cells = filter_config["exclude_empty_cells"]

    source_key = filter_config["key"]
    attribute_type_user_code = source_key.split("attributes.")[1]

    attribute_type = GenericAttributeType.objects.get(
        user_code=attribute_type_user_code,
        content_type=content_type,
        master_user=master_user,
    )

    attributes_qs = GenericAttribute.objects.filter(attribute_type=attribute_type)

    # print('attribute_type.value_type %s' % attribute_type.value_type)
    # print('value_type %s' % value_type)

    # region CLASSIFIER FILTERS START

    if filter_type == FilterType.MULTISELECTOR and value_type == ValueType.CLASSIFIER:
        print(filter_config["value"])

        if len(filter_config["value"]):
            values = filter_config["value"]
        else:
            values = []

        if values:
            clauses = []

            for value in values:
                clauses.append(Q(classifier__name__icontains=value))

            include_null_q = _get_classifier_include_null_q(exclude_empty_cells)

            clauses.append(include_null_q)

            query = reduce(operator.or_, clauses)

            attributes_qs = attributes_qs.filter(query)

    elif filter_type == FilterType.SELECTOR and value_type == ValueType.CLASSIFIER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"classifier__name__icontains": value}

            include_null_q = _get_classifier_include_null_q(exclude_empty_cells)

            attributes_qs = attributes_qs.filter(
                Q(**options) | include_null_q
            )

    elif filter_type == FilterType.EQUAL and value_type == ValueType.CLASSIFIER:
        if len(filter_config["value"]):
            value = int(filter_config["value"][0])

        if value:

            options = {"classifier__name__iexact": value}

            include_null_q = _get_classifier_include_null_q(exclude_empty_cells)

            attributes_qs = attributes_qs.filter(
                Q(**options) | include_null_q
            )

    elif filter_type == FilterType.HAS_SUBSTRING and value_type == ValueType.STRING:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            q = Q()
            substrings = value.split(" ")

            for text in substrings:
                q = q | Q(classifier__name__icontains=text)

            include_null_q = _get_classifier_include_null_q(exclude_empty_cells)

            q = q | include_null_q

            attributes_qs = attributes_qs.filter(q)

    elif filter_type == FilterType.CONTAINS and value_type == ValueType.CLASSIFIER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"classifier__name__icontains": value}

            # include_null_options = {}
            # if not exclude_empty_cells:
            #     include_null_options["classifier__isnull"] = True
            #     include_null_options["value_string__isnull"] = True
            #     include_null_options["value_float__isnull"] = True
            #     include_null_options["value_date__isnull"] = True
            include_null_q = _get_classifier_include_null_q(exclude_empty_cells)

            attributes_qs = attributes_qs.filter(
                Q(**options) | include_null_q
            )

    elif (
        filter_type == FilterType.DOES_NOT_CONTAINS
        and value_type == ValueType.CLASSIFIER
    ):
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"classifier__name__icontains": value}

            exclude_empty_cells_options = {}
            if exclude_empty_cells:
                exclude_empty_cells_options["classifier__isnull"] = True

            attributes_qs = attributes_qs.exclude(
                Q(**options) | Q(**exclude_empty_cells_options)
            )

    elif filter_type == FilterType.EMPTY and value_type == ValueType.CLASSIFIER:
        include_null_options = {}
        include_empty_string_options = {}

        include_null_options["value_string__isnull"] = True
        include_empty_string_options["value_string"] = ""

        attributes_qs = attributes_qs.filter(
            Q(**include_null_options) | Q(**include_empty_string_options)
        )

    # endregion CLASSIFIER FILTERS END

    # region STRING FILTERS START

    elif filter_type == FilterType.MULTISELECTOR and value_type == ValueType.STRING:
        print(filter_config["value"])

        if len(filter_config["value"]):
            values = filter_config["value"]
        else:
            values = []

        if values:
            clauses = []

            for value in values:
                clauses.append(Q(value_string__icontains=value))

            include_null_options = {}
            include_empty_string_options = {}
            if not exclude_empty_cells:
                include_null_options["value_string__isnull"] = True
                include_empty_string_options["value_string"] = ""

            clauses.append(Q(**include_null_options))
            clauses.append(Q(**include_empty_string_options))

            query = reduce(operator.or_, clauses)

            attributes_qs = attributes_qs.filter(query)

    elif filter_type == FilterType.SELECTOR and value_type == ValueType.STRING:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_string__icontains": value}

            include_null_options = {}
            include_empty_string_options = {}
            if not exclude_empty_cells:
                include_null_options["value_string__isnull"] = True
                include_empty_string_options["value_string"] = ""

            attributes_qs = attributes_qs.filter(
                Q(**options)
                | Q(**include_null_options)
                | Q(**include_empty_string_options)
            )

    elif filter_type == FilterType.CONTAINS and value_type == ValueType.STRING:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_string__icontains": value}

            include_null_options = {}
            include_empty_string_options = {}
            if not exclude_empty_cells:
                include_null_options["value_string__isnull"] = True
                include_empty_string_options["value_string"] = ""

            attributes_qs = attributes_qs.filter(
                Q(**options)
                | Q(**include_null_options)
                | Q(**include_empty_string_options)
            )

    elif filter_type == FilterType.DOES_NOT_CONTAINS and value_type == ValueType.STRING:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_string__icontains": value}

            exclude_empty_cells_options = {}
            exclude_null_options = {}
            if exclude_empty_cells:
                exclude_null_options["classifier__isnull"] = True
                exclude_empty_cells_options["value_string"] = ""

            attributes_qs = attributes_qs.exclude(
                Q(**options)
                | Q(**exclude_null_options)
                | Q(**exclude_empty_cells_options)
            )

    elif filter_type == FilterType.EQUAL and value_type == ValueType.STRING:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_string__iexact": value}

            include_null_options = {}
            include_empty_string_options = {}
            if not exclude_empty_cells:
                include_null_options["value_string__isnull"] = True
                include_empty_string_options["value_string"] = ""

            attributes_qs = attributes_qs.filter(
                Q(**options)
                | Q(**include_null_options)
                | Q(**include_empty_string_options)
            )

    elif filter_type == FilterType.HAS_SUBSTRING and value_type == ValueType.STRING:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            q = Q()
            substrings = value.split(" ")

            for text in substrings:
                q = q | Q(value_string__icontains=text)

            # TESTING464 TO DELETE
            #
            # include_null_options = {}
            # include_empty_string_options = {}
            # if not exclude_empty_cells:
            #     include_null_options["value_string__isnull"] = True
            #     include_empty_string_options["value_string"] = ""
            if not exclude_empty_cells:
                # include rows with null and empty string
                q = q | Q(value_string__isnull=True) | Q(value_string="")

            attributes_qs = attributes_qs.filter(q)

    elif filter_type == FilterType.EMPTY and value_type == ValueType.STRING:
        include_null_options = {"value_string__isnull": True}

        include_empty_string_options = {"value_string": ""}

        attributes_qs = attributes_qs.filter(
            Q(**include_null_options) | Q(**include_empty_string_options)
        )

    # endregion STRING FILTERS END

    # region NUMBER FILTERS START

    elif filter_type == FilterType.EQUAL and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = int(filter_config["value"][0])

        if value:
            # TESTING464
            #
            # options = {"value_float__exact": value}
            #
            # include_null_options = {}
            # if not exclude_empty_cells:
            #     include_null_options["value_float__isnull"] = True
            #
            # attributes_qs = attributes_qs.filter(
            #     Q(**options) | Q(**include_null_options)
            # )
            q = _get_equal_q("value_float", value, exclude_empty_cells)

            attributes_qs = attributes_qs.filter(q)

    elif filter_type == FilterType.NOT_EQUAL and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_float__exact": value}

            exclude_empty_cells_options = {}
            if exclude_empty_cells:
                exclude_empty_cells_options["value_float__isnull"] = True

            attributes_qs = attributes_qs.exclude(
                Q(**options) | Q(**exclude_empty_cells_options)
            )

    elif filter_type == FilterType.GREATER and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_float__gt": value}

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options["value_float__isnull"] = True

            attributes_qs = attributes_qs.filter(
                Q(**options) | Q(**include_null_options)
            )

    elif filter_type == FilterType.GREATER_EQUAL and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_float__gte": value}

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options["value_float__isnull"] = True

            attributes_qs = attributes_qs.filter(
                Q(**options) | Q(**include_null_options)
            )

    elif filter_type == FilterType.LESS and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_float__lt": value}

            include_null_options = {}

            if not exclude_empty_cells:
                include_null_options["value_float__isnull"] = True

            attributes_qs = attributes_qs.filter(
                Q(**options) | Q(**include_null_options)
            )

    elif filter_type == FilterType.LESS_EQUAL and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_float__lte": value}

            include_null_options = {}

            if not exclude_empty_cells:
                include_null_options["value_float__isnull"] = True

            attributes_qs = attributes_qs.filter(
                Q(**options) | Q(**include_null_options)
            )

    elif filter_type == FilterType.FROM_TO and value_type == ValueType.NUMBER:
        max_value = filter_config["value"]["max_value"]
        min_value = filter_config["value"]["min_value"]

        if max_value is not None and min_value is not None:
            options = {
                "value_float__gte": min_value,
                "value_float__lte": max_value,
            }

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options["value_float__isnull"] = True

            attributes_qs = attributes_qs.filter(
                Q(**options) | Q(**include_null_options)
            )

    elif filter_type == FilterType.EMPTY and int(value_type) == ValueType.NUMBER:
        include_null_options = {"value_float__isnull": True}

        attributes_qs = attributes_qs.filter(Q(**include_null_options))

    # endregion NUMBER FILTERS END

    # region DATE FILTERS START

    elif filter_type == FilterType.EQUAL and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            # TESTING464
            #
            # options = {"value_date": datetime.strptime(value, DATE_FORMAT).date()}
            #
            # include_null_options = {}
            # if not exclude_empty_cells:
            #     include_null_options["value_date__isnull"] = True
            #
            # attributes_qs = attributes_qs.filter(
            #     Q(**options) | Q(**include_null_options)
            # )
            q = _get_equal_q(
                "value_date",
                datetime.strptime(value, DATE_FORMAT).date(),
                exclude_empty_cells
            )

    elif filter_type == FilterType.NOT_EQUAL and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_date": datetime.strptime(value, DATE_FORMAT).date()}

            exclude_empty_cells_options = {}
            if exclude_empty_cells:
                exclude_empty_cells_options["value_date__isnull"] = True

            attributes_qs = attributes_qs.exclude(
                Q(**options) | Q(**exclude_empty_cells_options)
            )

    elif filter_type == FilterType.GREATER and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_date__gt": datetime.strptime(value, DATE_FORMAT).date()}

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options["value_date__isnull"] = True

            attributes_qs = attributes_qs.filter(
                Q(**options) | Q(**include_null_options)
            )

    elif filter_type == FilterType.GREATER_EQUAL and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_date__gte": datetime.strptime(value, DATE_FORMAT).date()}

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options["value_date__isnull"] = True

            attributes_qs = attributes_qs.filter(
                Q(**options) | Q(**include_null_options)
            )

    elif filter_type == FilterType.LESS and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_date__lt": datetime.strptime(value, DATE_FORMAT).date()}

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options["value_date__isnull"] = True

            attributes_qs = attributes_qs.filter(
                Q(**options) | Q(**include_null_options)
            )

    elif filter_type == FilterType.LESS_EQUAL and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_date__lte": datetime.strptime(value, DATE_FORMAT).date()}

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options["value_date__isnull"] = True

            attributes_qs = attributes_qs.filter(
                Q(**options) | Q(**include_null_options)
            )

    elif filter_type == FilterType.FROM_TO and value_type == ValueType.DATE:
        max_value = filter_config["value"]["max_value"]
        min_value = filter_config["value"]["min_value"]

        if max_value and min_value:
            options = {
                "value_date__gte": datetime.strptime(min_value, DATE_FORMAT).date(),
                "value_date__lte": datetime.strptime(max_value, DATE_FORMAT).date(),
            }

            include_null_options = {}

            if not exclude_empty_cells:
                include_null_options["value_date__isnull"] = True

            attributes_qs = attributes_qs.filter(
                Q(**options) | Q(**include_null_options)
            )

    elif filter_type == FilterType.EMPTY and int(value_type) == ValueType.DATE:
        include_null_options = {"value_date__isnull": True}

        attributes_qs = attributes_qs.filter(Q(**include_null_options))

    elif filter_type == FilterType.DATE_TREE and value_type == ValueType.DATE:
        dates = []

        if len(filter_config["value"]):
            for val in filter_config["value"]:
                dates.append(parse(val))

        if len(dates):
            options = {"value_date__in": dates}

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options["value_date__isnull"] = True

            attributes_qs = attributes_qs.filter(
                Q(**options) | Q(**include_null_options)
            )

    # endregion DATE FILTERS

    filtered_attributes_ids = attributes_qs.values_list("object_id", flat=True)

    qs = qs.filter(id__in=filtered_attributes_ids)

    return qs

def add_filter(qs, filter_config):
    # print('filter_config %s ' % filter_config)

    filter_type = filter_config["filter_type"]
    value_type = str(filter_config["value_type"])
    key = filter_config["key"]
    value = None
    _l.info(
        f"TESTING.POMS.COMMON.FILTERING_HANDLERS add_filter filter_config: "
        f"{filter_config}"
    )
    # print('value_type %s' % value_type)
    # print('value_type %s' % type(value_type))

    exclude_empty_cells = filter_config["exclude_empty_cells"]

    # region FIELD FILTERS. Uses same filter types as string filter
    if filter_type == FilterType.MULTISELECTOR and value_type == ValueType.FIELD:
        print(filter_config["value"])

        if len(filter_config["value"]):
            values = filter_config["value"]
        else:
            values = []

        if values:
            clauses = []

            for value in values:
                options = {key + "__user_code": value}

                clauses.append(Q(**options))

            include_null_options = {}
            include_empty_string_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__user_code__isnull"] = True
                include_empty_string_options[key + "__user_code"] = ""

            clauses.append(Q(**include_null_options))
            clauses.append(Q(**include_empty_string_options))

            query = reduce(operator.or_, clauses)

            qs = qs.filter(query)

    elif filter_type == FilterType.SELECTOR and value_type == ValueType.FIELD:
        # TODO HANDLE SYSTEM CODE

        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            print("value %s" % value)

            options = {key + "__user_code": value}

            include_null_options = {}
            include_empty_string_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__user_code__isnull"] = True
                include_empty_string_options[key + "__user_code"] = ""

            # print('include_null_options %s' % include_null_options)
            # print('options %s' % options)

            qs = qs.filter(
                Q(**options)
                | Q(**include_null_options)
                | Q(**include_empty_string_options)
            )

    elif filter_type == FilterType.CONTAINS and value_type == ValueType.FIELD:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {key + "__name__icontains": value}

            include_null_options = {}
            include_empty_string_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__name__isnull"] = True
                include_empty_string_options[key + "__name"] = ""

            # print('include_null_options %s' % include_null_options)
            # print('options %s' % options)

            qs = qs.filter(
                Q(**options)
                | Q(**include_null_options)
                | Q(**include_empty_string_options)
            )

    elif filter_type == FilterType.DOES_NOT_CONTAINS and value_type == ValueType.FIELD:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {key + "__name__icontains": value}

            exclude_nulls_options = {}
            exclude_empty_cells_options = {}
            if exclude_empty_cells:
                exclude_nulls_options[key + "__name__isnull"] = True
                exclude_empty_cells_options[key + "__name"] = ""

            qs = qs.exclude(
                Q(**options)
                | Q(**exclude_nulls_options)
                | Q(**exclude_empty_cells_options)
            )

    elif filter_type == FilterType.EQUAL and value_type == ValueType.FIELD:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:

            q = _get_equal_q(key + "__name", value, exclude_empty_cells)

            q = q | Q(**{f"{key}__name": ""})

            qs = qs.filter(q)

    elif filter_type == FilterType.HAS_SUBSTRING and value_type == ValueType.FIELD:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            key_name = key + "__name"

            q = _get_has_substring_q(key_name, value, exclude_empty_cells)

            qs = qs.filter(q)

    elif filter_type == FilterType.EMPTY and value_type == ValueType.FIELD:
        include_null_options = {key + "__name__isnull": True}

        include_empty_string_options = {key + "__name": ""}

        qs = qs.filter(Q(**include_null_options) | Q(**include_empty_string_options))

    # endregion FIELD FILTERS

    # region STRING FILTERS START

    elif filter_type == FilterType.MULTISELECTOR and value_type == ValueType.STRING:
        print(filter_config["value"])

        if len(filter_config["value"]):
            values = filter_config["value"]
        else:
            values = []

        if values:
            clauses = []

            for value in values:
                options = {key: value}

                clauses.append(Q(**options))

            include_null_options = {}
            include_empty_string_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__isnull"] = True
                include_empty_string_options[key] = ""

            clauses.append(Q(**include_null_options))
            clauses.append(Q(**include_empty_string_options))

            query = reduce(operator.or_, clauses)

            qs = qs.filter(query)

    elif filter_type == FilterType.SELECTOR and value_type == ValueType.STRING:
        # print('here?')

        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {key: value}

            include_null_options = {}
            include_empty_string_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__isnull"] = True
                include_empty_string_options[key] = ""

            # print('include_null_options %s' % include_null_options)
            # print('options %s' % options)

            qs = qs.filter(
                Q(**options)
                | Q(**include_null_options)
                | Q(**include_empty_string_options)
            )

    elif filter_type == FilterType.CONTAINS and value_type == ValueType.STRING:
        # print('here?')

        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {key + "__icontains": value}

            include_null_options = {}
            include_empty_string_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__isnull"] = True
                include_empty_string_options[key] = ""

            # print('include_null_options %s' % include_null_options)
            # print('options %s' % options)

            qs = qs.filter(
                Q(**options)
                | Q(**include_null_options)
                | Q(**include_empty_string_options)
            )

    elif filter_type == FilterType.DOES_NOT_CONTAINS and value_type == ValueType.STRING:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {key + "__icontains": value}

            exclude_nulls_options = {}
            exclude_empty_cells_options = {}
            if exclude_empty_cells:
                exclude_nulls_options[key + "__isnull"] = True
                exclude_empty_cells_options[key] = ""

            qs = qs.exclude(
                Q(**options)
                | Q(**exclude_nulls_options)
                | Q(**exclude_empty_cells_options)
            )

    elif filter_type == FilterType.EQUAL and value_type == ValueType.STRING:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            # TESTING464
            #
            # options = {key + "__iexact": value}
            #
            # include_null_options = {}
            # if not exclude_empty_cells:
            #     include_null_options[key + "__isnull"] = True
            #
            # qs = qs.filter(Q(**options) | Q(**include_null_options))
            q = _get_equal_q(key, value, exclude_empty_cells)

            qs = qs.filter(q)

    elif filter_type == FilterType.HAS_SUBSTRING and value_type == ValueType.STRING:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            q = _get_has_substring_q(key, value, exclude_empty_cells)

            qs = qs.filter(q)

    elif filter_type == FilterType.EMPTY and value_type == ValueType.STRING:
        include_null_options = {}
        include_empty_string_options = {}

        include_null_options[key + "__isnull"] = True
        include_empty_string_options[key] = ""

        qs = qs.filter(Q(**include_null_options) | Q(**include_empty_string_options))

    # endregion STRING FILTERS END

    # region NUMBER FILTERS START

    elif filter_type == FilterType.EQUAL and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value or value == 0:
            # TESTING464
            #
            # options = {key + "__exact": value}
            #
            # include_null_options = {}
            # if not exclude_empty_cells:
            #     include_null_options[key + "__isnull"] = True
            #
            # qs = qs.filter(Q(**options) | Q(**include_null_options))
            q = _get_equal_q(key, value, exclude_empty_cells)

            qs = qs.filter(q)

    elif filter_type == FilterType.NOT_EQUAL and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value or value == 0:
            options = {key + "__exact": value}

            exclude_empty_cells_options = {}
            if exclude_empty_cells:
                exclude_empty_cells_options[key + "__isnull"] = True

            # print('exclude_empty_cells_options %s' % exclude_empty_cells_options)

            qs = qs.exclude(Q(**options) | Q(**exclude_empty_cells_options))

    elif filter_type == FilterType.GREATER and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value or value == 0:
            options = {key + "__gt": value}

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__isnull"] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.GREATER_EQUAL and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value or value == 0:
            options = {key + "__gte": value}

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__isnull"] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.LESS and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value or value == 0:
            options = {key + "__lt": value}

            include_null_options = {}

            if not exclude_empty_cells:
                include_null_options[key + "__isnull"] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.LESS_EQUAL and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value or value == 0:
            options = {key + "__lte": value}

            include_null_options = {}

            if not exclude_empty_cells:
                include_null_options[key + "__isnull"] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.FROM_TO and value_type == ValueType.NUMBER:
        max_value = filter_config["value"]["max_value"]
        min_value = filter_config["value"]["min_value"]

        if max_value is not None and min_value is not None:
            options = {
                key + "__gte": min_value,
                key + "__lte": max_value,
            }

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__isnull"] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.EMPTY and value_type == ValueType.NUMBER:
        include_null_options = {}
        include_null_options[key + "__isnull"] = True

        qs = qs.filter(Q(**include_null_options))

    # endregion NUMBER FILTERS END

    # DATE FILTERS START

    elif filter_type == FilterType.EQUAL and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            # TESTING464
            #
            # options = {key: datetime.strptime(value, DATE_FORMAT).date()}
            #
            # include_null_options = {}
            # if not exclude_empty_cells:
            #     include_null_options[key + "__isnull"] = True
            #
            # qs = qs.filter(Q(**options) | Q(**include_null_options))
            q = _get_equal_q(
                key,
                datetime.strptime(value, DATE_FORMAT).date(),
                exclude_empty_cells
            )

            qs = qs.filter(q)

    elif filter_type == FilterType.NOT_EQUAL and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {key: datetime.strptime(value, DATE_FORMAT).date()}

            exclude_empty_cells_options = {}
            if exclude_empty_cells:
                exclude_empty_cells_options[key + "__isnull"] = True

            qs = qs.exclude(Q(**options) | Q(**exclude_empty_cells_options))

    elif filter_type == FilterType.GREATER and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {key + "__gt": datetime.strptime(value, DATE_FORMAT).date()}

            print("options", options)

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__isnull"] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.GREATER_EQUAL and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {key + "__gte": datetime.strptime(value, DATE_FORMAT).date()}

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__isnull"] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.LESS and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {key + "__lt": datetime.strptime(value, DATE_FORMAT).date()}

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__isnull"] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.LESS_EQUAL and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {key + "__lte": datetime.strptime(value, DATE_FORMAT).date()}

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__isnull"] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.FROM_TO and value_type == ValueType.DATE:
        max_value = filter_config["value"]["max_value"]
        min_value = filter_config["value"]["min_value"]

        if max_value and min_value:
            options = {
                key + "__gte": datetime.strptime(min_value, DATE_FORMAT).date(),
                key + "__lte": datetime.strptime(max_value, DATE_FORMAT).date(),
            }

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__isnull"] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    elif filter_type == FilterType.EMPTY and value_type == ValueType.DATE:
        include_null_options = {}

        include_null_options[key + "__isnull"] = True

        qs = qs.filter(Q(**include_null_options))

    elif filter_type == FilterType.DATE_TREE and value_type == ValueType.DATE:
        dates = []

        if len(filter_config["value"]):
            for val in filter_config["value"]:
                dates.append(parse(val))

        if len(dates):
            options = {key + "__in": dates}

            include_null_options = {}
            if not exclude_empty_cells:
                include_null_options[key + "__isnull"] = True

            qs = qs.filter(Q(**options) | Q(**include_null_options))

    # DATE FILTERS END

    # BOOLEAN FILTER

    elif filter_type == FilterType.EQUAL and value_type == ValueType.BOOLEAN:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            # TESTING464
            #
            # options = {key: value}
            #
            # include_null_options = {}
            # if not exclude_empty_cells:
            #     include_null_options[key + "__isnull"] = True
            #
            # qs = qs.filter(Q(**options) | Q(**include_null_options))
            q = _get_equal_q(key, value, exclude_empty_cells)

            qs = qs.filter(q)

    # print('qs len after filters %s' % len(list(qs)))

    return qs


def is_dynamic_attribute_filter(filter_config):
    key = filter_config["key"]

    return "attributes" in key


def handle_filters(qs, filter_settings, master_user, content_type):
    # print('Handle filters %s' % filter_settings)
    _l.info(
        f"TESTING.POMS.COMMON.FILTERING_HANDLERS handle_filters filter_settings: "
        f"{filter_settings}"
    )
    start_time = time.time()

    if filter_settings:
        for filter_config in filter_settings:
            if is_dynamic_attribute_filter(filter_config):
                qs = add_dynamic_attribute_filter(
                    qs, filter_config, master_user, content_type
                )
            else:
                qs = add_filter(qs, filter_config)

    # _l.debug("handle_filters done in %s seconds " % "{:3.3f}".format(time.time() - start_time))

    return qs


def handle_global_table_search(qs, global_table_search, model, content_type):
    start_time = time.time()

    # _l.info('handle_global_table_search.global_table_search %s' % global_table_search)

    q = Q()

    relation_fields = [
        f
        for f in model._meta.fields
        if isinstance(f, ForeignKey)
        and f.name != "master_user"
        and f.name != "owner"
        and f.name != "procedure_instance"
        and f.name != "complex_transaction"
        and f.name != "event_schedule"
        and f.name != "member"
        and f.name != "action"
        and f.name != "previous_date_record"
        and f.name != "transaction"
        and f.name != "status"
        and f.name != "linked_import_task"
        and f.name != "content_type"
    ]

    # _l.info('relation_fields %s' % relation_fields)

    relation_queries_short_name = [
        Q(**{f.name + "__short_name__icontains": global_table_search})
        for f in relation_fields
    ]

    for query in relation_queries_short_name:
        q = q | query

    relation_queries_name = [
        Q(**{f.name + "__name__icontains": global_table_search})
        for f in relation_fields
    ]

    for query in relation_queries_name:
        q = q | query

    relation_queries_user_code = [
        Q(**{f.name + "__user_code__icontains": global_table_search})
        for f in relation_fields
    ]

    for query in relation_queries_user_code:
        q = q | query

    char_fields = [
        f
        for f in model._meta.fields
        if isinstance(f, CharField) and f.name != "deleted_user_code"
    ]

    # _l.info('char_fields %s' % char_fields)

    char_queries = [
        Q(**{f.name + "__icontains": global_table_search}) for f in char_fields
    ]

    for query in char_queries:
        q = q | query

    text_fields = [f for f in model._meta.fields if isinstance(f, TextField)]

    # _l.info('text_fields %s' % text_fields)

    text_queries = [
        Q(**{f.name + "__icontains": global_table_search}) for f in text_fields
    ]

    for query in text_queries:
        q = q | query

    date_fields = [f for f in model._meta.fields if isinstance(f, DateField)]
    date_queries = [
        Q(**{f.name + "__icontains": global_table_search}) for f in date_fields
    ]

    for query in date_queries:
        q = q | query

    integer_fields = [f for f in model._meta.fields if isinstance(f, IntegerField)]
    integer_queries = [
        Q(**{f.name + "__icontains": global_table_search}) for f in integer_fields
    ]

    for query in integer_queries:
        q = q | query

    float_fields = [f for f in model._meta.fields if isinstance(f, FloatField)]
    float_queries = [
        Q(**{f.name + "__icontains": global_table_search}) for f in float_fields
    ]

    for query in float_queries:
        q = q | query

    if content_type.model not in [
        "currencyhistory",
        "pricehistory",
        "transaction",
        "currencyhistoryerror",
        "portfoliohistory",
        "complextransactionimportscheme",
        "csvimportscheme",
        "pricehistoryerror",
        "generatedevent",
        "portfolioregisterrecord",
        "complextransaction",
    ]:
        string_attr_query = Q(
            **{"attributes__value_float__icontains": global_table_search}
        )
        date_attr_query = Q(
            **{"attributes__value_date__icontains": global_table_search}
        )
        float_attr_query = Q(
            **{"attributes__value_float__icontains": global_table_search}
        )
        classifier_attr_query = Q(
            **{"attributes__classifier__name__icontains": global_table_search}
        )

        q = q | classifier_attr_query
        q = q | float_attr_query
        q = q | string_attr_query
        q = q | date_attr_query

        q = q & Q(**{"is_deleted": False})

    # _l.info('q %s' % q)

    qs = qs.filter(q).distinct()

    _l.debug(
        "handle_global_table_search done in %s seconds "
        % "{:3.3f}".format(time.time() - start_time)
    )

    return qs
