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

    # def test__api_url(self):
    #     response = self.client.get(path=self.url)
    #     response_json = response.json()
    #
    #     self.assertEqual(response.status_code, 200, response.content)
    #     self.assertEqual(len(response_json["results"]), 0)
    #     self.assertEqual(response_json["count"], 0)
    #     self.assertIn("next", response_json)
    #     self.assertIn("previous", response_json)
    #     self.assertIn("meta", response_json)
