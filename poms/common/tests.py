from __future__ import unicode_literals, division, print_function

import json
import unittest
import uuid

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils.text import Truncator
from rest_framework import status
from rest_framework.test import APITestCase

from poms.accounts.models import AccountType, Account
from poms.chats.models import Thread, Message, DirectMessage, ThreadGroup
from poms.counterparties.models import Counterparty, Responsible, CounterpartyGroup, ResponsibleGroup
from poms.currencies.models import Currency
from poms.instruments.models import InstrumentClass, InstrumentType, Instrument
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier
from poms.obj_perms.utils import assign_perms3, get_all_perms, get_change_perms
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy3Group, Strategy2Group, Strategy1Group, Strategy1Subgroup, Strategy2Subgroup, \
    Strategy3Subgroup, Strategy1, Strategy2, Strategy3
from poms.transactions.models import TransactionTypeGroup, TransactionType
from poms.users.models import MasterUser, Member, Group

ABSTRACT_TESTS = list()


def load_tests(loader, standard_tests, pattern):
    result = []

    for test_case in standard_tests:

        if len(test_case._tests):

            add = True

            for test in test_case._tests:

                if type(test) in ABSTRACT_TESTS:
                    add = False

            if add:
                result.append(test_case)

    return loader.suiteClass(result)


class BaseApiTestCase(APITestCase):
    model = None
    ordering_fields = None
    filtering_fields = None

    # def __init__(self, *args, **kwargs):
    #     super(BaseApiTestCase, self).__init__(*args, **kwargs)

    def setUp(self):
        super(BaseApiTestCase, self).setUp()

        if self.__class__ is BaseApiTestCase:
            raise unittest.SkipTest("Base class")

        # print('setUp self %s' % self)

        self._url_list = None
        self._url_object = None
        if self.model:
            self._change_permission = get_change_perms(self.model)[0]
            self.all_permissions = set(get_all_perms(self.model))
            self.default_owner_permissions = set(get_all_perms(self.model))

        self._a_master_user = str(uuid.uuid4())
        self._a_owner_user = str(uuid.uuid4())
        self._a_admin_user = str(uuid.uuid4())
        self._a_user_full_access = str(uuid.uuid4())
        self._a_user_viewonly_access = str(uuid.uuid4())
        self._a_user_restricted_access = str(uuid.uuid4())

        self.create_user(self._a_owner_user)

        mua = self.create_master_user(name=self._a_master_user, user=self._a_owner_user)
        self.def_g = Group.objects.get(master_user=mua, role=Group.ADMIN)
        # self.create_group('g1', self._a_admin_user)
        # self.create_group('g2', self._a_admin_user)

        self.create_user(self._a_admin_user)
        self.create_user(self._a_user_full_access)
        self.create_user(self._a_user_viewonly_access)
        self.create_user(self._a_user_restricted_access)
        self.create_member(user=self._a_owner_user, master_user=mua, is_owner=True, is_admin=True)
        self.create_member(user=self._a_admin_user, master_user=mua, is_owner=False, is_admin=True)
        # self.create_member(user=self._a_user_viewonly_access, master_user=mua, groups=['Default', 'g1'])
        # self.create_member(user=self._a_user_restricted_access, master_user=mua, groups=['Default', 'g2'])

    def create_name(self):
        return uuid.uuid4().hex

    def create_user_code(self, name=None):
        if not name:
            name = uuid.uuid4().hex
        return Truncator(name).chars(20, truncate='')

    def create_master_user(self, name, user=None):
        if user:
            user = self.get_user(user)
        return MasterUser.objects.create_master_user(name=name, user=user)

    def get_master_user(self, name):
        return MasterUser.objects.get(name=name)

    def create_user(self, name):
        return User.objects.create_user(name, password=name)

    def get_user(self, name):
        return User.objects.get(username=name)

    def create_member(self, user, master_user, is_owner=False, is_admin=False, groups=None):
        master_user = self.get_master_user(master_user)
        user = self.get_user(user)
        member = Member.objects.create(master_user=master_user, user=user, is_owner=is_owner, is_admin=is_admin)
        if groups:
            member.groups = Group.objects.filter(master_user=master_user, name__in=groups)
        # print('create member: id=%s, name=%s, master_user=%s, is_owner=%s, is_admin=%s, groups=%s' %
        #       (member.id, user, master_user, is_owner, is_admin, groups))
        return member

    def get_member(self, user, master_user):
        return Member.objects.get(user__username=user, master_user__name=master_user)

    def create_group(self, name, master_user):
        master_user = self.get_master_user(master_user)
        group = Group.objects.create(master_user=master_user, name=name)
        # print('create group: id=%s, name=%s, master_user=%s' %
        #       (group.id, name, master_user))
        return group

    def get_group(self, name, master_user):
        return Group.objects.get(name=name, master_user__name=master_user)

    def create_attribute_type(self, name, master_user, base_model=None, value_type=GenericAttributeType.STRING,
                              classifier_tree=None):
        master_user = self.get_master_user(master_user)

        base_model = base_model or self.model
        attribute_type = GenericAttributeType.objects.create(master_user=master_user,
                                                             content_type=ContentType.objects.get_for_model(base_model),
                                                             name=name, value_type=value_type)
        if classifier_tree and value_type == GenericAttributeType.CLASSIFIER:
            for root in classifier_tree:
                self.create_classifier(attribute_type, root, None)
        return attribute_type

    def create_classifier(self, attribute_type, node, parent):
        name = node['name']
        children = node.get('children', [])
        classifier = GenericClassifier.objects.create(attribute_type=attribute_type, name=name, parent=parent)
        for child in children:
            self.create_classifier(attribute_type, child, classifier)
        return classifier

    def get_classifier(self, name, master_user, classifier_name=None):
        attribute_type = self.get_attribute_type(name, master_user)
        classifier = GenericClassifier.objects.get(attribute_type=attribute_type, name=classifier_name)
        return classifier

    def get_attribute_type(self, name, master_user, base_model=None):
        base_model = base_model or self.model
        return GenericAttributeType.objects.get(name=name, content_type=ContentType.objects.get_for_model(base_model),
                                                master_user__name=master_user)

    def create_currency(self, name, master_user):
        master_user = self.get_master_user(master_user)
        currency = Currency.objects.create(master_user=master_user, name=name)
        return currency

    def get_currency(self, name, master_user):
        if name:
            return Currency.objects.get(user_code=name, master_user__name=master_user)
        else:
            master_user = self.get_master_user(master_user)
            return master_user.currency

    def create_account_type(self, name, master_user):
        master_user = self.get_master_user(master_user)
        account_type = AccountType.objects.create(master_user=master_user, name=name)
        return account_type

    def get_account_type(self, name, master_user):
        return AccountType.objects.get(name=name, master_user__name=master_user)

    def create_account_attribute_type(self, name, master_user, value_type=GenericAttributeType.STRING,
                                      classifiers=None):
        return self.create_attribute_type(name, master_user, base_model=Account, value_type=value_type,
                                          classifier_tree=classifiers)

    def get_account_attribute_type(self, name, master_user):
        return self.get_attribute_type(name, master_user, base_model=Account)

    def create_account(self, name, master_user, account_type='-'):
        account_type = self.get_account_type(account_type, master_user)
        master_user = self.get_master_user(master_user)
        account = Account.objects.create(master_user=master_user, type=account_type, name=name)
        return account

    def get_account(self, name, master_user):
        return Account.objects.get(name=name, master_user__name=master_user)

    def create_counterparty_group(self, name, master_user):
        master_user = self.get_master_user(master_user)
        counterparty_group = CounterpartyGroup.objects.create(master_user=master_user, name=name)
        return counterparty_group

    def get_counterparty_group(self, name, master_user):
        return CounterpartyGroup.objects.get(name=name, master_user__name=master_user)

    def create_counterparty(self, name, master_user, group='-'):
        master_user = self.get_master_user(master_user)
        group = self.get_counterparty_group(group, master_user)
        counterparty = Counterparty.objects.create(master_user=master_user, group=group, name=name)
        return counterparty

    def get_counterparty(self, name, master_user):
        return Counterparty.objects.get(name=name, master_user__name=master_user)

    def create_responsible_group(self, name, master_user):
        master_user = self.get_master_user(master_user)
        responsible = ResponsibleGroup.objects.create(master_user=master_user, name=name)
        return responsible

    def get_responsible_group(self, name, master_user):
        return ResponsibleGroup.objects.get(name=name, master_user__name=master_user)

    def create_responsible(self, name, master_user, group='-'):
        master_user = self.get_master_user(master_user)
        group = self.get_responsible_group(group, master_user)
        responsible = Responsible.objects.create(master_user=master_user, group=group, name=name)
        return responsible

    def get_responsible(self, name, master_user):
        return Responsible.objects.get(name=name, master_user__name=master_user)

    def create_portfolio(self, name, master_user):
        master_user = self.get_master_user(master_user)
        portfolio = Portfolio.objects.create(master_user=master_user, name=name)
        return portfolio

    def get_portfolio(self, name, master_user):
        return Portfolio.objects.get(name=name, master_user__name=master_user)

    def create_instrument_type(self, name, master_user, instrument_class=None, accrued_currency=None):
        master_user = self.get_master_user(master_user)

        accrued_currency = self.get_currency(accrued_currency, master_user)

        instrument_class = instrument_class or InstrumentClass.objects.get(pk=InstrumentClass.GENERAL)
        instrument_type = InstrumentType.objects.create(master_user=master_user, instrument_class=instrument_class,
                                                        name=name, accrued_currency=accrued_currency)
        return instrument_type

    def get_instrument_type(self, name, master_user):
        return InstrumentType.objects.get(name=name, master_user__name=master_user)

    def create_instrument(self, name, master_user, instrument_type=None, pricing_currency=None, accrued_currency=None):
        instrument_type = self.get_instrument_type(instrument_type, master_user)
        pricing_currency = self.get_currency(pricing_currency, master_user)
        accrued_currency = self.get_currency(accrued_currency, master_user)
        master_user = self.get_master_user(master_user)
        instrument = Instrument.objects.create(master_user=master_user, instrument_type=instrument_type, name=name,
                                               pricing_currency=pricing_currency, accrued_currency=accrued_currency)
        return instrument

    def get_instrument(self, name, master_user):
        return Instrument.objects.get(name=name, master_user__name=master_user)

    def create_strategy_group(self, code, name, master_user):
        if code == 1:
            model = Strategy1Group
        elif code == 2:
            model = Strategy2Group
        elif code == 3:
            model = Strategy3Group
        else:
            raise ValueError('invalid strategy code')
        master_user = self.get_master_user(master_user)
        strategy = model.objects.create(master_user=master_user, name=name)
        return strategy

    def get_strategy_group(self, code, name, master_user):
        if code == 1:
            model = Strategy1Group
        elif code == 2:
            model = Strategy2Group
        elif code == 3:
            model = Strategy3Group
        else:
            raise ValueError('invalid strategy code')
        return model.objects.get(name=name, master_user__name=master_user)

    def create_strategy_subgroup(self, code, name, master_user, group='-'):
        if code == 1:
            model = Strategy1Subgroup
        elif code == 2:
            model = Strategy2Subgroup
        elif code == 3:
            model = Strategy3Subgroup
        else:
            raise ValueError('invalid strategy code')
        group = self.get_strategy_group(code, group, master_user)
        master_user = self.get_master_user(master_user)
        strategy = model.objects.create(master_user=master_user, name=name, group=group)
        return strategy

    def get_strategy_subgroup(self, code, name, master_user):
        if code == 1:
            model = Strategy1Subgroup
        elif code == 2:
            model = Strategy2Subgroup
        elif code == 3:
            model = Strategy3Subgroup
        else:
            raise ValueError('invalid strategy code')
        return model.objects.get(name=name, master_user__name=master_user)

    def create_strategy(self, code, name, master_user, subgroup='-'):
        if code == 1:
            model = Strategy1
        elif code == 2:
            model = Strategy2
        elif code == 3:
            model = Strategy3
        else:
            raise ValueError('invalid strategy code')
        subgroup = self.get_strategy_subgroup(code, subgroup, master_user)
        master_user = self.get_master_user(master_user)
        strategy = model.objects.create(master_user=master_user, name=name, subgroup=subgroup)
        return strategy

    def get_strategy(self, code, name, master_user):
        if code == 1:
            model = Strategy1
        elif code == 2:
            model = Strategy2
        elif code == 3:
            model = Strategy3
        else:
            raise ValueError('invalid strategy code')
        return model.objects.get(name=name, master_user__name=master_user)

    def create_transaction_type_group(self, name, master_user):
        master_user = self.get_master_user(master_user)
        transaction_type_group = TransactionTypeGroup.objects.create(master_user=master_user, name=name)
        return transaction_type_group

    def get_transaction_type_group(self, name, master_user):
        return TransactionTypeGroup.objects.get(name=name, master_user__name=master_user)

    def create_transaction_type(self, name, master_user, group=None, display_expr='name'):
        master_user = self.get_master_user(master_user)
        group = self.get_transaction_type_group(group, master_user) if group else None
        transaction_type = TransactionType.objects.create(master_user=master_user, name=name, display_expr=display_expr,
                                                          group=group)
        return transaction_type

    def get_transaction_type(self, name, master_user):
        return TransactionType.objects.get(name=name, master_user__name=master_user)

    def create_thread_group(self, name, master_user):
        master_user = self.get_master_user(master_user)
        thread = ThreadGroup.objects.create(master_user=master_user, name=name)
        return thread

    def get_thread_group(self, name, master_user):
        return ThreadGroup.objects.get(name=name, master_user__name=master_user)

    def create_thread(self, subject, master_user, thread_group='-', is_closed=False):
        thread_group = self.get_thread_group(thread_group, master_user)
        master_user = self.get_master_user(master_user)
        thread = Thread.objects.create(master_user=master_user, thread_group=thread_group, subject=subject,
                                       is_closed=is_closed)
        return thread

    def get_thread(self, subject, master_user):
        return Thread.objects.get(subject=subject, master_user__name=master_user)

    def create_message(self, text, sender, master_user, thread):
        thread = self.get_thread(thread, master_user)
        sender = self.get_member(sender, master_user)
        message = Message.objects.create(text=text, sender=sender, thread=thread)
        return message

    def get_message(self, text, master_user):
        return Message.objects.get(text=text, thread__master_user__name=master_user)

    def create_direct_message(self, text, master_user, sender, recipient):
        sender = self.get_member(sender, master_user)
        recipient = self.get_member(recipient, master_user)
        message = DirectMessage.objects.create(text=text, sender=sender, recipient=recipient)
        return message

    def get_direct_message(self, text, master_user):
        return DirectMessage.objects.get(text=text, sender__master_user__name=master_user,
                                         recipient__master_user__name=master_user)

    def assign_perms(self, obj, master_user, users=None, groups=None, perms=None):
        if users:
            members = Member.objects.filter(user__username__in=users, master_user__name=master_user)
        else:
            members = None
        if groups:
            groups = Group.objects.filter(name__in=groups, master_user__name=master_user)

        if perms is None:
            # perms = self.default_owner_permissions
            perms = set(get_all_perms(obj))

        perms_l = []
        if members:
            for member in members:
                for perm in perms:
                    perms_l.append({
                        'group': None,
                        'member': member,
                        'permission': perm
                    })
        if groups:
            for group in groups:
                for perm in perms:
                    perms_l.append({
                        'group': group,
                        'member': None,
                        'permission': perm
                    })
        assign_perms3(obj, perms=perms_l)

    def _dump(self, data):
        # pprint.pprint(data, width=40)
        print(json.dumps(data, indent=2, sort_keys=True))

    def _create_obj(self, name='acc'):
        print('setUp self %s' % self)
        raise NotImplementedError()
        # return self.create_account(name, self._a_master_user)

    def _get_obj(self, name='acc'):
        print('setUp self %s' % self)
        raise NotImplementedError()
        # return self.get_account(name, self._a_master_user)

    def _list(self, user, data=None):
        self.client.login(username=user, password=user)
        response = self.client.get(self._url_list, format='json', data=data)
        self.client.logout()
        return response

    def _list_order(self, user, field, count=None):
        response = self._list(user, data={'ordering': '%s' % field})
        self.assertEqual(response.status_code, status.HTTP_200_OK, 'Failed ordering: field=%s' % field)
        # if count is not None:
        #     self.assertEqual(response.data['count'], count, 'Failed ordering: field=%s' % field)

        response = self._list(user, data={'ordering': '-%s' % field})
        self.assertEqual(response.status_code, status.HTTP_200_OK, 'Failed ordering: field=-%s' % field)
        # if count is not None:
        #     self.assertEqual(response.data['count'], count, 'Failed ordering: field=-%s' % field)

    def _list_filter(self, user, field, value, count=None):
        response = self._list(user, data={field: value})
        self.assertEqual(response.status_code, status.HTTP_200_OK, 'Failed filtering: field=-%s' % field)
        # if count is not None:
        #     self.assertEqual(response.data['count'], count, 'Failed filtering: field=-%s' % field)
        return response

    def _get(self, user, id):
        self.client.login(username=user, password=user)
        response = self.client.get(self._url_object % id, format='json')
        self.client.logout()
        return response

    def _log_response(self, response):
        # if response.status_code in (status.HTTP_400_BAD_REQUEST,):
        #     print('response: status_code=%s, data=%s' % (response.status_code, response.data))
        pass

    def _add(self, user, data):
        self.client.login(username=user, password=user)

        response = self.client.post(self._url_list, data=data, format='json')
        self.client.logout()
        self._log_response(response)
        return response

    def _update(self, user, id, data):
        self.client.login(username=user, password=user)
        response = self.client.put(self._url_object % id, data=data, format='json')
        self.client.logout()
        self._log_response(response)
        return response

    def _partial_update(self, user, id, data):
        self.client.login(username=user, password=user)
        response = self.client.patch(self._url_object % id, data=data, format='json')
        self.client.logout()
        self._log_response(response)
        return response

    def _delete(self, user, id):
        self.client.login(username=user, password=user)
        response = self.client.delete(self._url_object % id)
        self.client.logout()
        self._log_response(response)
        return response

    def _make_new_data(self, **kwargs):
        n = self.create_name()
        data = {
            'name': n,
        }
        data.update(kwargs)
        return data

    def test_list(self):
        self._create_obj(self.create_name())
        self._create_obj(self.create_name())
        self._create_obj(self.create_name())

        # admin
        response = self._list(self._a_admin_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertEqual(response.data['count'], 4 if self.has_dash_obj else 3)

    def test_get(self):
        obj = self._create_obj(self.create_name())

        # admin
        response = self._get(self._a_admin_user, obj.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add(self):
        data = self._make_new_data()
        response = self._add(self._a_admin_user, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update(self):
        obj = self._create_obj(self.create_name())

        response = self._get(self._a_admin_user, obj.id)
        udata = response.data.copy()

        # create by admin
        udata['name'] = self.create_name()
        response = self._update(self._a_admin_user, obj.id, udata)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        obj = self._create_obj(self.create_name())
        response = self._delete(self._a_admin_user, obj.id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class BaseNamedModelTestCase(BaseApiTestCase):
    def test_list_ordering(self):
        self._create_obj(self.create_name())
        self._create_obj(self.create_name())
        self._create_obj(self.create_name())

        self._list_order(self._a_admin_user, 'user_code', None)
        self._list_order(self._a_admin_user, 'name', None)
        self._list_order(self._a_admin_user, 'short_name', None)

    def test_list_filtering(self):
        obj1 = self._create_obj(self.create_name())
        self._create_obj(self.create_name())

        self._list_filter(self._a_admin_user, 'user_code', obj1.user_code, 1)
        self._list_filter(self._a_admin_user, 'name', obj1.name, 1)
        self._list_filter(self._a_admin_user, 'short_name', obj1.short_name, 1)


class BaseApiWithPermissionTestCase(BaseApiTestCase):
    def setUp(self):
        super(BaseApiWithPermissionTestCase, self).setUp()

        if self.__class__ is BaseApiWithPermissionTestCase:
            raise unittest.SkipTest("Base class")


class BaseAttributeTypeApiTestCase(BaseNamedModelTestCase, BaseApiWithPermissionTestCase):
    model = GenericAttributeType
    base_model = None

    def setUp(self):
        super(BaseAttributeTypeApiTestCase, self).setUp()

        self._change_permission = get_change_perms(GenericAttributeType)[0]

    def _create_default_attrs(self):
        self._attr_str = self.create_attribute_type(
            'str',
            self._a_master_user,
            base_model=self.base_model,
            value_type=GenericAttributeType.STRING
        )
        self._attr_num = self.create_attribute_type(
            'num',
            self._a_master_user,
            base_model=self.base_model,
            value_type=GenericAttributeType.NUMBER
        )
        self._attr_date = self.create_attribute_type(
            'date',
            self._a_master_user,
            base_model=self.base_model,
            value_type=GenericAttributeType.DATE
        )
        self._attr_clsfr1 = self.create_attribute_type(
            'clsfr1', self._a_master_user, base_model=self.base_model,
            value_type=GenericAttributeType.CLASSIFIER,
            classifier_tree=[
                {
                    'name': 'clsfr1_n1',
                    'children': [
                        {'name': 'clsfr1_n11', },
                        {'name': 'clsfr1_n12', },
                    ]
                }, {
                    'name': 'clsfr1_n2',
                    'children': [
                        {'name': 'clsfr1_n21', },
                        {'name': 'clsfr1_n22', },
                    ]
                },
            ]
        )
        self._attr_clsfr2 = self.create_attribute_type(
            'clsfr2',
            self._a_master_user,
            base_model=self.base_model,
            value_type=GenericAttributeType.CLASSIFIER,
            classifier_tree=[
                {
                    'name': 'clsfr2_n1',
                    'children': [
                        {'name': 'clsfr2_n11', },
                        {'name': 'clsfr2_n12', },
                    ]
                }, {
                    'name': 'clsfr2_n2',
                    'children': [
                        {'name': 'clsfr2_n21', },
                        {'name': 'clsfr2_n22', },
                    ]
                },
            ]
        )

    def _gen_classifiers(self):
        n = self.create_name()
        uc = self.create_user_code(n)
        return [
            {
                "user_code": '1_%s' % uc,
                "name": '1_%s' % n,
                "children": [
                    {
                        "user_code": '11_%s' % uc,
                        "name": '11_%s' % n,
                        "children": [
                            {
                                "user_code": '111_%s' % uc,
                                "name": '111_%s' % n,
                            }
                        ]
                    },
                    {
                        "user_code": '12_%s' % uc,
                        "name": '12_%s' % n,
                    }
                ]
            },
            {
                "user_code": '2_%s' % uc,
                "name": '2_%s' % n,
                "children": [
                    {
                        "user_code": '22_%s' % uc,
                        "name": '22_%s' % n,
                        "children": []
                    }
                ]
            }
        ]

    def _make_new_data_with_classifiers(self, value_type=GenericAttributeType.CLASSIFIER, **kwargs):
        data = self._make_new_data(value_type=value_type, **kwargs)
        data['classifiers'] = self._gen_classifiers()
        return data

    def _create_obj(self, name='acc'):
        return self.create_attribute_type(name, self._a_master_user, base_model=self.base_model)

    def _get_obj(self, name='acc'):
        return self.get_attribute_type(name, self._a_master_user, base_model=self.base_model)

    def test_classifiers_get(self):
        self._create_default_attrs()
        response = self._get(self._a_admin_user, self._attr_clsfr1.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['classifiers']), 2)

    def test_classifiers_add(self):
        data = self._make_new_data_with_classifiers()
        response = self._add(self._a_admin_user, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['classifiers']), 2)

        # try create with classifier with other value type
        data = self._make_new_data_with_classifiers(value_type=GenericAttributeType.STRING)
        response = self._add(self._a_admin_user, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['classifiers'], [])

    def test_classifiers_update(self):
        data = self._make_new_data(value_type=GenericAttributeType.CLASSIFIER)
        response = self._add(self._a_admin_user, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['classifiers']), 0)

        # TODO check this test
        # data = response.data.copy()
        # data['classifiers'] = self._gen_classifiers()
        # print(data)
        # response = self._update(self._a_admin_user, data['id'], data)
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # print("result")
        # print(response.data)
        # self.assertEqual(len(response.data['classifiers']), 2)

        # try add classifier to other value type
        data = self._make_new_data(value_type=GenericAttributeType.STRING)
        response = self._add(self._a_admin_user, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.data.copy()
        data['classifiers'] = self._gen_classifiers()
        response = self._update(self._a_admin_user, data['id'], data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['classifiers'], [])


class BaseApiWithAttributesTestCase(BaseApiTestCase):
    pass

    # def setUp(self):
    #     super(BaseApiWithAttributesTestCase, self).setUp()
    #
    #     self._attr_str = self.create_attribute_type('str', self._a_master_user, value_type=GenericAttributeType.STRING)
    #     self._attr_num = self.create_attribute_type('num', self._a_master_user, value_type=GenericAttributeType.NUMBER)
    #     self._attr_date = self.create_attribute_type('date', self._a_master_user, value_type=GenericAttributeType.DATE)
    #     self._attr_clsfr1 = self.create_attribute_type('clsfr1', self._a_master_user,
    #                                                    value_type=GenericAttributeType.CLASSIFIER,
    #                                                    classifier_tree=[{
    #                                                        'name': 'clsfr1_n1',
    #                                                        'children': [
    #                                                            {'name': 'clsfr1_n11',},
    #                                                            {'name': 'clsfr1_n12',},
    #                                                        ]
    #                                                    }, {
    #                                                        'name': 'clsfr1_n2',
    #                                                        'children': [
    #                                                            {'name': 'clsfr1_n21',},
    #                                                            {'name': 'clsfr1_n22',},
    #                                                        ]
    #                                                    }, ])
    #     self._attr_clsfr2 = self.create_attribute_type('clsfr2', self._a_master_user,
    #                                                    value_type=GenericAttributeType.CLASSIFIER,
    #                                                    classifier_tree=[{
    #                                                        'name': 'clsfr2_n1',
    #                                                        'children': [
    #                                                            {'name': 'clsfr2_n11',},
    #                                                            {'name': 'clsfr2_n12',},
    #                                                        ]
    #                                                    }, {
    #                                                        'name': 'clsfr2_n2',
    #                                                        'children': [
    #                                                            {'name': 'clsfr2_n21',},
    #                                                            {'name': 'clsfr2_n22',},
    #                                                        ]
    #                                                    }, ])
    #
    # def _get_model_classifier(self, name, classifier_name=None):
    #     return self.get_classifier(name, master_user=self._a_master_user, classifier_name=classifier_name)
    #
    # def _attr_value_key(self, value_type):
    #     if value_type == GenericAttributeType.STRING:
    #         return 'value_string'
    #     elif value_type == GenericAttributeType.NUMBER:
    #         return 'value_float'
    #     elif value_type == GenericAttributeType.DATE:
    #         return 'value_date'
    #     elif value_type == GenericAttributeType.CLASSIFIER:
    #         return 'classifier'
    #     else:
    #         self.fail('invalid value_type %s' % (value_type))
    #
    # def add_attr_value(self, data, attr, value):
    #     attribute_type = self.get_attribute_type(attr, master_user=self._a_master_user)
    #     attributes = data.get('attributes', [])
    #     attributes = [x for x in attributes if x['attribute_type'] != attribute_type.id]
    #     # if value is not None:
    #     value_key = self._attr_value_key(attribute_type.value_type)
    #     attributes.append({'attribute_type': attribute_type.id, value_key: value})
    #     data['attributes'] = attributes
    #     return data
    #
    # def assertAttrEqual(self, attr, expected, attributes):
    #     attribute_type = self.get_attribute_type(attr, master_user=self._a_master_user)
    #     attributes = [x for x in attributes if x['attribute_type'] == attribute_type.id]
    #     if not attributes:
    #         self.fail('attribute %s not founded' % attr)
    #     value_key = self._attr_value_key(attribute_type.value_type)
    #     self.assertEqual(expected, attributes[0][value_key])
    #
    # def _simple_attrs(self, attr, value1, value2):
    #
    #     # create item
    #     data = self._make_new_data()
    #     data = self.add_attr_value(data, attr, value1)
    #     response = self._add(self._a_admin_user, data)
    #     data = response.data.copy()
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #
    #     self.assertEqual(len(response.data['attributes']), 5)
    #     self.assertAttrEqual(attr, value1, response.data['attributes'])
    #
    #     # update item
    #     data2 = data.copy()
    #     data2 = self.add_attr_value(data2, attr, value2)
    #     response = self._update(self._a_admin_user, data2['id'], data2)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(response.data['attributes']), 5)
    #     self.assertAttrEqual(attr, value2, response.data['attributes'])
    #
    #     # # update with None (currently attr doesn't deleted)
    #     data3 = data.copy()
    #     data3 = self.add_attr_value(data3, attr, None)
    #     response = self._update(self._a_admin_user, data3['id'], data3)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(response.data['attributes']), 5)
    #
    #     # # delete attr
    #     response = self._delete(self._a_admin_user, data3['id'])
    #     self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    #
    # def test_attrs_str(self):
    #     self._simple_attrs('str', 'value1', 'value2')
    #
    # def test_attrs_num(self):
    #     self._simple_attrs('num', 123, 456)
    #
    # def test_attrs_date(self):
    #     self._simple_attrs('date', '2014-01-01', '2015-01-01')
    #
    # def test_attrs_clsfr(self):
    #     classifier1 = self._get_model_classifier('clsfr1', 'clsfr1_n11')
    #     classifier2 = self._get_model_classifier('clsfr1', 'clsfr1_n21')
    #     self._simple_attrs('clsfr1', classifier1.id, classifier2.id)
    #
    # def test_attrs_2_attrs(self):
    #     data = self._make_new_data()
    #     data = self.add_attr_value(data, 'str', 'value1')
    #
    #     print(' test_attrs_2_attrs data %s' % data)
    #
    #     # get list
    #     response = self._list(self._a_admin_user, data)
    #     data = response.data.copy()
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(response.data['attributes']), 5)
    #
    #     data1 = data.copy()
    #     data1 = self.add_attr_value(data1, 'num', 123)
    #     response = self._update(self._a_admin_user, data1['id'], data1)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(response.data['attributes']), 5)
    #     self.assertAttrEqual('str', 'value1', response.data['attributes'])
    #     self.assertAttrEqual('num', 123, response.data['attributes'])
    #
    #     data2 = data.copy()
    #     data2 = self.add_attr_value(data2, 'num', 0.0)
    #     response = self._update(self._a_admin_user, data2['id'], data2)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(response.data['attributes']), 5)
    #     self.assertAttrEqual('str', 'value1', response.data['attributes'])
    #     self.assertAttrEqual('num', 0.0, response.data['attributes'])

    # def test_attrs_with_perms(self):
    #     self.assign_perms(self._attr_num, self._a_admin_user, users=[self._a_admin_user], perms=get_all_perms(GenericAttributeType))
    #
    #     data = self._make_new_data()
    #     data = self.add_attr_value(data, 'str', 'value1')
    #     response = self._add(self._a_admin_user, data)
    #     data = response.data.copy()
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #     self.assertEqual(len(response.data['attributes']), 1)
    #
    #     self.assign_perms(self.model.objects.get(pk=data['id']), self._a_admin_user, users=[self._a1])
    #
    #     # user see only attrs with types perms
    #     response = self._get(self._a_admin_user, data['id'])
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertTrue('attributes' in response.data)
    #     self.assertEqual(len(response.data['attributes']), 0)
    #
    #     # user add attribute
    #     data2 = response.data.copy()
    #     data2 = self.add_attr_value(data2, 'num', 123)
    #     response = self._update(self._a_admin_user, data2['id'], data2)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(response.data['attributes']), 1)
    #
    #     # superuser see all attrs
    #     response = self._get(self._a_admin_user, data['id'])
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(response.data['attributes']), 1)
    #
    #     # user delete attribute
    #     data2 = response.data.copy()
    #     data2['attributes'] = []
    #     response = self._update(self._a_admin_user, data2['id'], data2)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(response.data['attributes']), 0)
    #
    #     # superuser see 1 attr
    #     response = self._get(self._a_admin_user, data['id'])
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(response.data['attributes']), 0)
    #
    #     # try update attrs without type perms
    #     data3 = data.copy()
    #     data3 = self.add_attr_value(data3, 'num', 123)
    #     response = self._update(self._a_admin_user, data3['id'], data3)
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=str(response.data))


ABSTRACT_TESTS.append(BaseApiTestCase)
ABSTRACT_TESTS.append(BaseNamedModelTestCase)
ABSTRACT_TESTS.append(BaseApiWithPermissionTestCase)
ABSTRACT_TESTS.append(BaseApiWithAttributesTestCase)
ABSTRACT_TESTS.append(BaseAttributeTypeApiTestCase)
