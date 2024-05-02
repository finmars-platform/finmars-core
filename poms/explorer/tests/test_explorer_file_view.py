from unittest import mock

from poms.common.common_base_test import BaseTestCase

from poms.common.storage import FinmarsS3Storage


class ExplorerViewFileViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/view/"

    @mock.patch("poms.explorer.views.storage")
    def test__url(self, storage):
        storage.return_value = mock.MagicMock(spec=FinmarsS3Storage)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
