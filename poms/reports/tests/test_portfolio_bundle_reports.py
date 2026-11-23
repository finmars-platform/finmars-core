from copy import deepcopy
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache

from poms.accounts.models import Account
from poms.common.common_base_test import BIG, SMALL
from poms.iam.models import AccessPolicy
from poms.instruments.fields import BundleField
from poms.portfolios.models import Portfolio, PortfolioBundle, PortfolioRegister
from poms.reports.models import PLReportInstance
from poms.reports.tests.common_report_case import BACKEND_OPTIONS, PL_FIRST_DATE, ReportsTestCase
from poms.transactions.models import TransactionClass
from poms.users.models import MasterUser, Member


class PortfolioBundleReportTest(ReportsTestCase):
    def setUp(self):
        super().setUp()
        other_account = Account.objects.create(
            master_user=self.master_user, owner=self.member, user_code="Other", name="Other"
        )
        self.other = Portfolio.objects.create(
            master_user=self.master_user, owner=self.member, user_code="Other", name="Other"
        )
        self.other.accounts.add(other_account)
        self.book(self.other, None, TransactionClass.CASH_INFLOW, 0, 0, 700, date(2025, 11, 3))
        self.book(self.other, self.tesla, TransactionClass.BUY, 3, -150, -150, date(2026, 2, 10))
        self.register_big = PortfolioRegister.objects.get(master_user=self.master_user, user_code=BIG)
        self.register_small = PortfolioRegister.objects.get(master_user=self.master_user, user_code=SMALL)
        self.bundle = PortfolioBundle.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code="synthetic-bundle",
            name="Synthetic bundle",
        )
        self.bundle.registers.set([self.register_big, self.register_small])

    def compare_items(self, endpoint, bundle_value=None, **kwargs):
        if bundle_value is None:
            bundle_value = self.bundle.id
        by_bundle = self.post_report(endpoint, bundle=bundle_value, **kwargs)
        by_portfolios = self.post_report(endpoint, portfolios=[self.big.id, self.small.id], **kwargs)
        self.assertEqual(by_bundle.status_code, 200, by_bundle.content)
        self.assertEqual(by_portfolios.status_code, 200, by_portfolios.content)
        self.assertTrue(by_bundle.json()["items"])
        self.assertEqual(self.positions(by_bundle.json()["items"]), self.positions(by_portfolios.json()["items"]))
        return by_bundle.json()

    def test_balance_bundle_matches_portfolios_by_id_and_user_code(self):
        for bundle_value in (self.bundle.id, self.bundle.user_code):
            for mode in (0, 1):
                with self.subTest(bundle_value=bundle_value, mode=mode):
                    data = self.compare_items(
                        "balance-report",
                        bundle_value=bundle_value,
                        portfolio_mode=mode,
                        account_mode=mode,
                        calculate_pl=True,
                    )
                    self.assertEqual(set(data["portfolios"]), {self.big.id, self.small.id})
                    self.assertNotIn("bundle", data)

    def test_pl_bundle_matches_portfolios(self):
        for mode in (0, 1):
            with self.subTest(mode=mode):
                self.compare_items(
                    "pl-report", pl_first_date=str(PL_FIRST_DATE), portfolio_mode=mode, account_mode=mode
                )

    def test_backend_items_match_portfolios(self):
        for endpoint in ("backend-balance-report/items", "backend-pl-report/items"):
            kwargs = {"frontend_request_options": deepcopy(BACKEND_OPTIONS)}
            if "pl-report" in endpoint:
                kwargs["pl_first_date"] = str(PL_FIRST_DATE)
                kwargs["ignore_cache"] = True
            with self.subTest(endpoint=endpoint):
                self.compare_items(endpoint, **kwargs)

    def test_backend_groups_match_portfolios(self):
        options = {**BACKEND_OPTIONS, "groups_types": [{"key": "portfolio.user_code"}]}
        for endpoint in ("backend-balance-report/groups", "backend-pl-report/groups"):
            kwargs = {"frontend_request_options": deepcopy(options)}
            if "pl-report" in endpoint:
                kwargs["pl_first_date"] = str(PL_FIRST_DATE)
                kwargs["ignore_cache"] = True
            with self.subTest(endpoint=endpoint):
                by_bundle = self.post_report(endpoint, bundle=self.bundle.id, **kwargs)
                by_portfolios = self.post_report(endpoint, portfolios=[self.big.id, self.small.id], **kwargs)
                self.assertEqual(by_bundle.status_code, 200, by_bundle.content)
                self.assertEqual(by_portfolios.status_code, 200, by_portfolios.content)
                actual = {item["___group_identifier"] for item in by_bundle.json()["items"]}
                expected = {item["___group_identifier"] for item in by_portfolios.json()["items"]}
                self.assertTrue(expected)
                self.assertEqual(actual, expected)

    def test_empty_bundle_and_conflicting_selectors_are_rejected(self):
        empty = PortfolioBundle.objects.create(
            master_user=self.master_user, owner=self.member, user_code="synthetic-empty", name="Empty bundle"
        )
        for endpoint in ("balance-report", "pl-report"):
            kwargs = {"pl_first_date": str(PL_FIRST_DATE)} if endpoint == "pl-report" else {}
            with self.subTest(endpoint=endpoint, case="empty"):
                self.assertEqual(self.post_report(endpoint, bundle=empty.id, **kwargs).status_code, 400)
            with self.subTest(endpoint=endpoint, case="both"):
                self.assertEqual(
                    self.post_report(
                        endpoint, bundle=self.bundle.id, portfolios=[self.other.id], **kwargs
                    ).status_code,
                    400,
                )
            with self.subTest(endpoint=endpoint, case="empty-portfolio-list"):
                self.assertEqual(
                    self.post_report(endpoint, bundle=self.bundle.id, portfolios=[], **kwargs).status_code, 200
                )

    def test_duplicate_registers_do_not_duplicate_portfolios(self):
        duplicate = self.db_data.create_portfolio_register(
            portfolio=self.big, instrument=self.db_data.default_instrument, user_code="synthetic-second-register"
        )
        self.bundle.registers.add(duplicate)
        data = self.compare_items("balance-report", portfolio_mode=0, account_mode=0, calculate_pl=True)
        self.assertEqual(set(data["portfolios"]), {self.big.id, self.small.id})
        self.assertEqual(len(data["portfolios"]), 2)

    def test_deleted_bundle_members_are_not_silently_ignored(self):
        PortfolioRegister.objects.filter(pk=self.register_big.pk).update(is_deleted=True)
        response = self.post_report("balance-report", bundle=self.bundle.id)
        self.assertEqual(response.status_code, 400)

    def test_deleted_portfolio_is_not_silently_ignored(self):
        Portfolio.objects.filter(pk=self.big.pk).update(is_deleted=True)
        response = self.post_report("balance-report", bundle=self.bundle.id)
        self.assertEqual(response.status_code, 400)

    def test_unknown_bundle_is_rejected(self):
        for endpoint in ("balance-report", "pl-report"):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.post_report(endpoint, bundle="missing-synthetic-bundle").status_code, 400)

    def test_bundle_from_another_master_user_is_rejected(self):
        other_master = MasterUser.objects.create(name="Synthetic foreign master", space_code="spaceforeign")
        other_bundle = PortfolioBundle.objects.create(
            master_user=other_master, owner=self.member, user_code="synthetic-foreign", name="Synthetic foreign"
        )
        other_bundle.registers.add(self.register_big)
        self.assertEqual(self.post_report("balance-report", bundle=other_bundle.id).status_code, 400)

    def test_bundle_user_code_is_scoped_to_current_master_user(self):
        other_master = MasterUser.objects.create(name="Synthetic foreign master", space_code="spaceforeign")
        other_bundle = PortfolioBundle.objects.create(
            master_user=other_master, owner=self.member, user_code=self.bundle.user_code, name="Synthetic foreign"
        )
        other_bundle.registers.add(self.register_big)
        self.compare_items("balance-report", bundle_value=self.bundle.user_code, calculate_pl=True)

    def test_numeric_string_id_works_without_user_code_conflict(self):
        self.compare_items("balance-report", bundle_value=str(self.bundle.id), calculate_pl=True)

    def test_numeric_code_matching_its_own_id_is_unambiguous(self):
        PortfolioBundle.objects.filter(pk=self.bundle.pk).update(user_code=str(self.bundle.pk))
        self.compare_items("balance-report", bundle_value=str(self.bundle.pk), calculate_pl=True)

    def test_ambiguous_numeric_user_code_is_rejected_without_selecting_wrong_bundle(self):
        other = PortfolioBundle.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=str(self.bundle.id),
            name="Synthetic numeric code",
        )
        other.registers.add(self.register_big)
        response = self.post_report("balance-report", bundle=str(self.bundle.id))
        self.assertEqual(response.status_code, 400)
        self.compare_items("balance-report", bundle_value=self.bundle.id, calculate_pl=True)

    def test_boolean_bundle_value_is_rejected_before_lookup(self):
        with patch.object(BundleField, "to_internal_value", side_effect=AssertionError("unexpected bundle lookup")):
            for value in (True, False):
                with self.subTest(value=value):
                    response = self.post_report("balance-report", bundle=value)
                    self.assertEqual(response.status_code, 400)

    def test_register_or_portfolio_from_another_master_user_is_rejected(self):
        other_master = MasterUser.objects.create(name="Synthetic foreign master", space_code="spaceforeign")
        for model, obj in ((PortfolioRegister, self.register_big), (Portfolio, self.big)):
            with self.subTest(model=model.__name__):
                model.objects.filter(pk=obj.pk).update(master_user=other_master)
                response = self.post_report("balance-report", bundle=self.bundle.id)
                self.assertEqual(response.status_code, 400)
                model.objects.filter(pk=obj.pk).update(master_user=self.master_user)

    def test_null_bundle_preserves_existing_portfolio_selection(self):
        for endpoint in ("balance-report", "pl-report"):
            kwargs = {"pl_first_date": str(PL_FIRST_DATE)} if endpoint == "pl-report" else {}
            with self.subTest(endpoint=endpoint):
                original = self.post_report(endpoint, portfolios=[self.big.id], **kwargs)
                with_null = self.post_report(endpoint, portfolios=[self.big.id], bundle=None, **kwargs)
                self.assertEqual(original.status_code, 200, original.content)
                self.assertEqual(with_null.status_code, 200, with_null.content)
                self.assertTrue(original.json()["items"])
                self.assertEqual(self.positions(original.json()["items"]), self.positions(with_null.json()["items"]))
                self.assertNotIn("bundle", with_null.json())

    def test_bundle_with_a_denied_portfolio_is_rejected(self):
        user = User.objects.create_user(username="synthetic_bundle_viewer")
        viewer = Member.objects.create(
            master_user=self.master_user, user=user, username="synthetic_bundle_viewer", is_admin=False, is_owner=False
        )
        for model, code in (("portfoliobundle", self.bundle.user_code), ("portfolio", self.big.user_code)):
            policy = AccessPolicy.objects.create(
                owner=self.member,
                configuration_code="local.poms.space00000",
                user_code=f"synthetic_{model}_grant",
                name=f"Synthetic {model} grant",
                policy={
                    "Version": "2023-01-01",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [f"finmars:{model}:view"],
                            "Resource": [f"frn:finmars:portfolios:{model}:{code}"],
                        }
                    ],
                },
            )
            policy.members.add(viewer)
        cache.delete(f"member_access_policies_{viewer.pk}")
        self.client.force_authenticate(user)
        for endpoint in ("balance-report", "pl-report"):
            kwargs = {"pl_first_date": str(PL_FIRST_DATE)} if endpoint == "pl-report" else {}
            with self.subTest(endpoint=endpoint):
                allowed = self.post_report(endpoint, portfolios=[self.big.id], **kwargs)
                self.assertEqual(allowed.status_code, 200, allowed.content)
                denied = self.post_report(endpoint, bundle=self.bundle.id, **kwargs)
                self.assertEqual(denied.status_code, 400, denied.content)

    def test_bundle_backend_pl_does_not_read_or_write_report_cache(self):
        for endpoint in ("backend-pl-report/items", "backend-pl-report/groups"):
            options = deepcopy(BACKEND_OPTIONS)
            if endpoint.endswith("groups"):
                options["groups_types"] = [{"key": "portfolio.user_code"}]
            with self.subTest(endpoint=endpoint):
                before = PLReportInstance.objects.count()
                with (
                    patch.object(PLReportInstance.objects, "get", side_effect=AssertionError("cache read")),
                    patch.object(PLReportInstance, "save", side_effect=AssertionError("cache write")),
                ):
                    response = self.post_report(
                        endpoint,
                        bundle=self.bundle.id,
                        pl_first_date=str(PL_FIRST_DATE),
                        frontend_request_options=options,
                        ignore_cache=False,
                    )
                self.assertEqual(response.status_code, 200, response.content)
                self.assertIsNone(response.json().get("report_instance_id"))
                self.assertFalse(response.json()["ignore_cache"])
                self.assertEqual(PLReportInstance.objects.count(), before)

    def test_bundle_membership_changes_are_reflected_in_backend_pl(self):
        options = deepcopy(BACKEND_OPTIONS)
        first = self.post_report(
            "backend-pl-report/items",
            bundle=self.bundle.id,
            pl_first_date=str(PL_FIRST_DATE),
            frontend_request_options=options,
        )
        self.assertEqual(first.status_code, 200, first.content)
        self.bundle.registers.set([self.register_big])
        second = self.post_report(
            "backend-pl-report/items",
            bundle=self.bundle.id,
            pl_first_date=str(PL_FIRST_DATE),
            frontend_request_options=deepcopy(BACKEND_OPTIONS),
        )
        expected = self.post_report(
            "backend-pl-report/items",
            portfolios=[self.big.id],
            pl_first_date=str(PL_FIRST_DATE),
            frontend_request_options=deepcopy(BACKEND_OPTIONS),
            ignore_cache=True,
        )
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(expected.status_code, 200, expected.content)
        self.assertTrue(expected.json()["items"])
        self.assertEqual(self.positions(second.json()["items"]), self.positions(expected.json()["items"]))
        self.assertNotEqual(self.positions(first.json()["items"]), self.positions(second.json()["items"]))

    def test_pl_inception_with_explicit_start_matches_portfolio_list(self):
        for endpoint in ("pl-report", "backend-pl-report/items"):
            kwargs = {"period_type": "inception", "pl_first_date": str(PL_FIRST_DATE)}
            if endpoint.startswith("backend-"):
                kwargs["frontend_request_options"] = deepcopy(BACKEND_OPTIONS)
            with self.subTest(endpoint=endpoint):
                self.compare_items(endpoint, **kwargs)
