import json
import uuid

from django.contrib.contenttypes.models import ContentType
from rest_framework import status

from poms.accounts.models import Account
from poms.common.tests import BaseApiTestCase
from poms.ui.models import ListLayout, EditLayout


def load_tests(loader, standard_tests, pattern):
    from poms.common.tests import load_tests as t
    return t(loader, standard_tests, pattern)


class ListLayoutApiTestCase(BaseApiTestCase):
    model = ListLayout

    def setUp(self):
        super(ListLayoutApiTestCase, self).setUp()
        self._url_list = '/api/v1/ui/list-layout/'
        self._url_object = '/api/v1/ui/list-layout/%s/'

    def _create_obj(self, name='name'):
        member = self.get_member(self._a, self._a)
        content_type = ContentType.objects.get_for_model(Account)
        return self.model.objects.create(name=name, member=member, content_type=content_type,
                                         data=json.dumps({'name': name}))

    def _get_obj(self, name='name'):
        member = self.get_member(self._a, self._a)
        content_type = ContentType.objects.get_for_model(Account)
        return self.model.objects.get(name=name, member=member, content_type=content_type)

    def _make_new_data(self, **kwargs):
        content_type = ContentType.objects.get_for_model(Account)
        kwargs.setdefault('content_type', '%s.%s' % (content_type.app_label, content_type.model,))
        kwargs.setdefault('data', {'pos': 1, 'uuid': str(uuid.uuid4())})
        return super(ListLayoutApiTestCase, self)._make_new_data(**kwargs)


class EditLayoutApiTestCase(BaseApiTestCase):
    model = EditLayout

    def setUp(self):
        super(EditLayoutApiTestCase, self).setUp()
        self._url_list = '/api/v1/ui/edit-layout/'
        self._url_object = '/api/v1/ui/edit-layout/%s/'

    def _create_obj(self, name='name'):
        member = self.get_member(self._a, self._a)
        content_type = ContentType.objects.get_for_model(Account)
        return self.model.objects.create(member=member, content_type=content_type,
                                         data=json.dumps({'name': name}))

    def _get_obj(self, name=None):
        member = self.get_member(self._a, self._a)
        content_type = ContentType.objects.get_for_model(Account)
        return self.model.objects.get(member=member, content_type=content_type)

    def _make_new_data(self, **kwargs):
        content_type = ContentType.objects.get_for_model(Account)
        kwargs.setdefault('content_type', '%s.%s' % (content_type.app_label, content_type.model,))
        kwargs.setdefault('data', {'pos': 1, 'uuid': str(uuid.uuid4())})
        return super(EditLayoutApiTestCase, self)._make_new_data(**kwargs)

    def test_list(self):
        self._create_obj('obj1')

        # owner
        response = self._list(self._a)
        self.assertEqual(response.status_code, status.HTTP_200_OK)