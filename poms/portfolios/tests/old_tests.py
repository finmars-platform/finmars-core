# from poms.common.tests import BaseApiWithPermissionTestCase, BaseApiWithAttributesTestCase, \
#     BaseAttributeTypeApiTestCase, BaseNamedModelTestCase
# from poms.portfolios.models import Portfolio
#
#
# def load_tests(loader, standard_tests, pattern):
#     from poms.common.tests import load_tests as t
#     return t(loader, standard_tests, pattern)
#
#
# class PortfolioAttributeTypeApiTestCase(BaseAttributeTypeApiTestCase):
#     base_model = Portfolio
#
#     def setUp(self):
#         super(PortfolioAttributeTypeApiTestCase, self).setUp()
#
#         self._url_list = '/api/v1/portfolios/portfolio-attribute-type/'
#         self._url_object = '/api/v1/portfolios/portfolio-attribute-type/%s/'
#         # self._change_permission = 'change_portfolioattributetype'
#
#
# class PortfolioApiTestCase(BaseNamedModelTestCase, BaseApiWithPermissionTestCase,
#                            BaseApiWithAttributesTestCase):
#     model = Portfolio
#
#     def setUp(self):
#         super(PortfolioApiTestCase, self).setUp()
#
#         self._url_list = '/api/v1/portfolios/portfolio/'
#         self._url_object = '/api/v1/portfolios/portfolio/%s/'
#         self._change_permission = 'change_portfolio'
#
#     def _create_obj(self, name='portfolio'):
#         return self.create_portfolio(name, self._a_master_user)
#
#     def _get_obj(self, name='portfolio'):
#         return self.get_portfolio(name, self._a_master_user)
