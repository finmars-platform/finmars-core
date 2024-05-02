from unittest import mock

from poms.common.common_base_test import BaseTestCase

from poms.common.storage import FinmarsS3Storage


class ExplorerViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/explorer/"

    @mock.patch("poms.explorer.views.storage")
    def test__no_path(self, storage):
        storage.return_value = mock.MagicMock(spec=FinmarsS3Storage)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)

    @mock.patch("poms.explorer.views.storage")
    def test__path_ends_with_slash(self, storage):
        storage.return_value = mock.MagicMock(spec=FinmarsS3Storage)

        response = self.client.get(self.url, {"path": "test/"})
        self.assertEqual(response.status_code, 400)

    @BaseTestCase.cases(
        ("test", "test"),
        ("test_test", "/test/test"),
    )
    @mock.patch("poms.explorer.views.storage")
    def test__with_path(self, path, storage):
        storage.return_value = mock.MagicMock(spec=FinmarsS3Storage)
        storage.listdir.return_value = [], []

        response = self.client.get(self.url, {"path": path})

        self.assertEqual(response.status_code, 200)

        storage.listdir.assert_called_once()

        response_data = response.json()
        print(response_data)
        # self.assertEqual(response_data["path"], [])
