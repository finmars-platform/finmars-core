from __future__ import unicode_literals

from poms.common.tests import BaseApiWithPermissionTestCase, BaseNamedModelTestCase, \
    ABSTRACT_TESTS
from poms.strategies.models import Strategy1, Strategy1Group, Strategy1Subgroup, Strategy2Group, Strategy2Subgroup, \
    Strategy2, Strategy3Group, Strategy3Subgroup, Strategy3


def load_tests(loader, standard_tests, pattern):
    from poms.common.tests import load_tests as t
    return t(loader, standard_tests, pattern)


class BaseStrategyGroupApiTestCase(BaseNamedModelTestCase, BaseApiWithPermissionTestCase):
    model = None
    strategy_code = None

    def setUp(self):
        super(BaseStrategyGroupApiTestCase, self).setUp()

        self._url_list = '/api/v1/strategies/%s/group/' % self.strategy_code
        self._url_object = '/api/v1/strategies/%s/group/%%s/' % self.strategy_code
        # self._change_permission = 'change_strategy%s' % self.strategy_code

    def _create_obj(self, name='strategy'):
        return self.create_strategy_group(self.strategy_code, name, self._a_master_user)

    def _get_obj(self, name='strategy'):
        return self.get_strategy_group(self.strategy_code, name, self._a_master_user)


class BaseStrategySubgroupApiTestCase(BaseNamedModelTestCase, BaseApiWithPermissionTestCase):
    model = None
    strategy_code = None

    def setUp(self):
        super(BaseStrategySubgroupApiTestCase, self).setUp()

        self._url_list = '/api/v1/strategies/%s/subgroup/' % self.strategy_code
        self._url_object = '/api/v1/strategies/%s/subgroup/%%s/' % self.strategy_code
        # self._change_permission = 'change_strategy%s' % self.strategy_code

    def _create_obj(self, name='strategy-subgroup'):
        return self.create_strategy_subgroup(self.strategy_code, name, self._a_master_user)

    def _get_obj(self, name='strategy-subgroup'):
        return self.get_strategy_subgroup(self.strategy_code, name, self._a_master_user)

    def _make_new_data(self, **kwargs):
        group = self.get_strategy_group(self.strategy_code, kwargs.get('group', '-'), self._a_master_user)
        data = super(BaseStrategySubgroupApiTestCase, self)._make_new_data(group=group.id, **kwargs)
        return data


class BaseStrategyApiTestCase(BaseNamedModelTestCase, BaseApiWithPermissionTestCase):
    model = None
    strategy_code = None

    def setUp(self):
        super(BaseStrategyApiTestCase, self).setUp()

        self._url_list = '/api/v1/strategies/%s/strategy/' % self.strategy_code
        self._url_object = '/api/v1/strategies/%s/strategy/%%s/' % self.strategy_code
        # self._change_permission = 'change_strategy%s' % self.strategy_code

    def _create_obj(self, name='strategy'):
        return self.create_strategy(self.strategy_code, name, self._a_master_user)

    def _get_obj(self, name='strategy'):
        return self.get_strategy(self.strategy_code, name, self._a_master_user)

    def _make_new_data(self, **kwargs):
        subgroup = self.get_strategy_subgroup(self.strategy_code, kwargs.get('subgroup', '-'), self._a_master_user)
        data = super(BaseStrategyApiTestCase, self)._make_new_data(subgroup=subgroup.id, **kwargs)
        return data


ABSTRACT_TESTS.append(BaseStrategyGroupApiTestCase)
ABSTRACT_TESTS.append(BaseStrategySubgroupApiTestCase)
ABSTRACT_TESTS.append(BaseStrategyApiTestCase)


# 1

class Strategy1GroupApiTestCase(BaseStrategyGroupApiTestCase):
    model = Strategy1Group
    strategy_code = 1


class Strategy1SubgroupApiTestCase(BaseStrategySubgroupApiTestCase):
    model = Strategy1Subgroup
    strategy_code = 1


class Strategy1ApiTestCase(BaseStrategyApiTestCase):
    model = Strategy1
    strategy_code = 1


# 2


class Strategy2GroupApiTestCase(BaseStrategyGroupApiTestCase):
    model = Strategy2Group
    strategy_code = 2


class Strategy2SubgroupApiTestCase(BaseStrategySubgroupApiTestCase):
    model = Strategy2Subgroup
    strategy_code = 2


class Strategy2ApiTestCase(BaseStrategyApiTestCase):
    model = Strategy2
    strategy_code = 2


# 3

class Strategy3GroupApiTestCase(BaseStrategyGroupApiTestCase):
    model = Strategy3Group
    strategy_code = 3


class Strategy3SubgroupApiTestCase(BaseStrategySubgroupApiTestCase):
    model = Strategy3Subgroup
    strategy_code = 3


class Strategy3ApiTestCase(BaseStrategyApiTestCase):
    model = Strategy3
    strategy_code = 3
