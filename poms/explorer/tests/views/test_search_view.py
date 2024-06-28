from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import FinmarsFile


class ExplorerViewFileViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/search/"

    @BaseTestCase.cases(
        ("no_query", None),
        ("empty_query", ""),
        ("no_file", "empty"),
    )
    def test__no_query(self, query):
        api_url = self.url if query is None else f"{self.url}?query={query}"
        response = self.client.get(api_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(len(response_json), 0)
