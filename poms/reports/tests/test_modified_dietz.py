import datetime
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from poms.reports.performance_report import PerformanceReportBuilder
from poms.transactions.models import TransactionClass


class RecordQuerySet:
    """Small in-memory subset of the QuerySet operations used by the builder."""

    def __init__(self, records):
        self.records = list(records)

    def filter(self, **kwargs):
        def matches(record):
            for lookup, expected in kwargs.items():
                field, _, operator = lookup.partition("__")
                value = getattr(record, field)
                if operator == "in" and value not in expected:
                    return False
                if operator == "lte" and value > expected:
                    return False
                if operator == "gte" and value < expected:
                    return False
                if not operator and value != expected:
                    return False
                if operator not in {"", "in", "lte", "gte"}:
                    raise AssertionError(f"Unsupported lookup: {lookup}")
            return True

        return RecordQuerySet(record for record in self.records if matches(record))

    def order_by(self, field):
        if field != "transaction_date":
            raise AssertionError(f"Unsupported ordering: {field}")
        return RecordQuerySet(sorted(self.records, key=lambda record: record.transaction_date))

    def __len__(self):
        return len(self.records)

    def __iter__(self):
        return iter(self.records)


class ModifiedDietzTests(TestCase):
    def setUp(self):
        self.start = datetime.date(2024, 1, 1)
        self.end = datetime.date(2024, 1, 11)
        self.usd = SimpleNamespace(id=1)
        self.eur = SimpleNamespace(id=2)
        self.policy = object()
        self.first = self.register("first", self.start)
        self.second = self.register("second", self.start)
        self.later = self.register("later", datetime.date(2024, 1, 4))

    def register(self, code, first_date):
        portfolio = SimpleNamespace(user_code=code, first_transaction_date=first_date)
        return SimpleNamespace(portfolio=portfolio, valuation_pricing_policy=self.policy)

    def record(self, record_id, register, day, amount, transaction_class, currency=None):
        return SimpleNamespace(
            id=record_id,
            portfolio_register=register,
            transaction_date=datetime.date(2024, 1, day),
            cash_amount_valuation_currency=amount,
            transaction_class=transaction_class,
            transaction_class_id=transaction_class,
            valuation_currency=currency or self.usd,
        )

    def build(self, registers, records, begin=None, nav=None, end=None):
        begin = begin or self.start
        end = end or self.end
        nav = nav or {self.start: 0, end: 520}
        instance = SimpleNamespace(first_transaction_date=self.start, report_currency=self.usd)
        builder = PerformanceReportBuilder.__new__(PerformanceReportBuilder)
        builder.instance = instance
        builder.ecosystem_defaults = SimpleNamespace(currency=self.usd)
        queryset = RecordQuerySet(records)

        def fx_lookup(*, date, pricing_policy, currency):
            self.assertEqual(pricing_policy, self.policy)
            self.assertEqual(currency.id, self.eur.id)
            return SimpleNamespace(fx_rate=2)

        with (
            patch.object(builder, "get_portfolio_registers", return_value=registers),
            patch.object(builder, "get_nav_by_date", side_effect=lambda portfolios, date, policy: nav[date]),
            patch("poms.reports.performance_report.PortfolioRegisterRecord.objects") as manager,
            patch("poms.reports.performance_report.CurrencyHistory.objects.get", side_effect=fx_lookup),
        ):
            manager.filter.side_effect = queryset.filter
            builder.build_modified_dietz(begin, end)
        return instance

    def assert_result(self, result, *, begin, end, flow, weighted, inflow, outflow):
        self.assertAlmostEqual(result.begin_nav, begin)
        self.assertAlmostEqual(result.end_nav, end)
        self.assertAlmostEqual(result.grand_nav, end)
        self.assertAlmostEqual(result.grand_cash_flow, flow)
        self.assertAlmostEqual(result.grand_cash_flow_weighted, weighted)
        self.assertAlmostEqual(result.grand_absolute_pl, end - begin - flow)
        self.assertAlmostEqual(result.grand_return, (end - begin - flow) / (begin + weighted))
        self.assertAlmostEqual(result.grand_cash_inflow, inflow)
        self.assertAlmostEqual(result.grand_cash_outflow, outflow)

    def test_inception_order_later_start_end_date_fx_and_execution_log(self):
        inflow = TransactionClass.CASH_INFLOW
        outflow = TransactionClass.CASH_OUTFLOW
        records = [
            self.record(1, self.first, 1, 100, inflow),
            self.record(2, self.first, 6, 20, inflow),
            self.record(3, self.first, 11, -10, outflow),
            self.record(4, self.second, 1, 200, inflow),
            self.record(5, self.second, 1, 50, inflow),
            self.record(6, self.second, 4, 40, inflow, self.eur),
            self.record(7, self.later, 4, 30, inflow),
            self.record(8, self.first, 12, 999, inflow),
            self.record(9, self.first, 3, 999, -1),
            self.record(10, self.later, 3, 999, inflow),
        ]
        results = []
        for registers in ([self.first, self.second, self.later], [self.second, self.first, self.later]):
            with self.subTest(order=[register.portfolio.user_code for register in registers]):
                result = self.build(registers, records)
                results.append(result)
                self.assert_result(result, begin=350, end=520, flow=120, weighted=99, inflow=480, outflow=-10)
                self.assertEqual(result.begin_date, self.start)
                items = {item["record"]: item for item in result.execution_log["items"]}
                self.assertEqual(set(items), {1, 2, 3, 4, 5, 6, 7})
                for record_id in (1, 4, 5):
                    self.assertEqual(items[record_id]["time_weight"], 0)
                self.assertEqual(items[6]["transaction_date"], "2024-01-04")
                self.assertEqual((items[6]["date_from_n"], items[6]["date_n"], items[6]["date_to_n"]), (1, 4, 11))
                self.assertAlmostEqual(items[6]["fx_rate"], 2)
                self.assertAlmostEqual(items[6]["record_cash_flow"], 80)
                self.assertAlmostEqual(items[7]["time_weight"], 0.8)
                self.assertAlmostEqual(items[3]["time_weight"], 0.1)
                self.assertAlmostEqual(items[7]["grand_cash_flow"], 120)
                self.assertAlmostEqual(items[7]["grand_cash_flow_weighted"], 99)
                self.assertAlmostEqual(items[7]["grand_cash_inflow"], 480)
                self.assertAlmostEqual(items[7]["grand_cash_outflow"], -10)
        self.assertAlmostEqual(results[0].grand_return, results[1].grand_return)
        second_open = {item["record"]: item for item in results[0].execution_log["items"]}[4]
        self.assertAlmostEqual(second_open["grand_cash_flow"], 10)
        self.assertAlmostEqual(second_open["grand_cash_flow_weighted"], 11)

    def test_single_portfolio_multiple_opening_records(self):
        records = [
            self.record(1, self.first, 1, 100, TransactionClass.CASH_INFLOW),
            self.record(2, self.first, 1, 50, TransactionClass.INJECTION),
            self.record(3, self.first, 6, -10, TransactionClass.DISTRIBUTION),
        ]
        result = self.build([self.first], records, nav={self.start: 0, self.end: 160})
        self.assert_result(result, begin=150, end=160, flow=-10, weighted=-6, inflow=150, outflow=-10)
        self.assertEqual([item["time_weight"] for item in result.execution_log["items"]], [0, 0, 0.6])

    def test_same_day_period_has_no_cash_flow_or_division_by_zero(self):
        day = datetime.date(2024, 1, 3)
        records = [self.record(1, self.first, 3, 50, TransactionClass.CASH_INFLOW)]
        result = self.build([self.first], records, begin=day, end=day, nav={day: 400})
        self.assert_result(result, begin=400, end=400, flow=0, weighted=0, inflow=0, outflow=0)
        self.assertEqual(result.begin_date, day)
        self.assertEqual(result.execution_log["items"], [])

    def test_period_start_after_inception_preserves_previous_register_flows(self):
        begin = datetime.date(2024, 1, 3)
        records = [
            self.record(1, self.first, 1, 100, TransactionClass.CASH_INFLOW),
            self.record(2, self.first, 3, 5, TransactionClass.CASH_INFLOW),
            self.record(3, self.first, 6, 20, TransactionClass.CASH_INFLOW),
            self.record(4, self.second, 3, 7, TransactionClass.CASH_INFLOW),
            self.record(5, self.second, 11, -10, TransactionClass.CASH_OUTFLOW),
        ]
        for registers in ([self.first, self.second], [self.second, self.first]):
            with self.subTest(order=[register.portfolio.user_code for register in registers]):
                result = self.build(registers, records, begin, {begin: 400, self.end: 450})
                self.assert_result(result, begin=400, end=450, flow=10, weighted=13.75, inflow=32, outflow=-10)
                self.assertEqual(result.begin_date, begin)
                items = {item["record"]: item for item in result.execution_log["items"]}
                self.assertEqual(set(items), {2, 3, 4, 5})
                self.assertEqual(items[2]["time_weight"], 0)
                self.assertEqual(items[4]["time_weight"], 0)
                if registers[0] is self.first:
                    self.assertAlmostEqual(items[4]["grand_cash_flow"], 20)
                    self.assertAlmostEqual(items[4]["grand_cash_flow_weighted"], 15)
