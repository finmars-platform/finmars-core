import datetime
import json
import logging
import math
import time
import traceback
from datetime import timedelta

from django.db.utils import DataError
from django.forms import model_to_dict

from poms.accounts.models import Account, AccountType
from poms.common.exceptions import FinmarsBaseException
from poms.common.models import ProxyRequest, ProxyUser
from poms.common.utils import (
    get_closest_bday_of_yesterday,
    get_last_business_day,
    get_last_business_day_in_month,
    get_last_business_day_in_previous_quarter,
    get_last_business_day_of_previous_month,
    get_last_business_day_of_previous_year,
    get_list_of_business_days_between_two_dates,
    is_business_day,
)
from poms.currencies.models import Currency, CurrencyHistory
from poms.instruments.models import Instrument, InstrumentType, PriceHistory
from poms.portfolios.models import Portfolio, PortfolioRegister, PortfolioRegisterRecord
from poms.reports.common import Report
from poms.reports.models import BalanceReportCustomField
from poms.reports.sql_builders.pure_balance import PureBalanceReportBuilderSql
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.transactions.models import Transaction, TransactionClass
from poms.users.models import EcosystemDefault

_l = logging.getLogger("poms.reports")


class PerformanceReportBuilder:
    def __init__(self, instance=None):
        _l.debug("PerformanceReportBuilder init")

        self.instance = instance

        self.ecosystem_defaults = EcosystemDefault.cache.get_cache(master_user_pk=self.instance.master_user.pk)

        _l.debug("self.instance master_user %s", self.instance.master_user)
        _l.debug("self.instance period_type %s", self.instance.period_type)
        _l.debug("self.instance begin_date %s", self.instance.begin_date)
        _l.debug("self.instance end_date %s", self.instance.end_date)

        proxy_user = ProxyUser(self.instance.member, self.instance.master_user)
        proxy_request = ProxyRequest(proxy_user)

        self.context = {
            "request": proxy_request,
            "master_user": self.instance.master_user,
            "member": self.instance.member,
        }

    def get_first_transaction(self):
        try:
            portfolio_registers = []

            if self.instance.bundle:
                # self.instance.bunch_portfolios = []
                # for item in self.instance.bundle.registers.all():
                #     if item.linked_instrument_id:
                #         self.instance.bunch_portfolios.append(item.linked_instrument_id)

                portfolio_registers = self.instance.bundle.registers.all()

            elif self.instance.registers:
                portfolio_registers = self.instance.registers
            # else:
            #     self.instance.bunch_portfolios = self.instance.registers  # instruments #debug szhitenev fund
            #
            # portfolio_registers = PortfolioRegister.objects.filter(master_user=self.instance.master_user,
            #                                                        linked_instrument__in=self.instance.bunch_portfolios) # noqa: E501

            portfolio_registers_map = {}

            portfolios = []

            if not len(portfolio_registers):
                raise FinmarsBaseException(
                    error_key="no_portfolio_registers_found",
                    message="No portfolios register found",
                )

            for portfolio_register in portfolio_registers:
                portfolios.append(portfolio_register.portfolio_id)
                portfolio_registers_map[portfolio_register.portfolio_id] = portfolio_register

            # _l.debug('get_first_transaction.portfolios %s ' % portfolios)

            transaction = (
                Transaction.objects.filter(
                    portfolio__in=portfolios,
                    transaction_class__in=[
                        TransactionClass.CASH_INFLOW,
                        TransactionClass.CASH_OUTFLOW,
                        TransactionClass.INJECTION,
                        TransactionClass.DISTRIBUTION,
                    ],
                )
                .order_by("transaction_date")
                .first()
            )

            return transaction.transaction_date

        except FinmarsBaseException as e:
            raise e
        except Exception as e:
            _l.error("Could not find first transaction date")
            raise FinmarsBaseException(error_key="no_first_transaction_date", message=str(e)) from e

    def build_report(self):  # noqa: PLR0912, PLR0915
        st = time.perf_counter()

        self.instance.first_transaction_date = self.get_first_transaction()

        if not self.instance.first_transaction_date:
            self.instance.execution_time = float(f"{time.perf_counter() - st:3.3f}")
            self.instance.items = []
            self.instance.error_message = "Could not find begin date. Please, check if portfolio has transactions"

            return self.instance

        self.instance.items = []

        self.end_date = self.instance.end_date

        _l.debug("typeof end_date %s", type(self.end_date))

        if not self.instance.end_date:
            self.end_date = get_closest_bday_of_yesterday()

        if not is_business_day(self.instance.end_date):
            self.instance.end_date = get_last_business_day(self.instance.end_date)

        begin_date = None

        if not self.instance.begin_date and self.instance.period_type:
            _l.debug("No begin date passed, calculating begin date based on period_type and end_date")
            _l.debug("self.instance.period_type %s", self.instance.period_type)

            if self.instance.period_type == "inception":
                begin_date = get_last_business_day(self.instance.first_transaction_date)

            elif self.instance.period_type == "ytd":
                begin_date = get_last_business_day_of_previous_year(self.instance.end_date)

            elif self.instance.period_type == "qtd":
                begin_date = get_last_business_day_in_previous_quarter(self.instance.end_date)

            elif self.instance.period_type == "mtd":
                begin_date = get_last_business_day_of_previous_month(self.instance.end_date)

            elif self.instance.period_type == "daily":
                begin_date = get_last_business_day(self.instance.end_date - timedelta(days=1))

        else:
            begin_date = self.instance.begin_date

        if not begin_date or begin_date <= self.instance.first_transaction_date:
            # szhitenev 2024-10-04
            # before here was  begin_date = get_last_business_day(self.instance.first_transaction_date)
            begin_date = self.instance.first_transaction_date

        self.instance.begin_date = begin_date

        _l.debug("typeof end_date %s", type(self.end_date))
        _l.debug("typeof begin_date %s", type(begin_date))

        self.end_date = max(self.end_date, begin_date)

        if self.instance.adjustment_type == "annualized":
            self.check_can_calculate_annualized_report()

        self.instance.periods = self.get_periods(begin_date, self.end_date, self.instance.segmentation_type)

        cumulative_return = 0

        if self.instance.calculation_type == "time_weighted":
            for period in self.instance.periods:
                table = self.build_time_weighted(period["date_from"], period["date_to"])

                for key, value in table.items():  # noqa: B007
                    period["items"].append(value)

                period = self.calculate_time_weighted_total_values(period)  # noqa: PLW2901

                period["cumulative_return"] = (cumulative_return + 1) * (period["total_return"] + 1) - 1

                cumulative_return = period["cumulative_return"]

            self.calculate_time_weighted_grand_total_values()

            for period in self.instance.periods:
                for item in period["items"]:
                    for key, value in item["portfolios"].items():  # noqa: B007
                        result_dicts = []

                        for record in item["portfolios"][key]["records"]:
                            record_json = model_to_dict(record)
                            result_dicts.append(record_json)

                        item["portfolios"][key]["records"] = result_dicts

            self.instance.items = []
            self.instance.raw_items = json.loads(
                json.dumps(self.instance.periods, indent=4, sort_keys=True, default=str)
            )

            for period in self.instance.periods:
                item = {
                    "date_from": period["date_from"],
                    "date_to": period["date_to"],
                    "begin_nav": period["begin_nav"],
                    "end_nav": period["end_nav"],
                    "cash_flow": period["total_cash_flow"],
                    "cash_inflow": period["total_cash_inflow"],
                    "cash_outflow": period["total_cash_outflow"],
                    "nav": period["total_nav"],
                    "instrument_return": period["total_return"],
                }
                if "cumulative_return" in period:
                    item["cumulative_return"] = period["cumulative_return"]

                self.instance.items.append(item)

        if self.instance.calculation_type == "modified_dietz":
            try:  # noqa: SIM105
                self.build_modified_dietz(begin_date, self.end_date)
            except DataError:
                pass

        if self.instance.adjustment_type == "annualized":
            self.calc_annualized_grand_total()

        # _l.debug('items total %s' % len(self.instance.items))

        _l.debug("build_st done: %s", f"{time.perf_counter() - st:3.3f}")

        self.instance.execution_time = float(f"{time.perf_counter() - st:3.3f}")

        relation_prefetch_st = time.perf_counter()

        # self.add_data_items()

        self.instance.relation_prefetch_time = float(f"{time.perf_counter() - relation_prefetch_st:3.3f}")

        return self.instance

    def calculate_time_weighted_grand_total_values(self):
        grand_return = 1

        grand_cash_flow = 0
        grand_cash_inflow = 0
        grand_cash_outflow = 0

        for period in self.instance.periods:
            grand_return = grand_return * (period["total_return"] + 1)
            grand_cash_flow = grand_cash_flow + period["total_cash_flow"]
            grand_cash_inflow = grand_cash_inflow + period["total_cash_inflow"]
            grand_cash_outflow = grand_cash_outflow + period["total_cash_outflow"]

        grand_return = grand_return - 1

        begin_nav = self.instance.periods[0]["total_nav"]
        grand_nav = self.instance.periods[-1]["total_nav"]
        end_nav = self.instance.periods[-1]["total_nav"]

        self.instance.grand_return = grand_return
        self.instance.grand_cash_flow = grand_cash_flow
        self.instance.grand_cash_inflow = grand_cash_inflow
        self.instance.grand_cash_outflow = grand_cash_outflow
        self.instance.grand_nav = grand_nav
        self.instance.begin_nav = begin_nav
        self.instance.end_nav = end_nav

    def calculate_modified_dietz_grand_total_values(self):
        grand_return = 1

        grand_cash_flow = 0
        grand_cash_inflow = 0
        grand_cash_outflow = 0

        # TODO for grand return we need to calculate separate perfomance ignoring months period
        # e.g. instead of 30days windows, we need full amount of days, e.g. 10 years = 3650 days
        # e.g. date_from = inception, date_to = date_to
        for period in self.instance.periods:
            grand_return = grand_return * (period["total_return"] + 1)
            grand_cash_flow = grand_cash_flow + period["total_cash_flow"]
            grand_cash_inflow = grand_cash_inflow + period["total_cash_inflow"]
            grand_cash_outflow = grand_cash_outflow + period["total_cash_outflow"]

        grand_return = grand_return - 1

        begin_nav = self.instance.periods[0]["total_nav"]
        grand_nav = self.instance.periods[-1]["total_nav"]
        end_nav = self.instance.periods[-1]["total_nav"]

        self.instance.grand_return = grand_return
        self.instance.grand_cash_flow = grand_cash_flow
        self.instance.grand_cash_inflow = grand_cash_inflow
        self.instance.grand_cash_outflow = grand_cash_outflow
        self.instance.grand_nav = grand_nav
        self.instance.begin_nav = begin_nav
        self.instance.end_nav = end_nav

    def calculate_time_weighted_total_values(self, period):
        total_nav = 0
        total_cash_flow = 0
        total_cash_inflow = 0
        total_cash_outflow = 0
        total_return = 1

        for item in period["items"]:
            total_nav = item["subtotal_nav"]
            total_cash_flow = total_cash_flow + item["subtotal_cash_flow"]
            total_cash_inflow = total_cash_inflow + item["subtotal_cash_inflow"]
            total_cash_outflow = total_cash_outflow + item["subtotal_cash_outflow"]

            total_return = total_return * (item["subtotal_return"] + 1)

        total_return = total_return - 1

        period["begin_nav"] = period["items"][0]["subtotal_nav"]
        period["end_nav"] = period["items"][-1]["subtotal_nav"]

        period["total_cash_flow"] = total_cash_flow
        period["total_cash_inflow"] = total_cash_inflow
        period["total_cash_outflow"] = total_cash_outflow
        period["total_nav"] = total_nav
        period["total_return"] = total_return

        return period

    def calculate_modified_dietz_total_values(self, period):
        total_nav = 0
        total_cash_flow = 0
        total_cash_inflow = 0
        total_cash_outflow = 0
        total_cash_flow_weighted = 0
        total_return = 1

        for item in period["items"]:
            total_nav = item["subtotal_nav"]
            total_cash_flow = total_cash_flow + item["subtotal_cash_flow"]
            total_cash_inflow = total_cash_inflow + item["subtotal_cash_inflow"]
            total_cash_outflow = total_cash_outflow + item["subtotal_cash_outflow"]
            total_cash_flow_weighted = total_cash_flow_weighted + item["subtotal_cash_flow_weighted"]

        period["begin_nav"] = period["items"][0]["subtotal_nav"]
        period["end_nav"] = period["items"][-1]["subtotal_nav"]

        try:
            total_return = (period["end_nav"] - period["begin_nav"] - total_cash_flow) / (
                period["begin_nav"] + total_cash_flow_weighted
            )
        except Exception:
            total_return = 0

        period["total_cash_flow"] = total_cash_flow
        period["total_cash_inflow"] = total_cash_inflow
        period["total_cash_outflow"] = total_cash_outflow
        period["total_cash_flow_weighted"] = total_cash_flow_weighted
        period["total_nav"] = total_nav
        period["total_return"] = total_return

        return period

    def get_dict_of_dates_between_two_dates_with_order(self, date_from, date_to):
        list_result = []
        result = {}

        diff = date_to - date_from

        for i in range(diff.days + 1):
            day = date_from + timedelta(days=i)
            list_result.append(day)

        index = 0
        for item in list_result:
            result[str(item)] = index + 1
            index = index + 1

        return result

    def get_periods(self, date_from, date_to, segmentation_type):
        # _l.debug("Getting periods %s from %s to %s" % (self.instance.segmentation_type, date_from, date_to))

        result = []

        dates = get_list_of_business_days_between_two_dates(date_from, date_to)

        # _l.debug('dates %s' % dates)

        if len(dates) == 0:
            return result

        if segmentation_type == "days":
            if date_from == date_to and is_business_day(date_from):
                result = self.format_to_days(dates)

            else:
                dates = [get_last_business_day(date_from)]

                result = self.format_to_days(dates)

        if segmentation_type == "months":
            result = self.format_to_months(dates)

        return result

    def format_to_months(self, dates):
        result = []

        result_obj = {}

        begin_date = dates[0]

        for date in dates:
            date_str = str(date)

            date_pieces = date_str.split("-")

            year = int(date_pieces[0])
            month = int(date_pieces[1])

            year_month = str(year) + "-" + str(month)

            month_end = get_last_business_day_in_month(year, month)

            if month_end >= self.end_date:
                month_end = self.end_date

                if not is_business_day(month_end):
                    month_end = get_last_business_day(month_end)

            month_start = get_last_business_day(
                datetime.date(year, month, 1) - timedelta(days=1)
            )  # 2022-10-01 - 2022-09-30

            month_start = max(month_start, begin_date)

            if year_month not in result_obj:
                result_obj[year_month] = {
                    "date_from": month_start,
                    "date_to": month_end,
                    "items": [],
                    "total_nav": 0,
                    "total_return": 0,
                }

        for key, value in result_obj.items():  # noqa: B007
            result.append(value)

        # _l.debug("result %s" % result)

        return result

    def format_to_weeks(self, table):
        result = []

        return result

    def format_to_days(self, dates):
        result = []

        for date in dates:
            result_item = {}

            result_item["date_from"] = date - timedelta(days=1)
            result_item["date_to"] = date
            result_item["items"] = []
            result_item["total_nav"] = 0
            result_item["total_return"] = 0

            result.append(result_item)

        return result

    def build_time_weighted(self, date_from, date_to):  # noqa: PLR0912, PLR0915
        # _l.debug("build portfolio records")

        date_from_str = str(date_from)
        date_to_str = str(date_to)

        if self.instance.bundle:
            self.instance.bunch_portfolios = []
            for item in self.instance.bundle.registers.all():
                if item.linked_instrument_id:
                    self.instance.bunch_portfolios.append(item.linked_instrument_id)
        else:
            self.instance.bunch_portfolios = self.instance.registers  # instruments #debug szhitenev fund

        portfolio_registers = PortfolioRegister.objects.filter(
            master_user=self.instance.master_user,
            linked_instrument__in=self.instance.bunch_portfolios,
        )

        portfolio_registers_map = {}

        portfolios = []

        for portfolio_register in portfolio_registers:
            portfolios.append(portfolio_register.portfolio_id)
            portfolio_registers_map[portfolio_register.portfolio_id] = portfolio_register

        records = PortfolioRegisterRecord.objects.filter(
            portfolio_register__in=portfolio_registers,
            transaction_date__gte=date_from,
            transaction_date__lte=date_to,
            transaction_class__in=[
                TransactionClass.CASH_INFLOW,
                TransactionClass.CASH_OUTFLOW,
                TransactionClass.INJECTION,
                TransactionClass.DISTRIBUTION,
            ],
        ).order_by("transaction_date")

        # create empty structure start

        table = {}

        if date_from_str not in table:
            table[date_from_str] = {}
            table[date_from_str]["date"] = date_from_str
            table[date_from_str]["portfolios"] = {}
            table[date_from_str]["subtotal_cash_flow"] = 0
            table[date_from_str]["subtotal_cash_inflow"] = 0
            table[date_from_str]["subtotal_cash_outflow"] = 0
            table[date_from_str]["subtotal_nav"] = 0
            table[date_from_str]["subtotal_return"] = 0

            for portfolio_id in portfolios:
                table[date_from_str]["portfolios"][portfolio_id] = {
                    "portfolio_register": portfolio_registers_map[portfolio_id],
                    "portfolio_id": portfolio_id,
                    "transaction_date_str": date_from_str,
                    "transaction_date": date_from,
                    "cash_flow": 0,
                    "cash_inflow": 0,
                    "cash_outflow": 0,
                    "previous_nav": 0,
                    "nav": 0,
                    "instrument_return": 0,
                    "records": [],
                }

        for record in records:
            transaction_date_str = str(record.transaction_date)

            if transaction_date_str not in table:
                table[transaction_date_str] = {}
                table[transaction_date_str]["date"] = transaction_date_str
                table[transaction_date_str]["portfolios"] = {}
                table[transaction_date_str]["subtotal_cash_flow"] = 0
                table[transaction_date_str]["subtotal_cash_inflow"] = 0
                table[transaction_date_str]["subtotal_cash_outflow"] = 0
                table[transaction_date_str]["subtotal_nav"] = 0
                table[transaction_date_str]["subtotal_return"] = 0

            if record.portfolio_id not in table[transaction_date_str]["portfolios"]:
                table[transaction_date_str]["portfolios"][record.portfolio_id] = {
                    "portfolio_register": record.portfolio_register,
                    "portfolio_id": record.portfolio_id,
                    "transaction_date_str": transaction_date_str,
                    "transaction_date": record.transaction_date,
                    "cash_flow": 0,
                    "cash_inflow": 0,
                    "cash_outflow": 0,
                    "previous_nav": 0,
                    "nav": 0,
                    "instrument_return": 0,
                    "records": [],
                }

            if transaction_date_str != date_from_str:  # Always empty records for date_from
                table[transaction_date_str]["portfolios"][record.portfolio_id]["records"].append(record)

        if date_to_str not in table:
            table[date_to_str] = {}
            table[date_to_str]["date"] = date_to_str
            table[date_to_str]["portfolios"] = {}
            table[date_to_str]["subtotal_cash_flow"] = 0
            table[date_to_str]["subtotal_cash_inflow"] = 0
            table[date_to_str]["subtotal_cash_outflow"] = 0
            table[date_to_str]["subtotal_nav"] = 0
            table[date_to_str]["subtotal_return"] = 0

            for portfolio_id in portfolios:
                table[date_to_str]["portfolios"][portfolio_id] = {
                    "portfolio_register": portfolio_registers_map[portfolio_id],
                    "portfolio_id": portfolio_id,
                    "transaction_date_str": date_to_str,
                    "transaction_date": date_to,
                    "cash_flow": 0,
                    "cash_inflow": 0,
                    "cash_outflow": 0,
                    "previous_nav": 0,
                    "nav": 0,
                    "instrument_return": 0,
                    "records": [],
                }

        # create empty structure end Fill with Data

        previous_date = None

        for key, value in table.items():  # noqa: B007
            item_date = value

            _l.debug("performance.table.key %s", key)
            _l.debug("performance.table.previous_date %s", previous_date)

            for _key, _value in item_date["portfolios"].items():
                item = item_date["portfolios"][_key]

                try:
                    price_history = PriceHistory.objects.get(
                        date=item["transaction_date"],
                        instrument=item["portfolio_register"].linked_instrument,
                        pricing_policy=item["portfolio_register"].valuation_pricing_policy,
                    )

                    if (
                        self.instance.report_currency.id
                        == item["portfolio_register"].linked_instrument.pricing_currency.id
                    ):
                        fx_rate = 1
                    else:
                        if self.instance.report_currency.id == self.ecosystem_defaults.currency.id:
                            report_currency_fx_rate = 1
                        else:
                            report_currency_fx_rate = CurrencyHistory.objects.get(
                                date=item["transaction_date"],
                                currency=self.instance.report_currency,
                                pricing_policy=item["portfolio_register"].valuation_pricing_policy,
                            ).fx_rate

                        if (
                            item["portfolio_register"].linked_instrument.pricing_currency.id
                            == self.ecosystem_defaults.currency.id
                        ):
                            instrument_pricing_currency_fx_rate = 1
                        else:
                            instrument_pricing_currency_fx_rate = CurrencyHistory.objects.get(
                                date=item["transaction_date"],
                                currency=item["portfolio_register"].linked_instrument.pricing_currency,
                                pricing_policy=item["portfolio_register"].valuation_pricing_policy,
                            ).fx_rate

                        fx_rate = instrument_pricing_currency_fx_rate / report_currency_fx_rate

                    nav = price_history.nav * fx_rate

                    # report currency / linked_instrument.pricing currency

                except Exception as e:
                    _l.error("Could not calculate nav %s ", e)
                    nav = 0

                previous_nav = 0

                try:
                    if previous_date:
                        previous_nav = previous_date["portfolios"][_key]["nav"]
                except Exception:
                    previous_nav = 0

                cash_flow = 0
                cash_inflow = 0
                cash_outflow = 0

                for record in item["records"]:
                    try:
                        if self.instance.report_currency.id == record.valuation_currency.id:
                            fx_rate = 1
                        else:
                            if self.instance.report_currency.id == self.ecosystem_defaults.currency.id:
                                report_currency_fx_rate = 1
                            else:
                                report_currency_fx_rate = CurrencyHistory.objects.get(
                                    date=record.transaction_date,
                                    pricing_policy=record.portfolio_register.valuation_pricing_policy,
                                    currency=self.instance.report_currency,
                                ).fx_rate

                            if record.valuation_currency.id == self.ecosystem_defaults.currency.id:
                                record_valuation_currency_fx_rate = 1
                            else:
                                record_valuation_currency_fx_rate = CurrencyHistory.objects.get(
                                    date=record.transaction_date,
                                    pricing_policy=record.portfolio_register.valuation_pricing_policy,
                                    currency=record.valuation_currency,
                                ).fx_rate

                            fx_rate = record_valuation_currency_fx_rate / report_currency_fx_rate

                    except Exception as e:
                        _l.error("Could not calculate fx_rate e %s", e)
                        _l.error("Could not calculate fx_rate traceback %s", traceback.format_exc())
                        fx_rate = 1

                    # report / valuation

                    cash_flow = cash_flow + record.cash_amount_valuation_currency * fx_rate

                    if record.transaction_class_id in [
                        TransactionClass.CASH_INFLOW,
                        TransactionClass.INJECTION,
                    ]:
                        cash_inflow = cash_inflow + record.cash_amount_valuation_currency * fx_rate

                    if record.transaction_class_id in [
                        TransactionClass.CASH_OUTFLOW,
                        TransactionClass.DISTRIBUTION,
                    ]:
                        cash_outflow = cash_outflow + record.cash_amount_valuation_currency * fx_rate

                if previous_nav:
                    instrument_return = (nav - cash_flow - previous_nav) / previous_nav
                elif nav:
                    instrument_return = (nav - cash_flow) / nav
                    # instrument_return = (nav - cash_flow) / cash_flow # 2023-11-08, performance fix
                else:
                    instrument_return = 0

                item["nav"] = nav

                if item["transaction_date_str"] == date_from_str:
                    item["cash_flow"] = 0
                else:
                    item["cash_flow"] = cash_flow

                if item["transaction_date_str"] == date_from_str:
                    item["cash_inflow"] = 0
                else:
                    item["cash_inflow"] = cash_inflow

                if item["transaction_date_str"] == date_from_str:
                    item["cash_outflow"] = 0
                else:
                    item["cash_outflow"] = cash_outflow

                item["previous_nav"] = previous_nav

                item["instrument_return"] = instrument_return

                if previous_date:
                    item["previous_date"] = json.loads(json.dumps(previous_date, default=str))
                else:
                    item["previous_date"] = None

                previous_date = item_date

        # Calculate nav

        previous_date = None

        for key, value in table.items():  # noqa: B007
            item_date = value

            for _key, _value in item_date["portfolios"].items():
                item = item_date["portfolios"][_key]

                item_date["subtotal_nav"] = item_date["subtotal_nav"] + item["nav"]
                item_date["subtotal_cash_flow"] = item_date["subtotal_cash_flow"] + item["cash_flow"]
                item_date["subtotal_cash_inflow"] = item_date["subtotal_cash_inflow"] + item["cash_inflow"]
                item_date["subtotal_cash_outflow"] = item_date["subtotal_cash_outflow"] + item["cash_outflow"]

                if previous_date and previous_date["subtotal_nav"]:
                    item_date["subtotal_return"] = item_date["subtotal_return"] + (
                        item["instrument_return"] * item["previous_nav"] / previous_date["subtotal_nav"]
                    )

                previous_date = item_date

        # print('table %s' % table)

        return table

    def get_portfolio_registers(self):
        try:
            # if self.instance.bundle:
            #     self.instance.bunch_portfolios = []
            #     for item in self.instance.bundle.registers.all():
            #         if item.linked_instrument_id:
            #             self.instance.bunch_portfolios.append(item.linked_instrument_id)
            # else:
            #     self.instance.bunch_portfolios = self.instance.registers  # instruments #debug szhitenev fund

            if self.instance.bundle:
                # self.instance.bunch_portfolios = []
                # for item in self.instance.bundle.registers.all():
                #     if item.linked_instrument_id:
                #         self.instance.bunch_portfolios.append(item.linked_instrument_id)

                portfolio_registers = self.instance.bundle.registers.all()

            elif self.instance.registers:
                portfolio_registers = self.instance.registers

            else:
                raise RuntimeError("no portfolio_registers found")

            # portfolio_registers = PortfolioRegister.objects.filter(master_user=self.instance.master_user,
            #                                                        linked_instrument__in=self.instance.bunch_portfolios) # noqa: E501

            portfolio_registers_map = {}

            portfolios = []

            for portfolio_register in portfolio_registers:
                portfolios.append(portfolio_register.portfolio_id)
                portfolio_registers_map[portfolio_register.portfolio_id] = portfolio_register

            return portfolio_registers

        except Exception as e:
            raise FinmarsBaseException(error_key="cannot_get_portfolio_registers", message=str(e)) from e

    def get_portfolios(self, portfolio_registers):
        try:
            portfolios = []

            for portfolio_register in portfolio_registers:
                portfolios.append(portfolio_register.portfolio)

            return portfolios

        except Exception as e:
            raise FinmarsBaseException(error_key="cannot_get_portfolios", message=str(e)) from e

    def get_modified_dietz_nav_for_record(self, register_record):
        try:
            price_history = PriceHistory.objects.get(
                date=register_record.transaction_date,
                instrument=register_record.portfolio_register.linked_instrument,
                pricing_policy=register_record.portfolio_register.valuation_pricing_policy,
            )

            try:
                if (
                    self.instance.report_currency.id
                    == register_record.portfolio_register.linked_instrument.pricing_currency.id
                ):
                    fx_rate = 1
                else:
                    if self.instance.report_currency.id == self.ecosystem_defaults.currency.id:
                        report_currency_fx_rate = 1
                    else:
                        report_currency_fx_rate = CurrencyHistory.objects.get(
                            date=register_record,
                            currency=self.instance.report_currency,
                            pricing_policy=register_record.portfolio_register.valuation_pricing_policy,
                        ).fx_rate

                    if (
                        register_record.portfolio_register.linked_instrument.pricing_currency.id
                        == self.ecosystem_defaults.currency.id
                    ):
                        instrument_pricing_currency_fx_rate = 1
                    else:
                        instrument_pricing_currency_fx_rate = CurrencyHistory.objects.get(
                            date=register_record.transaction_date,
                            currency=register_record.portfolio_register.linked_instrument.pricing_currency,
                            pricing_policy=register_record.portfolio_register.valuation_pricing_policy,
                        ).fx_rate

                    fx_rate = instrument_pricing_currency_fx_rate / report_currency_fx_rate

            except Exception as e:
                _l.error("fx_rate e %s", e)
                fx_rate = 1

            nav = price_history.nav * fx_rate

        except Exception:
            nav = 0

        return nav

    def get_inception_date_cash_flow(self, portfolios, date, pricing_policy):
        portfolio_registers = self.get_portfolio_registers()

        portfolio_records = PortfolioRegisterRecord.objects.filter(
            portfolio_register__in=portfolio_registers,
            transaction_date__lte=date,  # 2023-12-29
            transaction_class__in=[
                TransactionClass.CASH_INFLOW,
                TransactionClass.CASH_OUTFLOW,
                TransactionClass.INJECTION,
                TransactionClass.DISTRIBUTION,
            ],
        ).order_by("transaction_date")

        cash_flow = 0

        for record in portfolio_records:
            fx_rate = self.get_record_fx_rate(record)

            cash_flow = cash_flow + record.cash_amount_valuation_currency * fx_rate

        return cash_flow

    def get_nav_by_date(self, portfolios, date, pricing_policy):
        balance_report = Report(master_user=self.instance.master_user)
        balance_report.master_user = self.instance.master_user
        balance_report.member = self.instance.member
        balance_report.report_date = date
        balance_report.pricing_policy = pricing_policy
        balance_report.portfolios = portfolios
        balance_report.report_currency = self.instance.report_currency

        # builder = BalanceReportBuilderSql(instance=balance_report)
        builder = PureBalanceReportBuilderSql(instance=balance_report)
        balance_report = builder.build_balance_sync()

        nav = 0

        _l.debug(f"get_nav_by_date.balance_report. date: {date}, len:{len(balance_report.items)}")

        for it in balance_report.items:
            if it["market_value"]:
                nav = nav + it["market_value"]

        return nav

    def get_record_fx_rate(self, record):
        fx_rate = 1

        try:
            if self.instance.report_currency.id == record.valuation_currency.id:
                fx_rate = 1
            else:
                if self.instance.report_currency.id == self.ecosystem_defaults.currency.id:
                    report_currency_fx_rate = 1
                else:
                    report_currency_fx_rate = CurrencyHistory.objects.get(
                        date=record.transaction_date,
                        pricing_policy=record.portfolio_register.valuation_pricing_policy,
                        currency=self.instance.report_currency,
                    ).fx_rate

                if record.valuation_currency.id == self.ecosystem_defaults.currency.id:
                    record_valuation_currency_fx_rate = 1
                else:
                    record_valuation_currency_fx_rate = CurrencyHistory.objects.get(
                        pricing_policy=record.portfolio_register.valuation_pricing_policy,
                        date=record.transaction_date,
                        currency=record.valuation_currency,
                    ).fx_rate

                fx_rate = record_valuation_currency_fx_rate / report_currency_fx_rate

        except Exception as e:
            _l.error("fx_rate e %s", e)
            fx_rate = 1  # TODO check if this is correct

        return fx_rate

    def build_modified_dietz(self, date_from, date_to):  # noqa: PLR0915
        start_time = time.perf_counter()
        _l.debug("performance_report.build_modified_dietz")

        portfolio_registers = self.get_portfolio_registers()
        portfolios = self.get_portfolios(portfolio_registers)

        # TODO may cause errors if portfolios has different pricing policies
        # Consider to discuss with ogreshnev what to do
        # 2023-11-14 szhitenev
        pricing_policy = portfolio_registers[0].valuation_pricing_policy

        begin_nav_start = time.perf_counter()
        begin_nav = self.get_nav_by_date(portfolios, date_from, pricing_policy)
        _l.debug(
            "Begin NAV calculated in: %s seconds",
            f"{time.perf_counter() - begin_nav_start:3.3f}",
        )

        end_nav_start = time.perf_counter()
        end_nav = self.get_nav_by_date(portfolios, date_to, pricing_policy)
        _l.debug(
            "End NAV calculated in: %s seconds",
            f"{time.perf_counter() - end_nav_start:3.3f}",
        )

        inception_cash_flow = 0
        if date_from <= self.instance.first_transaction_date:
            inception_cash_flow = self.get_inception_date_cash_flow(portfolios, date_from, pricing_policy)
            date_from = self.instance.first_transaction_date - timedelta(days=1)
            begin_nav = inception_cash_flow

        self.instance.execution_log = {"items": []}

        total_nav = begin_nav
        grand_cash_flow = 0
        grand_cash_inflow = 0
        grand_cash_outflow = 0
        grand_cash_flow_weighted = 0
        grand_return = 0

        date_from = max(date_from, self.instance.first_transaction_date)
        dates_map = self.get_dict_of_dates_between_two_dates_with_order(date_from, date_to)

        if date_to > date_from:
            no_first_date = []
            no_register_records = []
            for register in portfolio_registers:
                portfolio = register.portfolio
                first_transaction_date = portfolio.first_transaction_date
                if not first_transaction_date:
                    no_first_date.append(portfolio.user_code)
                    continue

                portfolio_records = PortfolioRegisterRecord.objects.filter(
                    portfolio_register=register,
                    transaction_date__lte=date_to,  # 2023-12-29
                    transaction_class__in=[
                        TransactionClass.CASH_INFLOW,
                        TransactionClass.CASH_OUTFLOW,
                        TransactionClass.INJECTION,
                        TransactionClass.DISTRIBUTION,
                    ],
                ).order_by("transaction_date")

                if not portfolio_records:
                    no_register_records.append(portfolio.user_code)
                    continue

                portfolio_records = portfolio_records.filter(
                    transaction_date__gte=max(
                        date_from, first_transaction_date
                    ),  # 2023-10-30, 2023-09-29, # 2023-09-20
                )

                _l.debug("portfolio_records count %s ", len(portfolio_records))

                for record in portfolio_records:
                    fx_rate = self.get_record_fx_rate(record)
                    record_cash_flow = record.cash_amount_valuation_currency * fx_rate

                    if record.transaction_class_id in [
                        TransactionClass.CASH_INFLOW,
                        TransactionClass.INJECTION,
                    ]:
                        grand_cash_inflow = grand_cash_inflow + record_cash_flow
                    else:
                        grand_cash_outflow = grand_cash_outflow + record_cash_flow

                    date_n = dates_map[str(record.transaction_date)]
                    date_to_n = dates_map[str(date_to)]
                    date_from_n = dates_map[str(date_from)]
                    # 2022-03-31
                    # 2022-04-01

                    # date_n = 2022-04-02
                    # date_to_n = 2022-04-29
                    # date_from_n = 2022-03-31

                    #   (30 - (3-1)) / (30 - 1) = 28 / 29 = 0

                    # 319 - 13 / 319 - 1

                    # szhitenev
                    # 2024-05-27
                    # we never count initial cash flow to total cashflow
                    # initial cash cash is baseline that we calculate performance based on
                    if record.transaction_date == date_from:
                        # transaction at the start of period is not weighed
                        time_weight = 0
                        grand_cash_flow = 0
                        grand_cash_flow_weighted = 0
                        # total_nav += record_cash_flow
                    elif record.transaction_date == self.instance.first_transaction_date:
                        time_weight = 0
                        grand_cash_flow = 0
                        grand_cash_flow_weighted = 0
                    else:
                        time_weight = (date_to_n - (date_n - 1)) / (date_to_n - date_from_n)
                        grand_cash_flow += record_cash_flow
                        grand_cash_flow_weighted += record_cash_flow * time_weight

                    self.instance.execution_log["items"].append(
                        {
                            "record": record.id,
                            "date_n": date_n,
                            "transaction_date": str(record.transaction_date),
                            "date_from_n": date_from_n,
                            "date_to_n": date_to_n,
                            "time_weight": time_weight,
                            "fx_rate": fx_rate,
                            "record_cash_flow": record_cash_flow,
                            "grand_cash_inflow": grand_cash_inflow,
                            "grand_cash_outflow": grand_cash_outflow,
                            "grand_cash_flow": grand_cash_flow,
                            "grand_cash_flow_weighted": grand_cash_flow_weighted,
                        }
                    )

            if no_first_date:
                raise FinmarsBaseException(
                    error_key="no_first_transaction_date",
                    message=(
                        f"The following portfolios have empty first_transaction"
                        f"_date field, check if they have transactions: "
                        f"{', '.join(no_first_date)}"
                    ),
                )

            # 2024-05-27
            # szhitenev
            # TODO come back in 1.7.0 asignee = aalekseev
            # if begin_nav == 0 and grand_cash_flow == 0:
            #     raise FinmarsBaseException(
            #         error_key="no_begin_nav",
            #         message=(
            #             f"No begin NAV found for the following portfolios "
            #             f"for the specified period: {', '.join(no_register_records)}"
            #         ),
            #     )

            if no_register_records:
                raise FinmarsBaseException(
                    error_key="no_portfolio_register_records",
                    message=(
                        f"No portfolio register records found for the following portfolios "
                        f"for the specified period: {', '.join(no_register_records)}"
                    ),
                )

            try:
                cf_adjusted_total_nav = total_nav + grand_cash_flow
                wcf_adjusted_total_nav = total_nav + grand_cash_flow_weighted
                grand_return = (end_nav - cf_adjusted_total_nav) / wcf_adjusted_total_nav
            except Exception as e:
                _l.error("Could not calculate modified dietz return error %s", e)
                _l.error("Could not calculate modified dietz return traceback %s", traceback.format_exc())
                grand_return = 0

        earliest_transaction_date = min(portfolio.first_transaction_date for portfolio in portfolios)
        self.instance.begin_date = min(date_to, max(date_from, earliest_transaction_date))
        self.instance.grand_return = grand_return
        self.instance.grand_cash_flow = grand_cash_flow
        self.instance.grand_cash_flow_weighted = grand_cash_flow_weighted
        self.instance.grand_cash_inflow = grand_cash_inflow
        self.instance.grand_cash_outflow = grand_cash_outflow
        self.instance.grand_nav = end_nav
        self.instance.begin_nav = begin_nav
        self.instance.end_nav = end_nav

        self.instance.grand_absolute_pl = end_nav - begin_nav - grand_cash_flow

        _l.debug(
            "performance_report.build_modified_dietz completed in: %s seconds",
            f"{time.perf_counter() - start_time:3.3f}",
        )

    def check_can_calculate_annualized_report(self):
        if self.instance.bundle:
            portfolio_registers = self.instance.bundle.registers.all()
        else:
            portfolio_registers = self.instance.registers
        short_portfolios = []
        for portfolio_register in portfolio_registers:
            transaction_date = portfolio_register.portfolio.first_cash_flow_date
            if not transaction_date or (self.end_date - transaction_date).days < 365:
                short_portfolios.append(portfolio_register.portfolio.user_code)
        if short_portfolios:
            raise FinmarsBaseException(
                error_key="less_than_year",
                message=(
                    f"Return period of the following portfolio registers is "
                    f"less than a year (<365 days) (must not be annualized): "
                    f"{', '.join(short_portfolios[:10])}"
                ),
            )

    def calc_annualized_grand_total(self):
        value = None
        try:
            diff_in_years = (self.end_date - self.instance.begin_date).days / 365
            if diff_in_years < 1:
                raise Exception("Return period is less than a year (<365 days) (must not be annualized)")
            if self.instance.calculation_type == "time_weighted":
                if self.instance.grand_return < -1:
                    raise FinmarsBaseException(
                        error_key="less_than_100_pct",
                        message="Return since inception is less than -100% (can’t calculate the geometric mean)",
                    )
                # formula to calculate annualized return
                # (return_since_inception+1)^(1/number_of_years_since_inception) - 1`
                value = math.pow(self.instance.grand_return + 1, 1 / diff_in_years) - 1
            elif self.instance.calculation_type == "modified_dietz":
                value = self.instance.grand_return / diff_in_years
        except Exception as ex:
            _l.error(str(ex))
        self.instance.grand_return = value


def add_data_items_instruments(self, ids):
    self.instance.item_instruments = (
        Instrument.objects.prefetch_related(
            "attributes",
            "attributes__attribute_type",
            "attributes__classifier",
        )
        .filter(master_user=self.instance.master_user)
        .filter(id__in=ids)
    )


def add_data_items_instrument_types(self, instruments):
    ids = []

    for instrument in instruments:
        ids.append(instrument.instrument_type_id)

    self.instance.item_instrument_types = (
        InstrumentType.objects.prefetch_related(
            "attributes",
            "attributes__attribute_type",
            "attributes__classifier",
        )
        .filter(master_user=self.instance.master_user)
        .filter(id__in=ids)
    )


def add_data_items_portfolios(self, ids):
    self.instance.item_portfolios = (
        Portfolio.objects.prefetch_related("attributes")
        .defer("responsibles", "counterparties", "transaction_types", "accounts")
        .filter(master_user=self.instance.master_user)
        .filter(id__in=ids)
    )


def add_data_items_accounts(self, ids):
    self.instance.item_accounts = (
        Account.objects.prefetch_related(
            "attributes",
            "attributes__attribute_type",
            "attributes__classifier",
        )
        .filter(master_user=self.instance.master_user)
        .filter(id__in=ids)
    )


def add_data_items_account_types(self, accounts):
    ids = []

    for account in accounts:
        ids.append(account.type_id)

    self.instance.item_account_types = (
        AccountType.objects.prefetch_related(
            "attributes",
            "attributes__attribute_type",
            "attributes__classifier",
        )
        .filter(master_user=self.instance.master_user)
        .filter(id__in=ids)
    )


def add_data_items_currencies(self, ids):
    self.instance.item_currencies = (
        Currency.objects.prefetch_related(
            "attributes",
            "attributes__attribute_type",
            "attributes__classifier",
        )
        .filter(master_user=self.instance.master_user)
        .filter(id__in=ids)
    )


def add_data_items_strategies1(self, ids):
    self.instance.item_strategies1 = (
        Strategy1.objects.prefetch_related(
            "attributes",
            "attributes__attribute_type",
            "attributes__classifier",
        )
        .filter(master_user=self.instance.master_user)
        .filter(id__in=ids)
    )


def add_data_items_strategies2(self, ids):
    self.instance.item_strategies2 = (
        Strategy2.objects.prefetch_related(
            "attributes",
            "attributes__attribute_type",
            "attributes__classifier",
        )
        .filter(master_user=self.instance.master_user)
        .filter(id__in=ids)
    )


def add_data_items_strategies3(self, ids):
    self.instance.item_strategies3 = (
        Strategy3.objects.prefetch_related(
            "attributes",
            "attributes__attribute_type",
            "attributes__classifier",
        )
        .filter(master_user=self.instance.master_user)
        .filter(id__in=ids)
    )


def add_data_items(self):  # noqa: PLR0915
    instance_relations_st = time.perf_counter()

    _l.debug(
        "_refresh_with_perms_optimized instance relations done: %s",
        f"{time.perf_counter() - instance_relations_st:3.3f}",
    )

    permissions_st = time.perf_counter()

    _l.debug(
        "_refresh_with_perms_optimized permissions done: %s",
        f"{time.perf_counter() - permissions_st:3.3f}",
    )

    item_relations_st = time.perf_counter()

    instrument_ids = []
    portfolio_ids = []
    account_ids = []
    currencies_ids = []
    strategies1_ids = []
    strategies2_ids = []
    strategies3_ids = []

    for item in self.instance.items:
        if "portfolio_id" in item and item["portfolio_id"] != "-":
            portfolio_ids.append(item["portfolio_id"])

        if "instrument_id" in item:
            instrument_ids.append(item["instrument_id"])

        if "account_position_id" in item and item["account_position_id"] != "-":
            account_ids.append(item["account_position_id"])
        if "account_cash_id" in item and item["account_cash_id"] != "-":
            account_ids.append(item["account_cash_id"])

        if "currency_id" in item:
            currencies_ids.append(item["currency_id"])
        if "pricing_currency_id" in item:
            currencies_ids.append(item["pricing_currency_id"])
        if "exposure_currency_id" in item:
            currencies_ids.append(item["exposure_currency_id"])

        if "strategy1_position_id" in item:
            strategies1_ids.append(item["strategy1_position_id"])

        if "strategy2_position_id" in item:
            strategies2_ids.append(item["strategy2_position_id"])

        if "strategy3_position_id" in item:
            strategies3_ids.append(item["strategy3_position_id"])

        if "strategy1_cash_id" in item:
            strategies1_ids.append(item["strategy1_cash_id"])

        if "strategy2_cash_id" in item:
            strategies2_ids.append(item["strategy2_cash_id"])

        if "strategy3_cash_id" in item:
            strategies3_ids.append(item["strategy3_cash_id"])

    instrument_ids = list(set(instrument_ids))
    portfolio_ids = list(set(portfolio_ids))
    account_ids = list(set(account_ids))
    currencies_ids = list(set(currencies_ids))
    strategies1_ids = list(set(strategies1_ids))
    strategies2_ids = list(set(strategies2_ids))
    strategies3_ids = list(set(strategies3_ids))

    self.add_data_items_instruments(instrument_ids)
    self.add_data_items_portfolios(portfolio_ids)
    self.add_data_items_accounts(account_ids)
    self.add_data_items_currencies(currencies_ids)
    self.add_data_items_strategies1(strategies1_ids)
    self.add_data_items_strategies2(strategies2_ids)
    self.add_data_items_strategies3(strategies3_ids)

    self.add_data_items_instrument_types(self.instance.item_instruments)
    self.add_data_items_account_types(self.instance.item_accounts)

    self.instance.custom_fields = BalanceReportCustomField.objects.filter(master_user=self.instance.master_user)

    _l.debug(
        "_refresh_with_perms_optimized item relations done: %s",
        f"{time.perf_counter() - item_relations_st:3.3f}",
    )
