from __future__ import unicode_literals

from poms.common.tests import BaseApiWithPermissionTestCase, BaseAttributeTypeApiTestCase, \
    BaseNamedModelTestCase
from poms.transactions.models import TransactionType, TransactionTypeGroup, Transaction


def load_tests(loader, standard_tests, pattern):
    from poms.common.tests import load_tests as t
    return t(loader, standard_tests, pattern)


class TransactionTypeGroupApiTestCase(BaseNamedModelTestCase, BaseApiWithPermissionTestCase):
    model = TransactionTypeGroup

    def setUp(self):
        super(TransactionTypeGroupApiTestCase, self).setUp()

        self._url_list = '/api/v1/transactions/transaction-type-group/'
        self._url_object = '/api/v1/transactions/transaction-type-group/%s/'
        self._change_permission = 'change_transactiontypegroup'

    def _create_obj(self, name='transaction_type_group'):
        return self.create_transaction_type_group(name, self._a_master_user)

    def _get_obj(self, name='transaction_type_group'):
        return self.get_transaction_type_group(name, self._a_master_user)


class TransactionTypeApiTestCase(BaseNamedModelTestCase, BaseApiWithPermissionTestCase):
    model = TransactionType

    def setUp(self):
        super(TransactionTypeApiTestCase, self).setUp()

        self._url_list = '/api/v1/transactions/transaction-type/'
        self._url_object = '/api/v1/transactions/transaction-type/%s/'
        # self._change_permission = 'change_transactiontype'

        self.group_def = self.get_transaction_type_group('-', self._a_master_user)
        # self.assign_perms(self.group_def, self._a, users=[self._a0, self._a1, self._a2], groups=['g1', 'g2'],
        #                   perms=get_perms_codename(self.group_def, ['change', 'view']))

    def _create_obj(self, name='transaction_type'):
        return self.create_transaction_type(name, self._a_master_user, group=self.group_def)

    def _get_obj(self, name='transaction_type'):
        return self.get_transaction_type_group(name, self._a_master_user)

    def _make_new_data(self, **kwargs):
        group = self.get_transaction_type_group(kwargs['group'],
                                                self._a_master_user) if 'group' in kwargs else self.group_def
        kwargs['group'] = group.id

        if 'display_expr' not in kwargs:
            kwargs['display_expr'] = 'name'
        if 'portfolios' not in kwargs:
            kwargs['portfolios'] = []
        if 'instrument_types' not in kwargs:
            kwargs['instrument_types'] = []
        if 'inputs' not in kwargs:
            kwargs['inputs'] = []
        if 'actions' not in kwargs:
            kwargs['actions'] = []

        data = super(TransactionTypeApiTestCase, self)._make_new_data(**kwargs)
        return data


class TransactionAttributeTypeApiTestCase(BaseAttributeTypeApiTestCase):
    base_model = Transaction

    def setUp(self):
        super(TransactionAttributeTypeApiTestCase, self).setUp()

        self._url_list = '/api/v1/transactions/transaction-attribute-type/'
        self._url_object = '/api/v1/transactions/transaction-attribute-type/%s/'
        # self._change_permission = 'change_transactionattributetype'

# class TransactionApiTestCase(BaseNamedModelTestCase, BaseApiWithPermissionTestCase,
#                             BaseApiWithAttributesTestCase):
#     model = Transaction
#     attribute_type_model = TransactionAttributeType
#     classifier_model = TransactionClassifier
#
#     def setUp(self):
#         super(TransactionApiTestCase, self).setUp()
#
#         self._url_list = '/api/v1/instruments/instrument/'
#         self._url_object = '/api/v1/instruments/instrument/%s/'
#         self._change_permission = 'change_instrument'
#
#         self.type_def = self.create_instrument_type('-', self._a)
#         self.assign_perms(self.type_def, self._a, users=[self._a0, self._a1, self._a2], groups=['g1', 'g2'],
#                           perms=get_perms_codename(self.type_def, ['change', 'view']))
#
#         self.type1 = self.create_instrument_type('type1', self._a)
#         self.type2_a1 = self.create_instrument_type('type2_a1', self._a)
#         self.assign_perms(self.type2_a1, self._a, users=[self._a1], groups=[])
#         self.type3_g2 = self.create_instrument_type('type3_g2', self._a)
#         self.assign_perms(self.type3_g2, self._a, groups=['g2'])
#
#     def _create_obj(self, name='instrument', instrument_type=None, pricing_currency=None, accrued_currency=None):
#         instrument_type = instrument_type or self.type_def
#         pricing_currency = pricing_currency or self.get_currency(settings.CURRENCY_CODE, self._a)
#         accrued_currency = accrued_currency or self.get_currency(settings.CURRENCY_CODE, self._a)
#         return self.create_instrument(name, self._a, instrument_type=instrument_type, pricing_currency=pricing_currency,
#                                       accrued_currency=accrued_currency)
#
#     def _get_obj(self, name='instrument'):
#         return self.get_instrument(name, self._a_master_user)
#
#     def _make_new_data(self, **kwargs):
#         instrument_type = self.get_instrument_type(kwargs.get('instrument_type', '-'), self._a)
#         kwargs['instrument_type'] = instrument_type.id
#         pricing_currency = self.get_currency(kwargs.get('pricing_currency', settings.CURRENCY_CODE), self._a)
#         kwargs['pricing_currency'] = pricing_currency.id
#         accrued_currency = self.get_currency(kwargs.get('accrued_currency', settings.CURRENCY_CODE), self._a)
#         kwargs['accrued_currency'] = accrued_currency.id
#         data = super(TransactionApiTestCase, self)._make_new_data(**kwargs)
#         return data
#
#     def test_add_by_user_with_type_without_perms(self):
#         data = self._make_new_data(instrument_type='type1')
#         response = self._add(self._a1, data)
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#
#     def test_add_by_group_with_type_without_perms(self):
#         data = self._make_new_data(instrument_type='type1')
#         response = self._add(self._a2, data)
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
