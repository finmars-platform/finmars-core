from django.utils.timezone import now

from poms.common.common_base_test import BIG, SMALL, BaseTestCase
from poms.portfolios.fields import ReconcileStatus
from poms.portfolios.models import PortfolioReconcileGroup, PortfolioReconcileHistory

EXPECTED_RESPONSE = {
    "Big": {
        "final_status": "ok",
        "history_objects": [
            {
                "id": 3,
                "user_code": "YMFTBFBQTJ",
                "name": "",
                "portfolio_reconcile_group": "ZQLGGNQNVC",
                "date": "2025-02-24",
                "verbose_result": None,
                "error_message": None,
                "status": "ok",
                "file_report": {
                    "content_type": "application/json",
                    "content_type_verbose": "json",
                    "created_at": "2025-02-25T17:14:11.704773Z",
                    "file_url": "/.system/file_reports/WUKYVOAUKF_2025-02-25-17-14_n.json",
                    "id": 2,
                    "name": "Reconciliation report " "2025-02-25-17-14 " "(Task None).json",
                    "notes": "System File",
                    "type": "simple_import.import",
                },
                "report_ttl": 90,
                "created_at": "2025-02-24T19:44:46.255778Z",
                "modified_at": "2025-02-24T19:44:46.255781Z",
            }
        ],
    },
}


class PortfolioReconcileHistoryViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-reconcile-history/status/"
        self.portfolio_big = self.db_data.portfolios[BIG]
        self.portfolio_small = self.db_data.portfolios[SMALL]
        self.group = self.create_reconcile_group()
        self.portfolios_list = [self.portfolio_big.user_code, self.portfolio_small.user_code]

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
            "portfolios": [self.random_string(), self.portfolio_big.user_code],
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
    def test__status_no_group_by_id(self, user_code):
        p_id = self.portfolio_big.id if user_code == BIG else self.portfolio_small.id
        data = {"portfolios": [p_id], "date": str(now().date())}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json), 1)
        self.assertEqual(
            response_json[user_code], {"final_status": "no_group", "all_statuses": {}, "history_objects": []}
        )

    @BaseTestCase.cases(
        ("small", SMALL),
        ("big", BIG),
    )
    def test__status_no_group_by_user_code(self, user_code):
        data = {"portfolios": [user_code], "date": str(now().date())}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json), 1)
        self.assertEqual(
            response_json[user_code], {"final_status": "no_group", "all_statuses": {}, "history_objects": []}
        )

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
        self.assertEqual(
            response_json[user_code], {"final_status": "not_run_yet", "all_statuses": {}, "history_objects": []}
        )

    @BaseTestCase.cases(
        ("small", SMALL),
        ("big", BIG),
    )
    def test__status_ok(self, user_code):
        portfolio = self.db_data.portfolios[user_code]
        self.group.portfolios.add(portfolio)
        self.group.save()
        history = self.create_reconcile_history(self.group)
        history.file_report = history.generate_json_report(b"report ok")
        history.save()

        data = {"portfolios": [user_code], "date": str(now().date())}

        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json), 1)

        self.assertEqual(response_json[user_code]["final_status"], ReconcileStatus.OK.value)

    def test__status_ok_double(self):
        self.group.portfolios.add(self.portfolio_big)
        self.group.portfolios.add(self.portfolio_small)
        self.group.save()
        _ = self.create_reconcile_history(self.group)

        data = {"portfolios": [BIG, SMALL], "date": str(now().date())}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json), 2)

        for user_code, result in response_json.items():
            self.assertEqual(result["final_status"], ReconcileStatus.OK.value)

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
        history.file_report = history.generate_json_report(b"report error")
        history.save()

        data = {"portfolios": [user_code], "date": str(now().date())}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json), 1)

        self.assertEqual(response_json[user_code]["final_status"], ReconcileStatus.ERROR.value)

    def test__status_error_double(self):
        self.group.portfolios.add(self.portfolio_big)
        self.group.portfolios.add(self.portfolio_small)
        self.group.save()
        history = self.create_reconcile_history(self.group)
        history.status = PortfolioReconcileHistory.STATUS_ERROR
        history.save()

        data = {"portfolios": [BIG, SMALL], "date": str(now().date())}
        response = self.client.get(path=self.url, data=data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json), 2)

        for user_code, result in response_json.items():
            self.assertEqual(result["final_status"], ReconcileStatus.ERROR.value)
