from __future__ import unicode_literals, print_function

import logging
import time

from celery import shared_task

from poms.currencies.models import CurrencyHistory
from poms.portfolios.models import PortfolioRegister, PortfolioRegisterRecord
from poms.reports.builders.balance_item import Report
from poms.reports.builders.balance_pl import ReportBuilder
from poms.reports.sql_builders.balance import BalanceReportBuilderSql
from poms.transactions.models import Transaction, TransactionClass
from poms.users.models import MasterUser

_l = logging.getLogger('poms.portfolios')

from celery.utils.log import get_task_logger
import traceback


celery_logger = get_task_logger(__name__)


def calculate_simple_balance_report(transaction, portfolio_register):

    instance = Report(master_user=transaction.master_user)

    instance.master_user = transaction.master_user
    instance.report_date = transaction.accounting_date
    instance.pricing_policy = portfolio_register.valuation_pricing_policy
    instance.report_currency = transaction.settlement_currency
    instance.portfolios = [transaction.portfolio]

    builder = BalanceReportBuilderSql(instance=instance)
    instance = builder.build_balance()

    return instance


@shared_task(name='portfolios.calculate_portfolio_register_record', bind=True)
def calculate_portfolio_register_record(self, portfolio_register_ids, master_user_id):

    try:
        st = time.perf_counter()

        master_user = MasterUser.objects.get(id=master_user_id)

        _l.info("calculate_portfolio_register_record master_user %s" % master_user)

        portfolio_registers = PortfolioRegister.objects.filter(master_user_id=master_user,
                                                               id__in=portfolio_register_ids)

        portfolio_ids = []
        portfolio_registers_map = {}

        for item in portfolio_registers:
            portfolio_ids.append(item.portfolio_id)
            portfolio_registers_map[item.portfolio_id] = item

        # from oldest to newest
        transactions = Transaction.objects.filter(master_user=master_user, portfolio_id__in=portfolio_ids,
                                                  transaction_class_id__in=[TransactionClass.CASH_INFLOW,
                                                                            TransactionClass.CASH_OUTFLOW]).order_by(
            '-accounting_date')

        transactions_dict = {}

        PortfolioRegisterRecord.objects.filter(master_user=master_user,
                                               portfolio_register_id__in=portfolio_register_ids).delete()

        for item in transactions:

            if item.portfolio_id not in transactions_dict:
                transactions_dict[item.portfolio_id] = []

            transactions_dict[item.portfolio_id].append(item)

        for key in transactions_dict:

            previous = None

            for trn in transactions_dict[key]:

                portfolio_register = portfolio_registers_map[trn.portfolio_id]

                record = PortfolioRegisterRecord()

                record.master_user = master_user

                record.portfolio_id = key
                record.instrument_id = trn.instrument_id
                record.transaction_date = trn.accounting_date
                record.transaction_code = trn.transaction_code
                record.transaction_type = trn.transaction_class_id
                record.cash_amount = trn.cash_consideration
                record.cash_currency_id = trn.settlement_currency_id

                record.valuation_currency_id = portfolio_register.valuation_currency_id

                if record.cash_currency_id == record.valuation_currency_id:
                    record.fx_rate = 1
                else:
                    try:

                        valuation_ccy_fx_rate = CurrencyHistory.objects.get(currency_id=record.valuation_currency_id,
                                                                            date=record.transaction_date).fx_rate
                        cash_ccy_fx_rate = CurrencyHistory.objects.get(currency_id=record.cash_currency_id,
                                                                       date=record.transaction_date).fx_rate

                        record.fx_rate = valuation_ccy_fx_rate / cash_ccy_fx_rate

                    except Exception:
                        record.fx_rate = 0

                record.cash_amount_valuation_currency = record.cash_amount * record.fx_rate

                balance_report = calculate_simple_balance_report(trn, portfolio_register)

                nav = 0

                for item in balance_report.items:

                    if item['market_value']:
                        nav = nav + item['market_value']

                record.nav_previous_day_valuation_currency = nav

                # n_shares_previous_day
                if previous:
                    record.n_shares_previous_day = previous.n_shares_end_of_the_day
                else:
                    record.n_shares_previous_day = 0

                record.n_shares_end_of_the_day = record.n_shares_previous_day + record.n_shares_added

                # dealing_price_valuation_currency here
                if trn.trade_price == 0 or trn.trade_price == None:
                    record.dealing_price_valuation_currency = record.nav_previous_day_valuation_currency / record.n_shares_previous_day
                else:
                    record.dealing_price_valuation_currency = trn.trade_price

                # n_shares_added here
                if trn.position_size_with_sign == 0 or trn.position_size_with_sign == None:
                    record.n_shares_added = record.cash_amount / record.dealing_price_valuation_currency
                else:
                    record.n_shares_added = trn.position_size_with_sign

                record.transaction_id = trn.id
                record.complex_transaction_id = trn.complex_transaction_id
                record.portfolio_register_id = portfolio_register.id

                record.save()

                previous = record


    except Exception as e:

        _l.info('calculate_portfolio_register_record error %s' % e)
        _l.info(traceback.format_exc())
