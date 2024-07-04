from poms.common.common_base_test import BaseTestCase
from poms.explorer.models import FinmarsFile

expected_response = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {
            "type": "file",
            "mime_type": "application/pdf",
            "name": "name_1.pdf",
            "created": "2024-06-30T11:02:20.655172Z",
            "modified": "2024-06-30T11:02:20.655180Z",
            "file_path": "/test/",
            "size": 8567748,
            "size_pretty": "8.17 MB",
        }
    ],
    "meta": {"execution_time": 3, "request_id": "b212f36e-9144-4f13-aaed-d9a16b54133d"},
}


class SearchFileViewSetTest(BaseTestCase):
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
        self.assertEqual(response_json["count"], 0)
        self.assertEqual(len(response_json["results"]), 0)

    @BaseTestCase.cases(
        ("post", "post"),
        ("put", "put"),
        ("patch", "patch"),
        ("delete", "delete"),
    )
    def test__405_methods(self, name: str):
        method = getattr(self.client, name)

        response = method(self.url)

        self.assertEqual(response.status_code, 405)

    def test__405_retrieve(self):
        response = self.client.get(f"{self.url}1/")

        self.assertEqual(response.status_code, 405)

    def test__list_no_query(self):
        size = self.random_int(111, 10000000)
        kwargs = dict(
            name="name_1.pdf",
            path="/test/",
            size=size,
        )
        file = FinmarsFile.objects.create(**kwargs)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()

        self.assertIn("meta", response_json)
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(len(response_json["results"]), 1)

        file_json = response_json["results"][0]
        self.assertEqual(file_json["type"], "file")
        self.assertEqual(file_json["mime_type"], "application/pdf")
        self.assertEqual(file_json["name"], file.name)
        self.assertIn("created", file_json)
        self.assertIn("modified", file_json)
        self.assertEqual(file_json["file_path"], file.path)
        self.assertEqual(file_json["size"], file.size)
        self.assertIn("size_pretty", file_json)

    def test__list_many(self):
        amount = self.random_int(5, 10)
        for i in range(1, amount + 1):
            FinmarsFile.objects.create(
                name=f"name_{i}.pdf",
                path="/root/etc/system/",
                size=self.random_int(10, 1000),
            )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()

        self.assertEqual(response_json["count"], amount)
        self.assertEqual(len(response_json["results"]), amount)

    @BaseTestCase.cases(
        ("name_1", "name_1", 1),
        ("name_2", "1,2,3", 3),
        ("name_all", "name", None),
        ("exten", "2.pdf", 1),
        ("path_1", "/root", None),
        ("path_2", "etc", None),
        ("path_3", "/system/", None),
    )
    def test__list_with_filters(
        self,
        value,
        count,
    ):
        amount = self.random_int(5, 9)
        for i in range(1, amount + 1):
            FinmarsFile.objects.create(
                name=f"name_{i}.pdf",
                path="/root/etc/system/",
                size=self.random_int(10, 1000),
            )

        count = count or amount
        response = self.client.get(path=f"{self.url}?query={value}")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json["count"], count)
        self.assertEqual(len(response_json["results"]), count)
