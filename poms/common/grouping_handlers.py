import logging
import time

from django.apps import apps
from django.db.models import F, Q
from rest_framework.exceptions import ValidationError

from poms.common.filtering_handlers import handle_filters, handle_global_table_search
from poms.common.filters import filter_items_for_group, get_q_obj_for_attribute_type
from poms.common.utils import attr_is_relation
from poms.obj_attrs.models import GenericAttributeType

_l = logging.getLogger("poms.common")

ATTRIBUTE_PREFIX = "attributes."


def get_root_dynamic_attr_group(qs, root_group, groups_order):
    start_time = time.time()

    attribute_type = GenericAttributeType.objects.get(id__exact=root_group)

    qs = qs.filter(attributes__attribute_type=attribute_type)

    if attribute_type.value_type == 20:
        qs = (
            qs.values(attr=F("attributes__value_float"))
            .distinct()
            .annotate(group_identifier=F("attr"), group_name=F("attr"))
            .values("group_name", "group_identifier")
            .order_by()
        )
    elif attribute_type.value_type == 10:
        qs = (
            qs.values(attr=F("attributes__value_string"))
            .distinct()
            .annotate(group_identifier=F("attr"), group_name=F("attr"))
            .values("group_name", "group_identifier")
            .order_by()
        )
    elif attribute_type.value_type == 30:
        qs = (
            qs.values("attributes__classifier")
            .annotate(group_identifier=F("attributes__classifier"))
            .distinct()
            .annotate(
                group_name=F("attributes__classifier__name"),
                group_identifier=F("attributes__classifier"),
            )
            .values("group_name", "group_identifier")
            .order_by()
        )
    elif attribute_type.value_type == 40:
        qs = (
            qs.values(attr=F("attributes__value_date"))
            .distinct()
            .annotate(group_identifier=F("attr"), group_name=F("attr"))
            .values("group_name", "group_identifier")
            .order_by()
        )

    if groups_order == "asc":
        qs = qs.order_by(F("group_name").asc())
    elif groups_order == "desc":
        qs = qs.order_by(F("group_name").desc())

    _l.debug(f"get_root_dynamic_attr_group {time.time() - start_time} seconds ")

    return qs


def has_attribute(item) -> bool:
    return ATTRIBUTE_PREFIX in item


def get_root_system_attr_group(qs, root_group, groups_order, content_type_key):
    if attr_is_relation(content_type_key, root_group):
        qs = (
            qs.values(root_group)
            .annotate(group_identifier=F(f"{root_group}__user_code"))
            .distinct()
            .annotate(group_name=F(f"{root_group}__short_name"))
            .values("group_name", "group_identifier")
            .order_by()
        )
    else:
        qs = (
            qs.distinct()
            .annotate(group_name=F(root_group), group_identifier=F(root_group))
            .values("group_name", "group_identifier")
            .order_by(root_group)
        )

    if groups_order == "asc":
        qs = qs.order_by(F("group_name").asc())
    elif groups_order == "desc":
        qs = qs.order_by(F("group_name").desc())

    return qs


def get_last_dynamic_attr_group(qs, last_group, groups_order):
    start_time = time.time()

    attribute_type = GenericAttributeType.objects.get(id__exact=last_group)

    qs = qs.filter(attributes__attribute_type=attribute_type)

    if attribute_type.value_type == 20:
        qs = (
            qs.values(attr=F("attributes__value_float"))
            .distinct()
            .annotate(group_identifier=F("attr"), group_name=F("attr"))
            .values("group_name", "group_identifier")
            .order_by()
        )

    elif attribute_type.value_type == 10:
        qs = (
            qs.values(attr=F("attributes__value_string"))
            .distinct()
            .annotate(group_identifier=F("attr"), group_name=F("attr"))
            .values("group_name", "group_identifier")
            .order_by()
        )
    elif attribute_type.value_type == 30:
        qs = (
            qs.values("attributes__classifier")
            .annotate(group_identifier=F("attributes__classifier"))
            .distinct()
            .annotate(group_name=F("attributes__classifier__name"))
            .values("group_name", "group_identifier")
            .order_by()
        )
    elif attribute_type.value_type == 40:
        qs = (
            qs.values(attr=F("attributes__value_date"))
            .distinct()
            .annotate(group_identifier=F("attr"), group_name=F("attr"))
            .values("group_name", "group_identifier")
            .order_by()
        )

    # force_qs_evaluation(qs)

    if groups_order == "asc":
        qs = qs.order_by(F("group_name").asc())
    if groups_order == "desc":
        qs = qs.order_by(F("group_name").desc())

    _l.debug(f"get_last_dynamic_attr_group {time.time() - start_time} seconds ")

    return qs


def get_last_system_attr_group(qs, last_group, groups_order, content_type_key):
    print(f"last_group {last_group} ")

    if attr_is_relation(content_type_key, last_group):
        qs = (
            qs.values(last_group)
            .annotate(group_identifier=F(f"{last_group}__user_code"))
            .distinct()
            .annotate(group_name=F(f"{last_group}__short_name"))
            .values("group_name", "group_identifier")
            .order_by()
        )
    else:
        qs = (
            qs.distinct(last_group)
            .annotate(group_name=F(last_group), group_identifier=F(last_group))
            .values("group_name", "group_identifier")
            .order_by()
        )

    if groups_order == "desc":
        qs = qs.order_by(F("group_name").desc())
    else:
        qs = qs.order_by(F("group_name").asc())

    return qs


# ME: 2024-02-08 TODO: delete later if everything works fine
# def get_queryset_filters(qs, groups_types, groups_values, original_qs, content_type_key, model):
#     start_time = time.time()
#
#     # print('get_queryset_filters len %s' % len(qs    ))
#     qs = filter_items_for_group(qs, groups_types, groups_values, content_type_key, model)
#     _l.debug("get_queryset_filters %s seconds " % (time.time() - start_time))
#
#     return qs


def is_digit_attribute(item):
    return item.isdigit()


def is_root_groups_configuration(groups_types, groups_values):
    return len(groups_types) == 1 and not len(groups_values)


def format_groups(group_type: str, master_user, content_type) -> str:
    has_attribute_prefix = has_attribute(group_type)
    attribute_code = (
        group_type.split(ATTRIBUTE_PREFIX)[1] if has_attribute_prefix else None
    )
    if has_attribute_prefix and not attribute_code:
        raise ValidationError(
            f"format_groups: invalid group_type '{group_type}' (no attribute code)"
        )
    if has_attribute_prefix:
        attribute_type = GenericAttributeType.objects.get(
            user_code__exact=attribute_code,
            master_user=master_user,
            content_type=content_type,
        )
        return str(attribute_type.id)

    return group_type


def handle_groups(
    qs,
    groups_types,
    groups_values,
    groups_order,
    master_user,
    original_qs,
    content_type,
):
    start_time = time.time()

    groups_types = list(
        map(lambda x: format_groups(x, master_user, content_type), groups_types)
    )

    content_type_key = f"{content_type.app_label}.{content_type.model}"

    if is_root_groups_configuration(groups_types, groups_values):
        if is_digit_attribute(groups_types[0]):
            qs = get_root_dynamic_attr_group(
                qs, root_group=groups_types[0], groups_order=groups_order
            )

        else:
            qs = get_root_system_attr_group(
                qs,
                root_group=groups_types[0],
                groups_order=groups_order,
                content_type_key=content_type_key,
            )

    else:
        Model = apps.get_model(
            app_label=content_type.app_label, model_name=content_type.model
        )

        qs = filter_items_for_group(
            qs, groups_types, groups_values, content_type_key, Model
        )

        if is_digit_attribute(groups_types[-1]):
            qs = get_last_dynamic_attr_group(
                qs, last_group=groups_types[-1], groups_order=groups_order
            )

        else:
            qs = get_last_system_attr_group(
                qs,
                last_group=groups_types[-1],
                groups_order=groups_order,
                content_type_key=content_type_key,
            )

    _l.debug(f"handle_groups {time.time() - start_time} seconds ")

    return qs


def count_groups(
    qs,
    groups_types,
    group_values,
    master_user,
    original_qs,
    content_type,
    filter_settings,
    ev_options,
    global_table_search,
):
    Model = apps.get_model(
        app_label=content_type.app_label, model_name=content_type.model
    )

    start_time = time.time()

    content_type_key = f"{content_type.app_label}.{content_type.model}"

    for item in qs:
        q = Q()
        index = 0
        for groups_type in groups_types:
            has_attribute_prefix = has_attribute(groups_type)
            attribute_code = (
                groups_type.split(ATTRIBUTE_PREFIX)[1] if has_attribute_prefix else None
            )
            if has_attribute_prefix:
                if not attribute_code:
                    raise ValidationError(
                        f"Invalid attribute code {groups_type} for attribute type"
                    )

                attribute_type = GenericAttributeType.objects.get(
                    user_code__exact=attribute_code,
                    master_user=master_user,
                    content_type=content_type,
                )

                if len(group_values) and index < len(group_values):
                    value = group_values[index]
                else:
                    value = item["group_identifier"]

                result = []

                attr_type_q = get_q_obj_for_attribute_type(attribute_type, value)

                if attr_type_q != Q():
                    result = Model.objects.filter(q & attr_type_q).values_list(
                        "id", flat=True
                    )

                key = "id__in"

                if len(result):
                    # options[key] = result
                    q = q & Q(**{f"{key}": result})

            else:
                key = groups_type

                if attr_is_relation(content_type_key, key):
                    key = f"{key}__user_code"

                if len(group_values) and index < len(group_values):
                    # TODO: delete in 1.9.0
                    # if group_values[index] == '-':
                    #     q = q & get_q_obj_for_group_dash(content_type_key, Model, groups_type)
                    #
                    # else:
                    #     q = q & Q(**{f"{key}": group_values[index]})

                    q = q & Q(**{f"{key}": group_values[index]})

                else:
                    q = q & Q(**{f"{key}": item["group_identifier"]})

            index = index + 1

        if content_type.model in ["currencyhistory", "currencyhistoryerror"]:
            # options['currency__master_user_id'] = master_user.pk
            q = q & Q(currency__master_user_id=master_user.pk)
        elif content_type.model in ["pricehistory", "pricehistoryerror"]:
            # options['instrument__master_user_id'] = master_user.pk
            q = q & Q(instrument__master_user_id=master_user.pk)
        else:
            # options['master_user_id'] = master_user.pk
            q = q & Q(master_user_id=master_user.pk)

            if (
                content_type.model
                not in [
                    "portfolioregisterrecord",
                    "portfoliohistory",
                    "portfolioreconcilehistory",
                ]
                and ev_options["entity_filters"]
            ):
                if (
                    content_type.model
                    not in [
                        "objecthistory4entry",
                        "generatedevent",
                    ]
                    and "deleted" not in ev_options["entity_filters"]
                ):
                    q = q & Q(is_deleted=False)

                if content_type.model in ["instrument"]:
                    if (
                        "active" in ev_options["entity_filters"]
                        and "inactive" not in ev_options["entity_filters"]
                    ):
                        # options['is_active'] = True
                        q = q & Q(is_active=True)

                    if (
                        "inactive" in ev_options["entity_filters"]
                        and "active" not in ev_options["entity_filters"]
                    ):
                        # options['is_active'] = False
                        q = q & Q(is_active=False)

                if (
                    content_type.model not in ["complextransaction"]
                    and "disabled" not in ev_options["entity_filters"]
                ):
                    q = q & Q(is_enabled=True)

        if content_type.model in ["complextransaction"]:
            # options['is_deleted'] = False
            q = q & Q(is_deleted=False)

        # item['items_count'] = Model.objects.filter(Q(**options)).count()
        # count_cs = Model.objects.filter(Q(**options))
        count_cs = Model.objects.filter(q)

        item["items_count_raw"] = count_cs.count()
        count_cs = handle_filters(count_cs, filter_settings, master_user, content_type)
        if global_table_search:
            count_cs = handle_global_table_search(
                count_cs, global_table_search, Model, content_type
            )
        item["items_count"] = count_cs.count()

    _l.debug(f"count_groups {str(time.time() - start_time)} seconds ")

    return qs
