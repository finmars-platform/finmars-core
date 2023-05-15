# from rest_framework import status
#
# from poms.common.tests import (
#     BaseNamedModelTestCase,
#     BaseApiWithAttributesTestCase,
#     BaseAttributeTypeApiTestCase,
# )
# from poms.currencies.models import Currency
#
#
# def load_tests(loader, standard_tests, pattern):
#     from poms.common.tests import load_tests as t
#
#     return t(loader, standard_tests, pattern)
#
#
# class CurrencyAttributeTypeApiTestCase(BaseAttributeTypeApiTestCase):
#     base_model = Currency
#
#     def setUp(self):
#         super(CurrencyAttributeTypeApiTestCase, self).setUp()
#
#         self._url_list = "/api/v1/currencies/currency-attribute-type/"
#         self._url_object = "/api/v1/currencies/currency-attribute-type/%s/"
#         # self._change_permission = 'change_instrumentattributetype'
#
#
# class CurrencyApiTestCase(BaseNamedModelTestCase, BaseApiWithAttributesTestCase):
#     # auto created "default"
#     model = Currency
#
#     # Currency have or not update?
#
#     def setUp(self):
#         super(CurrencyApiTestCase, self).setUp()
#         self._url_list = "/api/v1/currencies/currency/"
#         self._url_object = "/api/v1/currencies/currency/%s/"
#         self._change_permission = "change_currency"
#
#     def _create_obj(self, name="currency"):
#         return self.create_currency(name, self._a_master_user)
#
#     def _get_obj(self, name="currency"):
#         return self.get_currency(name, self._a_master_user)
#
#     def test_list(self):
#         response = self._list(self._a_admin_user)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_list_ordering(self):
#         self._list_order(self._a_admin_user, "user_code", None)
#         self._list_order(self._a_admin_user, "name", None)
#         self._list_order(self._a_admin_user, "short_name", None)
#
#         # def test_list(self):
#         #     self._create_obj('obj1')
#         #     self._create_obj('obj2')
#         #     self._create_obj('obj3')
#         #
#         #     # owner
#         #     response = self._list(self._a)
#         #     self.assertEqual(response.status_code, status.HTTP_200_OK)
#         #     self.assertEqual(response.data['count'], 4)
#         #
#         # def test_list_ordering(self):
#         #     self._create_obj('obj1')
#         #     self._create_obj('obj2')
#         #     self._create_obj('obj3')
#         #
#         #     self._list_order(self._a, 'user_code', 4)
#         #     self._list_order(self._a, 'name', 4)
#         #     self._list_order(self._a, 'short_name', 4)
