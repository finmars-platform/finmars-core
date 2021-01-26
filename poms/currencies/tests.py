from __future__ import unicode_literals

from rest_framework import status

from poms.common.tests import BaseApiWithTagsTestCase, BaseNamedModelTestCase, BaseApiWithAttributesTestCase, \
    BaseAttributeTypeApiTestCase
from poms.currencies.models import Currency


def load_tests(loader, standard_tests, pattern):
    from poms.common.tests import load_tests as t
    return t(loader, standard_tests, pattern)


class CurrencyAttributeTypeApiTestCase(BaseAttributeTypeApiTestCase):
    base_model = Currency

    def setUp(self):
        super(CurrencyAttributeTypeApiTestCase, self).setUp()

        self._url_list = '/api/v1/currencies/currency-attribute-type/'
        self._url_object = '/api/v1/currencies/currency-attribute-type/%s/'
        # self._change_permission = 'change_instrumentattributetype'


class CurrencyApiTestCase(BaseNamedModelTestCase, BaseApiWithTagsTestCase, BaseApiWithAttributesTestCase):
    # auto created "default"
    model = Currency
    # Currency have or not update?

    def setUp(self):
        super(CurrencyApiTestCase, self).setUp()
        self._url_list = '/api/v1/currencies/currency/'
        self._url_object = '/api/v1/currencies/currency/%s/'
        self._change_permission = 'change_currency'

    def _create_obj(self, name='currency'):
        return self.create_currency(name, self._a_master_user)

    def _get_obj(self, name='currency'):
        return self.get_currency(name, self._a_master_user)

    def test_list(self):
        response = self._list(self._a_admin_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_ordering(self):
        self._list_order(self._a_admin_user, 'user_code', None)
        self._list_order(self._a_admin_user, 'name', None)
        self._list_order(self._a_admin_user, 'short_name', None)

        # def test_list(self):
        #     self._create_obj('obj1')
        #     self._create_obj('obj2')
        #     self._create_obj('obj3')
        #
        #     # owner
        #     response = self._list(self._a)
        #     self.assertEqual(response.status_code, status.HTTP_200_OK)
        #     self.assertEqual(response.data['count'], 4)
        #
        # def test_list_ordering(self):
        #     self._create_obj('obj1')
        #     self._create_obj('obj2')
        #     self._create_obj('obj3')
        #
        #     self._list_order(self._a, 'user_code', 4)
        #     self._list_order(self._a, 'name', 4)
        #     self._list_order(self._a, 'short_name', 4)
        #
        # def test_tags_list(self):
        #     obj = self._create_obj()
        #     self.assign_perms(obj, self._a, users=[self._a1], groups=['g2'])
        #     obj.tags = [self.tag1, self.tag2_a1, self.tag3_g2]
        #
        #     response = self._list(self._a)
        #     self.assertEqual(response.status_code, status.HTTP_200_OK)
        #     self.assertEqual(response.data['count'], 2)
        #     self.assertEqual(set(response.data['results'][1]['tags']), {self.tag1.id, self.tag2_a1.id, self.tag3_g2.id, })
        #
        #     response = self._list(self._a0)
        #     self.assertEqual(response.status_code, status.HTTP_200_OK)
        #     self.assertEqual(response.data['count'], 2)
        #     self.assertEqual(set(response.data['results'][1]['tags']), {self.tag1.id, self.tag2_a1.id, self.tag3_g2.id, })
        #
        #     response = self._list(self._a1)
        #     self.assertEqual(response.status_code, status.HTTP_200_OK)
        #     self.assertEqual(response.data['count'], 2)
        #     self.assertEqual(set(response.data['results'][1]['tags']), {self.tag2_a1.id})
        #
        #     response = self._list(self._a2)
        #     self.assertEqual(response.status_code, status.HTTP_200_OK)
        #     self.assertEqual(response.data['count'], 2)
        #     self.assertEqual(set(response.data['results'][1]['tags']), {self.tag3_g2.id, })
        #
        # def test_tags_update(self):
        #     data = self._make_new_data(tags=[self.tag1.id])
        #     response = self._add(self._a, data)
        #     data = response.data.copy()
        #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        #     self.assertEqual(set(response.data['tags']), {self.tag1.id})
        #
        #     udata = data.copy()
        #     udata['tags'] = {self.tag1.id, self.tag2_a1.id, self.tag3_g2.id, }
        #     response = self._update(self._a, data['id'], udata)
        #     self.assertEqual(response.status_code, status.HTTP_200_OK)
        #     self.assertEqual(set(response.data['tags']), {self.tag1.id, self.tag2_a1.id, self.tag3_g2.id, })
        #
        #     # only master user can change currency
        #     self.assign_perms(self.model.objects.get(id=data['id']), self._a, users=[self._a1], groups=['g2'],
        #                       perms=self.all_permissions)
        #     response = self._get(self._a1, data['id'])
        #     udata = response.data.copy()
        #     udata['tags'] = []
        #     response = self._update(self._a1, data['id'], udata)
        #     self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
