from __future__ import unicode_literals

from poms.common.tests import BaseApiWithPermissionTestCase, BaseNamedModelTestCase
from poms.tags.models import Tag


def load_tests(loader, standard_tests, pattern):
    from poms.common.tests import load_tests as t
    return t(loader, standard_tests, pattern)


class TagApiTestCase(BaseNamedModelTestCase, BaseApiWithPermissionTestCase):
    model = Tag

    def setUp(self):
        super(TagApiTestCase, self).setUp()

        self._url_list = '/api/v1/tags/tag/'
        self._url_object = '/api/v1/tags/tag/%s/'
        self._change_permission = 'change_tag'

    def _create_obj(self, name='tag'):
        return self.create_tag(name, self._a)

    def _get_obj(self, name='tag'):
        return self.get_tag(name, self._a)

    def _make_new_data(self, **kwargs):
        content_types = kwargs.get('content_types', [])
        if not content_types:
            content_types = [
                "accounts.accounttype",
                "accounts.account",
                "counterparties.counterparty",
                "counterparties.responsible",
                "currencies.currency",
                "instruments.instrument",
                "portfolios.portfolio",
                "instruments.instrumenttype",
                "transactions.transactiontype",
                "strategies.strategy1",
                "strategies.strategy2",
                "strategies.strategy3",
            ]
        kwargs['content_types'] = content_types
        return super(TagApiTestCase, self)._make_new_data(**kwargs)
