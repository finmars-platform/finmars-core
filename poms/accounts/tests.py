# from poms.accounts.models import Account, AccountType
# from poms.common.tests import (
#     BaseApiWithPermissionTestCase,
#     BaseApiWithAttributesTestCase,
#     BaseAttributeTypeApiTestCase,
#     BaseNamedModelTestCase,
# )
#
#
# def load_tests(loader, standard_tests, pattern):
#     from poms.common.tests import load_tests as t
#
#     return t(loader, standard_tests, pattern)
#
#
# class AccountTypeApiTestCase(BaseNamedModelTestCase, BaseApiWithPermissionTestCase):
#     model = AccountType
#
#     def setUp(self):
#         super(AccountTypeApiTestCase, self).setUp()
#
#         self._url_list = "/api/v1/accounts/account-type/"
#         self._url_object = "/api/v1/accounts/account-type/%s/"
#         self._change_permission = "change_accounttype"
#
#     def _create_obj(self, name="acc"):
#         return self.create_account_type(name, master_user=self._a_master_user)
#
#     def _get_obj(self, name="acc"):
#         return self.get_account_type(name, master_user=self._a_master_user)
#
#
# class AccountAttributeTypeApiTestCase(BaseAttributeTypeApiTestCase):
#     base_model = Account
#
#     def setUp(self):
#         super(AccountAttributeTypeApiTestCase, self).setUp()
#
#         self._url_list = "/api/v1/accounts/account-attribute-type/"
#         self._url_object = "/api/v1/accounts/account-attribute-type/%s/"
#
#
# class AccountApiTestCase(
#     BaseNamedModelTestCase, BaseApiWithPermissionTestCase, BaseApiWithAttributesTestCase
# ):
#     model = Account
#
#     def setUp(self):
#         super(AccountApiTestCase, self).setUp()
#
#         self._url_list = "/api/v1/accounts/account/"
#         self._url_object = "/api/v1/accounts/account/%s/"
#         self._change_permission = "change_account"
#
#         self.type_def = self.get_account_type("-", self._a_master_user)
#         # self.assign_perms(self.type_def, self._a_master_user, users=[self._a0, self._a1, self._a2], groups=['g1', 'g2'],
#         #                   perms=get_perms_codename(self.type_def, ['change', 'view']))
#         #
#         # self.type1 = self.create_account_type('type1', self._a_master_user)
#         # self.type2_a1 = self.create_account_type('type2_a1', self._a_master_user)
#         # self.assign_perms(self.type2_a1, self._a_master_user, users=['a1'])
#         # self.type3_g2 = self.create_account_type('type3_g2', self._a_master_user)
#         # self.assign_perms(self.type3_g2, self._a_master_user, groups=['g2'])
#
#     def _create_obj(self, name="account"):
#         return self.create_account(name, self._a_master_user)
#
#     def _get_obj(self, name="account"):
#         return self.get_account(name, self._a_master_user)
#
#     def _make_new_data(self, **kwargs):
#         account_type = self.get_account_type(
#             kwargs.get("account_type", "-"), self._a_master_user
#         )
#         data = super(AccountApiTestCase, self)._make_new_data(
#             type=account_type.id, **kwargs
#         )
#         return data
#
#     # def test_add_by_user_with_type_without_perms(self):
#     #     data = self._make_new_data(account_type='type1')
#     #     response = self._add('a1', data)
#     #     self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
#     #
#     # def test_add_by_group_with_type_without_perms(self):
#     #     data = self._make_new_data(account_type='type1')
#     #     response = self._add('a2', data)
#     #     self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
