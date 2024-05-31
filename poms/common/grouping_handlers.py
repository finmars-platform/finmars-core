import logging
import time

from django.apps import apps
from django.db.models import F
from django.db.models import Q
from django.core.exceptions import FieldDoesNotExist

from poms.common.filters import filter_items_for_group, get_q_obj_for_group_dash, get_q_obj_for_attribute_type
from poms.common.filtering_handlers import handle_filters, handle_global_table_search
from poms.obj_attrs.models import GenericAttributeType
from poms.common.utils import attr_is_relation

_l = logging.getLogger('poms.common')


def get_root_dynamic_attr_group(qs, root_group, groups_order):
    start_time = time.time()

    attribute_type = GenericAttributeType.objects.get(id__exact=root_group)

    # attr_qs = GenericAttribute.objects.filter(attribute_type=attribute_type)

    # force_qs_evaluation(qs)

    qs = qs.filter(attributes__attribute_type=attribute_type)

    # force_qs_evaluation(qs)

    # print('get_root_dynamic_attr_group len qs %s' % len(qs))

    # print('attribute_type.value_type %s' % attribute_type.value_type)

    # if attribute_type.value_type == 20:
    #     qs = qs \
    #         .distinct('attributes__value_float') \
    #         .order_by('-attributes__value_float') \
    #         .annotate(group_name=F('attributes__value_float'), group_identifier=F('attributes__value_float'), items_count=Count('attributes__value_float')) \
    #         .values('group_name', 'group_identifier', 'items_count') \
    #         .order_by()

    if attribute_type.value_type == 20:
        qs = qs \
            .values(attr=F('attributes__value_float')) \
            .distinct() \
            .annotate(group_identifier=F('attr'), group_name=F('attr')) \
            .values('group_name', 'group_identifier') \
            .order_by()

    if attribute_type.value_type == 10:
        # qs = qs \
        #     .order_by('attributes__value_string') \
        #     .distinct('attributes__value_string') \
        #     .order_by('-attributes__value_string') \
        #     .annotate(group_name=F('attributes__value_string'), group_identifier=F('attributes__value_string'), items_count=Count('attributes__value_string')) \
        #     .values('group_name', 'group_identifier', 'items_count') \
        #     .order_by()
        qs = qs \
            .values(attr=F('attributes__value_string')) \
            .distinct() \
            .annotate(group_identifier=F('attr'), group_name=F('attr')) \
            .values('group_name', 'group_identifier') \
            .order_by()

    if attribute_type.value_type == 30:
        qs = qs \
            .values('attributes__classifier') \
            .annotate(group_identifier=F('attributes__classifier')) \
            .distinct() \
            .annotate(group_name=F('attributes__classifier__name'), group_identifier=F('attributes__classifier')) \
            .values('group_name', 'group_identifier') \
            .order_by()

    if attribute_type.value_type == 40:
        # qs = qs \
        #     .distinct('attributes__value_date') \
        #     .order_by('-attributes__value_date') \
        #     .annotate(group_name=F('attributes__value_date'), group_identifier=F('attributes__value_date'), items_count=Count('attributes__value_date')) \
        #     .values('group_name', 'group_identifier', 'items_count') \
        #     .order_by()
        qs = qs \
            .values(attr=F('attributes__value_date')) \
            .distinct() \
            .annotate(group_identifier=F('attr'), group_name=F('attr')) \
            .values('group_name', 'group_identifier') \
            .order_by()

    # force_qs_evaluation(qs)

    if groups_order == 'asc':
        qs = qs.order_by(F('group_name').asc())
    if groups_order == 'desc':
        qs = qs.order_by(F('group_name').desc())

    _l.debug("get_root_dynamic_attr_group %s seconds " % (time.time() - start_time))

    return qs


def is_attribute(item):
    return 'attributes.' in item


def get_root_system_attr_group(qs, root_group, groups_order, content_type_key):
    if attr_is_relation(content_type_key, root_group):

        qs = qs.values(root_group) \
            .annotate(group_identifier=F(root_group + '__user_code')) \
            .distinct() \
            .annotate(group_name=F(root_group + '__short_name')) \
            .values('group_name', 'group_identifier') \
            .order_by()
    else:
        qs = qs \
            .distinct() \
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

    # force_qs_evaluation(qs)

    if attribute_type.value_type == 20:
        # .distinct('attributes__value_float') \
        # qs = qs \
        #     .distinct('attributes__value_float') \
        #     .order_by('-attributes__value_float') \
        #     .annotate(group_name=F('attributes__value_float'), group_identifier=F('attributes__value_float'), items_count=Count('attributes__value_float')) \
        #     .values('group_name', 'group_identifier', 'items_count') \
        #     .order_by()

        qs = qs \
            .values(attr=F('attributes__value_float')) \
            .distinct() \
            .annotate(group_identifier=F('attr'), group_name=F('attr')) \
            .values('group_name', 'group_identifier') \
            .order_by()

    if attribute_type.value_type == 10:
        # .distinct('attributes__value_string') \
        # qs = qs \
        #     .distinct() \
        #     .order_by('-attributes__value_string') \
        #     .annotate(group_name=F('attributes__value_string'), group_identifier=F('attributes__value_string'), items_count=Count('attributes__value_string')) \
        #     .values('group_name', 'group_identifier', 'items_count') \
        #     .order_by()
        qs = qs \
            .values(attr=F('attributes__value_string')) \
            .distinct() \
            .annotate(group_identifier=F('attr'), group_name=F('attr')) \
            .values('group_name', 'group_identifier') \
            .order_by()

    if attribute_type.value_type == 30:
        qs = qs \
            .values('attributes__classifier') \
            .annotate(group_identifier=F('attributes__classifier')) \
            .distinct() \
            .annotate(group_name=F('attributes__classifier__name')) \
            .values('group_name', 'group_identifier') \
            .order_by()

    if attribute_type.value_type == 40:
        # qs = qs \
        #     .distinct('attributes__value_date') \
        #     .order_by('-attributes__value_date') \
        #     .annotate(group_name=F('attributes__value_date'), group_identifier=F('attributes__value_date'), items_count=Count('attributes__value_date')) \
        #     .values('group_name', 'group_identifier', 'items_count') \
        #     .order_by()
        qs = qs \
            .values(attr=F('attributes__value_date')) \
            .distinct() \
            .annotate(group_identifier=F('attr'), group_name=F('attr')) \
            .values('group_name', 'group_identifier') \
            .order_by()

    # force_qs_evaluation(qs)

    if groups_order == 'asc':
        qs = qs.order_by(F('group_name').asc())
    if groups_order == 'desc':
        qs = qs.order_by(F('group_name').desc())

    _l.debug("get_last_dynamic_attr_group %s seconds " % (time.time() - start_time))

    return qs


def get_last_system_attr_group(qs, last_group, groups_order, content_type_key):
    print('last_group %s ' % last_group)

    if attr_is_relation(content_type_key, last_group):
        qs = qs.values(last_group) \
            .annotate(group_identifier=F(last_group + '__user_code')) \
            .distinct() \
            .annotate(group_name=F(last_group + '__short_name')) \
            .values('group_name', 'group_identifier') \
            .order_by()
    else:

        qs = qs.distinct(last_group) \
            .annotate(group_name=F(last_group), group_identifier=F(last_group)) \
            .values('group_name', 'group_identifier') \
            .order_by()

    if groups_order == 'desc':
        qs = qs.order_by(F('group_name').desc())
    else:
        qs = qs.order_by(F('group_name').asc())

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

    content_type_key = content_type.app_label + '.' + content_type.model

    if is_root_groups_configuration(groups_types, groups_values):

        if is_dynamic_attribute(groups_types[0]):

            qs = get_root_dynamic_attr_group(qs, root_group=groups_types[0], groups_order=groups_order)


        else:

            qs = get_root_system_attr_group(qs, root_group=groups_types[0], groups_order=groups_order, content_type_key=content_type_key)

    else:

        Model = apps.get_model(app_label=content_type.app_label, model_name=content_type.model)

        # qs = get_queryset_filters(qs, groups_types, groups_values, original_qs, content_type_key, Model)
        qs = filter_items_for_group(qs, groups_types, groups_values, content_type_key, Model)

        # print('handle groups after filters qs len %s' % len(qs))
        # print('handle groups after filters qs len %s' % qs)

        if is_dynamic_attribute(groups_types[-1]):

            qs = get_last_dynamic_attr_group(qs, last_group=groups_types[-1], groups_order=groups_order)

        else:

            qs = get_last_system_attr_group(qs, last_group=groups_types[-1], groups_order=groups_order, content_type_key=content_type_key)

    # print('handle_groups  %s' % qs)

    _l.debug("handle_groups %s seconds " % (time.time() - start_time))

    return qs

def count_groups(qs, groups_types, group_values, master_user, original_qs, content_type, filter_settings, ev_options,
                 global_table_search):
    Model = apps.get_model(app_label=content_type.app_label, model_name=content_type.model)

    start_time = time.time()

    # _l.info('groups_types %s' % groups_types)
    # _l.info('group_values %s' % group_values)

    # _l.info('qs %s' % qs[0])

    content_type_key = content_type.app_label + '.' + content_type.model

    for item in qs:

        # options = {}
        q = Q()

        index = 0

        # _l.info('item %s' % item['group_identifier'])

        #  TODO handle attributes
        for groups_type in groups_types:

            if is_attribute(groups_type):

                attribute_type_user_code = groups_type.split('attributes.')[1]

                attribute_type = GenericAttributeType.objects.get(user_code__exact=attribute_type_user_code,
                                                                  master_user=master_user, content_type=content_type)

                value = None
                if len(group_values) and index < len(group_values):
                    value = group_values[index]
                else:
                    value = item['group_identifier']

                result = []

                attr_type_q = get_q_obj_for_attribute_type(attribute_type, value)

                if attr_type_q != Q():
                    result = Model.objects.filter(q & attr_type_q).values_list('id', flat=True)

                # _l.info('result %s' % result)

                key = 'id__in'

                if len(result):
                    # options[key] = result
                    q = q & Q(**{f"{key}": result})

            else:

                key = groups_type

                if attr_is_relation(content_type_key, groups_type):
                    key = key + '__user_code'

                if len(group_values) and index < len(group_values):

                    # TODO: delete in 1.9.0
                    # if group_values[index] == '-':
                    #     q = q & get_q_obj_for_group_dash(content_type_key, Model, groups_type)
                    #
                    # else:
                    #     q = q & Q(**{f"{key}": group_values[index]})

                    q = q & Q(**{f"{key}": group_values[index]})

                else:
                    q = q & Q(**{f"{key}": item['group_identifier']})

            index = index + 1

        if content_type.model in ['currencyhistory', 'currencyhistoryerror']:
            # options['currency__master_user_id'] = master_user.pk
            q = q & Q(currency__master_user_id=master_user.pk)
        elif content_type.model in ['pricehistory', 'pricehistoryerror']:
            # options['instrument__master_user_id'] = master_user.pk
            q = q & Q(instrument__master_user_id=master_user.pk)
        else:
            # options['master_user_id'] = master_user.pk
            q = q & Q(master_user_id=master_user.pk)

            if content_type.model not in ['portfolioregisterrecord', 'portfoliohistory', 'portfolioreconcilehistory']:
                if ev_options['entity_filters']:

                    if content_type.model not in ['objecthistory4entry', 'generatedevent']:

                        if 'deleted' not in ev_options['entity_filters']:
                            # options['is_deleted'] = False
                            q = q & Q(is_deleted=False)


                    if content_type.model in ['instrument']:
                        if 'active' in ev_options['entity_filters'] and not 'inactive' in ev_options['entity_filters']:
                            # options['is_active'] = True
                            q = q & Q(is_active=True)

                        if 'inactive' in ev_options['entity_filters'] and not 'active' in ev_options['entity_filters']:
                            # options['is_active'] = False
                            q = q & Q(is_active=False)

                    if content_type.model not in ['complextransaction']:
                        if 'disabled' not in ev_options['entity_filters']:
                            # options['is_enabled'] = True
                            q = q & Q(is_enabled=True)

        if content_type.model in ['complextransaction']:
            # options['is_deleted'] = False
            q = q & Q(is_deleted=False)
        # _l.info('options %s' % options)

        # item['items_count'] = Model.objects.filter(Q(**options)).count()
        # count_cs = Model.objects.filter(Q(**options))
        count_cs = Model.objects.filter(q)

        item['items_count_raw'] = count_cs.count()
        count_cs = handle_filters(count_cs, filter_settings, master_user, content_type)
        if global_table_search:
            count_cs = handle_global_table_search(count_cs, global_table_search, Model, content_type)
        item['items_count'] = count_cs.count()

    _l.debug("count_groups %s seconds " % str((time.time() - start_time)))

    return qs
