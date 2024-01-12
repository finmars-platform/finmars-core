from unittest import mock

from django.test import override_settings

from poms.bootstrap.apps import BootstrapConfig
from poms.common.common_base_test import BaseTestCase


class FinmarsTaskTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.mock_response_data = {
            "name": "new_master",
            "description": "description",
            "is_from_backup": True,
            "old_backup_name": None,
            "version": "6.6.6",
            "base_api_url": "space11111",
            "owner": {"username": self.user.username, "email": None},
            "status": 0,  # INITIAL
        }
        self.mock_response = mock.Mock()
        self.mock_response.status_code = 200
        self.mock_response.json.return_value = self.mock_response_data

    @mock.patch("poms.bootstrap.apps.requests.post")
    @override_settings(AUTHORIZER_URL="authorizer/api/")
    def test__run_load_ok(self, mock_post):
        mock_post.return_value = self.mock_response

        BootstrapConfig.load_master_user_data()

        mock_post.assert_called()
