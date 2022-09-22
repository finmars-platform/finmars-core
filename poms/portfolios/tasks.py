from __future__ import unicode_literals, print_function

import logging
import time
from datetime import timedelta, datetime

from celery import shared_task
from django.db import transaction
from django.views.generic.dates import timezone_today

from poms.common.utils import get_list_of_dates_between_two_dates
from poms.currencies.models import CurrencyHistory
from poms.instruments.models import PriceHistory, PricingPolicy
from poms.portfolios.models import PortfolioRegister, PortfolioRegisterRecord
from poms.reports.builders.balance_item import Report
from poms.reports.builders.balance_pl import ReportBuilder
from poms.reports.sql_builders.balance import BalanceReportBuilderSql
from poms.system_messages.handlers import send_system_message
from poms.transactions.models import Transaction, TransactionClass
from poms.users.models import MasterUser, EcosystemDefault

_l = logging.getLogger('poms.portfolios')

from celery.utils.log import get_task_logger
import traceback

celery_logger = get_task_logger(__name__)


def calculate_simple_balance_report(report_date, portfolio_register, pricing_policy):
    instance = Report(master_user=portfolio_register.master_user)

    _l.info('calculate_simple_balance_report.report_date %s' % report_date)

    instance.master_user = portfolio_register.master_user
    instance.report_date = report_date
    instance.pricing_policy = pricing_policy
    # instance.report_currency = portfolio_register.valuation_currency
    instance.report_currency = portfolio_register.linked_instrument.pricing_currency
    instance.portfolios = [portfolio_register.portfolio]

    builder = BalanceReportBuilderSql(instance=instance)
    instance = builder.build_balance()

    return instance


def calculate_cash_flow(master_user, date, pricing_policy, portfolio_register):

    _l.info('calculate_cash_flow.date %s pricing_policy %s' % (date, pricing_policy))

    cash_flow = 0

    transactions = Transaction.objects.filter(master_user=master_user, portfolio_id=portfolio_register.portfolio,
                                              accounting_date=date,
                                               transaction_class_id__in=[TransactionClass.CASH_INFLOW,
                                                                         TransactionClass.DISTRIBUTION,
                                                                         TransactionClass.INJECTION,
                                                                         TransactionClass.CASH_OUTFLOW]).order_by(
        'accounting_date')

    fx_rate = 0

    error = False

    for transaction in transactions:

        if transaction.transaction_currency == portfolio_register.linked_instrument.pricing_currency:
            fx_rate = 1
        else:

            try:
                trn_currency_fx_rate = 0
                instr_pricing_currency_fx_rate = 0

                trn_currency_fx_rate = CurrencyHistory.objects.get(currency_id=transaction.transaction_currency,
                                                               pricing_policy=pricing_policy,
                                                               date=date).fx_rate

                instr_pricing_currency_fx_rate = CurrencyHistory.objects.get(currency_id=portfolio_register.linked_instrument.pricing_currency,
                                                                   pricing_policy=pricing_policy,
                                                                   date=date).fx_rate

                fx_rate = trn_currency_fx_rate / instr_pricing_currency_fx_rate

            except Exception as e:
                error = True
                fx_rate = 0

        cash_flow = cash_flow + (transaction.cash_consideration * transaction.reference_fx_rate * fx_rate)

    if error:
        cash_flow = 0
        _l.error("Could not calculate cash flow for %s %s %s" % (date, portfolio_register.linked_instrument, pricing_policy ))

    _l.info('calculate_cash_flow.date %s pricing_policy %s RESULT %s' % (date, pricing_policy, cash_flow))

    return cash_flow


@shared_task(name='portfolios.calculate_portfolio_register_record', ignore_result=True)
def calculate_portfolio_register_record(master_users=None):
    _l.info('calculate_portfolio_register_record')

    try:

        master_user_qs = MasterUser.objects.prefetch_related(
            'members'
        )
        if master_users:
            master_user_qs = master_user_qs.filter(pk__in=master_users)

        for master_user in master_user_qs:

            send_system_message(master_user=master_user,
                                performed_by='system',
                                section='schedules',
                                type='info',
                                title='Calculating Portfolio Register Records',
                                description=''
                                )

            _l.info("calculate_portfolio_register_record0 master_user %s" % master_user)

            portfolio_registers = PortfolioRegister.objects.filter(master_user_id=master_user)

            ecosystem_defaults = EcosystemDefault.objects.get(master_user=master_user)

            portfolio_ids = []
            portfolio_registers_map = {}

            for item in portfolio_registers:
                portfolio_ids.append(item.portfolio_id)
                portfolio_registers_map[item.portfolio_id] = item

            # from oldest to newest
            transactions = Transaction.objects.filter(master_user=master_user, portfolio_id__in=portfolio_ids,
                                                      transaction_class_id__in=[TransactionClass.CASH_INFLOW,

                                                                                TransactionClass.CASH_OUTFLOW]).order_by(
                'accounting_date')

            transactions_dict = {}

            PortfolioRegisterRecord.objects.filter(master_user=master_user).delete()

            count = 0

            for item in transactions:

                if item.portfolio_id not in transactions_dict:
                    transactions_dict[item.portfolio_id] = []

                transactions_dict[item.portfolio_id].append(item)

            for key in transactions_dict:

                previous_record = None
                previous_date_record = None

                for trn in transactions_dict[key]:

                    portfolio_register = portfolio_registers_map[trn.portfolio_id]

                    record = PortfolioRegisterRecord()

                    record.master_user = master_user

                    record.portfolio_id = key
                    record.instrument_id = portfolio_register.linked_instrument_id
                    record.transaction_date = trn.accounting_date
                    record.transaction_code = trn.transaction_code
                    record.transaction_class_id = trn.transaction_class_id
                    record.cash_amount = trn.cash_consideration

                    record.cash_currency_id = trn.transaction_currency_id
                    record.valuation_currency_id = portfolio_register.valuation_currency_id

                    try:
                        previous_date_record = PortfolioRegisterRecord.objects.filter(master_user=master_user,
                                                                                      portfolio_register=portfolio_register,
                                                                                      transaction_date__lt=record.transaction_date).order_by(
                            '-id')[0]
                    except Exception as e:
                        _l.error("Exceptino %s" % e)
                        previous_date_record = None

                    if record.cash_currency_id == record.valuation_currency_id:
                        record.fx_rate = 1
                    else:
                        try:

                            valuation_ccy_fx_rate = 1

                            if record.valuation_currency_id == ecosystem_defaults.currency_id:
                                valuation_ccy_fx_rate = 1
                            else:
                                valuation_ccy_fx_rate = CurrencyHistory.objects.get(
                                    currency_id=record.valuation_currency_id,
                                    pricing_policy=portfolio_register.valuation_pricing_policy,
                                    date=record.transaction_date).fx_rate

                            cash_ccy_fx_rate = 1

                            if record.cash_currency_id == ecosystem_defaults.currency_id:

                                cash_ccy_fx_rate = 1

                            else:

                                cash_ccy_fx_rate = CurrencyHistory.objects.get(currency_id=record.cash_currency_id,
                                                                               pricing_policy=portfolio_register.valuation_pricing_policy,
                                                                               date=record.transaction_date).fx_rate

                            _l.info(
                                "calculate_portfolio_register_record0_valuation_ccy_fx_rate %s " % valuation_ccy_fx_rate)
                            _l.info("calculate_portfolio_register_record0_cash_ccy_fx_rate %s " % cash_ccy_fx_rate)

                            record.fx_rate = cash_ccy_fx_rate / valuation_ccy_fx_rate

                        except Exception as e:
                            _l.info("calculate_portfolio_register_record0 fx rate lookup error %s " % e)
                            record.fx_rate = 0
                    # why  use cashamount after , not    record.cash_amount_valuation_currency
                    record.cash_amount_valuation_currency = record.cash_amount * record.fx_rate * trn.reference_fx_rate
                    # start block NAV

                    report_date = trn.accounting_date - timedelta(days=1)
                    balance_report = calculate_simple_balance_report(report_date, portfolio_register, portfolio_register.valuation_pricing_policy)

                    nav = 0

                    for item in balance_report.items:

                        if item['market_value']:
                            nav = nav + item['market_value']

                    _l.info("calculate_portfolio_register_record.items %s" % len(balance_report.items))
                    _l.info("calculate_portfolio_register_record.nav %s" % nav)

                    record.nav_previous_day_valuation_currency = nav
                    # end block NAV
                    # n_shares_previous_day
                    if previous_date_record:
                        record.n_shares_previous_day = previous_date_record.rolling_shares_of_the_day
                    else:
                        record.n_shares_previous_day = 0

                    # dealing_price_valuation_currency here

                    if trn.trade_price:
                        record.dealing_price_valuation_currency = trn.trade_price
                    else:
                        if previous_date_record:
                            # let's MOVE block NAV here
                            record.dealing_price_valuation_currency = record.nav_previous_day_valuation_currency / record.n_shares_previous_day
                        else:
                            record.dealing_price_valuation_currency = portfolio_register.default_price

                    if trn.position_size_with_sign:
                        record.n_shares_added = trn.position_size_with_sign
                    else:

                        # why  use cashamount , not    record.cash_amount_valuation_currency
                        record.n_shares_added = record.cash_amount_valuation_currency / record.dealing_price_valuation_currency

                    # record.n_shares_end_of_the_day = record.n_shares_previous_day + record.n_shares_added
                    # record.n_shares_end_of_the_day  - rolling n_shares, but we take only last record of the day - it's total of the day

                    if previous_record:
                        record.rolling_shares_of_the_day = previous_record.rolling_shares_of_the_day + record.n_shares_added
                    else:
                        record.rolling_shares_of_the_day = record.n_shares_added

                    record.transaction_id = trn.id
                    record.complex_transaction_id = trn.complex_transaction_id
                    record.portfolio_register_id = portfolio_register.id

                    _l.info("calculate_portfolio_register_record.record.__dict__ %s" % record.__dict__)

                    record.previous_date_record = previous_date_record
                    record.save()

                    count = count + 1

                    previous_record = record

            send_system_message(master_user=master_user,
                                performed_by='system',
                                section='schedules',
                                type='info',
                                title='Portfolio Register Records calculation finish',
                                description='Record created: %s ' % count
                                )

    except Exception as e:

        _l.error('calculate_portfolio_register_records error %s' % e)
        _l.error(traceback.format_exc())


@shared_task(name='portfolios.calculate_portfolio_register_price_history', ignore_result=True)
def calculate_portfolio_register_price_history(master_users=None, date_from=None):


    try:

        _l.info('calculate_portfolio_register_nav: master_users=%s date_from=%s', master_users, date_from)

        from poms.instruments.models import PriceHistory

        master_user_qs = MasterUser.objects.prefetch_related(
            'members'
        )
        if master_users:
            master_user_qs = master_user_qs.filter(pk__in=master_users)

        for master_user in master_user_qs:

            send_system_message(master_user=master_user,
                                performed_by='system',
                                section='schedules',
                                type='info',
                                title='Start portfolio price recalculation',
                                description='Starting from date %s' % date_from,
                                )

            _l.debug('calculate_portfolio_register_nav: master_user=%s', master_user.id)

            portfolio_registers = PortfolioRegister.objects.filter(master_user=master_user)
            pricing_policies = PricingPolicy.objects.filter(master_user=master_user)

            count = 0

            for portfolio_register in portfolio_registers:

                if date_from and isinstance(date_from, str):
                    format = '%Y-%m-%d'
                    date_from = datetime.strptime(date_from, format).date()
                else:
                    first_transaction = \
                        Transaction.objects.filter(portfolio=portfolio_register.portfolio).order_by('accounting_date')[0]
                    date_from = first_transaction.accounting_date

                date_to = timezone_today() - timedelta(days=1)

                _l.info('calculate_portfolio_register_nav0.date_from %s' % date_from)
                _l.info('calculate_portfolio_register_nav0.date_to %s' % date_to)
                dates = get_list_of_dates_between_two_dates(date_from, date_to)

                _l.info('calculate_portfolio_register_nav0.dates %s ' % len(dates))


                true_pricing_policy = portfolio_register.valuation_pricing_policy

                for date in dates:

                    try:

                        price_history = None
                        registry_record = PortfolioRegisterRecord.objects.filter(instrument=portfolio_register.linked_instrument, transaction_date__lte=date).order_by('-transaction_date', '-transaction_code')[0]

                        balance_report = calculate_simple_balance_report(date, portfolio_register, true_pricing_policy)

                        nav = 0
                        cash_flow = 0

                        for item in balance_report.items:

                            if item['market_value']:
                                nav = nav + item['market_value']

                        cash_flow = calculate_cash_flow(master_user, date, pricing_policy, portfolio_register)


                        # principal_price = nav / (registry_record.n_shares_previous_day + registry_record.n_shares_added)
                        principal_price = nav / registry_record.rolling_shares_of_the_day


                        for pricing_policy in pricing_policies:
                            try:

                                price_history = PriceHistory.objects.get(instrument=portfolio_register.linked_instrument, date=date,
                                                                         pricing_policy=pricing_policy)
                            except Exception as e:
                                price_history = PriceHistory(instrument=portfolio_register.linked_instrument, date=date,
                                                             pricing_policy=pricing_policy)


                            price_history.nav = nav
                            price_history.cash_flow = cash_flow
                            price_history.principal_price = principal_price

                            price_history.save()

                        count = count + 1

                    except Exception as e:
                        _l.error('calculate_portfolio_register_price_history.error %s ' % e)
                        _l.error('date %s' % date)


            send_system_message(master_user=master_user,
                                performed_by='system',
                                section='schedules',
                                type='success',
                                title='Portfolio price recalculation finish',
                                description='Calculated %s prices' % count,
                                )

    except Exception as e:

        _l.error("calculate_portfolio_register_price_history.exception %s" % e)
        _l.error("calculate_portfolio_register_price_history.exception %s" % traceback.format_exc())
