from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import Instrument, FinmarsFile

expected_response = [
    {
        "id": 1,
        "instruments": [{"id": 1, "user_code": "-"}],
        "created": "2024-06-30T15:38:23.565757Z",
        "modified": "2024-06-30T15:38:23.565764Z",
        "name": "file_1.json",
        "path": "/root/workload",
        "extension": "json",
        "size": 730,
    },
    {
        "id": 2,
        "instruments": [{"id": 1, "user_code": "-"}],
        "created": "2024-06-30T15:38:23.566583Z",
        "modified": "2024-06-30T15:38:23.566588Z",
        "name": "file_2.json",
        "path": "/root/workload",
        "extension": "json",
        "size": 632,
    },
    {
        "id": 3,
        "instruments": [{"id": 1, "user_code": "-"}],
        "created": "2024-06-30T15:38:23.567007Z",
        "modified": "2024-06-30T15:38:23.567012Z",
        "name": "file_3.json",
        "path": "/root/workload",
        "extension": "json",
        "size": 332,
    },
]


class AttachmentViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm = "realm00000"
        self.space = "space00000"
        self.url = f"/{self.realm}/{self.space}/api/v1/instruments/attachments/"
        self.instrument = Instrument.objects.first()

    @BaseTestCase.cases(
        ("get", "get"),
        ("put", "put"),
        ("post", "post"),
        ("delete", "delete"),
    )
    def test__invalid_methods(self, name: str):
        method = getattr(self.client, name)

        response = method(self.url)

        self.assertEqual(response.status_code, 405)

    def test__files_added(self):
        amount = self.random_int(2, 10)
        files = []
        path = "/root/workload"
        for i in range(1, amount + 1):
            name = f"file_{i}.json"
            FinmarsFile.objects.create(
                name=name,
                path=path,
                size=self.random_int(10, 1000),
            )
            files.append(f"{path}/{name}")

        response = self.client.patch(
            path=f"{self.url}{self.instrument.id}/",
            data={"attachments": files},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json), amount)

        file_data = response_json[0]
        self.assertIn("id", file_data)
        self.assertIn("instruments", file_data)
        self.assertEqual(len(file_data["instruments"]), 1)
        self.assertIn("created", file_data)
        self.assertIn("modified", file_data)
        self.assertIn("name", file_data)
        self.assertIn("path", file_data)
        self.assertEqual(file_data["path"], path)
        self.assertIn("extension", file_data)
        self.assertEqual(file_data["extension"], "json")
        self.assertIn("size", file_data)

    def test__no_attachments(self):
        response = self.client.patch(
            path=f"{self.url}{self.instrument.id}/",
            data={"attachments": []},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertEqual(len(response_json), 0)

    def test__invalid_data(self):
        response = self.client.patch(
            path=f"{self.url}{self.instrument.id}/",
            data={"wrong_name": []},
            format="json",
        )
        self.assertEqual(response.status_code, 204, response.content)
