from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import Instrument


class InstrumentViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/instruments/instrument/ev-group/"
        self.instrument = Instrument.objects.first()
        self.instrument.country = self.get_country(name="United States of America")
        self.instrument.save()

        self.instrument = Instrument.objects.last()
        self.instrument.country = self.get_country(name="Turkey")
        self.instrument.save()

        self.expected_names = {"United States of America", "Turkey", None}

    def test__post_ev_group(self):
        post_data = {
            "groups_values": [],
            "page": 1,
            "page_size": 60,
            "is_enabled": "any",
            "groups_types": ["country"],
            "ev_options": {"entity_filters": ["disabled", "inactive", "active"]},
            "filter_settings": [],
            "global_table_search": "",
        }
        response = self.client.post(self.url, data=post_data, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json["count"], 3)
        self.assertEqual(len(response_json["results"]), 3)
        names = {group["group_name"] for group in response_json["results"]}
        self.assertEqual(names, self.expected_names)
