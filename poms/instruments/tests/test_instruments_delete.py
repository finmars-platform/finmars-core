from django.conf import settings
from poms.currencies.constants import DASH
from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import Instrument

class InstrumentDeleteViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = 'realm00000'
        self.space_code = 'space00000'
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/instruments/instrument"

    def test_detail_delete_main_instruments(self):
        for instrument in Instrument.objects.filter(user_code__in=DASH):
            response = self.client.delete(path=f"{self.url}/{instrument.id}/")
            self.assertEqual(response.status_code, 409)
            
    def test_detail_delete_custom_instruments(self):
        instrument_last = Instrument.objects.last()
        instrument = Instrument.objects.create(
            user_code="test",
            name="test",
            owner=instrument_last.owner,
            master_user=instrument_last.master_user,
            accrued_currency=instrument_last.accrued_currency,
            instrument_type=instrument_last.instrument_type,
            pricing_currency=instrument_last.pricing_currency,
        )

        self.assertNotIn(instrument.user_code, DASH)

        response = self.client.delete(path=f"{self.url}/{instrument.id}/")
        self.assertEqual(response.status_code, 204)