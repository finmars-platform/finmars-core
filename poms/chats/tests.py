from __future__ import unicode_literals

# TODO update unit tests
# def load_tests(loader, standard_tests, pattern):
#     from poms.common.tests import load_tests as t
#     return t(loader, standard_tests, pattern)
#
#
# class ThreadGroupApiTestCase(BaseApiTestCase):
#     model = ThreadGroup
#
#     def setUp(self):
#         super(ThreadGroupApiTestCase, self).setUp()
#
#         self._url_list = '/api/v1/chats/thread-group/'
#         self._url_object = '/api/v1/chats/thread-group/%s/'
#         self._change_permission = 'change_threadgroup'
#
#     def _create_obj(self, name='thread-group'):
#         return self.create_thread_group(name, self._a_master_user)
#
#     def _get_obj(self, name='thread-group'):
#         return self.get_thread(name, self._a_master_user)
#
#     def _make_new_data(self, **kwargs):
#         data = super(ThreadGroupApiTestCase, self)._make_new_data(**kwargs)
#         data['name'] = data.pop('name')
#         return data
#
#     # def test_permissions_get_not_visible(self):
#     #     obj = self._create_obj('obj')
#     #
#     #     response = self._get(self._a, obj.id)
#     #     self.assertEqual(response.status_code, status.HTTP_200_OK)
#     #     response = self._get(self._a0, obj.id)
#     #     self.assertEqual(response.status_code, status.HTTP_200_OK)
#     #     response = self._get(self._a1, obj.id)
#     #     self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
#     #     response = self._get(self._a2, obj.id)
#     #     self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
#
#
# class ThreadApiTestCase(BaseApiWithPermissionTestCase):
#     model = Thread
#
#     def setUp(self):
#         super(ThreadApiTestCase, self).setUp()
#
#         self._url_list = '/api/v1/chats/thread/'
#         self._url_object = '/api/v1/chats/thread/%s/'
#         self._change_permission = 'change_thread'
#
#     def _create_obj(self, subject='thread', is_closed=False):
#         return self.create_thread(subject, self._a, is_closed=is_closed)
#
#     def _get_obj(self, subject='thread'):
#         return self.get_thread(subject, self._a)
#
#     def _make_new_data(self, **kwargs):
#         data = super(ThreadApiTestCase, self)._make_new_data(**kwargs)
#         data['subject'] = data.pop('name')
#         return data
#
#     def test_permissions_get_not_visible(self):
#         obj = self._create_obj('obj')
#         obj12 = self._create_obj('obj_a1')
#         self.assign_perms(obj12, self._a, users=[self._a1], groups=['g2'], perms=self.default_owner_permissions)
#
#         response = self._get(self._a1, obj.id)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(set(response.data.keys()),
#                          {'id', 'display_name', 'granted_permissions'})
#
#         response = self._get(self._a2, obj.id)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(set(response.data.keys()),
#                          {'id', 'display_name', 'granted_permissions'})
#
#
# class MessageApiTest(BaseApiTestCase):
#     model = Message
#
#     def setUp(self):
#         super(MessageApiTest, self).setUp()
#
#         self._url_list = '/api/v1/chats/message/'
#         self._url_object = '/api/v1/chats/message/%s/'
#
#         self.thread1 = self.create_thread('-', self._a)
#
#     def _create_obj(self, text='thread_status', sender=None, thread='-'):
#         if sender is None:
#             sender = self._a
#         return self.create_message(text, sender, self._a, thread)
#
#     def _get_obj(self, text='thread_status'):
#         return self.get_message(text, self._a)
#
#     def _make_new_data(self, **kwargs):
#         thread = self.get_thread(kwargs.get('thread', '-'), self._a)
#         sender = self.get_member(kwargs.get('sender', self._a), self._a)
#         kwargs['thread'] = thread.id
#         kwargs['sender'] = sender.id
#         data = super(MessageApiTest, self)._make_new_data(**kwargs)
#         data['text'] = data.pop('name')
#         return data
#
#     def test_delete(self):
#         obj = self._create_obj('obj_a')
#         response = self._delete(self._a, obj.id)
#         self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
#
#
# class DirectMessageApiTest(BaseApiTestCase):
#     model = DirectMessage
#
#     def setUp(self):
#         super(DirectMessageApiTest, self).setUp()
#
#         self._url_list = '/api/v1/chats/direct-message/'
#         self._url_object = '/api/v1/chats/direct-message/%s/'
#
#     def _create_obj(self, text='text', sender=None, recipient=None):
#         if sender is None:
#             sender = self._a
#         if recipient is None:
#             recipient = self._a0
#         return self.create_direct_message(text, self._a, sender, recipient)
#
#     def _get_obj(self, text='text'):
#         return self.get_direct_message(text, self._a)
#
#     def _make_new_data(self, **kwargs):
#         sender = self.get_member(kwargs.get('sender', self._a), self._a)
#         recipient = self.get_member(kwargs.get('recipient', self._a), self._a)
#         kwargs['sender'] = sender.id
#         kwargs['recipient'] = recipient.id
#         data = super(DirectMessageApiTest, self)._make_new_data(**kwargs)
#         data['text'] = data.pop('name')
#         return data
#
#     def test_delete(self):
#         obj = self._create_obj('obj_a')
#         response = self._delete(self._a, obj.id)
#         self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
