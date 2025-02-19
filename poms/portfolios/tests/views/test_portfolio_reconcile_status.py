from django.utils.timezone import now

from poms.common.common_base_test import BIG, BaseTestCase, SMALL
from poms.portfolios.models import PortfolioReconcileGroup, PortfolioReconcileHistory
from poms.portfolios.fields import ReconcileStatus


class PortfolioReconcileHistoryViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-reconcile-history/status/"
        self.portfolio_1 = self.db_data.portfolios[BIG]
        self.portfolio_2 = self.db_data.portfolios[SMALL]
        self.group = self.create_reconcile_group()
        self.portfolios_list = [self.portfolio_1.user_code, self.portfolio_2.user_code]

    def create_reconcile_group(self) -> PortfolioReconcileGroup:
        return PortfolioReconcileGroup.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            name=self.random_string(),
            params={
                "precision": 1,
                "only_errors": False,
            },
        )

    def create_reconcile_history(self, group: PortfolioReconcileGroup) -> PortfolioReconcileHistory:
        return PortfolioReconcileHistory.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            portfolio_reconcile_group=group,
            date=now().date(),
        )

    def test__empty_portfolios(self):
        data = {"portfolios": [], "date": str(now().date())}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 400, response.content)

    def test__no_portfolios(self):
        data = {"date": str(now().date())}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 400, response.content)

    def test__invalid_portfolios(self):
        data = {
            "portfolios": [self.random_string(), self.portfolio_1.user_code],
            "date": str(now().date()),
        }
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 400, response.content)

    def test__no_date(self):
        data = {"portfolios": self.portfolios_list}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 400, response.content)

    def test__invalid_date(self):
        data = {"portfolios": self.portfolios_list, "date": "172671652"}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 400, response.content)

    @BaseTestCase.cases(
        ("small", SMALL),
        ("big", BIG),
    )
    def test__status_no_group(self, user_code):
        data = {"portfolios": [user_code], "date": str(now().date())}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json), 1)
        self.assertEqual(response_json[user_code], ReconcileStatus.NO_GROUP.value)

    @BaseTestCase.cases(
        ("small", SMALL),
        ("big", BIG),
    )
    def test__status_not_run_yet(self, user_code):
        portfolio = self.db_data.portfolios[user_code]
        self.group.portfolios.add(portfolio)
        self.group.save()

        data = {"portfolios": [user_code], "date": str(now().date())}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json), 1)
        self.assertEqual(response_json[user_code], ReconcileStatus.NOT_RUN_YET.value)

    @BaseTestCase.cases(
        ("small", SMALL),
        ("big", BIG),
    )
    def test__status_ok(self, user_code):
        portfolio = self.db_data.portfolios[user_code]
        self.group.portfolios.add(portfolio)
        self.group.save()
        _ = self.create_reconcile_history(self.group)

        data = {"portfolios": [user_code], "date": str(now().date())}

        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json), 1)
        self.assertEqual(response_json[user_code], ReconcileStatus.OK.value)

    @BaseTestCase.cases(
        ("small", SMALL),
        ("big", BIG),
    )
    def test__status_error(self, user_code):
        portfolio = self.db_data.portfolios[user_code]
        self.group.portfolios.add(portfolio)
        self.group.save()
        history = self.create_reconcile_history(self.group)
        history.status = PortfolioReconcileHistory.STATUS_ERROR
        history.save()

        data = {"portfolios": [user_code], "date": str(now().date())}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json), 1)
        self.assertEqual(response_json[user_code], ReconcileStatus.ERROR.value)
