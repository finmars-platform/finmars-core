from django.utils.timezone import now

from poms.common.common_base_test import BIG, BaseTestCase, SMALL
from poms.portfolios.models import PortfolioReconcileGroup


class PortfolioReconcileHistoryViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-reconcile-history/status/"
        self.portfolio_1 = self.db_data.portfolios[BIG]
        self.portfolio_2 = self.db_data.portfolios[SMALL]
        self.group = self.create_reconcile_group()
        self.portfolios = [self.portfolio_1.id, self.portfolio_2.id]

    def create_reconcile_group(self) -> PortfolioReconcileGroup:
        return PortfolioReconcileGroup.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            name=self.random_string(),
            params={
                "precision": 1,
                "only_errors": False,
            }
        )

    def test__no_portfolios(self):
        data = {"portfolios": []}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 400, response.content)

    def test__invalid_portfolios(self):
        data = {"portfolios": [self.random_int(10000, 20000), self.random_int(10000, 20000)]}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 400, response.content)

    def test_check_is_not_member(self):
        data = {"portfolios": self.portfolios}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        result_1 = response_json[0]
        self.assertIn(int(list(result_1.keys())[0]), self.portfolios)
        self.assertEqual(list(result_1.values())[0], "isn't member of any reconcile group")

        result_2 = response_json[1]
        self.assertIn(int(list(result_2.keys())[0]), self.portfolios)
        self.assertEqual(list(result_2.values())[0], "isn't member of any reconcile group")

    def test_check_not_run_yet(self):
        for p in self.portfolios:
            self.group.portfolios.add(p)
        self.group.save()

        data = {"portfolios": self.portfolios}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        result_1 = response_json[0]
        self.assertIn(int(list(result_1.keys())[0]), self.portfolios)
        self.assertEqual(list(result_1.values())[0], "reconciliation didn't start yet")

        result_2 = response_json[1]
        self.assertIn(int(list(result_2.keys())[0]), self.portfolios)
        self.assertEqual(list(result_2.values())[0], "reconciliation didn't start yet")

    def test_check_has_last_time(self):
        for p in self.portfolios:
            self.group.portfolios.add(p)

        self.group.last_calculated_at = now()
        self.group.save()

        data = {"portfolios": self.portfolios}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        print(response_json)

        result_1 = response_json[0]
        self.assertIn(int(list(result_1.keys())[0]), self.portfolios)
        self.assertEqual(list(result_1.values())[0], str(now().date()))

        result_2 = response_json[1]
        self.assertIn(int(list(result_2.keys())[0]), self.portfolios)
        self.assertEqual(list(result_2.values())[0], str(now().date()))
