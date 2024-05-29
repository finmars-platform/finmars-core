from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage


class UnzipViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/unzip/"

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

        self.mimetypes_patch = mock.patch(
            "poms.explorer.views.mimetypes.guess_type",
            return_value=("text/plain", "utf-8"),
        )
        self.mimetypes_mock = self.mimetypes_patch.start()
        self.addCleanup(self.mimetypes_patch.stop)

    @BaseTestCase.cases(
        ("no_target_1", {"target_directory_path": "", "file_path": "file"}),
        ("no_target_2", {"file_path": "file"}),
        ("no_file_path_1", {"target_directory_path": "target", "file_path": ""}),
        ("no_file_path_2", {"target_directory_path": "target" }),
    )
    def test__path_ends_or_starts_with_slash(self, data):
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 400)

    @BaseTestCase.cases(
        ("short_target", {"target_directory_path": "target", "file_path": "file.zip"}),
        ("long_target", {"target_directory_path": "a/b/c", "file_path": "file.zip"}),
    )
    @mock.patch("poms.explorer.views.unzip_file")
    def test__unzip(self, data, mock_unzip):
        self.storage_mock.dir_exists.return_value = True
        self.storage_mock.size.return_value = 100

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.storage_mock.dir_exists.assert_called_once()
        self.storage_mock.size.assert_called_once()

        mock_unzip.assert_called_once()
        args, kwargs = mock_unzip.call_args_list[0]
        self.assertEqual(args[1], f'space00000/{data["file_path"]}')
        self.assertEqual(args[2], f'space00000/{data["target_directory_path"]}/')
