import logging
import traceback
from datetime import timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from dateutil import parser
from django.views.generic.dates import timezone_today

from poms.celery_tasks.models import CeleryTask
from poms.common.utils import get_list_of_dates_between_two_dates
from poms.currencies.models import CurrencyHistory
from poms.instruments.models import PricingPolicy
from poms.portfolios.models import (
    PortfolioRegister,
    PortfolioRegisterRecord,
)
from poms.portfolios.utils import get_price_calculation_type
from poms.reports.common import Report
from poms.reports.sql_builders.balance import BalanceReportBuilderSql
from poms.system_messages.handlers import send_system_message
from poms.transactions.models import Transaction, TransactionClass
from poms.users.models import EcosystemDefault, MasterUser

_l = logging.getLogger("poms.portfolios")
celery_logger = get_task_logger(__name__)


def calculate_simple_balance_report(report_date, portfolio_register, pricing_policy, member):
    """
    Probably is duplicated method. Here we just getting Balance Report instance
    on specific date, portfolio and pricing policy

    :param report_date:
    :param portfolio_register:
    :param pricing_policy:
    :return:
    """
    instance = Report(master_user=portfolio_register.master_user)

    _l.info(f"calculate_simple_balance_report.report_date {report_date}")

    instance.master_user = portfolio_register.master_user
    instance.member = member
    instance.report_date = report_date
    instance.pricing_policy = pricing_policy
    # instance.report_currency = portfolio_register.valuation_currency
    instance.report_currency = portfolio_register.linked_instrument.pricing_currency
    instance.portfolios = [portfolio_register.portfolio]

    builder = BalanceReportBuilderSql(instance=instance)
    instance = builder.build_balance_sync()

    return instance


def calculate_cash_flow(master_user, date, pricing_policy, portfolio_register):
    _l.info(f"calculate_cash_flow.date {date} pricing_policy {pricing_policy}")

    cash_flow = 0

    transactions = Transaction.objects.filter(
        master_user=master_user,
        portfolio_id=portfolio_register.portfolio,
        accounting_date=date,
        transaction_class_id__in=[
            TransactionClass.CASH_INFLOW,
            TransactionClass.DISTRIBUTION,
            TransactionClass.INJECTION,
            TransactionClass.CASH_OUTFLOW,
        ],
    ).order_by("accounting_date")

    error = False

    for transaction in transactions:
        if (
                transaction.transaction_currency
                == portfolio_register.linked_instrument.pricing_currency
        ):
            fx_rate = 1
        else:
            try:
                trn_currency_fx_rate = CurrencyHistory.objects.get(
                    currency_id=transaction.transaction_currency,
                    pricing_policy=pricing_policy,
                    date=date,
                ).fx_rate

                instr_pricing_currency_fx_rate = CurrencyHistory.objects.get(
                    currency_id=portfolio_register.linked_instrument.pricing_currency,
                    pricing_policy=pricing_policy,
                    date=date,
                ).fx_rate

                fx_rate = trn_currency_fx_rate / instr_pricing_currency_fx_rate

            except Exception:
                error = True
                fx_rate = 0

        cash_flow = cash_flow + (
                transaction.cash_consideration * transaction.reference_fx_rate * fx_rate
        )

    if error:
        cash_flow = 0
        _l.error(
            f"Could not calculate cash flow for {date} "
            f"{portfolio_register.linked_instrument} {pricing_policy}"
        )

    _l.info(
        f"calculate_cash_flow.date {date} pricing_policy {pricing_policy} "
        f"RESULT {cash_flow}"
    )

    return cash_flow


@shared_task(name="portfolios.calculate_portfolio_register_record", bind=True)
def calculate_portfolio_register_record(self, task_id):
    """
    Now as it a part of Finmars Backend project its specific task over portfolio
    The idea is to collect all Cash In/Cash Out transactions and create
    from them RegisterRecord instances
    at this points we also calculate number of shares for each Register Record

    :param self:
    :param task_id:
    :return:
    """
    log = "calculate_portfolio_register_record"
    _l.info(f"{log} init, task_id={task_id}")

    task = CeleryTask.objects.get(id=task_id)
    task.celery_tasks_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    task.save()

    portfolio_user_codes = []

    if task.options_object and "portfolios" in task.options_object:
        portfolio_user_codes = task.options_object["portfolios"]

    master_user = MasterUser.objects.prefetch_related("members").all().first()

    result = {}
    try:
        send_system_message(
            master_user=master_user,
            performed_by="system",
            section="schedules",
            type="info",
            title="Calculating Portfolio Register Records",
            description="",
        )

        _l.info(f"{log} master_user={master_user}")

        if len(portfolio_user_codes):
            portfolio_registers = PortfolioRegister.objects.filter(
                master_user_id=master_user,
                portfolio__user_code__in=portfolio_user_codes,
            )

        else:
            portfolio_registers = PortfolioRegister.objects.filter(
                master_user_id=master_user
            )

        ecosystem_defaults = EcosystemDefault.objects.get(master_user=master_user)

        portfolio_ids = []
        portfolio_registers_map = {}

        for item in portfolio_registers:
            portfolio_ids.append(item.portfolio_id)
            portfolio_registers_map[item.portfolio_id] = item

        # from oldest to newest
        transactions = Transaction.objects.filter(
            master_user=master_user,
            portfolio_id__in=portfolio_ids,
            is_deleted=False,
            transaction_class_id__in=[
                TransactionClass.CASH_INFLOW,
                TransactionClass.CASH_OUTFLOW,
            ],
        ).order_by("accounting_date")

        PortfolioRegisterRecord.objects.filter(
            master_user=master_user,
            portfolio_id__in=portfolio_ids,
            transaction_class_id__in=[
                TransactionClass.CASH_INFLOW,
                TransactionClass.CASH_OUTFLOW,
            ],
        ).delete()

        count = 0
        total = len(transactions)
        transactions_dict = {}
        for item in transactions:
            if item.portfolio_id not in transactions_dict:
                transactions_dict[item.portfolio_id] = []

            transactions_dict[item.portfolio_id].append(item)

        for key, value in transactions_dict.items():
            previous_record = None
            for trn in value:
                portfolio_register = portfolio_registers_map[trn.portfolio_id]

                record = PortfolioRegisterRecord()
                record.master_user = master_user
                record.portfolio_id = key
                record.instrument_id = portfolio_register.linked_instrument_id
                record.transaction_date = trn.accounting_date
                record.transaction_code = trn.transaction_code
                record.cash_amount = trn.cash_consideration
                record.cash_currency_id = trn.transaction_currency_id
                record.valuation_currency_id = portfolio_register.valuation_currency_id
                record.transaction_class = trn.transaction_class
                record.share_price_calculation_type = get_price_calculation_type(
                    transaction_class=trn.transaction_class,
                    transaction=trn,
                )

                try:
                    previous_date_record = PortfolioRegisterRecord.objects.filter(
                        master_user=master_user,
                        portfolio_register=portfolio_register,
                        transaction_date__lt=record.transaction_date,
                    ).order_by("-id")[0]
                except Exception as e:
                    _l.error(f"Exception {e}")
                    previous_date_record = None

                if record.cash_currency_id == record.valuation_currency_id:
                    record.fx_rate = 1
                else:
                    try:
                        valuation_ccy_fx_rate = (
                            1
                            if (
                                    record.valuation_currency_id
                                    == ecosystem_defaults.currency_id
                            )
                            else CurrencyHistory.objects.get(
                                currency_id=record.valuation_currency_id,
                                pricing_policy=portfolio_register.valuation_pricing_policy,
                                date=record.transaction_date,
                            ).fx_rate
                        )

                        if record.cash_currency_id == ecosystem_defaults.currency_id:
                            cash_ccy_fx_rate = 1
                        else:
                            cash_ccy_fx_rate = CurrencyHistory.objects.get(
                                currency_id=record.cash_currency_id,
                                pricing_policy=portfolio_register.valuation_pricing_policy,
                                date=record.transaction_date,
                            ).fx_rate

                        _l.info(
                            f"{log} valuation_ccy_fx_rate={valuation_ccy_fx_rate} "
                            f"cash_ccy_fx_rate={cash_ccy_fx_rate} "
                        )

                        record.fx_rate = (
                            cash_ccy_fx_rate / valuation_ccy_fx_rate
                            if valuation_ccy_fx_rate
                            else 0
                        )

                    except Exception as e:
                        _l.info(f"{log} fx rate lookup error {e}")
                        record.fx_rate = 0

                # why use cash amount after, not record.cash_amount_valuation_currency
                record.cash_amount_valuation_currency = (
                        record.cash_amount * record.fx_rate * trn.reference_fx_rate
                )
                # start block NAV
                report_date = trn.accounting_date - timedelta(days=1)
                balance_report = calculate_simple_balance_report(
                    report_date,
                    portfolio_register,
                    portfolio_register.valuation_pricing_policy,
                    task.member
                )

                nav = sum(
                    item["market_value"]
                    for item in balance_report.items
                    if item["market_value"]
                )
                _l.info(f"{log} len(items)={len(balance_report.items)} nav={nav}")

                record.nav_previous_day_valuation_currency = nav
                # end block NAV

                # n_shares_previous_day
                if previous_date_record:
                    record.n_shares_previous_day = (
                        previous_date_record.rolling_shares_of_the_day
                    )
                else:
                    record.n_shares_previous_day = 0

                # dealing_price_valuation_currency here
                try:
                    if trn.trade_price:
                        record.dealing_price_valuation_currency = trn.trade_price
                    elif previous_date_record:
                        # let's MOVE block NAV here
                        record.dealing_price_valuation_currency = (
                            (
                                    record.nav_previous_day_valuation_currency
                                    / record.n_shares_previous_day
                            )
                            if record.n_shares_previous_day
                            else 0
                        )
                    else:
                        record.dealing_price_valuation_currency = (
                            portfolio_register.default_price
                        )
                except Exception:
                    record.dealing_price_valuation_currency = (
                        portfolio_register.default_price
                    )

                if trn.position_size_with_sign:
                    record.n_shares_added = trn.position_size_with_sign
                else:
                    # why  use cashamount , not    record.cash_amount_valuation_currency
                    record.n_shares_added = record.cash_amount_valuation_currency / record.dealing_price_valuation_currency

                # record.n_shares_end_of_the_day =
                # record.n_shares_previous_day + record.n_shares_added
                # record.n_shares_end_of_the_day  - rolling n_shares,
                # but we take only last record of the day - it's total of the day

                if previous_record:
                    record.rolling_shares_of_the_day = (
                            previous_record.rolling_shares_of_the_day
                            + record.n_shares_added
                    )
                else:
                    record.rolling_shares_of_the_day = record.n_shares_added

                record.transaction_id = trn.id
                record.complex_transaction_id = trn.complex_transaction_id
                record.portfolio_register_id = portfolio_register.id

                _l.info(f"{log} record.__dict__={record.__dict__}")

                record.previous_date_record = previous_date_record
                record.save()

                count += 1

                task.update_progress(
                    {
                        "current": count,
                        "percent": round(count / (total / 100)),
                        "total": total,
                        "description": f"Record {record} calculated",
                    }
                )

                previous_record = record

        send_system_message(
            master_user=master_user,
            performed_by="system",
            section="schedules",
            type="info",
            title="Portfolio Register Records calculation finish",
            description=f"Record created: {count}",
        )

        result["message"] = f"Records calculated: {total}"

        task.status = CeleryTask.STATUS_DONE
        task.result_object = result
        task.save()

    except Exception as e:
        task.status = CeleryTask.STATUS_ERROR
        task.error_message = str(e)
        task.result_object = result
        task.save()

        send_system_message(
            master_user=master_user,
            action_status="required",
            type="error",
            title=f"Task Failed. Name: {log}",
            description=str(e),
        )

        _l.error(f"{log} error {e}\n{traceback.format_exc()}")


@shared_task(name="portfolios.calculate_portfolio_register_price_history", bind=True)
def calculate_portfolio_register_price_history(self, task_id):
    """
    It should be triggered after calculate_portfolio_register_record finished

    This purpose of this task is to get PriceHistory.principal_price of Portfolio

    Later on it would be used in Performance Report

    Also it calculates NAV and Cash Flows and saves it in Price History

    :param self:
    :param task_id
    :return:
    """

    from poms.celery_tasks.models import CeleryTask

    # member=None, date_from=None, date_to=None, portfolios=None
    # _l.info('calculate_portfolio_register_price_history.date_from %s' % date_from)
    # _l.info('calculate_portfolio_register_price_history.date_to %s' % date_to)
    # _l.info('calculate_portfolio_register_price_history.portfolios %s' % portfolios)
    #
    # TODO if we return to signle base logic, fix it
    # master_user = MasterUser.objects.all().first()
    #
    # if not date_to:
    #     date_to = timezone_today() - timedelta(days=1)
    #
    # if not member:
    #     # member = Member.objects.get(master_user=master_user, is_owner=True)
    #     member = Member.objects.get(username='finmars_bot')
    # task = CeleryTask.objects.create(
    #     master_user=master_user,
    #     member=member,
    #     verbose_name="Calculate Portfolio Register Prices",
    #     type='calculate_portfolio_register_price_history',
    #     status=CeleryTask.STATUS_PENDING
    # )

    task = CeleryTask.objects.get(id=task_id)
    task.celery_tasks_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    task.save()

    date_from = None
    date_to = None
    portfolios_user_codes = []

    if task.options_object:
        if "date_from" in task.options_object:
            date_from = task.options_object["date_from"]

        if "date_to" in task.options_object:
            date_from = task.options_object["date_to"]

        if "portfolios" in task.options_object:
            portfolios_user_codes = task.options_object["portfolios"]

    if not date_to:
        date_to = timezone_today() - timedelta(days=1)

    if not task.notes:
        task.notes = ""

    try:
        _l.info(f"calculate_portfolio_register_nav: date_from={date_from}")

        from poms.instruments.models import PriceHistory

        send_system_message(
            master_user=task.master_user,
            performed_by="system",
            section="schedules",
            type="info",
            title="Start portfolio price recalculation",
            description=f"Starting from date {date_from}",
        )

        if len(portfolios_user_codes):
            portfolio_registers = PortfolioRegister.objects.filter(
                master_user=task.master_user,
                portfolio__user_code__in=portfolios_user_codes,
            )
        else:
            portfolio_registers = PortfolioRegister.objects.filter(
                master_user=task.master_user
            )

        pricing_policies = PricingPolicy.objects.filter(master_user=task.master_user)

        count = 0
        total = 0

        portfolio_register_map = {}

        result = {}

        for portfolio_register in portfolio_registers:
            portfolio_register_map[portfolio_register.user_code] = portfolio_register

            result[portfolio_register.user_code] = {
                "portfolio_register_id": portfolio_register.id,
                "portfolio_register_object": {
                    "id": portfolio_register.id,
                    "user_code": portfolio_register.user_code,
                },
                "error_message": None,
                "dates": [],
            }

            _date_from = None

            if date_from and isinstance(date_from, str) and date_from != "None":
                # format = "%Y-%m-%d"
                # _date_from = datetime.strptime(date_from, format).date()
                _date_from = parser.parse(date_from).date()
            else:
                try:
                    first_transaction = (
                        Transaction.objects.filter(
                            portfolio=portfolio_register.portfolio
                        )
                        .order_by("accounting_date")
                        .first()
                    )
                    _date_from = first_transaction.accounting_date

                except Exception:
                    result[portfolio_register.user_code]["error_message"] = (
                            "Portfolio % has no transactions"
                            % portfolio_register.portfolio.name
                    )
                    result[portfolio_register.user_code]["dates"] = []
                    continue

            result[portfolio_register.user_code]["date_from"] = _date_from
            result[portfolio_register.user_code]["date_to"] = date_to

            result[portfolio_register.user_code]["dates"] = get_list_of_dates_between_two_dates(_date_from, date_to)

            if not portfolio_register.linked_instrument:
                result[portfolio_register.user_code]["error_message"] = (
                        "Portfolio % has no linked instrument"
                        % portfolio_register.portfolio.name
                )
                result[portfolio_register.user_code]["dates"] = []
                continue

        # Calculate total
        for item in result.values():
            total = total + len(item["dates"])

        # Init calculation
        for item in result.values():
            portfolio_register = portfolio_register_map[
                item["portfolio_register_object"]["user_code"]
            ]

            true_pricing_policy = portfolio_register.valuation_pricing_policy

            _l.info('going calculate %s' % portfolio_register)
            # _l.info('going calculate date_from %s' % item["date_from"])
            # _l.info('going calculate date_to %s' % item["date_to"])
            _l.info('going calculate dates len %s' % len(item["dates"]))

            for date in item["dates"]:
                try:
                    registry_record = (
                        PortfolioRegisterRecord.objects.filter(
                            instrument=portfolio_register.linked_instrument,
                            transaction_date__lte=date,
                        )
                        .order_by("-transaction_date", "-transaction_code")
                        .first()
                    )

                    if registry_record:

                        if registry_record.rolling_shares_of_the_day != 0:

                            balance_report = calculate_simple_balance_report(
                                date, portfolio_register, true_pricing_policy, task.member
                            )

                            nav = 0

                            for item in balance_report.items:
                                if item["market_value"]:
                                    nav = nav + item["market_value"]

                            cash_flow = calculate_cash_flow(
                                task.master_user, date, true_pricing_policy, portfolio_register
                            )

                            # principal_price = nav / (registry_record.n_shares_previous_day
                            # + registry_record.n_shares_added)

                            principal_price = nav / registry_record.rolling_shares_of_the_day

                            for pricing_policy in pricing_policies:
                                try:
                                    price_history = PriceHistory.objects.get(
                                        instrument=portfolio_register.linked_instrument,
                                        date=date,
                                        pricing_policy=pricing_policy,
                                    )
                                except Exception:
                                    price_history = PriceHistory(
                                        instrument=portfolio_register.linked_instrument,
                                        date=date,
                                        pricing_policy=pricing_policy,
                                    )

                                price_history.nav = nav
                                price_history.cash_flow = cash_flow
                                price_history.principal_price = principal_price

                                price_history.save()

                            count = count + 1

                            task.update_progress(
                                {
                                    "current": count,
                                    "percent": round(count / (total / 100)),
                                    "total": total,
                                    "description": f"Calculating {portfolio_register} at {date}",
                                }
                            )

                except Exception as e:
                    _l.error(f"calculate_portfolio_register_price_history.error {e} ")
                    _l.error(
                        f"calculate_portfolio_register_price_history.exception {traceback.format_exc()}"
                    )
                    _l.error(f"date {date}")

        # Finish calculation

        send_system_message(
            master_user=task.master_user,
            performed_by="system",
            section="schedules",
            type="success",
            title="Portfolio price recalculation finish",
            description=f"Calculated {count} prices",
        )

        task.result_object = result

        task.status = CeleryTask.STATUS_DONE
        task.save()

    except Exception as e:
        send_system_message(
            master_user=task.master_user,
            action_status="required",
            type="error",
            title="Task Failed. Name: calculate_portfolio_register_price_history",
            description=str(e),
        )

        task.error_message = f"Error {e}. Traceback {traceback.format_exc()}"
        task.status = CeleryTask.STATUS_ERROR
        task.save()

        _l.error(
            f"calculate_portfolio_register_price_history.exception {e} {traceback.format_exc()}"
        )
