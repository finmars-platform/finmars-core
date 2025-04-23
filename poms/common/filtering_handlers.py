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
from rest_framework.exceptions import ValidationError

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
    JSON = "json"


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


def _get_equal_q(field_key, value_type, value):
    """
    :param field_key:
    :param value_type: - values: 10, 20, 30, 40
    :param value:
    :return: Q object for filter type "equal"
    """
    lookup = "iexact"

    if value_type in (ValueType.NUMBER, ValueType.DATE):
        lookup = "exact"

    return Q(**{f"{field_key}__{lookup}": value})


def _get_has_substring_q(field_key, value):
    """
    :param field_key:
    :param value:
    :return: Q object for filter type "contains_has_substring"
    """
    q = Q()
    # TODO: Use commented code for CONTAINS filters
    #
    # substrings = value.split(" ")
    #
    # for text in substrings:
    #     q = q | Q(**{f"{field_key}__icontains": text})
    q = q | Q(**{f"{field_key}__icontains": value})

    return q


def add_dynamic_attribute_filter(qs, filter_config, master_user, content_type):
    filter_type = filter_config["filter_type"]
    value_type = str(filter_config["value_type"])
    value = None

    source_key = filter_config["key"]
    attribute_type_user_code = source_key.split("attributes.")[1]
    if not attribute_type_user_code:
        raise ValidationError(
            f"Empty attribute type user code in source_key={source_key}"
        )

    attribute_type = GenericAttributeType.objects.get(
        user_code=attribute_type_user_code,
        content_type=content_type,
        master_user=master_user,
    )

    attributes_qs = GenericAttribute.objects.filter(attribute_type=attribute_type)

    # CLASSIFIER FILTERS

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

            query = reduce(operator.or_, clauses)

            attributes_qs = attributes_qs.filter(query)

    elif filter_type == FilterType.SELECTOR and value_type == ValueType.CLASSIFIER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            attributes_qs = attributes_qs.filter(classifier__name__icontains=value)

    elif filter_type == FilterType.EQUAL and value_type == ValueType.CLASSIFIER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            attributes_qs = attributes_qs.filter(classifier__name__iexact=value)

    elif filter_type == FilterType.HAS_SUBSTRING and value_type == ValueType.CLASSIFIER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            attributes_qs = attributes_qs.filter(classifier__name__icontains=value)

    elif filter_type == FilterType.CONTAINS and value_type == ValueType.CLASSIFIER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            q = Q()
            substrings = value.split(" ")

            for text in substrings:
                q = q & Q(classifier__name__icontains=text)

            attributes_qs = attributes_qs.filter(q)

    elif (
        filter_type == FilterType.DOES_NOT_CONTAINS
        and value_type == ValueType.CLASSIFIER
    ):
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            attributes_qs = attributes_qs.exclude(
                Q(classifier__name__icontains=value) | Q(classifier__isnull=True)
            )

    elif filter_type == FilterType.EMPTY and value_type == ValueType.CLASSIFIER:
        attributes_qs = attributes_qs.filter(classifier__isnull=True)

    # STRING FILTERS START
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

            query = reduce(operator.or_, clauses)

            attributes_qs = attributes_qs.filter(query)

    elif filter_type == FilterType.SELECTOR and value_type == ValueType.STRING:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_string__icontains": value}

            attributes_qs = attributes_qs.filter(Q(**options))

    elif filter_type == FilterType.CONTAINS and value_type == ValueType.STRING:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_string__icontains": value}

            attributes_qs = attributes_qs.filter(Q(**options))

    elif filter_type == FilterType.DOES_NOT_CONTAINS and value_type == ValueType.STRING:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_string__icontains": value}

            exclude_null_options = {"classifier__isnull": True}
            exclude_empty_cells_options = {"value_string": ""}

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

            attributes_qs = attributes_qs.filter(Q(**options))

    elif filter_type == FilterType.HAS_SUBSTRING and value_type == ValueType.STRING:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            q = Q()
            substrings = value.split(" ")

            for text in substrings:
                q = q | Q(value_string__icontains=text)

            attributes_qs = attributes_qs.filter(q)

    elif filter_type == FilterType.EMPTY and value_type == ValueType.STRING:
        include_null_options = {"value_string__isnull": True}

        include_empty_string_options = {"value_string": ""}

        attributes_qs = attributes_qs.filter(
            Q(**include_null_options) | Q(**include_empty_string_options)
        )

    # NUMBER FILTERS
    elif filter_type == FilterType.EQUAL and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            q = _get_equal_q("value_float", value_type, value)

            attributes_qs = attributes_qs.filter(q)

    elif filter_type == FilterType.NOT_EQUAL and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_float__exact": value}

            exclude_empty_cells_options = {"value_float__isnull": True}

            attributes_qs = attributes_qs.exclude(
                Q(**options) | Q(**exclude_empty_cells_options)
            )

    elif filter_type == FilterType.GREATER and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_float__gt": value}

            attributes_qs = attributes_qs.filter(Q(**options))

    elif filter_type == FilterType.GREATER_EQUAL and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_float__gte": value}

            attributes_qs = attributes_qs.filter(Q(**options))

    elif filter_type == FilterType.LESS and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_float__lt": value}

            attributes_qs = attributes_qs.filter(Q(**options))

    elif filter_type == FilterType.LESS_EQUAL and value_type == ValueType.NUMBER:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_float__lte": value}

            attributes_qs = attributes_qs.filter(Q(**options))

    elif filter_type == FilterType.FROM_TO and value_type == ValueType.NUMBER:
        max_value = filter_config["value"].get("max_value")
        min_value = filter_config["value"].get("min_value")

        if max_value is not None and min_value is not None:
            options = {
                "value_float__gte": min_value,
                "value_float__lte": max_value,
            }

            attributes_qs = attributes_qs.filter(Q(**options))

    elif filter_type == FilterType.OUT_OF_RANGE and value_type == ValueType.NUMBER:
        max_value = filter_config["value"].get("max_value")
        min_value = filter_config["value"].get("min_value")

        if max_value is not None and min_value is not None:
            q_less_than_min = Q(value_float__lt=min_value)
            q_greater_than_max = Q(value_float__gt=max_value)

            attributes_qs = attributes_qs.filter(q_less_than_min | q_greater_than_max)

    elif filter_type == FilterType.EMPTY and value_type == ValueType.NUMBER:
        include_null_options = {"value_float__isnull": True}

        attributes_qs = attributes_qs.filter(Q(**include_null_options))

    # DATE FILTERS
    elif filter_type == FilterType.EQUAL and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            q = _get_equal_q(
                "value_date",
                value_type,
                datetime.strptime(value, DATE_FORMAT).date(),
            )

            attributes_qs = attributes_qs.filter(q)

    elif filter_type == FilterType.NOT_EQUAL and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_date": datetime.strptime(value, DATE_FORMAT).date()}

            exclude_empty_cells_options = {"value_date__isnull": True}

            attributes_qs = attributes_qs.exclude(
                Q(**options) | Q(**exclude_empty_cells_options)
            )

    elif filter_type == FilterType.GREATER and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_date__gt": datetime.strptime(value, DATE_FORMAT).date()}

            attributes_qs = attributes_qs.filter(Q(**options))

    elif filter_type == FilterType.GREATER_EQUAL and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_date__gte": datetime.strptime(value, DATE_FORMAT).date()}

            attributes_qs = attributes_qs.filter(Q(**options))

    elif filter_type == FilterType.LESS and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_date__lt": datetime.strptime(value, DATE_FORMAT).date()}

            attributes_qs = attributes_qs.filter(Q(**options))

    elif filter_type == FilterType.LESS_EQUAL and value_type == ValueType.DATE:
        if len(filter_config["value"]):
            value = filter_config["value"][0]

        if value:
            options = {"value_date__lte": datetime.strptime(value, DATE_FORMAT).date()}

            attributes_qs = attributes_qs.filter(Q(**options))

    elif filter_type == FilterType.FROM_TO and value_type == ValueType.DATE:
        max_value = filter_config["value"].get("max_value")
        min_value = filter_config["value"].get("min_value")

        if max_value and min_value:
            options = {
                "value_date__gte": datetime.strptime(min_value, DATE_FORMAT).date(),
                "value_date__lte": datetime.strptime(max_value, DATE_FORMAT).date(),
            }

            attributes_qs = attributes_qs.filter(Q(**options))

    elif filter_type == FilterType.OUT_OF_RANGE and value_type == ValueType.DATE:
        max_value = filter_config["value"].get("max_value")
        min_value = filter_config["value"].get("min_value")

        if max_value and min_value:
            q_less_than_min = Q(
                value_date__lt=datetime.strptime(min_value, DATE_FORMAT).date()
            )
            q_greater_than_max = Q(
                value_date__gt=datetime.strptime(max_value, DATE_FORMAT).date()
            )

            attributes_qs = attributes_qs.filter(q_less_than_min | q_greater_than_max)

    elif filter_type == FilterType.EMPTY and value_type == ValueType.DATE:
        include_null_options = {"value_date__isnull": True}

        attributes_qs = attributes_qs.filter(Q(**include_null_options))

    elif filter_type == FilterType.DATE_TREE and value_type == ValueType.DATE:
        dates = []

        if len(filter_config["value"]):
            for val in filter_config["value"]:
                dates.append(parse(val))

        if len(dates):
            options = {"value_date__in": dates}

            attributes_qs = attributes_qs.filter(Q(**options))

    filtered_attributes_ids = attributes_qs.values_list("object_id", flat=True)

    qs = qs.filter(id__in=filtered_attributes_ids)

    return qs


def add_filter(qs, filter_config):
    filter_type = filter_config["filter_type"]
    value_type = str(filter_config["value_type"])
    key = filter_config["key"]
    exclude_empty_cells = filter_config.get("exclude_empty_cells", False)
    values = filter_config["value"]
    value = None
    if isinstance(values, list) and values:
        value = values[0]

    _l.info(
        f"add_filter: values={values} value={value} value_type={value_type} key={key}"
    )

    # FIELD FILTERS. Uses same filter types as string filter
    if filter_type == FilterType.MULTISELECTOR and value_type == ValueType.FIELD:
        if values:
            clauses = []
            for value in values:
                options = {f"{key}__user_code": value}
                clauses.append(Q(**options))

            query = reduce(operator.or_, clauses)
            qs = qs.filter(query)

    elif filter_type == FilterType.SELECTOR and value_type == ValueType.FIELD:
        if value:
            options = {f"{key}__user_code": value}
            qs = qs.filter(Q(**options))

    elif filter_type == FilterType.CONTAINS and value_type == ValueType.FIELD:
        if value:
            options = {f"{key}__name__icontains": value}
            qs = qs.filter(Q(**options))

    elif filter_type == FilterType.DOES_NOT_CONTAINS and value_type == ValueType.FIELD:
        if value:
            options = {f"{key}__name__icontains": value}
            exclude_nulls_options = {f"{key}__name__isnull": True}
            exclude_empty_cells_options = {f"{key}__name": ""}

            qs = qs.exclude(
                Q(**options)
                | Q(**exclude_nulls_options)
                | Q(**exclude_empty_cells_options)
            )

    elif filter_type == FilterType.EQUAL and value_type == ValueType.FIELD:
        if value and isinstance(value, str):
            q1 = _get_equal_q(f"{key}__name", value_type, value)
            q2 = _get_equal_q(f"{key}__short_name", value_type, value)
            q3 = _get_equal_q(f"{key}__public_name", value_type, value)
            q = q1 | q2 | q3
            if not exclude_empty_cells:
                q4 = Q(**{f"{key}__name": ""})
                q |= q4

            qs = qs.filter(q)

    elif filter_type == FilterType.HAS_SUBSTRING and value_type == ValueType.FIELD:
        if value:
            key_name = f"{key}__name"
            q = _get_has_substring_q(key_name, value)
            qs = qs.filter(q)

    elif filter_type == FilterType.EMPTY and value_type == ValueType.FIELD:
        include_null_options = {key + "__name__isnull": True}
        include_empty_string_options = {key + "__name": ""}
        qs = qs.filter(Q(**include_null_options) | Q(**include_empty_string_options))

    # STRING FILTERS
    elif filter_type == FilterType.MULTISELECTOR and value_type == ValueType.STRING:
        if values:
            clauses = []
            for value in values:
                options = {key: value}
                clauses.append(Q(**options))

            query = reduce(operator.or_, clauses)
            qs = qs.filter(query)

    elif filter_type == FilterType.SELECTOR and value_type == ValueType.STRING:
        if value:
            options = {key: value}
            qs = qs.filter(Q(**options))

    elif filter_type == FilterType.CONTAINS and value_type == ValueType.STRING:
        if value:
            options = {key + "__icontains": value}
            qs = qs.filter(Q(**options))

    elif filter_type == FilterType.DOES_NOT_CONTAINS and value_type == ValueType.STRING:
        if value:
            options = {key + "__icontains": value}
            exclude_nulls_options = {key + "__isnull": True}
            exclude_empty_cells_options = {key: ""}
            qs = qs.exclude(
                Q(**options)
                | Q(**exclude_nulls_options)
                | Q(**exclude_empty_cells_options)
            )

    elif filter_type == FilterType.EQUAL and value_type == ValueType.STRING:
        if value:
            q = _get_equal_q(key, value_type, value)
            qs = qs.filter(q)

    elif filter_type == FilterType.HAS_SUBSTRING and value_type == ValueType.STRING:
        if value:
            q = _get_has_substring_q(key, value)
            qs = qs.filter(q)

    elif filter_type == FilterType.EMPTY and value_type == ValueType.STRING:
        include_null_options = {}
        include_empty_string_options = {}
        include_null_options[key + "__isnull"] = True
        include_empty_string_options[key] = ""

        qs = qs.filter(Q(**include_null_options) | Q(**include_empty_string_options))

    # NUMBER FILTERS
    elif filter_type == FilterType.EQUAL and value_type == ValueType.NUMBER:
        if value or value == 0:
            q = _get_equal_q(key, value_type, value)
            qs = qs.filter(q)

    elif filter_type == FilterType.NOT_EQUAL and value_type == ValueType.NUMBER:
        if value or value == 0:
            options = {key + "__exact": value}
            exclude_empty_cells_options = {key + "__isnull": True}
            qs = qs.exclude(Q(**options) | Q(**exclude_empty_cells_options))

    elif filter_type == FilterType.GREATER and value_type == ValueType.NUMBER:
        if value or value == 0:
            options = {key + "__gt": value}
            qs = qs.filter(Q(**options))

    elif filter_type == FilterType.GREATER_EQUAL and value_type == ValueType.NUMBER:
        if value or value == 0:
            options = {key + "__gte": value}
            qs = qs.filter(Q(**options))

    elif filter_type == FilterType.LESS and value_type == ValueType.NUMBER:
        if value or value == 0:
            options = {key + "__lt": value}
            qs = qs.filter(Q(**options))

    elif filter_type == FilterType.LESS_EQUAL and value_type == ValueType.NUMBER:
        if value or value == 0:
            options = {f"{key}__lte": value}
            qs = qs.filter(Q(**options))

    elif filter_type == FilterType.FROM_TO and value_type == ValueType.NUMBER:
        max_value = filter_config["value"].get("max_value")
        min_value = filter_config["value"].get("min_value")

        if max_value is not None and min_value is not None:
            options = {
                f"{key}__gte": min_value,
                f"{key}__lte": max_value,
            }
            qs = qs.filter(Q(**options))

    elif filter_type == FilterType.OUT_OF_RANGE and value_type == ValueType.NUMBER:
        max_value = filter_config["value"].get("max_value")
        min_value = filter_config["value"].get("min_value")

        if max_value is not None and min_value is not None:
            q_less_than_min = Q(**{key + "__lt": min_value})
            q_greater_than_max = Q(**{key + "__gt": max_value})
            qs = qs.filter(q_less_than_min | q_greater_than_max)

    elif filter_type == FilterType.EMPTY and value_type == ValueType.NUMBER:
        include_null_options = {f"{key}__isnull": True}
        qs = qs.filter(Q(**include_null_options))

    # DATE FILTERS
    elif filter_type == FilterType.EQUAL and value_type == ValueType.DATE:
        if value:
            q = _get_equal_q(
                key,
                value_type,
                datetime.strptime(value, DATE_FORMAT).date(),
            )
            qs = qs.filter(q)

    elif filter_type == FilterType.NOT_EQUAL and value_type == ValueType.DATE:
        if value:
            options = {key: datetime.strptime(value, DATE_FORMAT).date()}
            exclude_empty_cells_options = {f"{key}__isnull": True}
            qs = qs.exclude(Q(**options) | Q(**exclude_empty_cells_options))

    elif filter_type == FilterType.GREATER and value_type == ValueType.DATE:
        if value:
            options = {key + "__gt": datetime.strptime(value, DATE_FORMAT).date()}
            qs = qs.filter(Q(**options))

    elif filter_type == FilterType.GREATER_EQUAL and value_type == ValueType.DATE:
        if value:
            options = {key + "__gte": datetime.strptime(value, DATE_FORMAT).date()}
            qs = qs.filter(Q(**options))

    elif filter_type == FilterType.LESS and value_type == ValueType.DATE:
        if value:
            options = {key + "__lt": datetime.strptime(value, DATE_FORMAT).date()}
            qs = qs.filter(Q(**options))

    elif filter_type == FilterType.LESS_EQUAL and value_type == ValueType.DATE:
        if value:
            options = {key + "__lte": datetime.strptime(value, DATE_FORMAT).date()}
            qs = qs.filter(Q(**options))

    elif filter_type == FilterType.FROM_TO and value_type == ValueType.DATE:
        # values = {
        #    "min_value": "2020-01-01",
        #    "max_value": "2030-12-31"
        # }
        max_value = values.get("max_value")
        min_value = values.get("min_value")

        if max_value and min_value:
            options = {
                f"{key}__gte": datetime.strptime(min_value, DATE_FORMAT).date(),
                f"{key}__lte": datetime.strptime(max_value, DATE_FORMAT).date(),
            }
            qs = qs.filter(Q(**options))

    elif filter_type == FilterType.OUT_OF_RANGE and value_type == ValueType.DATE:
        # values = {
        #    "min_value": "2020-01-01",
        #    "max_value": "2030-12-31"
        # }
        max_value = values.get("max_value")
        min_value = values.get("min_value")

        if max_value and min_value:
            q_less_than_min = Q(
                **{f"{key}__lt": datetime.strptime(min_value, DATE_FORMAT).date()}
            )
            q_greater_than_max = Q(
                **{f"{key}__gt": datetime.strptime(max_value, DATE_FORMAT).date()}
            )
            qs = qs.filter(q_less_than_min | q_greater_than_max)

    elif filter_type == FilterType.EMPTY and value_type == ValueType.DATE:
        include_null_options = {f"{key}__isnull": True}
        qs = qs.filter(Q(**include_null_options))

    elif filter_type == FilterType.DATE_TREE and value_type == ValueType.DATE:
        dates = []
        if values:
            for val in values:
                dates.append(parse(val))

        if dates:
            options = {f"{key}__in": dates}
            qs = qs.filter(Q(**options))

    # BOOLEAN FILTER
    elif filter_type == FilterType.EQUAL and value_type == ValueType.BOOLEAN:
        if value:
            q = _get_equal_q(key, value_type, value)
            qs = qs.filter(q)

    return qs


def is_dynamic_attribute_filter(filter_config: dict) -> bool:
    from poms.common.grouping_handlers import ATTRIBUTE_PREFIX, has_attribute

    key = filter_config["key"]
    has_attribute_prefix = has_attribute(key)
    attribute_code = key.split(ATTRIBUTE_PREFIX)[1] if has_attribute_prefix else None
    return has_attribute_prefix and attribute_code


def handle_filters(qs, filter_settings, master_user, content_type):
    if filter_settings:
        for filter_config in filter_settings:
            if is_dynamic_attribute_filter(filter_config):
                qs = add_dynamic_attribute_filter(
                    qs, filter_config, master_user, content_type
                )
            else:
                qs = add_filter(qs, filter_config)

    return qs


def handle_global_table_search(qs, global_table_search, model, content_type):
    start_time = time.time()
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

    relation_queries_short_name = [
        Q(**{f"{f.name}__short_name__icontains": global_table_search})
        for f in relation_fields
    ]

    for query in relation_queries_short_name:
        q = q | query

    relation_queries_name = [
        Q(**{f"{f.name}__name__icontains": global_table_search})
        for f in relation_fields
    ]

    for query in relation_queries_name:
        q = q | query

    relation_queries_user_code = [
        Q(**{f"{f.name}__user_code__icontains": global_table_search})
        for f in relation_fields
    ]

    for query in relation_queries_user_code:
        q = q | query

    char_fields = [
        f
        for f in model._meta.fields
        if isinstance(f, CharField) and f.name != "deleted_user_code"
    ]

    char_queries = [
        Q(**{f"{f.name}__icontains": global_table_search}) for f in char_fields
    ]

    for query in char_queries:
        q = q | query

    text_fields = [f for f in model._meta.fields if isinstance(f, TextField)]

    text_queries = [
        Q(**{f"{f.name}__icontains": global_table_search}) for f in text_fields
    ]

    for query in text_queries:
        q = q | query

    date_fields = [f for f in model._meta.fields if isinstance(f, DateField)]
    date_queries = [
        Q(**{f"{f.name}__icontains": global_table_search}) for f in date_fields
    ]

    for query in date_queries:
        q = q | query

    integer_fields = [f for f in model._meta.fields if isinstance(f, IntegerField)]
    integer_queries = [
        Q(**{f"{f.name}__icontains": global_table_search}) for f in integer_fields
    ]

    for query in integer_queries:
        q = q | query

    float_fields = [f for f in model._meta.fields if isinstance(f, FloatField)]
    float_queries = [
        Q(**{f"{f.name}__icontains": global_table_search}) for f in float_fields
    ]

    for query in float_queries:
        q = q | query

    if content_type.model not in {
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
    }:
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

    qs = qs.filter(q).distinct()

    _l.debug(
        "handle_global_table_search done in %s seconds "
        % "{:3.3f}".format(time.time() - start_time)
    )

    return qs
