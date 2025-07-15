import logging
import traceback
from datetime import date, datetime, timedelta, timezone

from django.conf import settings
from django.views.generic.dates import timezone_today

from celery.utils.log import get_task_logger

from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.common.exceptions import FinmarsBaseException
from poms.common.utils import (
    get_last_bdays_of_months_between_two_dates,
    get_last_business_day,
    get_last_business_day_in_previous_quarter,
    get_last_business_day_of_previous_month,
    get_last_business_day_of_previous_year,
    get_list_of_business_days_between_two_dates,
    get_list_of_dates_between_two_dates, get_closest_bday_of_yesterday,
)
from poms.currencies.models import Currency, CurrencyHistory
from poms.instruments.models import CostMethod, PricingPolicy
from poms.portfolios.models import (
    Portfolio,
    PortfolioHistory,
    PortfolioReconcileGroup,
    PortfolioReconcileHistory,
    PortfolioRegister,
    PortfolioRegisterRecord,
)
from poms.portfolios.utils import get_price_calculation_type, update_price_histories
from poms.reports.common import Report
from poms.reports.sql_builders.balance import BalanceReportBuilderSql
from poms.system_messages.handlers import send_system_message
from poms.transactions.models import Transaction, TransactionClass
from poms.users.models import EcosystemDefault, Member

_l = logging.getLogger("poms.portfolios")
celery_logger = get_task_logger(__name__)


def calculate_simple_balance_report(
    report_date: date, portfolio_register: PortfolioRegister, member: Member
):
    """
    Probably is a duplicated method. Here we're just getting Balance Report instance
    on specific date, portfolio and pricing policy
    """
    log = "calculate_simple_balance_report"
    _l.info(
        f"{log} report_date={report_date} portfolio_register={portfolio_register} member={member}"
    )

    if not portfolio_register.linked_instrument:
        raise FinmarsBaseException(
            error_key="invalid_portfolio_register",
            message=f"{log} portfolio_register {portfolio_register} has no linked_instrument",
        )

    try:
        report = Report(master_user=portfolio_register.master_user)
        report.master_user = portfolio_register.master_user
        report.member = member
        report.report_date = report_date
        report.pricing_policy = portfolio_register.valuation_pricing_policy
        report.portfolios = [portfolio_register.portfolio]
        report.report_currency = portfolio_register.linked_instrument.pricing_currency

        builder = BalanceReportBuilderSql(report)
        report = builder.build_balance_sync()

    except Exception as e:
        err_msg = f"{log} resulted in error {repr(e)}"
        _l.error(f"{err_msg} trace {traceback.format_exc()}")
        raise RuntimeError(err_msg) from e

    return report


def calculate_cash_flow(master_user, date, pricing_policy, portfolio_register):
    log = "calculate_cash_flow"
    _l.info(
        f"{log} date {date} pricing_policy {pricing_policy} portfolio_register {portfolio_register}"
    )

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

            except Exception as e:
                err_msg = (
                    f"{log} fx_rate calculation for transaction {transaction.id} "
                    f"portfolio_registry {portfolio_register.id} and linked_instrument "
                    f"{portfolio_register.linked_instrument.id} resulted "
                    f"in error {repr(e)}"
                )
                raise RuntimeError(err_msg) from e

        cash_flow = cash_flow + (
            transaction.cash_consideration * transaction.reference_fx_rate * fx_rate
        )

    _l.info(
        f"{log} date {date} pricing_policy {pricing_policy} RESULT CASH_FLOW {cash_flow}"
    )

    return cash_flow


@finmars_task(name="portfolios.calculate_portfolio_register_record", bind=True)
def calculate_portfolio_register_record(self, task_id, *args, **kwargs):
    """
    Now as it a part of Finmars Backend project its specific task over portfolio
    The idea is to collect all Cash In/Cash Out transactions and create
    from them RegisterRecord instances
    at this point we also calculate number of shares for each Register Record
    """
    log = "calculate_portfolio_register_record"
    _l.info(f"{log} init, task_id={task_id}")

    task = CeleryTask.objects.get(id=task_id)
    task.celery_tasks_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    task.save()

    master_user = task.master_user
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

        portfolio_registers_user_codes = task.options_object.get("portfolio_registers", [])

        date_from = task.options_object.get("date_from", None)

        date_to = task.options_object.get("date_to", None)

        if not date_to:
            date_to = get_closest_bday_of_yesterday()


        if portfolio_registers_user_codes:
            portfolio_registers = PortfolioRegister.objects.filter(
                master_user_id=master_user,
                user_code__in=portfolio_registers_user_codes,
            )

        else:
            portfolio_registers = PortfolioRegister.objects.filter(
                master_user_id=master_user, is_deleted=False
            )

        portfolio_ids = []
        portfolio_registers_map = {}

        for item in portfolio_registers:
            portfolio_ids.append(item.portfolio_id)

            if item.portfolio_id not in portfolio_registers_map:
                portfolio_registers_map[item.portfolio_id] = []

            portfolio_registers_map[item.portfolio_id].append(item)



        if date_from:

            # from oldest to newest
            transactions = Transaction.objects.filter(
                master_user=master_user,
                portfolio_id__in=portfolio_ids,
                is_deleted=False,
                is_canceled=False,  # important update PLAT-1661
                accounting_date__gte=date_from,
                accounting_date__lte=date_to,
                transaction_class_id__in=[
                    TransactionClass.CASH_INFLOW,
                    TransactionClass.CASH_OUTFLOW,
                ],
            ).order_by("accounting_date")

            PortfolioRegisterRecord.objects.filter(
                master_user=master_user,
                portfolio_id__in=portfolio_ids,
                transaction_date__gte=date_from,
                transaction_date__lte=date_to,
                transaction_class_id__in=[
                    TransactionClass.CASH_INFLOW,
                    TransactionClass.CASH_OUTFLOW,
                ],
            ).delete()

        else:

            # from oldest to newest
            transactions = Transaction.objects.filter(
                master_user=master_user,
                portfolio_id__in=portfolio_ids,
                is_deleted=False,
                is_canceled=False,  # important update PLAT-1661
                transaction_class_id__in=[
                    TransactionClass.CASH_INFLOW,
                    TransactionClass.CASH_OUTFLOW,
                ],
            ).order_by("accounting_date")

            PortfolioRegisterRecord.objects.filter(
                master_user=master_user,
                portfolio_id__in=portfolio_ids,
                accounting_date__gte=date_from,
                transaction_date__lte=date_to,
                transaction_class_id__in=[
                    TransactionClass.CASH_INFLOW,
                    TransactionClass.CASH_OUTFLOW,
                ],
            ).delete()

        count = 0
        total = len(transactions)
        ecosystem = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)
        default_currency_id = ecosystem.currency_id
        transactions_dict = {}
        for item in transactions:
            if item.portfolio_id not in transactions_dict:
                transactions_dict[item.portfolio_id] = []

            transactions_dict[item.portfolio_id].append(item)

        for key, value in transactions_dict.items():
            previous_record = None
            for trn in value:
                portfolio_registers = portfolio_registers_map[trn.portfolio_id]

                for portfolio_register in portfolio_registers:
                    if not portfolio_register.linked_instrument:
                        _l.error(
                            f"{log} portfolio_register={portfolio_register} has no linked_instrument, ignored!"
                        )
                        continue

                    record = PortfolioRegisterRecord()
                    record.master_user = master_user
                    record.portfolio_id = key
                    record.instrument_id = portfolio_register.linked_instrument_id
                    record.transaction_date = trn.accounting_date
                    record.transaction_code = trn.transaction_code
                    record.cash_amount = trn.cash_consideration
                    record.cash_currency_id = trn.transaction_currency_id
                    record.valuation_currency_id = (
                        portfolio_register.valuation_currency_id
                    )
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
                        _l.error(f"calculate_portfolio_register_record error {e}")
                        previous_date_record = None

                    if record.cash_currency_id == record.valuation_currency_id:
                        record.fx_rate = 1
                    else:
                        valuation_ccy_fx_rate = (
                            1
                            if record.valuation_currency_id == default_currency_id
                            else CurrencyHistory.objects.get_fx_rate(
                                currency_id=record.valuation_currency_id,
                                pricing_policy=portfolio_register.valuation_pricing_policy,
                                date=record.transaction_date,
                            )
                        )

                        if record.cash_currency_id == default_currency_id:
                            cash_ccy_fx_rate = 1
                        else:
                            cash_ccy_fx_rate = CurrencyHistory.objects.get_fx_rate(
                                currency_id=record.cash_currency_id,
                                pricing_policy=portfolio_register.valuation_pricing_policy,
                                date=record.transaction_date,
                            )

                        _l.info(
                            f"{log} valuation_ccy_fx_rate={valuation_ccy_fx_rate} "
                            f"cash_ccy_fx_rate={cash_ccy_fx_rate} "
                        )

                        record.fx_rate = cash_ccy_fx_rate / valuation_ccy_fx_rate

                    # why use cash amount after, not record.cash_amount_valuation_currency
                    record.cash_amount_valuation_currency = (
                        record.cash_amount * record.fx_rate * trn.reference_fx_rate
                    )

                    # start block eod NAV
                    report_date = trn.accounting_date
                    balance_report = calculate_simple_balance_report(
                        report_date,
                        portfolio_register,
                        task.member,
                    )

                    nav_valuation_currency = 0

                    for item in balance_report.items:
                        if item["market_value"]:
                            nav_valuation_currency = (
                                nav_valuation_currency + item["market_value"]
                            )

                    _l.info(
                        f"{log} len(items)={len(balance_report.items)} nav={nav_valuation_currency}"
                    )

                    record.nav_valuation_currency = nav_valuation_currency
                    # end block eod NAV

                    # start block previous NAV

                    if previous_date_record:
                        previous_date_record_report_date = (
                            previous_date_record.transaction_date
                        )
                        balance_report = calculate_simple_balance_report(
                            previous_date_record_report_date,
                            portfolio_register,
                            task.member,
                        )

                        nav_previous_register_record_day_valuation_currency = 0

                        for item in balance_report.items:
                            if item["market_value"]:
                                nav_previous_register_record_day_valuation_currency = (
                                    nav_previous_register_record_day_valuation_currency
                                    + item["market_value"]
                                )

                        _l.info(
                            f"{log} len(items)={len(balance_report.items)} nav={nav_previous_register_record_day_valuation_currency}"
                        )

                        record.nav_previous_register_record_day_valuation_currency = (
                            nav_previous_register_record_day_valuation_currency
                        )
                    else:
                        record.nav_previous_register_record_day_valuation_currency = 0
                    # end block NAV

                    # get nav of yesterday business day

                    previous_business_day = get_last_business_day(
                        report_date - timedelta(days=1)
                    )
                    previous_business_day_balance_report = (
                        calculate_simple_balance_report(
                            previous_business_day,
                            portfolio_register,
                            task.member,
                        )
                    )

                    nav_previous_business_day_valuation_currency = 0

                    for item in previous_business_day_balance_report.items:
                        if item["market_value"]:
                            nav_previous_business_day_valuation_currency = (
                                nav_previous_business_day_valuation_currency
                                + item["market_value"]
                            )

                    _l.info(
                        f"{log} len(items)={len(previous_business_day_balance_report.items)} nav={nav_previous_business_day_valuation_currency}"
                    )

                    record.nav_previous_business_day_valuation_currency = (
                        nav_previous_business_day_valuation_currency
                    )

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
                                    record.nav_previous_business_day_valuation_currency
                                    / record.n_shares_previous_day
                                )
                                if record.n_shares_previous_day
                                else portfolio_register.default_price
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
                        record.n_shares_added = (
                            record.cash_amount_valuation_currency
                            / record.dealing_price_valuation_currency
                        )

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
            description=repr(e),
        )

        err_msg = f"{log} error {repr(e)}"
        _l.error(f"{err_msg} --> {traceback.format_exc()}")
        raise RuntimeError(err_msg) from e


@finmars_task(name="portfolios.calculate_portfolio_register_price_history", bind=True)
def calculate_portfolio_register_price_history(self, task_id: int, *args, **kwargs):
    """
    It should be triggered after calculate_portfolio_register_record finished
    This purpose of this task is to get PriceHistory.principal_price of Portfolio
    Later on it would be used in Performance Report
    Also, it calculates NAV and Cash Flows and saves it in Price History
    """
    from poms.celery_tasks.models import CeleryTask
    from poms.instruments.models import PriceHistory

    log = "calculate_portfolio_register_price_history"

    task = CeleryTask.objects.filter(id=task_id).first()
    if not task:
        raise FinmarsBaseException(
            error_key="task_not_found", message=f"{log} no such task={task_id}"
        )

    if not task.options_object:
        err_msg = "No task options supplied"
        send_system_message(
            master_user=task.master_user,
            action_status="required",
            type="error",
            title=f"Task Failed. Name: {log}",
            description=err_msg,
        )
        task.error_message = err_msg
        task.status = CeleryTask.STATUS_ERROR
        task.save()
        raise RuntimeError(err_msg)

    task.celery_tasks_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    if not task.notes:
        task.notes = ""

    task.save()

    _l.info(f"{log} task_id={task_id} task_options={task.options_object}")

    date_to = task.options_object.get("date_to")
    date_from = task.options_object.get("date_from")
    portfolio_registers_user_codes = task.options_object.get("portfolio_registers")
    master_user = task.master_user

    # convert date's string to a date object
    if not date_to:
        date_to = timezone_today() - timedelta(days=1)
    else:
        date_to = datetime.strptime(date_to, settings.API_DATE_FORMAT).date()

    if date_from:
        date_from = datetime.strptime(date_from, settings.API_DATE_FORMAT).date()

    # convert portfolios user_code, to portfolio_register objects
    if portfolio_registers_user_codes:
        portfolio_registers = PortfolioRegister.objects.filter(
            master_user=master_user,
            user_code__in=portfolio_registers_user_codes,
        )
    else:
        portfolio_registers = PortfolioRegister.objects.filter(master_user=master_user)

    try:
        send_system_message(
            master_user=master_user,
            performed_by="system",
            section="schedules",
            type="info",
            title="Start portfolio price recalculation",
            description=f"Starting from date {date_from}",
        )

        count = 0
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
                "error_message": "",
                "dates": [],
            }

            if date_from:
                portfolio_date_from = date_from
            else:
                first_transaction = (
                    Transaction.objects.filter(portfolio=portfolio_register.portfolio)
                    .order_by("accounting_date")
                    .first()
                )
                if not first_transaction:
                    result[portfolio_register.user_code]["error_message"] = (
                        f"Portfolio {portfolio_register.portfolio.name} has no transactions"
                    )
                    result[portfolio_register.user_code]["dates"] = []
                    continue

                portfolio_date_from = first_transaction.accounting_date

            result[portfolio_register.user_code]["date_from"] = portfolio_date_from
            result[portfolio_register.user_code]["date_to"] = date_to

            result[portfolio_register.user_code]["dates"] = (
                get_list_of_dates_between_two_dates(portfolio_date_from, date_to)
            )

            if not portfolio_register.linked_instrument:
                result[portfolio_register.user_code]["error_message"] = (
                    f"Portfolio {portfolio_register.portfolio.name} has no linked instrument"
                )
                result[portfolio_register.user_code]["dates"] = []
                continue

        total = sum(len(item["dates"]) for item in result.values())

        for item in result.values():
            portfolio_register = portfolio_register_map[
                item["portfolio_register_object"]["user_code"]
            ]

            _l.info(
                f"{log} calculate {portfolio_register} for {len(item['dates'])} days"
            )

            PriceHistory.objects.filter(
                instrument=portfolio_register.linked_instrument,
                date__gte=item['date_from'],
                date__lte=item['date_to'],
                pricing_policy=portfolio_register.valuation_pricing_policy,
            ).delete()

            for day in item["dates"]:
                pr_record = (
                    PortfolioRegisterRecord.objects.filter(
                        instrument=portfolio_register.linked_instrument,
                        transaction_date__lte=day,
                    )
                    .order_by("-transaction_date", "-transaction_code")
                    .first()
                )
                if not pr_record:
                    continue

                price_histories = []  # price history objects to be updated

                price_history, _ = PriceHistory.objects.get_or_create(
                    instrument=portfolio_register.linked_instrument,
                    date=day,
                    pricing_policy=portfolio_register.valuation_pricing_policy,
                )
                price_histories.append(price_history)

                try:
                    balance_report = calculate_simple_balance_report(
                        day,
                        portfolio_register,
                        task.member,
                    )
                    nav = 0
                    for it in balance_report.items:
                        if it["market_value"]:
                            nav = nav + it["market_value"]

                except Exception as e:
                    err_msg = (
                        f"{log} {portfolio_register} day {day} calculate_simple_"
                        f"balance_report func ended in error {repr(e)}"
                    )
                    _l.error(f"{err_msg} trace {traceback.format_exc()}")
                    update_price_histories(price_histories, error_message=err_msg)
                    continue

                try:
                    cash_flow = calculate_cash_flow(
                        master_user,
                        day,
                        portfolio_register.valuation_pricing_policy,
                        portfolio_register,
                    )
                    principal_price = nav / pr_record.rolling_shares_of_the_day

                except Exception as e:
                    err_msg = f"{log} {portfolio_register} day {day} calculate_cash_flow func ended in error {repr(e)}"
                    _l.error(f"{err_msg} trace {traceback.format_exc()}")
                    update_price_histories(price_histories, error_message=err_msg)
                    continue

                update_price_histories(
                    price_histories,
                    error_message="",
                    nav=nav,
                    cash_flow=cash_flow,
                    principal_price=principal_price,
                )

                count = count + 1
                task.update_progress(
                    {
                        "current": count,
                        "percent": round(count / (total / 100)),
                        "total": total,
                        "description": f"Calculating {portfolio_register} at {day}",
                    }
                )

        # Finish calculation
        send_system_message(
            master_user=master_user,
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
            master_user=master_user,
            action_status="required",
            type="error",
            title="Task Failed. Name: calculate_portfolio_register_price_history",
            description=str(e),
        )

        err_msg = f"calculate_portfolio_register_price_history.exception {repr(e)} trace {traceback.format_exc()}"
        task.error_message = err_msg
        task.status = CeleryTask.STATUS_ERROR
        task.save()

        _l.error(err_msg)
        raise RuntimeError(err_msg) from e


@finmars_task(name="portfolios.calculate_portfolio_history", bind=True)
def calculate_portfolio_history(self, task_id: int, *args, **kwargs):
    """
    Right now trigger only by manual request
    """
    from poms.celery_tasks.models import CeleryTask

    task = CeleryTask.objects.filter(id=task_id).first()
    if not task:
        raise FinmarsBaseException(
            error_key="task_not_found",
            message=f"calculate_portfolio_history, no such task={task_id}",
        )

    if not task.options_object:
        err_msg = "No task options supplied"
        send_system_message(
            master_user=task.master_user,
            action_status="required",
            type="error",
            title="Task Failed. Name: calculate_portfolio_history",
            description=err_msg,
        )
        task.error_message = err_msg
        task.status = CeleryTask.STATUS_ERROR
        task.save()
        raise RuntimeError(err_msg)

    task.celery_tasks_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    if not task.notes:
        task.notes = ""

    task.save()

    _l.info(f"calculate_portfolio_history: task_options={task.options_object}")

    date = task.options_object.get("date")

    date = datetime.strptime(date, settings.API_DATE_FORMAT).date()

    calculation_period_date_from = task.options_object.get(
        "calculation_period_date_from"
    )

    period_type = task.options_object.get("period_type")
    portfolio = task.options_object.get("portfolio")
    currency = task.options_object.get("currency")
    pricing_policy = task.options_object.get("pricing_policy")
    segmentation_type = task.options_object.get("segmentation_type")
    benchmark = task.options_object.get("benchmark")
    cost_method = task.options_object.get("cost_method")
    performance_method = task.options_object.get("performance_method")

    portfolio = Portfolio.objects.get(user_code=portfolio)
    currency = Currency.objects.get(user_code=currency)
    pricing_policy = PricingPolicy.objects.get(user_code=pricing_policy)
    cost_method = CostMethod.objects.get(user_code=cost_method)

    if period_type == "daily":
        date_from = get_last_business_day(date - timedelta(days=1))
    elif period_type == "mtd":
        date_from = str(get_last_business_day_of_previous_month(date))
    elif period_type == "qtd":
        date_from = str(get_last_business_day_in_previous_quarter(date))
    elif period_type == "ytd":
        date_from = str(get_last_business_day_of_previous_year(date))
    elif period_type == "inception":
        date_from = str(portfolio.first_transaction_date)
    else:
        raise FinmarsBaseException(
            error_key="invalid_period_type",
            message=f"invalid period_type={period_type}",
        )

    _l.info(f"calculate_portfolio_history: date_from {date_from}")

    if not calculation_period_date_from:
        calculation_period_date_from = date_from

    dates = []

    if segmentation_type == "business_days_end_of_months":
        dates = get_last_bdays_of_months_between_two_dates(
            calculation_period_date_from, date
        )
    elif segmentation_type == "business_days":
        dates = get_list_of_business_days_between_two_dates(
            calculation_period_date_from, date
        )
    elif segmentation_type == "days":
        dates = get_list_of_dates_between_two_dates(calculation_period_date_from, date)

    task.update_progress(
        {
            "current": 0,
            "total": len(dates),
            "percent": 0,
            "description": "Going to calculate portfolio history",
        }
    )

    count = 1

    PortfolioHistory.objects.filter(
        portfolio=portfolio,
        currency=currency,
        pricing_policy=pricing_policy,
        period_type=period_type,
        cost_method=cost_method,
        performance_method=performance_method,
        date__gte=calculation_period_date_from).delete()

    for d in dates:
        task.update_progress(
            {
                "current": count,
                "total": len(dates),
                "percent": round(count / (len(dates) / 100)),
                "description": f"Going to calculate portfolio {portfolio.user_code} for {d}",
            }
        )

        user_code = (
            f"portfolio_history_{portfolio.user_code}_{currency.user_code}_"
            f"{pricing_policy.user_code}_{date_from}_{d}_{period_type}_"
            f"{cost_method.user_code}_{performance_method}_{benchmark}"
        )

        try:
            portfolio_history = PortfolioHistory.objects.get(user_code=user_code)
        except PortfolioHistory.DoesNotExist:
            if period_type == "daily":
                d_date_from = get_last_business_day(d - timedelta(days=1))
            elif period_type == "mtd":
                d_date_from = str(get_last_business_day_of_previous_month(d))
            elif period_type == "qtd":
                d_date_from = str(get_last_business_day_in_previous_quarter(d))
            elif period_type == "ytd":
                d_date_from = str(get_last_business_day_of_previous_year(d))
            elif period_type == "inception":
                d_date_from = str(portfolio.first_transaction_date)
            else:
                raise FinmarsBaseException(
                    error_key="invalid_period_type",
                    message=f"invalid period_type={period_type}",
                )

            portfolio_history = PortfolioHistory.objects.create(
                master_user=task.master_user,
                owner=task.member,
                user_code=user_code,
                portfolio=portfolio,
                currency=currency,
                pricing_policy=pricing_policy,
                date=d,
                date_from=d_date_from,
                period_type=period_type,
                cost_method=cost_method,
                performance_method=performance_method,
                benchmark=benchmark,
            )

        portfolio_history.calculate()

        count = count + 1


def _send_err_message(task: CeleryTask, err_msg: str):
    send_system_message(
        master_user=task.master_user,
        action_status="required",
        type="error",
        title=f"Task Failed. Name: {task.type} Id: {task.id}",
        description=err_msg,
    )
    _l.error(f"Task Failed. Name: {task.type} Id: {task.id} err_msg: {err_msg}")


def _finish_task_as_error(task: CeleryTask, err_msg: str):
    task.error_message = err_msg
    task.status = CeleryTask.STATUS_ERROR
    task.save()
    _send_err_message(task, err_msg)


def _calculate_group_reconcile_history(
    day: str, reconcile_group: PortfolioReconcileGroup, task: CeleryTask
):
    history_user_code = f"portfolio_reconcile_history_{reconcile_group.user_code}_{day}"
    (
        portfolio_reconcile_history,
        created,
    ) = PortfolioReconcileHistory.objects.get_or_create(
        master_user=task.master_user,
        user_code=history_user_code,
        defaults=dict(
            date=day,
            owner=task.member,
            portfolio_reconcile_group=reconcile_group,
            report_ttl=reconcile_group.params.get("report_ttl", 90),
        ),
    )

    _l.info(
        f"portfolio_reconcile_history {history_user_code} {day} {'created' if created else 'updated'}"
    )

    portfolio_reconcile_history.linked_task = task
    portfolio_reconcile_history.save(update_fields=["linked_task"])
    portfolio_reconcile_history.calculate()

    if portfolio_reconcile_history.status == PortfolioReconcileHistory.STATUS_OK:
        reconcile_group.last_calculated_at = datetime.now(timezone.utc)
        reconcile_group.save(update_fields=["last_calculated_at"])

        _l.info(
            f"portfolio_reconcile_history {history_user_code} {day} successfully calculated"
        )

        return

    err_msg = f"portfolio_reconcile_history {history_user_code} {day} failed due to {portfolio_reconcile_history.error_message}"
    _l.error(err_msg)

    return err_msg


@finmars_task(name="portfolios.calculate_portfolio_reconcile_history", bind=True)
def calculate_portfolio_reconcile_history(self, task_id: int, *args, **kwargs):
    """
    Calculate portfolio reconcile history for one group, and for given dates
    """
    from poms.celery_tasks.models import CeleryTask

    task = CeleryTask.objects.filter(id=task_id).first()
    if not task:
        raise FinmarsBaseException(
            error_key="task_not_found",
            message=f"calculate_portfolio_reconcile_history: no such task={task_id}",
        )

    if not task.options_object:
        _finish_task_as_error(task, "No task options supplied")
        return

    _l.info(
        f"calculate_portfolio_reconcile_history: task_options={task.options_object}"
    )

    group_user_code = task.options_object.get("portfolio_reconcile_group")
    try:
        reconcile_group = PortfolioReconcileGroup.objects.get(user_code=group_user_code)
    except PortfolioReconcileGroup.DoesNotExist:
        _finish_task_as_error(task, f"No such reconcile group {group_user_code}")
        return

    task.celery_tasks_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    task.notes = task.notes or ""
    task.save()

    dates = task.options_object["dates"]
    days_number = len(dates)
    for count, day in enumerate(dates, start=1):
        task.update_progress(
            {
                "current": count,
                "percent": round(count / days_number / 100),
                "total": days_number,
                "description": f"Reconciling {group_user_code} at {day}",
            }
        )

        try:
            err_msg = _calculate_group_reconcile_history(
                day=day, reconcile_group=reconcile_group, task=task
            )
            if err_msg:
                _finish_task_as_error(task, err_msg)
                return

        except Exception as e:
            _finish_task_as_error(task, repr(e))
            return

    task.update_progress(
        {
            "current": days_number,
            "percent": 100,
            "total": days_number,
            "description": f"Reconciliation of the group {group_user_code} finished",
        }
    )
    task.status = CeleryTask.STATUS_DONE
    task.save()


@finmars_task(name="portfolios.bulk_calculate_reconcile_history", bind=True)
def bulk_calculate_reconcile_history(self, task_id: int, *args, **kwargs):
    """
    Bulk calculate of several reconcile groups
    """
    from poms.celery_tasks.models import CeleryTask

    task = CeleryTask.objects.filter(id=task_id).first()
    if not task:
        raise FinmarsBaseException(
            error_key="task_not_found",
            message=f"bulk_calculate_reconcile_history: no such task={task_id}",
        )

    if not task.options_object:
        _finish_task_as_error(task, "No task options supplied")
        return

    _l.info(f"bulk_calculate_reconcile_history: task_options={task.options_object}")

    error_messages = []
    dates = task.options_object.get("dates", [])
    days_number = len(dates)
    reconcile_groups = task.options_object.get("reconcile_groups", [])
    groups_amount = len(reconcile_groups)
    for count, group_user_code in enumerate(reconcile_groups):
        task.update_progress(
            {
                "current": count,
                "percent": round((count * 100) // groups_amount),
                "total": groups_amount,
                "description": f"Reconciling {group_user_code} group for {days_number} days",
            }
        )

        try:
            reconcile_group = PortfolioReconcileGroup.objects.get(
                user_code=group_user_code
            )

        except PortfolioReconcileGroup.DoesNotExist:
            err_msg = f"No such reconcile group {group_user_code}"
            _send_err_message(task, err_msg)
            error_messages.append(err_msg)
            continue

        for day in dates:
            try:
                err_msg = _calculate_group_reconcile_history(
                    day=day, reconcile_group=reconcile_group, task=task
                )
                if err_msg:
                    _send_err_message(task, err_msg)
                    error_messages.append(err_msg)

            except Exception as e:
                err_msg = f"group: {group_user_code} day: {day} err: {repr(e)}"
                _send_err_message(task, err_msg)
                error_messages.append(err_msg)
                continue

    task.update_progress(
        {
            "current": groups_amount,
            "percent": 100,
            "total": groups_amount,
            "description": f"Reconciliation of all {groups_amount} groups finished",
        }
    )
    if error_messages:
        task.error_message = "\n".join(error_messages)
        task.status = CeleryTask.STATUS_ERROR
    else:
        task.status = CeleryTask.STATUS_DONE

    task.save()
