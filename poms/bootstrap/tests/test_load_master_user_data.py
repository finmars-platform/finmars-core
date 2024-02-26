from unittest import mock

from django.test import override_settings

from poms.bootstrap.apps import BootstrapConfig
from poms.common.common_base_test import BaseTestCase
from poms.users.models import Member

MOCK_RESPONSE = {
    "name": "master_from_backup",
    "description": "description",
    "is_from_backup": True,
    "old_backup_name": None,
    "version": "6.6.6",
    "base_api_url": "space00000",
    "owner": {"username": "new_owner", "email": "test@mail.ru"},
    "status": 0,  # INITIAL
}


class FinmarsTaskTestCase(BaseTestCase):
    """
    Test doesn't run whole BootstrapConfig class,
    it checks only one method: load_master_user_data
    """

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.old_member = Member.objects.create(
            master_user=self.master_user,
            is_admin=True,
            is_owner=False,
            is_deleted=False,
        )

    @mock.patch("poms.bootstrap.apps.requests.post")
    @override_settings(AUTHORIZER_URL="authorizer/api/")
    def test__load_master_user_data_status_initial(self, mock_post):
        mock_response_data = MOCK_RESPONSE.copy()
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.text = "initial status"
        mock_response.json.return_value = mock_response_data

        mock_post.return_value = mock_response
        self.old_member.refresh_from_db(fields=["is_deleted"])
        self.assertFalse(self.old_member.is_deleted)

        BootstrapConfig.load_master_user_data()

        mock_post.assert_called()

        self.old_member.refresh_from_db(fields=["is_deleted"])
        self.assertTrue(self.old_member.is_deleted)

    @mock.patch("poms.bootstrap.apps.requests.post")
    @override_settings(AUTHORIZER_URL="authorizer/api/")
    def test__load_master_user_data_status_operational(self, mock_post):
        mock_response_data = MOCK_RESPONSE.copy()
        mock_response_data["status"] = 1  # OPERATIONAL
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.text = "operational status"
        mock_response.json.return_value = mock_response_data

        mock_post.return_value = mock_response
        self.old_member.refresh_from_db(fields=["is_deleted"])
        self.assertFalse(self.old_member.is_deleted)

        BootstrapConfig.load_master_user_data()

        mock_post.assert_called()

        self.old_member.refresh_from_db(fields=["is_deleted"])
        self.assertFalse(self.old_member.is_deleted)
