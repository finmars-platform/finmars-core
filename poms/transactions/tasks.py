from __future__ import unicode_literals, print_function

import logging
import time

from celery import shared_task
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from poms.accounts.models import Account
from poms.obj_perms.models import GenericObjectPermission
from poms.portfolios.models import Portfolio
from poms.transactions.models import Transaction, ComplexTransaction, TransactionType, ComplexTransactionInput
from poms.users.models import Group

_l = logging.getLogger('poms.transactions')

from celery.utils.log import get_task_logger

celery_logger = get_task_logger(__name__)


def get_access_to_inputs(group_id, complex_transaction):

    # print('get_access_to_inputs: group_id %s' % group_id)

    result = None

    portfolios = []
    accounts = []

    for input in ComplexTransactionInput.objects.filter(complex_transaction=complex_transaction['id']):

        if input.portfolio_id:
            portfolios.append(input.portfolio_id)

        if input.account_id:
            accounts.append(input.account_id)

    # print('get_access_to_inputs: accounts %s' % accounts)
    # print('get_access_to_inputs: portfolios %s' % portfolios)

    count = 0

    for id in portfolios:

        try:

            perm = GenericObjectPermission.objects.filter(object_id=id, group=group_id)

            if len(perm):
                count = count + 1

        except GenericObjectPermission.DoesNotExist:
            pass

    for id in accounts:

        try:

            perm = GenericObjectPermission.objects.filter(object_id=id, group=group_id)

            if len(perm):
                count = count + 1

        except GenericObjectPermission.DoesNotExist:
            pass

    # print('get_access_to_inputs: count %s' % count)
    # print('get_access_to_inputs: len portfolio/accounts %s' % str(len(accounts) + len(portfolios)))

    if count == 0:
        result = 'no_view'

    if count > 0:
        result = 'partial_view'

    if count == len(accounts) + len(portfolios):
        result = 'full_view'

    return result


def get_complex_transaction_codename(group_id, complex_transaction, transaction_per_complex,
                                     transaction_permissions_grouped, transaction_type_permissions_grouped,
                                     transaction_ctype):
    result = None

    if complex_transaction['status'] == ComplexTransaction.PENDING:

        inputs_access = get_access_to_inputs(group_id, complex_transaction)

        if inputs_access == 'full_view':

            result = 'view_complextransaction'

        elif inputs_access == 'partial_view':

            if complex_transaction['visibility_status'] == ComplexTransaction.SHOW_PARAMETERS:
                result = 'view_complextransaction_show_parameters'

            if complex_transaction['visibility_status'] == ComplexTransaction.HIDE_PARAMETERS:
                result = 'view_complextransaction_hide_parameters'

    else:

        transactions_total = transaction_per_complex[complex_transaction['id']]
        transactions_in_group = transaction_permissions_grouped[group_id]

        transaction_count = 0

        transactions_ids = []

        for transaction in transactions_in_group:
            if transaction['complex_transaction_id'] == complex_transaction['id']:
                transaction_count = transaction_count + 1
                transactions_ids.append(transaction['id'])

        if transaction_count == transactions_total:
            result = 'view_complextransaction'

        if transaction_count < transactions_total:

            if complex_transaction['visibility_status'] == 1:
                result = 'view_complextransaction_show_parameters'

            if complex_transaction['visibility_status'] == 2:
                result = 'view_complextransaction_hide_parameters'

        if complex_transaction['transaction_type_id'] not in transaction_type_permissions_grouped[
            group_id] and result is not None:
            result = 'view_complextransaction_hide_parameters'

        _l.info('get_complex_transaction_codename complex_transaction id  %s' % complex_transaction['id'])
        _l.info('get_complex_transaction_codename transaction_count %s' % transaction_count)
        _l.info('get_complex_transaction_codename transactions_total %s' % transactions_total)
        _l.info('get_complex_transaction_codename result %s' % result)

        if transaction_count == 0:
            result = None

    # if result is None: # Not Required
    #     _l.debug("Remove all basic transaction permissions group %s complex transaction %s" % (group, complex_transaction['id']))
    #     # If we do not have access to Complex Transaction, then remove permissions to it basic transactions
    #     GenericObjectPermission.objects.filter(group=group, object_id__in=transactions_ids, content_type=transaction_ctype).delete()

    # _l.debug('transactions_in_group transactions_total %s ' % transactions_total)
    # _l.debug('transactions_in_group transaction_count %s ' % transaction_count)
    # _l.debug('complex transaction visibility_status %s ' % complex_transaction['visibility_status'])
    # _l.debug('complex transaction transaction_type_id %s ' % complex_transaction['transaction_type_id'])
    # _l.debug('complex transaction %s codename %s ' % (complex_transaction['id'], result))

    return result


def get_transaction_access_type(group, transaction, accounts_permissions_grouped, portfolios_permissions_grouped):

    result = None

    has_portfolio_access = False
    has_account_position_access = False
    has_account_cash_access = False

    if transaction['portfolio_id'] in portfolios_permissions_grouped[group]:
        has_portfolio_access = True

    if transaction['account_position_id'] in accounts_permissions_grouped[group]:
        has_account_position_access = True

    if transaction['account_cash_id'] in accounts_permissions_grouped[group]:
        has_account_cash_access = True

    if not has_portfolio_access:
        return result  # If we dont have access to portfolio, then we dont have access to transaction

    if not has_account_position_access and not has_account_cash_access:
        return result  # If we dont have access to both accounts, then we dont have access to transaction

    if has_account_position_access:
        result = 'partial_view'

    if has_account_cash_access:
        result = 'partial_view'

    if has_account_position_access and has_account_cash_access and has_portfolio_access:
        result = 'full_view'

    return result


@shared_task(name='transactions.recalculate_permissions_transaction', bind=True)
def recalculate_permissions_transaction(self, instance):
    st = time.perf_counter()

    _l.debug("_recalculate_transactions master_user %s" % instance.master_user)

    data_st = time.perf_counter()

    groups = list(Group.objects.filter(master_user_id=instance.master_user.id).values_list('id', flat=True))

    transactions = Transaction.objects.filter(master_user_id=instance.master_user.id).values('id', 'portfolio_id',
                                                                                             'account_position_id',
                                                                                             'account_cash_id')
    transaction_ctype = ContentType.objects.get_for_model(Transaction)
    transaction_view_permission = Permission.objects.get(content_type=transaction_ctype, codename='view_transaction')
    transaction_partial_view_permission = Permission.objects.get(content_type=transaction_ctype,
                                                                 codename='partial_view_transaction')

    portfolio_ctype = ContentType.objects.get_for_model(Portfolio)
    portfolios_permissions = GenericObjectPermission.objects.filter(group__in=groups, content_type=portfolio_ctype,
                                                                    permission__codename='view_portfolio').values(
        'group', 'object_id')

    account_ctype = ContentType.objects.get_for_model(Account)
    accounts_permissions = GenericObjectPermission.objects.filter(group__in=groups, content_type=account_ctype,
                                                                  permission__codename='view_account').values('group',
                                                                                                              'object_id')

    _l.debug('_recalculate_transactions data load done: %s', (time.perf_counter() - data_st))

    _l.debug("_recalculate_transactions portfolios_permissions len %s" % len(list(portfolios_permissions)))
    _l.debug("_recalculate_transactions accounts_permissions len %s" % len(list(accounts_permissions)))
    _l.debug("_recalculate_transactions groups len %s" % len(list(groups)))
    _l.debug("_recalculate_transactions transactions len %s" % len(list(transactions)))

    logic_st = time.perf_counter()

    accounts_permissions_grouped = {}
    portfolios_permissions_grouped = {}

    for group in groups:
        accounts_permissions_grouped[group] = []
        portfolios_permissions_grouped[group] = []

    for perm in accounts_permissions:
        accounts_permissions_grouped[perm['group']].append(perm['object_id'])

    _l.debug("_recalculate_transactions accounts_permissions_grouped done")

    for perm in portfolios_permissions:
        portfolios_permissions_grouped[perm['group']].append(perm['object_id'])

    _l.debug("_recalculate_transactions portfolios_permissions_grouped done")

    permissions = []

    for group in groups:

        for transaction in transactions:

            access_type = get_transaction_access_type(group, transaction, accounts_permissions_grouped,
                                                      portfolios_permissions_grouped)

            if access_type:

                if access_type == 'full_view':
                    object_permission = GenericObjectPermission(group_id=group,
                                                                content_type=transaction_ctype,
                                                                object_id=transaction['id'],
                                                                permission=transaction_view_permission)

                    permissions.append(object_permission)

                if access_type == 'partial_view':
                    object_permission = GenericObjectPermission(group_id=group,
                                                                content_type=transaction_ctype,
                                                                object_id=transaction['id'],
                                                                permission=transaction_partial_view_permission)

                    permissions.append(object_permission)

    _l.debug('_recalculate_transactions logic_st done: %s', (time.perf_counter() - logic_st))

    deletion_st = time.perf_counter()

    GenericObjectPermission.objects.filter(group__in=groups, content_type=transaction_ctype).delete()

    _l.debug('_recalculate_transactions transaction deletion done: %s', (time.perf_counter() - deletion_st))

    create_st = time.perf_counter()

    GenericObjectPermission.objects.bulk_create(permissions)

    _l.debug('_recalculate_transactions transaction creation done: %s', (time.perf_counter() - create_st))

    _l.debug('_recalculate_transactions permissions len %s' % len(permissions))

    recalculate_permissions_complex_transaction(instance)

    _l.debug('_recalculate_transactions done: %s', (time.perf_counter() - st))

    return instance


@shared_task(name='transactions.recalculate_permissions_complex_transaction', bind=True)
def recalculate_permissions_complex_transaction(self, instance):
    st = time.perf_counter()
    data_st = time.perf_counter()

    groups = list(Group.objects.filter(master_user_id=instance.master_user.id).values_list('id', flat=True))
    complex_transactions = ComplexTransaction.objects.filter(master_user_id=instance.master_user.id).values('id',
                                                                                                            'status',
                                                                                                            'visibility_status',
                                                                                                            'transaction_type_id')

    transactions = Transaction.objects.filter(master_user_id=instance.master_user.id).values('id',
                                                                                             'complex_transaction_id')
    transaction_ctype = ContentType.objects.get_for_model(Transaction)
    transaction_permissions = GenericObjectPermission.objects.filter(group__in=groups,
                                                                     content_type=transaction_ctype,
                                                                     permission__codename__in=['view_transaction', 'partial_view_transaction']).values(
        'id',
        'group_id',
        'object_id')

    transaction_type_ctype = ContentType.objects.get_for_model(TransactionType)
    transaction_type_permissions = GenericObjectPermission.objects.filter(group__in=groups,
                                                                          content_type=transaction_type_ctype).values(
        'id',
        'group_id',
        'object_id')

    codenames = ['view_complextransaction', 'view_complextransaction_show_parameters',
                 'view_complextransaction_hide_parameters']

    complex_transaction_ctype = ContentType.objects.get_for_model(ComplexTransaction)
    complex_transaction_view_permission = Permission.objects.filter(content_type=complex_transaction_ctype,
                                                                    codename__in=codenames)

    _l.debug('_recalculate_transactions data load done: %s', (time.perf_counter() - data_st))
    _l.debug('_recalculate_complex_transaction complex_transactions len %s' % len(list(complex_transactions)))

    codenames_dict = {}

    for item in complex_transaction_view_permission:
        codenames_dict[item.codename] = item

    permissions = []

    transaction_per_complex = {}

    for complex_transaction in complex_transactions:

        if complex_transaction['id'] not in transaction_per_complex:
            transaction_per_complex[complex_transaction['id']] = 0

        for transaction in transactions:

            if transaction['complex_transaction_id'] == complex_transaction['id']:
                transaction_per_complex[complex_transaction['id']] = transaction_per_complex[
                                                                         complex_transaction['id']] + 1

    for transaction in transactions:
        for permission in transaction_permissions:
            if transaction['id'] == permission['object_id']:
                permission['complex_transaction_id'] = transaction['complex_transaction_id']

    transaction_permissions_grouped = {}

    for group in groups:
        transaction_permissions_grouped[group] = []

    for permission in transaction_permissions:
        transaction_permissions_grouped[permission['group_id']].append(permission)

    transaction_type_permissions_grouped = {}

    for group in groups:
        transaction_type_permissions_grouped[group] = []

    for permission in transaction_type_permissions:
        transaction_type_permissions_grouped[permission['group_id']].append(permission['object_id'])

    for group_id in groups:

        for complex_transaction in complex_transactions:

            codename = get_complex_transaction_codename(group_id, complex_transaction, transaction_per_complex,
                                                        transaction_permissions_grouped,
                                                        transaction_type_permissions_grouped, transaction_ctype)

            if codename:
                object_permission = GenericObjectPermission(group_id=group_id,
                                                            content_type=complex_transaction_ctype,
                                                            object_id=complex_transaction['id'],
                                                            permission=codenames_dict[codename])

                permissions.append(object_permission)

    deletion_st = time.perf_counter()

    GenericObjectPermission.objects.filter(group__in=groups, content_type=complex_transaction_ctype).delete()

    _l.debug('recalculate_complex_transaction transaction deletion done: %s',
             (time.perf_counter() - deletion_st))

    create_st = time.perf_counter()

    GenericObjectPermission.objects.bulk_create(permissions)

    _l.debug('recalculate_complex_transaction transaction creation done: %s',
             (time.perf_counter() - create_st))

    _l.debug('recalculate_complex_transaction permissions len %s' % len(permissions))

    _l.debug('recalculate_complex_transaction done: %s', (time.perf_counter() - st))

    return instance
