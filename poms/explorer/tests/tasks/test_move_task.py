from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage


class MoveViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    # def test__valid_data(self):
    #     request_data = {"target_directory_path": "test", "items": ["file.txt"]}
    #     file_content = "file_content"
    #     self.storage_mock.open.return_value.read.return_value = file_content
    #     self.storage_mock.listdir.return_value = ([], ["file.txt"])
    #     response = self.client.post(self.url, request_data)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(response.data, {"status": "ok"})
