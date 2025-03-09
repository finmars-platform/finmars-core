from poms.common.common_base_test import BIG, BUY_SELL, BaseTestCase
from poms.users.models import EcosystemDefault
from poms.users.tests.common_test_data import EXPECTED_RESPONSE_DATA


class EcosystemDefaultViewSetTest(BaseTestCase):
    maxDiff = None

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/users/ecosystem-default/"

    def test__list(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json["count"], 1)
        ecosystem_data = response_json["results"][0]
        self._validate_ecosystem_data(ecosystem_data)

    def test__retrieve(self):
        ecosystem_default = EcosystemDefault.objects.first()

        response = self.client.get(path=f"{self.url}{ecosystem_default.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self._validate_ecosystem_data(response_json)

    def _validate_ecosystem_data(self, data: dict):
        self.assertTrue(set(EXPECTED_RESPONSE_DATA.keys()).issubset(set(data.keys())))
        self.assertEqual(data["master_user"], self.master_user.id)
        self.assertEqual(data["instrument"], self.default_instrument.id)
        self.assertEqual(data["currency"], self.usd.id)

    def test__create(self):
        responsible = self.db_data.create_responsible()
        data = {
            "master_user": self.master_user.id,
            "currency": self.eur.id,
            "account_type": self.account_type.id,
            "account": self.account.id,
            "counterparty_group": self.db_data.counter_party.group.id,
            "counterparty": self.db_data.counter_party.id,
            "responsible_group": responsible.group_id,
            "responsible": responsible.id,
            "instrument_type": self.default_instrument_type.id,
            "instrument": self.default_instrument.id,
            "portfolio": self.db_data.portfolios[BIG].id,
            "strategy1_group": self.db_data.strategy_groups[1].id,
            "strategy1_subgroup": self.db_data.strategy_subgroups[1].id,
            "strategy1": self.db_data.strategies[1].id,
            "strategy2_group": self.db_data.strategy_groups[2].id,
            "strategy2_subgroup": self.db_data.strategy_subgroups[2].id,
            "strategy2": self.db_data.strategies[2].id,
            "strategy3_group": self.db_data.strategy_groups[3].id,
            "strategy3_subgroup": self.db_data.strategy_subgroups[3].id,
            "strategy3": self.db_data.strategies[3].id,
            "mismatch_portfolio": self.db_data.portfolios[BIG].id,
            "mismatch_account": self.account.id,
            "pricing_policy": self.create_pricing_policy().id,
            "transaction_type": self.db_data.transaction_types[BUY_SELL].id,
            "periodicity": self.get_periodicity().id,
        }

        response = self.client.post(path=self.url, format="json", data=data)

        self.assertEqual(response.status_code, 201, response.content)
