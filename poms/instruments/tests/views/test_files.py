from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import Instrument, FinmarsFile


class FinmarsFileViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/instruments/files/"
        self.instrument = Instrument.objects.first()

    def test__check_api_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test_list(self):
        amount = 10
        for i in range(1, amount + 1):
            FinmarsFile.objects.create(
                name=f"name_{i}.pdf",
                path="/root/etc/system/",
                size=self.random_int(100, 1000000),
            )

        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)
