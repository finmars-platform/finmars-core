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

    def test_list(self):
        pass
