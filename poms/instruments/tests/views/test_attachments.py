from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import Instrument, FinmarsFile, InstrumentAttachment


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

    def test__files_added_ok(self):
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
            path=self.url, data={"files": files}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        print(response_json)
