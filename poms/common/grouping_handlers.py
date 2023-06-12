import logging
import time

from django.apps import apps
from django.db.models import F
from django.db.models import Q

from poms.common.filtering_handlers import handle_filters, handle_global_table_search
from poms.obj_attrs.models import GenericAttributeType

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


def is_relation(item, content_type_key):

    if content_type_key == 'transactions.transactiontype':
        if item == 'group':
            return False # because configuration


    return item in ['type', 'currency', 'instrument',
                    'instrument_type', 'group',
                    'pricing_policy', 'portfolio',
                    'transaction_type', 'transaction_currency',
                    'cash_currency', 'valuation_currency',
                    'portfolio_register',
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

                    'subgroup',

                    'instrument_class',
                    'transaction_class',
                    'daily_pricing_model',
                    'payment_size_detail'

                    ]


def is_attribute(item):
    return 'attributes.' in item


def get_root_system_attr_group(qs, root_group, groups_order, content_type_key):
    if is_relation(root_group, content_type_key):

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


def get_last_system_attr_group(qs, last_group, groups_order):
    print('last_group %s ' % last_group)

    if is_relation(last_group):
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


def get_queryset_filters(qs, groups_types, groups_values, original_qs):
    start_time = time.time()

    i = 0

    # print('get_queryset_filters len %s' % len(qs    ))

    # force_qs_evaluation(qs)

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

                    qs = qs.filter(Q(**{res_attr + '__isnull': True}) | Q(**{res_attr: '-'}))

                else:
                    if is_relation(attr):
                        params[attr + '__user_code'] = groups_values[i]
                    else:
                        params[attr] = groups_values[i]

                    qs = qs.filter(**params)

        # force_qs_evaluation(qs)

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

    content_type_key = content_type.app_label + '.' + content_type.model

    if is_root_groups_configuration(groups_types, groups_values):

        if is_dynamic_attribute(groups_types[0]):

            qs = get_root_dynamic_attr_group(qs, root_group=groups_types[0], groups_order=groups_order)


        else:

            qs = get_root_system_attr_group(qs, root_group=groups_types[0], groups_order=groups_order, content_type_key=content_type_key)

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


def count_groups(qs, groups_types, group_values, master_user, original_qs, content_type, filter_settings, ev_options,
                 global_table_search):
    Model = apps.get_model(app_label=content_type.app_label, model_name=content_type.model)

    start_time = time.time()

    # _l.info('groups_types %s' % groups_types)
    # _l.info('group_values %s' % group_values)

    # _l.info('qs %s' % qs[0])

    content_type_key = content_type.app_label + '.' + content_type.model

    for item in qs:

        options = {}

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

                attribute_options = {
                    "attributes__attribute_type": attribute_type
                }

                # _l.info('attribute value %s' % value)

                # add previous options
                for key, val in options.items():
                    attribute_options[key] = val

                if attribute_type.value_type == 20:
                    attribute_options["attributes__value_float"] = value

                    result = Model.objects.filter(Q(**attribute_options)).values_list('id', flat=True)

                if attribute_type.value_type == 10:
                    attribute_options["attributes__value_string"] = value

                    # _l.info('attribute_options %s' % attribute_options)

                    result = Model.objects.filter(Q(**attribute_options)).values_list('id', flat=True)

                if attribute_type.value_type == 30:
                    attribute_options["attributes__classifier"] = value

                    result = Model.objects.filter(Q(**attribute_options)).values_list('id', flat=True)

                    # _l.info('attributes__classifier__name group_values %s ' % group_values)
                    # _l.info('attributes__classifier__name index %s ' % index)
                    # _l.info('attributes__classifier__name value %s ' % value)
                    # _l.info('attributes__classifier__name result %s ' % result)

                if attribute_type.value_type == 40:
                    attribute_options["attributes__value_date"] = value

                    result = Model.objects.filter(Q(**attribute_options)).values_list('id', flat=True)

                # _l.info('result %s' % result)

                key = 'id__in'

                if len(result):
                    options[key] = result

            else:

                key = groups_type

                if is_relation(groups_type, content_type_key):
                    key = key + '__user_code'

                if len(group_values) and index < len(group_values):
                    options[key] = group_values[index]
                else:
                    options[key] = item['group_identifier']

            index = index + 1

        if content_type.model in ['currencyhistory', 'currencyhistoryerror']:
            options['currency__master_user_id'] = master_user.pk
        elif content_type.model in ['pricehistory', 'pricehistoryerror']:
            options['instrument__master_user_id'] = master_user.pk
        else:
            options['master_user_id'] = master_user.pk

            if content_type.model not in ['portfolioregisterrecord']:
                if ev_options['entity_filters']:

                    if content_type.model not in ['objecthistory4entry', 'generatedevent']:

                        if 'deleted' not in ev_options['entity_filters']:
                            options['is_deleted'] = False

                    if content_type.model in ['instrument']:
                        if 'active' in ev_options['entity_filters'] and not 'inactive' in ev_options['entity_filters']:
                            options['is_active'] = True

                        if 'inactive' in ev_options['entity_filters'] and not 'active' in ev_options['entity_filters']:
                            options['is_active'] = False

                    if content_type.model not in ['complextransaction']:
                        if 'disabled' not in ev_options['entity_filters']:
                            options['is_enabled'] = True

        if content_type.model in ['complextransaction']:
            options['is_deleted'] = False

        # _l.info('options %s' % options)

        # item['items_count'] = Model.objects.filter(Q(**options)).count()
        count_cs = Model.objects.filter(Q(**options))
        item['items_count_raw'] = count_cs.count()
        count_cs = handle_filters(count_cs, filter_settings, master_user, content_type)
        if global_table_search:
            count_cs = handle_global_table_search(count_cs, global_table_search, Model, content_type)
        item['items_count'] = count_cs.count()

    _l.debug("count_groups %s seconds " % str((time.time() - start_time)))

    return qs
