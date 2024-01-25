from unittest import mock

from django.test import override_settings

from poms.bootstrap.apps import BootstrapConfig
from poms.common.common_base_test import BaseTestCase
from poms.users.models import Member


class FinmarsTaskTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.mock_response_data = {
            "name": "master_from_backup",
            "description": "description",
            "is_from_backup": True,
            "old_backup_name": None,
            "version": "6.6.6",
            "base_api_url": "space11111",
            "owner": {"username": "new_owner", "email": "test@mail.ru"},
            "status": 0,  # INITIAL
        }
        self.mock_response = mock.Mock()
        self.mock_response.status_code = 200
        self.mock_response.text = "nice mocked text"
        self.mock_response.json.return_value = self.mock_response_data
        self.old_member = Member.objects.create(
            master_user=self.master_user,
            is_admin=True,
            is_owner=False,
            is_deleted=False,
        )

    # TODO
    #  We need to decide, either we allow execution of bootstrap in tests or not
    #  If we allow, we need to create master user and finmars_bot there, so need to remove creating them in tests
    #  so, if we allow bootstrap in tests, we can uncomment this test
    # @mock.patch("poms.bootstrap.apps.requests.post")
    # @override_settings(AUTHORIZER_URL="authorizer/api/")
    # def test__run_load_ok(self, mock_post):
    #     mock_post.return_value = self.mock_response
    #     self.old_member.refresh_from_db(fields=["is_deleted"])
    #     self.assertFalse(self.old_member.is_deleted)
    #
    #     BootstrapConfig.load_master_user_data()
    #
    #     mock_post.assert_called()
    #
    #     self.old_member.refresh_from_db(fields=["is_deleted"])
    #     self.assertTrue(self.old_member.is_deleted)
