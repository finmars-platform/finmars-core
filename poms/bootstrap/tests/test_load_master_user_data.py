from unittest import mock

from poms.common.common_base_test import BaseTestCase

from poms.bootstrap.apps import BootstrapConfig


class FinmarsTaskTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

    @mock.patch("poms.bootstrap.apps.requests.post")
    def test__run_load_ok(self, mock_post):
        # BootstrapConfig("app_name", "app_module").load_master_user_data()
        #
        # mock_post.assert_not_called()
        pass
