from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.counterparties.models import Counterparty


class CompanyViewTestCase(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/counterparties/counterparty/light/"

    @BaseTestCase.cases(
        ("name", "name"),
        ("user_code", "user_code"),
        ("short_name", "short_name"),
        ("public_name", "public_name"),
    )
    def test__filter_by_query(self, field):
        query = self.random_string(10)
        company = Counterparty.objects.first()

        self.assertTrue(hasattr(company, field))
        setattr(company, field, query)

        company.save()

        response = self.client.get(self.url, data={"query": query})
        self.assertEqual(response.status_code, 200, response.content)
        response_data = response.json()

        self.assertEqual(len(response_data["results"]), 1)
        self.assertEqual(response_data["count"], 1)
        self.assertIsNone(response_data["next"])
        self.assertIsNone(response_data["previous"])

        item = response_data["results"][0]
        self.assertEqual(item[field], query)
