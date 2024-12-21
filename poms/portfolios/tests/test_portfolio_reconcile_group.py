from django.conf import settings
from django.test import override_settings

from poms.common.common_base_test import BIG, BaseTestCase, SMALL
from poms.configuration.utils import get_default_configuration_code
from poms.instruments.models import PricingPolicy
from poms.portfolios.models import PortfolioReconcileGroup


class PortfolioReconcileGroupViewTest(BaseTestCase):
    databases = "__all__"
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-reconcile-group/"
        self.portfolio_1 = self.db_data.portfolios[BIG]
        self.portfolio_2 = self.db_data.portfolios[SMALL]

    def test_check_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test_create(self):

        response = self.client.post(self.url, data=self.pr_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        pr = PortfolioRegister.objects.filter(name="name").first()
        self.assertIsNotNone(pr)

    def test_no_create_with_invalid_new_instrument(self):
        new_instrument = self.db_data.instruments["Tesla B."]
        new_pr_data = {
            **self.pr_data,
            "new_linked_instrument": {
                "name": new_instrument.name,
                "short_name": new_instrument.short_name,
                "user_code": new_instrument.user_code,
                "public_name": new_instrument.public_name,
                "instrument_type": self.random_int(),
            },
        }

        response = self.client.post(self.url, data=new_pr_data, format="json")
        self.assertEqual(response.status_code, 400, response.content)
