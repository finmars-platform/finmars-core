from __future__ import unicode_literals

from poms.common.tests import BaseApiWithPermissionTestCase, BaseApiWithAttributesTestCase, \
    BaseAttributeTypeApiTestCase, BaseNamedModelTestCase
from poms.counterparties.models import Counterparty, Responsible, CounterpartyGroup, ResponsibleGroup


def load_tests(loader, standard_tests, pattern):
    from poms.common.tests import load_tests as t
    return t(loader, standard_tests, pattern)


# Counterparty

class CounterpartyAttributeTypeApiTestCase(BaseAttributeTypeApiTestCase):
    base_model = Counterparty

    def setUp(self):
        super(CounterpartyAttributeTypeApiTestCase, self).setUp()

        self._url_list = '/api/v1/counterparties/counterparty-attribute-type/'
        self._url_object = '/api/v1/counterparties/counterparty-attribute-type/%s/'


class CounterpartyGroupApiTestCase(BaseNamedModelTestCase, BaseApiWithPermissionTestCase):
    model = CounterpartyGroup

    def setUp(self):
        super(CounterpartyGroupApiTestCase, self).setUp()

        self._url_list = '/api/v1/counterparties/counterparty-group/'
        self._url_object = '/api/v1/counterparties/counterparty-group/%s/'
        self._change_permission = 'change_counterpartygroup'

    def _create_obj(self, name='counterparty-group'):
        return self.create_counterparty_group(name, self._a_master_user)

    def _get_obj(self, name='counterparty-group'):
        return self.get_counterparty_group(name, self._a_master_user)


class CounterpartyApiTestCase(BaseNamedModelTestCase, BaseApiWithPermissionTestCase, BaseApiWithAttributesTestCase):
    model = Counterparty

    def setUp(self):
        super(CounterpartyApiTestCase, self).setUp()

        self._url_list = '/api/v1/counterparties/counterparty/'
        self._url_object = '/api/v1/counterparties/counterparty/%s/'
        self._change_permission = 'change_counterparty'

        # self.assign_perms(self.get_counterparty_group('-'), self._a,
        #                   users=[self._a0, self._a1, self._a2], groups=['g1', 'g2'],
        #                   perms=get_perms_codename(self.type_def, ['change', 'view']))

    def _create_obj(self, name='counterparty'):
        return self.create_counterparty(name, self._a_master_user)

    def _get_obj(self, name='counterparty'):
        return self.get_counterparty(name, self._a_master_user)

    def _make_new_data(self, **kwargs):
        group = self.get_counterparty_group(kwargs.get('group', '-'), self._a_master_user)
        data = super(CounterpartyApiTestCase, self)._make_new_data(group=group.id, **kwargs)
        return data


# Responsible

class ResponsibleAttributeTypeApiTestCase(BaseAttributeTypeApiTestCase):
    base_model = Responsible

    def setUp(self):
        super(ResponsibleAttributeTypeApiTestCase, self).setUp()

        self._url_list = '/api/v1/counterparties/responsible-attribute-type/'
        self._url_object = '/api/v1/counterparties/responsible-attribute-type/%s/'


class ResponsibleGroupApiTestCase(BaseNamedModelTestCase, BaseApiWithPermissionTestCase):
    model = ResponsibleGroup

    def setUp(self):
        super(ResponsibleGroupApiTestCase, self).setUp()

        self._url_list = '/api/v1/counterparties/responsible-group/'
        self._url_object = '/api/v1/counterparties/responsible-group/%s/'
        self._change_permission = 'change_responsiblegroup'

    def _create_obj(self, name='responsible-group'):
        return self.create_responsible_group(name, self._a_master_user)

    def _get_obj(self, name='responsible-group'):
        return self.get_responsible_group(name, self._a_master_user)


class ResponsibleApiTestCase(BaseNamedModelTestCase, BaseApiWithPermissionTestCase, BaseApiWithAttributesTestCase):
    model = Responsible

    def setUp(self):
        super(ResponsibleApiTestCase, self).setUp()

        self._url_list = '/api/v1/counterparties/responsible/'
        self._url_object = '/api/v1/counterparties/responsible/%s/'
        self._change_permission = 'change_responsible'

    def _create_obj(self, name='responsible'):
        return self.create_responsible(name, self._a_master_user)

    def _get_obj(self, name='responsible'):
        return self.get_responsible(name, self._a_master_user)

    def _make_new_data(self, **kwargs):
        group = self.get_responsible_group(kwargs.get('group', '-'), self._a_master_user)
        data = super(ResponsibleApiTestCase, self)._make_new_data(group=group.id, **kwargs)
        return data
