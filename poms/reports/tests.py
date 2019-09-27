import csv
import json
import logging
import math
import os
import random
import time
import zlib
from datetime import date, timedelta, datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.test import TestCase
from django.utils.functional import cached_property

from poms.accounts.models import AccountType, Account
from poms.counterparties.models import Counterparty, Responsible, CounterpartyGroup, ResponsibleGroup
from poms.currencies.models import Currency, CurrencyHistory
from poms.instruments.models import Instrument, PriceHistory, PricingPolicy, CostMethod, InstrumentType, \
    InstrumentClass, AccrualCalculationSchedule, AccrualCalculationModel, Periodicity, PaymentSizeDetail, \
    InstrumentFactorSchedule
from poms.portfolios.models import Portfolio
from poms.reports.builders.balance_item import ReportItem, Report
from poms.reports.builders.balance_pl import ReportBuilder
from poms.reports.builders.balance_virt_trn import VirtualTransaction
from poms.reports.builders.base_item import YTMMixin
from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, Strategy2Subgroup, \
    Strategy2, Strategy3Subgroup, Strategy3Group, Strategy3
from poms.transactions.models import Transaction, TransactionClass, TransactionType, ComplexTransaction
from poms.users.models import MasterUser, Member

_l = logging.getLogger('poms.reports')


def load_from_csv(master_user, instr, instr_price_hist, ccy_fx_rate, trn):
    _l.debug('load from csv: instr=%s, instr_price_hist=%s, ccy_fx_rate=%s, trn=%s',
             instr, instr_price_hist, ccy_fx_rate, trn)

    pricing_policy = PricingPolicy.objects.filter(master_user=master_user).first()

    account_type = AccountType.objects.get(master_user=master_user, user_code='-')
    account_type_wdetails = AccountType.objects.create(master_user=master_user, name='wdatails',
                                                       show_transaction_details=True)
    strategy1_subgroup = Strategy1Subgroup.objects.get(master_user=master_user, user_code='-')
    strategy2_subgroup = Strategy2Subgroup.objects.get(master_user=master_user, user_code='-')
    strategy3_subgroup = Strategy3Subgroup.objects.get(master_user=master_user, user_code='-')
    counterparty_group = CounterpartyGroup.objects.get(master_user=master_user, user_code='-')
    responsible_group = ResponsibleGroup.objects.get(master_user=master_user, user_code='-')

    transaction_class_maps = {
        'Buy': TransactionClass.objects.get(pk=TransactionClass.BUY),
        'Sell': TransactionClass.objects.get(pk=TransactionClass.SELL),
        'FX Trade': TransactionClass.objects.get(pk=TransactionClass.FX_TRADE),
        'Instrument PL': TransactionClass.objects.get(pk=TransactionClass.INSTRUMENT_PL),
        'Transaction PL': TransactionClass.objects.get(pk=TransactionClass.TRANSACTION_PL),
        'Transfer': TransactionClass.objects.get(pk=TransactionClass.TRANSFER),
        'FX Transfer': TransactionClass.objects.get(pk=TransactionClass.FX_TRANSFER),
        'Cash-In': TransactionClass.objects.get(pk=TransactionClass.CASH_INFLOW),
        'Cash-Out': TransactionClass.objects.get(pk=TransactionClass.CASH_OUTFLOW),
    }

    def _float(s):
        if not s:
            return 0.0
        s = s.replace(',', '.')
        s = s.replace(' ', '')
        s = s.replace('\xa0', '')
        return float(s)

    def _int(s):
        return int(_float(s))

    def _bool(s):
        if s == 'ЛОЖЬ':
            return False
        elif s == 'ИСТИНА':
            return True
        return bool(s)

    def _date(s):
        if not s:
            return date.max
        return datetime.strptime(s, "%Y-%m-%d").date()

    def _portfolio(user_code):
        obj, created = Portfolio.objects.get_or_create(
            master_user=master_user,
            user_code=user_code
        )
        return obj

    def _account(user_code):
        if user_code in ['Acc-Details-1', 'Acc-Details-2']:
            atype = account_type_wdetails
        else:
            atype = account_type
        obj, created = Account.objects.get_or_create(
            master_user=master_user,
            user_code=user_code,
            defaults={
                'type': atype,
            }
        )
        return obj

    def _strategy1(user_code):
        obj, created = Strategy1.objects.get_or_create(
            master_user=master_user,
            user_code=user_code,
            defaults={
                'subgroup': strategy1_subgroup,
            }
        )
        return obj

    def _strategy2(user_code):
        obj, created = Strategy2.objects.get_or_create(
            master_user=master_user,
            user_code=user_code,
            defaults={
                'subgroup': strategy2_subgroup,
            }
        )
        return obj

    def _strategy3(user_code):
        obj, created = Strategy3.objects.get_or_create(
            master_user=master_user,
            user_code=user_code,
            defaults={
                'subgroup': strategy3_subgroup,
            }
        )
        return obj

    def _counterparty(user_code):
        obj, created = Counterparty.objects.get_or_create(
            master_user=master_user,
            user_code=user_code,
            defaults={
                'group': counterparty_group,
            }
        )
        return obj

    def _responsible(user_code):
        obj, created = Responsible.objects.get_or_create(
            master_user=master_user,
            user_code=user_code,
            defaults={
                'group': responsible_group,
            }
        )
        return obj

    def _create_intr(data):
        # _l.debug('create instrument: %s', data)
        o = Instrument()
        o.master_user = master_user
        o.user_code = data['id']
        o.instrument_type = InstrumentType.objects.get(master_user=master_user, user_code='-')
        o.pricing_currency = Currency.objects.get(master_user=master_user, user_code=data['pricing_currency'])
        o.price_multiplier = _float(data['price_multiplier'])
        o.accrued_currency = Currency.objects.get(master_user=master_user, user_code=data['accrued_currency'])
        o.accrued_multiplier = _float(data['accrued_multiplier'])
        o.default_price = _float(data['default_price'])
        o.default_accrued = _float(data['default_accrued'])
        o.maturity_date = _date(data['maturity_date'])
        o.maturity_price = _float(data['maturity_price'])
        o.payment_size_detail = PaymentSizeDetail.objects.get(id=PaymentSizeDetail.PERCENT)
        o.save()
        return o

    def _create_instr_price_hist(data):
        # _l.debug('create price history: %s', data)
        o = PriceHistory()
        o.instrument = Instrument.objects.get(master_user=master_user, user_code=data['instrument'])
        o.pricing_policy = pricing_policy
        o.date = _date(data['date'])
        o.principal_price = _float(data['principal_price'])
        o.accrued_price = _float(data['accrued_price'])
        o.save()
        return o

    def _create_ccy_fx_rate(data):
        # _l.debug('create currency history: %s', data)
        o = CurrencyHistory()
        o.currency = Currency.objects.get(master_user=master_user, user_code=data['currency'])
        o.pricing_policy = pricing_policy
        o.date = _date(data['date'])
        o.fx_rate = _float(data['fx_rate'])
        o.save()
        return o

    def _create_trn(data):
        # _l.debug('create transaction: %s', data)

        o = Transaction()
        o.master_user = master_user
        o.transaction_code = _int(data['transaction_code'])
        o.transaction_class = transaction_class_maps[data['transaction_class']]
        o.instrument = Instrument.objects.get(master_user=master_user, user_code=data['instrument'])
        o.transaction_currency = Currency.objects.get(master_user=master_user, user_code=data['transaction_currency'])
        o.position_size_with_sign = _float(data['position_size_with_sign'])
        o.settlement_currency = Currency.objects.get(master_user=master_user, user_code=data['settlement_currency'])
        o.cash_consideration = _float(data['cash_consideration'])
        o.principal_with_sign = _float(data['principal_with_sign'])
        o.carry_with_sign = _float(data['carry_with_sign'])
        o.overheads_with_sign = _float(data['overheads_with_sign'])
        # o.transaction_date = _date(data['transaction_date'])
        o.accounting_date = _date(data['accounting_date'])
        o.cash_date = _date(data['cash_date'])
        o.portfolio = _portfolio(data['portfolio'])
        o.account_position = _account(data['account_position'])
        o.account_cash = _account(data['account_cash'])
        o.account_interim = _account(data['account_interim'])
        o.strategy1_position = _strategy1(data['strategy1_position'])
        o.strategy1_cash = _strategy1(data['strategy1_cash'])
        o.strategy2_position = _strategy2(data['strategy2_position'])
        o.strategy2_cash = _strategy2(data['strategy2_cash'])
        o.strategy3_position = _strategy3(data['strategy3_position'])
        o.strategy3_cash = _strategy3(data['strategy3_cash'])
        o.responsible = _responsible(data['responsible'])
        o.counterparty = _counterparty(data['counterparty'])
        o.linked_instrument = Instrument.objects.get(master_user=master_user, user_code=data['linked_instrument'])
        o.allocation_balance = Instrument.objects.get(master_user=master_user, user_code=data['allocation_balance'])
        o.allocation_pl = Instrument.objects.get(master_user=master_user, user_code=data['allocation_pl'])
        o.reference_fx_rate = _float(data['reference_fx_rate'])
        o.is_locked = _bool(data['is_locked'] == 'ЛОЖЬ')
        o.factor = _float(data['factor'])
        o.trade_price = _float(data['trade_price'])
        o.position_amount = _float(data['position_amount'])
        o.principal_amount = _float(data['principal_amount'])
        o.carry_amount = _float(data['carry_amount'])
        o.overheads = _float(data['overheads'])
        o.notes = data['notes']
        o.save()
        return o

    def _read(file_name, row_handler):
        delimiter = ';'
        quotechar = '"'
        # with open(file_name, mode='rt', encoding='utf-8') as csvfile:
        #     _l.info('-' * 10)
        #     _l.info(file_name)
        #
        #     reader = csv.reader(csvfile, delimiter=delimiter, quotechar=quotechar)
        #     for row in reader:
        #         _l.info('b=%s, data=%s' % (bool(row), row))
        #         if callable(row_handler):
        #             row_handler(row)

        with open(file_name, mode='rt', encoding='utf-8') as csvfile:
            # _l.debug('-' * 10)
            reader = csv.DictReader(csvfile, delimiter=delimiter, quotechar=quotechar)
            for row in reader:
                if all(not v for v in row.values()):
                    continue
                row = {k.lower(): v for k, v in row.items() if k}
                # _l.debug('%s', row)
                if callable(row_handler):
                    row_handler(row)

    if instr:
        _read(instr, _create_intr)
    if instr_price_hist:
        _read(instr_price_hist, _create_instr_price_hist)
    if ccy_fx_rate:
        _read(ccy_fx_rate, _create_ccy_fx_rate)
    if trn:
        _read(trn, _create_trn)


class ReportTestCase(TestCase):
    TRN_COLS_ALL = [
        # 'lid',
        'pk',
        # 'is_cloned',
        'is_hidden',
        # 'is_mismatch',
        'trn_code',
        'trn_cls',
        'instr',
        'trn_ccy',
        'pricing_ccy',
        'notes',
        'stl_ccy',
        'pos_size',
        # 'avco_multiplier',
        # 'avco_closed_by',
        # 'avco_rolling_pos_size',
        # 'fifo_multiplier',
        # 'fifo_closed_by',
        # 'fifo_rolling_pos_size',
        'multiplier',
        # 'closed_by',
        'rolling_pos_size',
        'balance_pos_size',
        'remaining_pos_size',
        'remaining_pos_size_percent',
        'cash',
        'principal',
        'carry',
        'overheads',
        'ref_fx',
        'trn_date',
        'acc_date',
        'cash_date',
        'prtfl',
        'acc_pos',
        'acc_cash',
        'acc_interim',
        'str1_pos',
        'str1_cash',
        'str2_pos',
        'str2_cash',
        'str3_pos',
        'str3_cash',
        'link_instr',
        'alloc_bl',
        'alloc_pl',
        'trade_price',
        'case',
        'report_ccy_cur',
        'report_ccy_cur_fx',
        'report_ccy_cash_hist',
        'report_ccy_cash_hist_fx',
        'report_ccy_acc_hist',
        'report_ccy_acc_hist_fx',
        'instr_price_cur',
        'instr_price_cur_principal_price',
        'instr_price_cur_accrued_price',
        'instr_pricing_ccy_cur',
        'instr_pricing_ccy_cur_fx',
        'instr_accrued_ccy_cur',
        'instr_accrued_ccy_cur_fx',
        'trn_ccy_cash_hist',
        'trn_ccy_cash_hist_fx',
        'trn_ccy_acc_hist',
        'trn_ccy_acc_hist_fx',
        'trn_ccy_cur',
        'trn_ccy_cur_fx',
        'stl_ccy_cash_hist',
        'stl_ccy_cash_hist_fx',
        'stl_ccy_acc_hist',
        'stl_ccy_acc_hist_fx',
        'stl_ccy_cur',
        'stl_ccy_cur_fx',
        'mismatch',
        'instr_principal',
        'instr_principal_res',
        'instr_accrued',
        'instr_accrued_res',
        'gross_cost_res',
        'net_cost_res',
        'principal_invested_res',
        'amount_invested_res',
        'ytm',
        'time_invested_days',
        'time_invested',
        'weighted_ytm',
        'weighted_time_invested_days',
        'weighted_time_invested',
        'cash_res',
        'total',

        'pl_fx_mul',
        'pl_fixed_mul',
        'principal_res',
        'carry_res',
        'overheads_res',
        'total_res',
        'principal_closed_res',
        'carry_closed_res',
        'overheads_closed_res',
        'total_closed_res',
        'principal_opened_res',
        'carry_opened_res',
        'overheads_opened_res',
        'total_opened_res',
        'principal_fx_res',
        'carry_fx_res',
        'overheads_fx_res',
        'total_fx_res',
        'principal_fx_closed_res',
        'carry_fx_closed_res',
        'overheads_fx_closed_res',
        'total_fx_closed_res',
        'principal_fx_opened_res',
        'carry_fx_opened_res',
        'overheads_fx_opened_res',
        'total_fx_opened_res',
        'principal_fixed_res',
        'carry_fixed_res',
        'overheads_fixed_res',
        'total_fixed_res',
        'principal_fixed_closed_res',
        'carry_fixed_closed_res',
        'overheads_fixed_closed_res',
        'total_fixed_closed_res',
        'principal_fixed_opened_res',
        'carry_fixed_opened_res',
        'overheads_fixed_opened_res',
        'total_fixed_opened_res',

        'pl_fx_mul_loc',
        'pl_fixed_mul_loc',
        'principal_loc',
        'carry_loc',
        'overheads_loc',
        'total_loc',
        'principal_closed_loc',
        'carry_closed_loc',
        'overheads_closed_loc',
        'total_closed_loc',
        'principal_opened_loc',
        'carry_opened_loc',
        'overheads_opened_loc',
        'total_opened_loc',
        'principal_fx_loc',
        'carry_fx_loc',
        'overheads_fx_loc',
        'total_fx_loc',
        'principal_fx_closed_loc',
        'carry_fx_closed_loc',
        'overheads_fx_closed_loc',
        'total_fx_closed_loc',
        'principal_fx_opened_loc',
        'carry_fx_opened_loc',
        'overheads_fx_opened_loc',
        'total_fx_opened_loc',
        'pl_fixed_mul',
        'principal_fixed_loc',
        'carry_fixed_loc',
        'overheads_fixed_loc',
        'total_fixed_loc',
        'principal_fixed_closed_loc',
        'carry_fixed_closed_loc',
        'overheads_fixed_closed_loc',
        'total_fixed_closed_loc',
        'principal_fixed_opened_loc',
        'carry_fixed_opened_loc',
        'overheads_fixed_opened_loc',
        'total_fixed_opened_loc', ]

    TRN_COLS_MINI = [
        # 'is_cloned',
        # 'lid',
        'pk',
        # 'is_hidden',
        # 'is_mismatch',
        'trn_code',
        'trn_cls',
        # 'avco_multiplier',
        # 'avco_closed_by',
        # 'avco_rolling_pos_size',
        # 'fifo_multiplier',
        # 'fifo_closed_by',
        # 'fifo_rolling_pos_size',
        # 'multiplier',
        # 'closed_by',
        # 'balance_pos_size',
        # 'rolling_pos_size',
        # 'remaining_pos_size',
        # 'remaining_pos_size_percent',
        'instr',
        'trn_ccy',
        'notes',
        'pos_size',
        'stl_ccy',
        'cash',
        'principal',
        'carry',
        # 'overheads',
        # 'ref_fx',
        # 'trn_date',
        # 'acc_date',
        # 'cash_date',
        # 'prtfl',
        # 'acc_pos',
        # 'acc_cash',
        # 'acc_interim',
        # 'str1_pos',
        # 'str1_cash',
        # 'str2_pos',
        # 'str2_cash',
        # 'str3_pos',
        # 'str3_cash',
        # 'link_instr',
        # 'alloc_bl',
        # 'alloc_pl',
        # 'trade_price',
        # 'notes',
        # 'case',
        # 'report_ccy_cur',
        # 'report_ccy_cur_fx',
        # 'report_ccy_cash_hist',
        # 'report_ccy_cash_hist_fx',
        # 'report_ccy_acc_hist',
        # 'report_ccy_acc_hist_fx',
        # 'instr_price_cur',
        # 'instr_price_cur_principal_price',
        # 'instr_price_cur_accrued_price',
        # 'instr_pricing_ccy_cur',
        # 'instr_pricing_ccy_cur_fx',
        # 'instr_accrued_ccy_cur',
        # 'instr_accrued_ccy_cur_fx',
        # 'trn_ccy_cash_hist',
        # 'trn_ccy_cash_hist_fx',
        # 'trn_ccy_acc_hist',
        # 'trn_ccy_acc_hist_fx',
        # 'trn_ccy_cur',
        # 'trn_ccy_cur_fx',
        # 'stl_ccy_cash_hist',
        # 'stl_ccy_cash_hist_fx',
        # 'stl_ccy_acc_hist',
        # 'stl_ccy_acc_hist_fx',
        # 'stl_ccy_cur',
        # 'stl_ccy_cur_fx',
        # 'mismatch',
        # 'instr_principal',
        # 'instr_principal_res',
        # 'instr_accrued',
        # 'instr_accrued_res',
        # 'gross_cost_res',
        # 'net_cost_res',
        # 'principal_invested_res',
        # 'amount_invested_res',
        # 'ytm',
        # 'time_invested_days',
        # 'time_invested',
        # 'weighted_ytm',
        # 'weighted_time_invested_days',
        # 'weighted_time_invested',
        # 'cash_res',
        # 'total',
        'principal_res',
        'carry_res',
        # 'overheads_res',
        # 'total_res',
        'principal_closed_res',
        'carry_closed_res',
        # 'overheads_closed_res',
        # 'total_closed_res',
        'principal_opened_res',
        'carry_opened_res',
        # 'overheads_opened_res',
        # 'total_opened_res',
        # 'pl_fx_mul',
        # 'principal_fx_res',
        # 'carry_fx_res',
        # 'overheads_fx_res',
        # 'total_fx_res',
        # 'principal_fx_closed_res',
        # 'carry_fx_closed_res',
        # 'overheads_fx_closed_res',
        # 'total_fx_closed_res',
        # 'principal_fx_opened_res',
        # 'carry_fx_opened_res',
        # 'overheads_fx_opened_res',
        # 'total_fx_opened_res',
        # 'pl_fixed_mul',
        # 'principal_fixed_res',
        # 'carry_fixed_res',
        # 'overheads_fixed_res',
        # 'total_fixed_res',
        # 'principal_fixed_closed_res',
        # 'carry_fixed_closed_res',
        # 'overheads_fixed_closed_res',
        # 'total_fixed_closed_res',
        # 'principal_fixed_opened_res',
        # 'carry_fixed_opened_res',
        # 'overheads_fixed_opened_res',
        # 'total_fixed_opened_res',
    ]
    TRN_COLS = TRN_COLS_MINI

    ITEM_COLS_ALL = [
        # 'is_cloned',
        'type_code',
        'subtype_code',
        'user_code',
        'short_name',
        'name',
        # 'trn',
        'instr',
        'ccy',
        'notes',
        'trn_ccy',
        'prtfl',
        'acc',
        'str1',
        'str2',
        'str3',
        'src_trns_id',
        # 'custom_fields',
        # 'is_empty',
        'pricing_ccy',
        'last_notes',
        'mismatch',
        'mismatch_prtfl',
        'mismatch_acc',
        'alloc_bl',
        'alloc_pl',
        # 'report_ccy_cur',
        'report_ccy_cur_fx',
        # 'instr_price_cur',
        'instr_price_cur_principal_price',
        'instr_price_cur_accrued_price',
        # 'instr_pricing_ccy_cur',
        'instr_pricing_ccy_cur_fx',
        # 'instr_accrued_ccy_cur',
        'instr_accrued_ccy_cur_fx',
        # 'ccy_cur',
        'ccy_cur_fx',
        # 'pricing_ccy_cur',
        'pricing_ccy_cur_fx',
        'instr_principal_res',
        'instr_accrued_res',
        'exposure_res',
        'exposure_loc',
        'instr_accrual',
        'instr_accrual_accrued_price',
        'pos_size',
        'market_value_res',
        'market_value_loc',
        'cost_res',
        'ytm',
        'modified_duration',
        'ytm_at_cost',
        'time_invested_days',
        'time_invested',
        'gross_cost_res',
        'gross_cost_loc',
        'net_cost_res',
        'net_cost_loc',
        'principal_invested_res',
        'principal_invested_loc',
        'amount_invested_res',
        'amount_invested_loc',
        'pos_return_res',
        'pos_return_loc',
        'net_pos_return_res',
        'net_pos_return_loc',
        'daily_price_change',
        'mtd_price_change',
        'principal_res',
        'carry_res',
        'overheads_res',
        'total_res',
        'principal_loc',
        'carry_loc',
        'overheads_loc',
        'total_loc',
        'principal_closed_res',
        'carry_closed_res',
        'overheads_closed_res',
        'total_closed_res',
        'principal_closed_loc',
        'carry_closed_loc',
        'overheads_closed_loc',
        'total_closed_loc',
        'principal_opened_res',
        'carry_opened_res',
        'overheads_opened_res',
        'total_opened_res',
        'principal_opened_loc',
        'carry_opened_loc',
        'overheads_opened_loc',
        'total_opened_loc',
        'principal_fx_res',
        'carry_fx_res',
        'overheads_fx_res',
        'total_fx_res',
        'principal_fx_loc',
        'carry_fx_loc',
        'overheads_fx_loc',
        'total_fx_loc',
        'principal_fx_closed_res',
        'carry_fx_closed_res',
        'overheads_fx_closed_res',
        'total_fx_closed_res',
        'principal_fx_closed_loc',
        'carry_fx_closed_loc',
        'overheads_fx_closed_loc',
        'total_fx_closed_loc',
        'principal_fx_opened_res',
        'carry_fx_opened_res',
        'overheads_fx_opened_res',
        'total_fx_opened_res',
        'principal_fx_opened_loc',
        'carry_fx_opened_loc',
        'overheads_fx_opened_loc',
        'total_fx_opened_loc',
        'principal_fixed_res',
        'carry_fixed_res',
        'overheads_fixed_res',
        'total_fixed_res',
        'principal_fixed_loc',
        'carry_fixed_loc',
        'overheads_fixed_loc',
        'total_fixed_loc',
        'principal_fixed_closed_res',
        'carry_fixed_closed_res',
        'overheads_fixed_closed_res',
        'total_fixed_closed_res',
        'principal_fixed_closed_loc',
        'carry_fixed_closed_loc',
        'overheads_fixed_closed_loc',
        'total_fixed_closed_loc',
        'principal_fixed_opened_res',
        'carry_fixed_opened_res',
        'overheads_fixed_opened_res',
        'total_fixed_opened_res',
        'principal_fixed_opened_loc',
        'carry_fixed_opened_loc',
        'overheads_fixed_opened_loc',
        'total_fixed_opened_loc',
    ]

    ITEM_COLS_MINI = [
        # 'is_cloned',
        'type_code',
        # 'subtype_code',
        # 'trn',
        'user_code',
        'short_name',
        'name',
        'instr',
        'ccy',
        'notes',
        # 'trn_ccy',
        # 'prtfl',
        # 'acc',
        # 'str1',
        # 'str2',
        # 'str3',
        'src_trns_id',
        # 'custom_fields',
        # 'is_empty',
        # 'pricing_ccy',
        # 'last_notes',
        # 'mismatch',
        # 'mismatch_prtfl',
        # 'mismatch_acc',
        'alloc_bl',
        'alloc_pl',
        'pos_size',
        # 'market_value_res',
        # 'report_ccy_cur',
        # 'report_ccy_cur_fx',
        # 'instr_price_cur',
        # 'instr_price_cur_principal_price',
        # 'instr_price_cur_accrued_price',
        # 'instr_pricing_ccy_cur',
        # 'instr_pricing_ccy_cur_fx',
        # 'instr_accrued_ccy_cur',
        # 'instr_accrued_ccy_cur_fx',
        # 'ccy_cur',
        # 'ccy_cur_fx',
        # 'pricing_ccy_cur',
        # 'pricing_ccy_cur_fx',
        # 'instr_principal_res',
        # 'instr_accrued_res',
        # 'exposure_res',
        # 'exposure_loc',
        # 'instr_accrual',
        # 'instr_accrual_accrued_price',
        # 'market_value_loc',
        # 'cost_res',
        # 'ytm',
        # 'modified_duration',
        # 'ytm_at_cost',
        # 'time_invested_days',
        # 'time_invested',
        # 'gross_cost_res',
        # 'gross_cost_loc',
        # 'net_cost_res',
        # 'net_cost_loc',
        # 'principal_invested_res',
        # 'principal_invested_loc',
        # 'amount_invested_res',
        # 'amount_invested_loc',
        # 'pos_return_res',
        # 'pos_return_loc',
        # 'net_pos_return_res',
        # 'net_pos_return_loc',
        # 'daily_price_change',
        # 'mtd_price_change',
        'principal_res',
        'carry_res',
        # 'overheads_res',
        # 'total_res',
        # 'principal_loc',
        # 'carry_loc',
        # 'overheads_loc',
        # 'total_loc',
        'principal_closed_res',
        'carry_closed_res',
        # 'overheads_closed_res',
        # 'total_closed_res',
        # 'principal_closed_loc',
        # 'carry_closed_loc',
        # 'overheads_closed_loc',
        # 'total_closed_loc',
        'principal_opened_res',
        'carry_opened_res',
        # 'overheads_opened_res',
        # 'total_opened_res',
        # 'principal_opened_loc',
        # 'carry_opened_loc',
        # 'overheads_opened_loc',
        # 'total_opened_loc',
        # 'principal_fx_res',
        # 'carry_fx_res',
        # 'overheads_fx_res',
        # 'total_fx_res',
        # 'principal_fx_loc',
        # 'carry_fx_loc',
        # 'overheads_fx_loc',
        # 'total_fx_loc',
        # 'principal_fx_closed_res',
        # 'carry_fx_closed_res',
        # 'overheads_fx_closed_res',
        # 'total_fx_closed_res',
        # 'principal_fx_closed_loc',
        # 'carry_fx_closed_loc',
        # 'overheads_fx_closed_loc',
        # 'total_fx_closed_loc',
        # 'principal_fx_opened_res',
        # 'carry_fx_opened_res',
        # 'overheads_fx_opened_res',
        # 'total_fx_opened_res',
        # 'principal_fx_opened_loc',
        # 'carry_fx_opened_loc',
        # 'overheads_fx_opened_loc',
        # 'total_fx_opened_loc',
        # 'principal_fixed_res',
        # 'carry_fixed_res',
        # 'overheads_fixed_res',
        # 'total_fixed_res',
        # 'principal_fixed_loc',
        # 'carry_fixed_loc',
        # 'overheads_fixed_loc',
        # 'total_fixed_loc',
        # 'principal_fixed_closed_res',
        # 'carry_fixed_closed_res',
        # 'overheads_fixed_closed_res',
        # 'total_fixed_closed_res',
        # 'principal_fixed_closed_loc',
        # 'carry_fixed_closed_loc',
        # 'overheads_fixed_closed_loc',
        # 'total_fixed_closed_loc',
        # 'principal_fixed_opened_res',
        # 'carry_fixed_opened_res',
        # 'overheads_fixed_opened_res',
        # 'total_fixed_opened_res',
        # 'principal_fixed_opened_loc',
        # 'carry_fixed_opened_loc',
        # 'overheads_fixed_opened_loc',
        # 'total_fixed_opened_loc',
    ]
    ITEM_COLS = ITEM_COLS_MINI

    def setUp(self):
        # _l.debug('*' * 100)

        # if pandas:
        #     pandas.set_option('display.width', 10000)
        #     pandas.set_option('display.max_rows', 100)
        #     pandas.set_option('display.max_columns', 1000)
        #     pandas.set_option('precision', 4)
        #     pandas.set_option('display.float_format', '{:.4f}'.format)

        self.report_date = date(2016, 3, 1)

        user = User.objects.create_user('a1')
        self.m = MasterUser.objects.create_master_user(user=user, name='a1_m1')
        self.mm = Member.objects.create(master_user=self.m, user=user, is_owner=True, is_admin=True)

        self.pp = PricingPolicy.objects.create(master_user=self.m)

        self.usd = self.m.system_currency
        # self.eur, _ = Currency.objects.get_or_create(user_code='EUR', master_user=self.m, defaults={'name': 'EUR'})
        # self.chf, _ = Currency.objects.get_or_create(user_code='CHF', master_user=self.m, defaults={'name': 'CHF'})
        # self.cad, _ = Currency.objects.get_or_create(user_code='CAD', master_user=self.m, defaults={'name': 'CAD'})
        # self.mex, _ = Currency.objects.get_or_create(user_code='MEX', master_user=self.m, defaults={'name': 'MEX'})
        # self.rub, _ = Currency.objects.get_or_create(user_code='RUB', master_user=self.m, defaults={'name': 'RUB'})
        # self.gbp, _ = Currency.objects.get_or_create(user_code='GBP', master_user=self.m, defaults={'name': 'GBP'})
        self.eur = self._ccy('EUR')
        self.chf = self._ccy('CHF')
        self.cad = self._ccy('CAD')
        self.mex = self._ccy('MEX')
        self.rub = self._ccy('RUB')
        self.gbp = self._ccy('GBP')

        CurrencyHistory.objects.all().delete()
        for days in range(0, 29):
            d = self._d(days)
            # CurrencyHistory.objects.create(currency=self.eur, pricing_policy=self.pp, date=d, fx_rate=1.3)
            # CurrencyHistory.objects.create(currency=self.chf, pricing_policy=self.pp, date=d, fx_rate=0.9)
            # CurrencyHistory.objects.create(currency=self.cad, pricing_policy=self.pp, date=d, fx_rate=1.2)
            # CurrencyHistory.objects.create(currency=self.mex, pricing_policy=self.pp, date=d, fx_rate=0.15)
            # CurrencyHistory.objects.create(currency=self.rub, pricing_policy=self.pp, date=d, fx_rate=1.0 / 75.0)
            # CurrencyHistory.objects.create(currency=self.gbp, pricing_policy=self.pp, date=d, fx_rate=1.6)
            self._ccy_hist(self.eur, d, 1.3)
            self._ccy_hist(self.chf, d, 0.9)
            self._ccy_hist(self.cad, d, 1.2)
            self._ccy_hist(self.mex, d, 0.15)
            self._ccy_hist(self.rub, d, 1.0 / 75.0)
            self._ccy_hist(self.gbp, d, 1.6)

        d = self._d(30)
        # CurrencyHistory.objects.create(currency=self.eur, pricing_policy=self.pp, date=d, fx_rate=1.2)
        # CurrencyHistory.objects.create(currency=self.chf, pricing_policy=self.pp, date=d, fx_rate=0.8)
        # CurrencyHistory.objects.create(currency=self.cad, pricing_policy=self.pp, date=d, fx_rate=1.1)
        # CurrencyHistory.objects.create(currency=self.mex, pricing_policy=self.pp, date=d, fx_rate=0.1)
        # CurrencyHistory.objects.create(currency=self.rub, pricing_policy=self.pp, date=d, fx_rate=1.0 / 100.0)
        # CurrencyHistory.objects.create(currency=self.gbp, pricing_policy=self.pp, date=d, fx_rate=1.5)
        self._ccy_hist(self.eur, d, 1.2)
        self._ccy_hist(self.chf, d, 0.8)
        self._ccy_hist(self.cad, d, 1.1)
        self._ccy_hist(self.mex, d, 0.1)
        self._ccy_hist(self.rub, d, 1.0 / 100.0)
        self._ccy_hist(self.gbp, d, 1.5)

        # self.bond0 = Instrument.objects.create(master_user=self.m, name="bond0, USD/USD",
        #                                        instrument_type=self.m.instrument_type,
        #                                        pricing_currency=self.usd, price_multiplier=1.0,
        #                                        accrued_currency=self.usd, accrued_multiplier=1.0)
        # self.bond1 = Instrument.objects.create(master_user=self.m, name="bond1, CHF/CHF",
        #                                        instrument_type=self.m.instrument_type,
        #                                        pricing_currency=self.chf, price_multiplier=0.01,
        #                                        accrued_currency=self.chf, accrued_multiplier=0.01)
        # self.bond2 = Instrument.objects.create(master_user=self.m, name="bond2, USD/USD",
        #                                        instrument_type=self.m.instrument_type,
        #                                        pricing_currency=self.usd, price_multiplier=0.01,
        #                                        accrued_currency=self.usd, accrued_multiplier=0.01)
        # self.bond3 = Instrument.objects.create(master_user=self.m, name="bond3, USD/USD",
        #                                        instrument_type=self.m.instrument_type,
        #                                        pricing_currency=self.usd, price_multiplier=0.01,
        #                                        accrued_currency=self.usd, accrued_multiplier=0.01)
        #
        # self.stock0 = Instrument.objects.create(master_user=self.m, name="stock1, USD/RUB",
        #                                         instrument_type=self.m.instrument_type,
        #                                         pricing_currency=self.usd, price_multiplier=1.0,
        #                                         accrued_currency=self.usd, accrued_multiplier=1.0)
        # self.stock1 = Instrument.objects.create(master_user=self.m, name="stock1, GBP/RUB",
        #                                         instrument_type=self.m.instrument_type,
        #                                         pricing_currency=self.gbp, price_multiplier=1.0,
        #                                         accrued_currency=self.rub, accrued_multiplier=1.0)
        # self.stock2 = Instrument.objects.create(master_user=self.m, name="stock2, USD/USD",
        #                                         instrument_type=self.m.instrument_type,
        #                                         pricing_currency=self.usd, price_multiplier=1.0,
        #                                         accrued_currency=self.usd, accrued_multiplier=1.0)
        self.bond0 = self._instr('bond0', pricing_ccy=self.usd, price_mult=1.0, accrued_ccy=self.usd, accrued_mult=1.0)
        self.bond01 = self._instr('bond01', pricing_ccy=self.usd, price_mult=1.0, accrued_ccy=self.usd,
                                  accrued_mult=1.0)
        self.bond1 = self._instr('bond1', pricing_ccy=self.chf, price_mult=0.01, accrued_ccy=self.chf,
                                 accrued_mult=0.01)
        self.bond2 = self._instr('bond2', pricing_ccy=self.usd, price_mult=0.01, accrued_ccy=self.usd,
                                 accrued_mult=0.01)
        self.bond3 = self._instr('bond3', pricing_ccy=self.usd, price_mult=0.01, accrued_ccy=self.usd,
                                 accrued_mult=0.01)
        self.stock0 = self._instr('stock0', pricing_ccy=self.usd, price_mult=1.0, accrued_ccy=self.usd,
                                  accrued_mult=1.0)
        self.stock1 = self._instr('stock1', pricing_ccy=self.gbp, price_mult=1.0, accrued_ccy=self.rub,
                                  accrued_mult=1.0)
        self.stock2 = self._instr('stock2', pricing_ccy=self.usd, price_mult=1.0, accrued_ccy=self.usd,
                                  accrued_mult=1.0)
        self.stock3 = self._instr('stock3', pricing_ccy=self.usd, price_mult=1.0, accrued_ccy=self.usd,
                                  accrued_mult=1.0)

        PriceHistory.objects.all().delete()
        for days in range(0, 29):
            d = self._d(days)
            # PriceHistory.objects.create(instrument=self.bond0, pricing_policy=self.pp, date=d, principal_price=1.0, accrued_price=1.0)
            # PriceHistory.objects.create(instrument=self.bond1, pricing_policy=self.pp, date=d, principal_price=20., accrued_price=0.5)
            # PriceHistory.objects.create(instrument=self.bond2, pricing_policy=self.pp, date=d, principal_price=20., accrued_price=0.5)
            # PriceHistory.objects.create(instrument=self.stock1, pricing_policy=self.pp, date=d, principal_price=1.5, accrued_price=2.0)
            # PriceHistory.objects.create(instrument=self.stock2, pricing_policy=self.pp, date=d, principal_price=1.5, accrued_price=2.0)
            self._instr_hist(self.bond0, d, 1.0, 1.0)
            self._instr_hist(self.bond1, d, 20.0, 0.5)
            self._instr_hist(self.bond2, d, 20.0, 0.5)
            self._instr_hist(self.stock1, d, 1.5, 2.0)
            self._instr_hist(self.stock2, d, 1.5, 2.0)

        self.at1 = AccountType.objects.create(master_user=self.m, name='at1', show_transaction_details=False)
        self.at2 = AccountType.objects.create(master_user=self.m, name='at2', show_transaction_details=False)
        self.at3 = AccountType.objects.create(master_user=self.m, name='at3', show_transaction_details=True)
        self.a1_1 = Account.objects.create(master_user=self.m, name='a1_1', type=self.at1)
        self.a1_2 = Account.objects.create(master_user=self.m, name='a1_2', type=self.at1)
        self.a2_3 = Account.objects.create(master_user=self.m, name='a2_3', type=self.at2)
        self.a3_4 = Account.objects.create(master_user=self.m, name='a3_4', type=self.at3)

        self.p1 = Portfolio.objects.create(master_user=self.m, name='p1')
        self.p2 = Portfolio.objects.create(master_user=self.m, name='p2')
        self.p3 = Portfolio.objects.create(master_user=self.m, name='p3')
        self.p4 = Portfolio.objects.create(master_user=self.m, name='p4')

        self.mismatch_p = Portfolio.objects.create(master_user=self.m, name='mismatch-prtfl')
        self.mismatch_a = Account.objects.create(master_user=self.m, name='mismatch-acc', type=self.m.account_type)
        self.m.mismatch_portfolio = self.mismatch_p
        self.m.mismatch_account = self.mismatch_a
        self.m.save()

        self.s1_1 = Strategy1Group.objects.create(master_user=self.m, name='1')
        self.s1_1_1 = Strategy1Subgroup.objects.create(master_user=self.m, group=self.s1_1, name='1-1')
        self.s1_1_1_1 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_1_1, name='1-1-1')
        self.s1_1_1_2 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_1_1, name='1-1-2')
        self.s1_1_1_3 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_1_1, name='1-1-3')
        self.s1_1_1_4 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_1_1, name='1-1-4')
        self.s1_1_2 = Strategy1Subgroup.objects.create(master_user=self.m, group=self.s1_1, name='1-2')
        self.s1_1_2_1 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_1_2, name='1-2-1')
        self.s1_1_2_2 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_1_2, name='1-2-2')
        self.s1_1_2_3 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_1_2, name='1-2-3')
        self.s1_1_2_4 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_1_2, name='1-2-4')
        self.s1_2 = Strategy1Group.objects.create(master_user=self.m, name='2')
        self.s1_2_1 = Strategy1Subgroup.objects.create(master_user=self.m, group=self.s1_2, name='2-1')
        self.s1_2_1_1 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_2_1, name='2-1-1')
        self.s1_2_1_2 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_2_1, name='2-1-2')
        self.s1_2_1_3 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_2_1, name='2-1-3')
        self.s1_2_1_4 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_2_1, name='2-1-4')
        self.s1_2_2 = Strategy1Subgroup.objects.create(master_user=self.m, group=self.s1_2, name='2-2')
        self.s1_2_2_1 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_2_2, name='2-2-1')
        self.s1_2_2_2 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_2_2, name='2-2-2')
        self.s1_2_2_3 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_2_2, name='2-2-3')
        self.s1_2_2_4 = Strategy1.objects.create(master_user=self.m, subgroup=self.s1_2_2, name='2-2-4')

        self.s2_1 = Strategy2Group.objects.create(master_user=self.m, name='1')
        self.s2_1_1 = Strategy2Subgroup.objects.create(master_user=self.m, group=self.s2_1, name='1-1')
        self.s2_1_1_1 = Strategy2.objects.create(master_user=self.m, subgroup=self.s2_1_1, name='1-1-1')
        self.s2_1_1_2 = Strategy2.objects.create(master_user=self.m, subgroup=self.s2_1_1, name='1-1-2')
        self.s2_1_1_3 = Strategy2.objects.create(master_user=self.m, subgroup=self.s2_1_1, name='1-1-3')

        self.s3_1 = Strategy3Group.objects.create(master_user=self.m, name='1')
        self.s3_1_1 = Strategy3Subgroup.objects.create(master_user=self.m, group=self.s3_1, name='1-1')
        self.s3_1_1_1 = Strategy3.objects.create(master_user=self.m, subgroup=self.s3_1_1, name='1-1-1')
        self.s3_1_1_2 = Strategy3.objects.create(master_user=self.m, subgroup=self.s3_1_1, name='1-1-2')
        self.s3_1_1_3 = Strategy3.objects.create(master_user=self.m, subgroup=self.s3_1_1, name='1-1-3')

        # for g_i in range(0, 10):
        #     g = Strategy1Group.objects.create(master_user=self.m, name='%s' % (g_i,))
        #     setattr(self, 's1_%s' % (g_i,), g)
        #     for sg_i in range(0, 10):
        #         sg = Strategy1Subgroup.objects.create(master_user=self.m, group=g, name='%s-%s' % (g_i, sg_i))
        #         setattr(self, 's1_%s_%s' % (g_i, sg_i), sg)
        #         for s_i in range(0, 10):
        #             s = Strategy1.objects.create(master_user=self.m, subgroup=sg, name='%s-%s-%s' % (g_i, sg_i, s_i))
        #             setattr(self, 's1_%s_%s_%s' % (g_i, sg_i, s_i), s)

        # from django.conf import settings
        # settings.DEBUG = True
        pass

    def _ccy(self, code, attr=None):
        val, created = Currency.objects.get_or_create(user_code=code, master_user=self.m, defaults={'name': code})
        if attr:
            setattr(self, attr, val)
        return val

    def _instr(self, code, instr_type=None, pricing_ccy=None, price_mult=1.0, accrued_ccy=None, accrued_mult=1.0,
               maturity_date=date.max, maturity_price=0.0, code_fmt='%(code)s %(pricing_ccy)s/%(accrued_ccy)s'):
        instr_type = instr_type or self.m.instrument_type
        pricing_ccy = pricing_ccy or self.usd
        accrued_ccy = accrued_ccy or self.usd
        return Instrument.objects.create(
            master_user=self.m,
            name=code_fmt % {
                'code': code,
                'pricing_ccy': pricing_ccy.user_code,
                'accrued_ccy': accrued_ccy.user_code,
            },
            instrument_type=instr_type,
            pricing_currency=pricing_ccy,
            price_multiplier=price_mult,
            accrued_currency=accrued_ccy,
            accrued_multiplier=accrued_mult,
            maturity_date=maturity_date,
            maturity_price=maturity_price,
        )

    def _instr_hist(self, instr, d, principal_price, accrued_price):
        return PriceHistory.objects.create(instrument=instr, pricing_policy=self.pp, date=d,
                                           principal_price=principal_price, accrued_price=accrued_price)

    def _ccy_hist(self, ccy, d, fx):
        return CurrencyHistory.objects.create(currency=ccy, pricing_policy=self.pp, date=d, fx_rate=fx)

    def _d(self, days=None):
        if isinstance(days, date):
            return days
        if days is None or days == 0:
            return self.report_date
        else:
            return self.report_date + timedelta(days=days)

    def _t(self, t_class=None, p=None, instr=None, trn_ccy=None, position=0.0,
           stl_ccy=None, cash=None, principal=0.0, carry=0.0, overheads=0.0,
           acc_date=None, acc_date_days=None, cash_date=None, cash_date_days=None, days=-1,
           acc_pos=None, acc_cash=None, acc_interim=None, fx_rate=None,
           s1_pos=None, s1_cash=None, s2_pos=None, s2_cash=None, s3_pos=None, s3_cash=None,
           link_instr=None, alloc_bl=None, alloc_pl=None, notes=None,
           save=True):

        if stl_ccy is None:
            stl_ccy = self.usd
        if trn_ccy is None:
            trn_ccy = stl_ccy

        t = Transaction()

        t.master_user = self.m
        t.transaction_class = t_class

        t.instrument = instr
        t.transaction_currency = trn_ccy
        t.position_size_with_sign = position

        t.settlement_currency = stl_ccy
        t.cash_consideration = cash if cash is not None else (principal + carry + overheads)
        t.principal_with_sign = principal
        t.carry_with_sign = carry
        t.overheads_with_sign = overheads

        t.accounting_date = acc_date if acc_date else self._d(acc_date_days if acc_date_days is not None else days)
        t.cash_date = cash_date if cash_date else self._d(cash_date_days if cash_date_days is not None else days)
        t.transaction_date = min(t.accounting_date, t.cash_date)

        t.portfolio = p or self.m.portfolio

        t.account_position = acc_pos or self.m.account
        t.account_cash = acc_cash or self.m.account
        t.account_interim = acc_interim or self.m.account

        t.strategy1_position = s1_pos or self.m.strategy1
        t.strategy1_cash = s1_cash or self.m.strategy1
        t.strategy2_position = s2_pos or self.m.strategy2
        t.strategy2_cash = s2_cash or self.m.strategy2
        t.strategy3_position = s3_pos or self.m.strategy3
        t.strategy3_cash = s3_cash or self.m.strategy3

        if fx_rate is None:
            if trn_ccy.id == stl_ccy.id:
                t.reference_fx_rate = 1.0
            else:
                t.reference_fx_rate = 0.0
        else:
            t.reference_fx_rate = fx_rate

        t.linked_instrument = link_instr or self.m.instrument
        t.allocation_balance = alloc_bl or self.m.instrument
        t.allocation_pl = alloc_pl or self.m.instrument

        t.notes = notes

        if save:
            t.save()

        return t

    def _t_cash_in(self, **kwargs):
        kwargs.setdefault('t_class', self._cash_inflow)
        return self._t(**kwargs)

    def _t_cash_out(self, **kwargs):
        kwargs.setdefault('t_class', self._cash_outflow)
        return self._t(**kwargs)

    def _t_buy(self, **kwargs):
        kwargs.setdefault('t_class', self._buy)
        return self._t(**kwargs)

    def _t_sell(self, **kwargs):
        kwargs.setdefault('t_class', self._sell)
        return self._t(**kwargs)

    def _t_instr_pl(self, **kwargs):
        kwargs.setdefault('t_class', self._instrument_pl)
        return self._t(**kwargs)

    def _t_trn_pl(self, **kwargs):
        kwargs.setdefault('t_class', self._transaction_pl)
        return self._t(**kwargs)

    def _t_fx_tade(self, **kwargs):
        kwargs.setdefault('t_class', self._fx_tade)
        return self._t(**kwargs)

    def _t_transfer(self, **kwargs):
        kwargs.setdefault('t_class', self._transfer)
        return self._t(**kwargs)

    def _t_fx_transfer(self, **kwargs):
        kwargs.setdefault('t_class', self._fx_transfer)
        return self._t(**kwargs)

    @cached_property
    def _cash_inflow(self):
        return TransactionClass.objects.get(id=TransactionClass.CASH_INFLOW)

    @cached_property
    def _cash_outflow(self):
        return TransactionClass.objects.get(id=TransactionClass.CASH_OUTFLOW)

    @cached_property
    def _buy(self):
        return TransactionClass.objects.get(id=TransactionClass.BUY)

    @cached_property
    def _sell(self):
        return TransactionClass.objects.get(id=TransactionClass.SELL)

    @cached_property
    def _instrument_pl(self):
        return TransactionClass.objects.get(id=TransactionClass.INSTRUMENT_PL)

    @cached_property
    def _transaction_pl(self):
        return TransactionClass.objects.get(id=TransactionClass.TRANSACTION_PL)

    @cached_property
    def _fx_tade(self):
        return TransactionClass.objects.get(id=TransactionClass.FX_TRADE)

    @cached_property
    def _transfer(self):
        return TransactionClass.objects.get(id=TransactionClass.TRANSFER)

    @cached_property
    def _fx_transfer(self):
        return TransactionClass.objects.get(id=TransactionClass.FX_TRANSFER)

    @cached_property
    def _avco(self):
        return CostMethod.objects.get(pk=CostMethod.AVCO)

    @cached_property
    def _fifo(self):
        return CostMethod.objects.get(pk=CostMethod.FIFO)

    def _sdump(self, builder, name, show_trns=True, show_items=True, trn_cols=None, item_cols=None,
               trn_filter=None, in_csv=False):
        transpose = True
        showindex = 'always'
        if show_trns or show_items:
            s = 'Report: %s\n' % (
                name,
            )
            if show_trns:
                trn_cols = trn_cols or self.TRN_COLS
                s += '\nVirtual transactions: \n%s\n' % (
                    VirtualTransaction.sdumps(builder.transactions, columns=trn_cols, filter=trn_filter,
                                              in_csv=in_csv, transpose=transpose, showindex=showindex)
                )

            if show_items:
                item_cols = item_cols or self.ITEM_COLS
                s += '\nItems: \n%s\n' % (
                    ReportItem.sdumps(builder.instance.items, columns=item_cols, in_csv=in_csv, transpose=transpose,
                                      showindex=showindex)
                )
            return s
        return None

    def _dump(self, *args, **kwargs):
        for r in self._sdump(*args, **kwargs).splitlines():
            _l.info(r)
            # _l.info(self._sdump(*args, **kwargs))

    def _sdump_hist(self, days=None, ccys=True, instrs=True, in_csv=False):
        s = ''
        if days:
            days = (
                self._d(days[0]) if days[0] is not None else date.min,
                self._d(days[1]) if days[1] is not None else date.max,
            )
        if ccys:
            ccys_hists = CurrencyHistory.objects.order_by('currency', 'date')
            if isinstance(ccys, (list, tuple)):
                ccys_hists = ccys_hists.filter(currency__in=ccys)
            if days:
                ccys_hists = ccys_hists.filter(date__range=days)
            s += '\nCurrency FX-Rates: \n%s\n' % (
                VirtualTransaction.sdumps(ccys_hists, columns=['id', 'currency', 'date', 'fx_rate'], in_csv=in_csv)
            )

        if instrs:
            instrs_price_hists = PriceHistory.objects.order_by('instrument', 'date', )
            if isinstance(instrs, (list, tuple)):
                instrs_price_hists = instrs_price_hists.filter(instrument__in=instrs)
            if days:
                instrs_price_hists = instrs_price_hists.filter(date__range=days)
            s += '\nInstrument pricing: \n%s\n' % (
                VirtualTransaction.sdumps(instrs_price_hists,
                                          columns=['id', 'instrument', 'date', 'principal_price', 'accrued_price'],
                                          in_csv=in_csv)
            )
        return s

    def _dump_hist(self, *args, **kwargs):
        for r in self._sdump_hist(*args, **kwargs).splitlines():
            _l.info(r)
            # _l.info(self._sdump_hist(*args, **kwargs))

    def _simple_run(self, name, result=None, trns=False, trn_cols=None, item_cols=None,
                    trn_dump_all=True, in_csv=False, build_balance_for_tests=False, **kwargs):
        _l.info('')
        _l.info('')
        _l.info('*' * 79)

        kwargs.setdefault('pricing_policy', self.pp)
        r = Report(master_user=self.m, member=self.mm, **kwargs)
        queryset = None
        if isinstance(trns, (list, tuple)):
            queryset = Transaction.objects.filter(pk__in=[int(t) if isinstance(t, int) else t.id for t in trns])
        b = ReportBuilder(instance=r, queryset=queryset)
        if r.report_type == Report.TYPE_BALANCE:
            if build_balance_for_tests:
                b.build_balance_for_tests(full=True)
            else:
                b.build_balance(full=True)
        elif r.report_type == Report.TYPE_PL:
            b.build_pl(full=True)
        r.transactions = b.transactions

        # mode_names = {
        #     Report.MODE_IGNORE: 'IGNORE_________',
        #     Report.MODE_INDEPENDENT: 'INDEPENDENT____',
        #     Report.MODE_INTERDEPENDENT: 'INTERDEPENDENT',
        # }
        name_part_delim = '_'
        name_parts = [
            '%s' % r.report_date,
            '%s' % r.report_currency,
            '%s' % r.report_type_str,
            # 'prtfl_%s' % mode_names[r.portfolio_mode],
            # 'acc_%s' % mode_names[r.account_mode],
            # 'str1_%s' % mode_names[r.strategy1_mode],
            # 'str2_%s' % mode_names[r.strategy2_mode],
            # 'str3_%s' % mode_names[r.strategy3_mode],
        ]
        name1 = name_part_delim.join(name_parts)
        if name:
            name += ' - ' + name1
        else:
            name = name1

        if trns:
            if isinstance(trns, bool):
                trns = [t.trn for t in r.transactions if not t.is_cloned]
            s = []
            for t in trns:
                s.append('%s/%s' % (t.transaction_class.name.lower(), t.position_size_with_sign))
            name += ' - ' + ', '.join(s)

        if trn_cols is None:
            trn_cols = self.TRN_COLS_ALL if trn_dump_all else self.TRN_COLS_MINI
        if item_cols is None:
            item_cols = self.ITEM_COLS_ALL if trn_dump_all else None

        if in_csv:
            trn_cols = self.TRN_COLS_MINI
            item_cols = self.ITEM_COLS_ALL

        def trn_filter(t):
            if trn_dump_all:
                return True
            else:
                return not t.is_cloned

        self._dump(b, name, trn_cols=trn_cols, item_cols=item_cols, trn_filter=trn_filter, in_csv=in_csv)
        return r

    def _write_results(self, reports, file_name=None, trn_cols=None, item_cols=None):
        import xlsxwriter

        trn_cols = trn_cols or self.TRN_COLS_MINI
        item_cols = item_cols or self.ITEM_COLS_ALL

        def _val(val):
            # if isinstance(val, (bool, int, float, str, date, datetime)):
            #     return val
            if val is None:
                return val
            if isinstance(val, (bool, int, float, str, datetime)):
                return val
            if isinstance(val, date):
                return datetime(val.year, month=val.month, day=val.day)
            return str(val)

        # data_path = os.path.join(tempfile.gettempdir(), 'data.xlsx')
        data_path = os.path.join('/Users', 'ailyukhin', 'tmp', file_name or 'data.xlsx')

        workbook = xlsxwriter.Workbook(data_path)
        header_fmt = workbook.add_format({'bold': True})
        date_fmt = workbook.add_format({'num_format': 'dd-mm-yyyy'})
        col_fmt = workbook.add_format({'bold': True, 'bg_color': '#EEEEEE'})
        delim_fmt = workbook.add_format({'bg_color': 'gray'})
        # num_fmt = workbook.add_format({'num_format': '#,###.###'})
        num_fmt = None

        modes_map = {
            Report.MODE_IGNORE: 'Ignore',
            Report.MODE_INDEPENDENT: 'Independent',
            Report.MODE_INTERDEPENDENT: 'Offsetting/Interdependent',
        }

        approach_map = {
            0.0: '0/100',
            0.5: '50/50',
            1.0: '100/0',
        }

        worksheet = workbook.add_worksheet()

        row = 0
        for r in reports:
            worksheet.set_row(row, cell_format=delim_fmt)
            row += 1

            # worksheet.write(row, 0, 'Report date:', header_fmt)
            worksheet.merge_range(row, 0, row, 2, 'Report date:', header_fmt)
            worksheet.write_datetime(row, 3, _val(r.report_date), date_fmt)
            row += 1

            # worksheet.write(row, 0, 'Report currency:', header_fmt)
            worksheet.merge_range(row, 0, row, 2, 'Report currency:', header_fmt)
            worksheet.write(row, 3, _val(r.report_currency))
            row += 1

            worksheet.merge_range(row, 0, row, 2, 'Portfolio:', header_fmt)
            worksheet.write(row, 3, _val(modes_map[r.portfolio_mode]))
            row += 1

            worksheet.merge_range(row, 0, row, 2, 'Account:', header_fmt)
            worksheet.write(row, 3, _val(modes_map[r.account_mode]))
            row += 1

            worksheet.merge_range(row, 0, row, 2, 'Strategy1:', header_fmt)
            worksheet.write(row, 3, _val(modes_map[r.strategy1_mode]))
            row += 1

            worksheet.merge_range(row, 0, row, 2, 'Strategy2:', header_fmt)
            worksheet.write(row, 3, _val(modes_map[r.strategy2_mode]))
            row += 1

            worksheet.merge_range(row, 0, row, 2, 'Strategy3:', header_fmt)
            worksheet.write(row, 3, _val(modes_map[r.strategy3_mode]))
            row += 1

            worksheet.merge_range(row, 0, row, 2, 'Approach:', header_fmt)
            worksheet.write(row, 3, _val(approach_map[r.approach_multiplier]))
            row += 1

            worksheet.merge_range(row, 0, row, 2, 'Show Transaction Details:', header_fmt)
            worksheet.write(row, 3, _val(r.show_transaction_details))
            row += 1

            # worksheet.write(row, 0, 'Virtual Transactions', header_fmt)
            worksheet.merge_range(row, 0, row, len(trn_cols), 'Virtual Transactions:', header_fmt)
            row += 1
            for col, name in enumerate(trn_cols):
                worksheet.write(row, col, name, col_fmt)
            row += 1
            for trn in r.transactions:
                if trn.is_cloned:
                    continue
                for col, val in enumerate(VirtualTransaction.dump_values(trn, trn_cols)):
                    val = _val(val)
                    if trn_cols[col] in ['trn_date', 'acc_date', 'cash_date']:
                        worksheet.write_datetime(row, col, val, date_fmt)
                    elif isinstance(val, (int, float)):
                        worksheet.write_number(row, col, val, num_fmt)
                    else:
                        worksheet.write(row, col, val)
                row += 1

            row += 2
            # worksheet.write(row, 0, 'Items', header_fmt)
            worksheet.merge_range(row, 0, row, len(item_cols), 'Items:', header_fmt)
            row += 1
            for col, name in enumerate(item_cols):
                worksheet.write(row, col, name, col_fmt)
            row += 1
            for item in r.items:
                for col, val in enumerate(ReportItem.dump_values(item, item_cols)):
                    val = _val(val)
                    if isinstance(val, (int, float)):
                        if math.isnan(val):
                            val = 0.0
                        worksheet.write_number(row, col, val, num_fmt)
                    else:
                        worksheet.write(row, col, val)
                row += 1

            row += 5

        workbook.close()

    # ------------------------------------------------------------------------------------------------------------------

    def _test_buy_sell(self):
        # self._t(t_class=self._cash_inflow, trn_ccy=self.usd, position=1000, fx_rate=1.3)
        self._t_buy(instr=self.bond0, position=5,
                    stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.,
                    days=1)
        self._t_buy(instr=self.bond0, position=5,
                    stl_ccy=self.usd, principal=-15., carry=-0., overheads=-0.,
                    days=2)
        self._t_sell(instr=self.bond0, position=-5,
                     stl_ccy=self.usd, principal=20., carry=0., overheads=0.,
                     days=3)

        self._simple_run('buy_sell - avco', report_date=self._d(14), cost_method=self._avco)
        # self._simple_run('buy_sell - fifo', report_date=self._d(14), cost_method=self._fifo)

    def _test_cash_in_out(self):
        self._t_cash_in(trn_ccy=self.eur, stl_ccy=self.eur, position=1000, fx_rate=1.3, notes='N1')
        self._t_cash_out(trn_ccy=self.usd, stl_ccy=self.usd, position=-1000, days=1, fx_rate=1.0, notes='N2')

        self._simple_run('cash_in_out', report_date=self._d(14))
        # self._dump_hist(days=(self._d(12), self._d(15)),
        #                 ccys=(self.eur, self.usd,),
        #                 instrs=False)

    def _test_fx_trade(self):
        self._ccy_hist(self.gbp, self._d(101), 1.45)
        self._ccy_hist(self.gbp, self._d(104), 1.2)

        self._ccy_hist(self.chf, self._d(101), 1.15)
        self._ccy_hist(self.chf, self._d(104), 1.1)

        self._ccy_hist(self.cad, self._d(101), 0.85)
        self._ccy_hist(self.cad, self._d(104), 0.9)

        self._ccy_hist(self.rub, self._d(101), 1 / 60)
        self._ccy_hist(self.rub, self._d(104), 1 / 65)

        self._t_fx_tade(trn_ccy=self.gbp, position=100,
                        stl_ccy=self.chf, principal=-140,
                        acc_date_days=101, cash_date_days=101,
                        notes='N1')

        self._t_fx_tade(trn_ccy=self.gbp, position=100,
                        stl_ccy=self.rub, principal=-140,
                        acc_date_days=101, cash_date_days=101,
                        notes='N2')

        self._simple_run('fx_trade', trns=True, report_currency=self.cad, report_date=self._d(104))
        # self._dump_hist(days=(self._d(100), self._d(105)),
        #                 ccys=(self.gbp, self.chf, self.cad, self.rub),
        #                 instrs=False)

    def _test_instrument_pl(self):
        # self._t_buy(instr=self.bond0, position=5,
        #             stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.,
        #             days=1)
        # self._t_instr_pl(instr=self.bond0, position=0.,
        #                  stl_ccy=self.chf, principal=0., carry=11., overheads=-1.,
        #                  days=2)
        #
        # self._t_buy(instr=self.bond0, position=5,
        #             stl_ccy=self.usd, principal=-15., carry=-0., overheads=-0.,
        #             days=3)
        # self._t_instr_pl(instr=self.bond0, position=0.,
        #                  stl_ccy=self.chf, principal=0., carry=20., overheads=0.,
        #                  days=4)
        #
        # self._t_sell(instr=self.bond0, position=-5,
        #              stl_ccy=self.usd, principal=20., carry=0., overheads=0.,
        #              days=5)
        # self._t_instr_pl(instr=self.bond0, position=0.,
        #                  stl_ccy=self.chf, principal=0., carry=20., overheads=0.,
        #                  days=6)
        #
        # self._t_sell(instr=self.bond0, position=-10,
        #              stl_ccy=self.usd, principal=20., carry=0., overheads=0.,
        #              days=7)
        # self._t_instr_pl(instr=self.bond0, position=0.,
        #                  stl_ccy=self.chf, principal=0., carry=20., overheads=0.,
        #                  days=8)


        # self._t_buy(instr=self.bond0, position=1, stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.)
        # self._t_instr_pl(instr=self.bond0, position=0., stl_ccy=self.chf, principal=0., carry=20., overheads=0.)

        self._t_sell(instr=self.bond0, position=-1, stl_ccy=self.usd, principal=20., carry=0., overheads=0.)
        self._t_instr_pl(instr=self.bond0, position=0., stl_ccy=self.chf, principal=0., carry=20., overheads=0.)

        # self._t_buy(instr=self.bond0, position=1, stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.)
        # self._t_instr_pl(instr=self.bond0, position=0., stl_ccy=self.chf, principal=0., carry=20., overheads=0.)

        self._t_sell(instr=self.bond0, position=-1, stl_ccy=self.usd, principal=20., carry=0., overheads=0.)
        self._t_instr_pl(instr=self.bond0, position=0., stl_ccy=self.chf, principal=0., carry=20., overheads=0.)

        # self._t_buy(instr=self.bond0, position=1, stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.)
        # self._t_instr_pl(instr=self.bond0, position=0., stl_ccy=self.chf, principal=0., carry=20., overheads=0.)

        self._t_sell(instr=self.bond0, position=-1, stl_ccy=self.usd, principal=20., carry=0., overheads=0.)
        self._t_instr_pl(instr=self.bond0, position=0., stl_ccy=self.chf, principal=0., carry=20., overheads=0.)

        self._t_buy(instr=self.bond0, position=1, stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.)
        self._t_instr_pl(instr=self.bond0, position=0., stl_ccy=self.chf, principal=0., carry=20., overheads=0.)

        # self._t_sell(instr=self.bond0, position=-1, stl_ccy=self.usd, principal=20., carry=0., overheads=0.)
        # self._t_instr_pl(instr=self.bond0, position=0., stl_ccy=self.chf, principal=0., carry=20., overheads=0.)

        self._t_buy(instr=self.bond0, position=1, stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.)
        self._t_instr_pl(instr=self.bond0, position=0., stl_ccy=self.chf, principal=0., carry=20., overheads=0.)

        self._t_buy(instr=self.bond0, position=1, stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.)
        self._t_instr_pl(instr=self.bond0, position=0., stl_ccy=self.chf, principal=0., carry=20., overheads=0.)

        self._t_buy(instr=self.bond0, position=1, stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.)
        self._t_instr_pl(instr=self.bond0, position=0., stl_ccy=self.chf, principal=0., carry=20., overheads=0.)

        self._t_sell(instr=self.bond0, position=-1, stl_ccy=self.usd, principal=20., carry=0., overheads=0.)
        self._t_instr_pl(instr=self.bond0, position=0., stl_ccy=self.chf, principal=0., carry=20., overheads=0.)

        trn_cols = ['trn_code', 'trn_cls', 'instr', 'pos_size', 'multiplier', 'rolling_pos_size',
                    'remaining_pos_size', 'sum_remaining_pos_size', 'balance_pos_size', ]
        item_cols = self.ITEM_COLS_ALL

        self._simple_run('instrument_pl', report_currency=self.cad, report_date=self._d(14),
                         trn_dump_all=False, trn_cols=trn_cols, item_cols=item_cols)

    def _test_transaction_pl(self):
        self._t_trn_pl(stl_ccy=self.rub, principal=0., carry=-900., overheads=-100.,
                       days=1, notes='N1')

        self._t_trn_pl(stl_ccy=self.rub, principal=0., carry=-900., overheads=-100.,
                       days=2, notes='N2')

        self._simple_run('transaction_pl', report_currency=self.cad, report_date=self._d(14))

    def _test_transfer(self):
        self._t_transfer(instr=self.bond0, position=-10.0,
                         acc_pos=self.a1_1, acc_cash=self.a1_2,
                         days=1, notes='N1')
        self._t_transfer(instr=self.bond0, position=-10.0,
                         acc_pos=self.a1_1, acc_cash=self.a2_3,
                         days=2, notes='N2')

        self._simple_run('transfer', report_currency=self.cad, report_date=self._d(14))

    def _test_fx_transfer(self):
        self._t_fx_transfer(trn_ccy=self.eur, position=-10.,
                            acc_pos=self.a1_1, acc_cash=self.a1_2,
                            days=1, notes='N1')
        self._t_fx_transfer(trn_ccy=self.gbp, position=-10.,
                            acc_pos=self.a1_1, acc_cash=self.a2_3,
                            days=2, notes='N2')
        self._simple_run('fx_transfer', report_currency=self.cad, report_date=self._d(14))

    def _test_some_notes(self):
        self._t_cash_in(trn_ccy=self.usd, stl_ccy=self.usd, position=1000, fx_rate=1.3, days=1, notes='N1')
        self._t_cash_out(trn_ccy=self.usd, stl_ccy=self.usd, position=-1000, fx_rate=1.0, days=1, notes='N2')

        self._t_fx_tade(trn_ccy=self.usd, position=100, stl_ccy=self.usd, principal=-140, days=1, notes='N1')
        self._t_fx_tade(trn_ccy=self.usd, position=100, stl_ccy=self.usd, principal=-140, days=1, notes='N2')

        self._t_trn_pl(stl_ccy=self.usd, principal=0., carry=-900., overheads=-100., days=1, notes='N1')
        self._t_trn_pl(stl_ccy=self.usd, principal=0., carry=-900., overheads=-100., days=1, notes='N2')

        self._simple_run('test_some_notes', report_currency=self.cad, report_date=self._d(14))

    # ------------------------------------------------------------------------------------------------------------------

    def _test_modes(self):
        trns = [
            self._buy,
            self._sell,
            self._cash_inflow,
            self._cash_outflow,
            self._fx_tade,
            self._instrument_pl,
            self._transaction_pl,
            self._transfer,
            self._fx_transfer,
        ]
        fields = [
            'ignore',
            'portfolio',
            'account',
            'strategy1',
            'strategy2',
            'strategy3',
            'all',
            # 'full',
        ]

        if self._buy in trns:
            self._t_buy(days=1, instr=self.bond0, position=10,
                        stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.,
                        p=self.p1, acc_pos=self.a1_1, acc_cash=self.a1_1, acc_interim=self.a1_1,
                        s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1,
                        s2_pos=self.s2_1_1_1, s2_cash=self.s2_1_1_1,
                        s3_pos=self.s3_1_1_1, s3_cash=self.s3_1_1_1)
            self._t_buy(days=1, instr=self.bond0, position=10,
                        stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.,
                        p=self.p2, acc_pos=self.a1_2, acc_cash=self.a1_2, acc_interim=self.a1_2,
                        s1_pos=self.s1_1_1_2, s1_cash=self.s1_1_1_2,
                        s2_pos=self.s2_1_1_2, s2_cash=self.s2_1_1_2,
                        s3_pos=self.s3_1_1_2, s3_cash=self.s3_1_1_2)

        if self._sell in trns:
            self._t_sell(days=1, instr=self.bond0, position=-5,
                         stl_ccy=self.usd, principal=10., carry=0., overheads=-0.,
                         p=self.p1, acc_pos=self.a1_1, acc_cash=self.a1_1, acc_interim=self.a1_1,
                         s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1,
                         s2_pos=self.s2_1_1_1, s2_cash=self.s2_1_1_1,
                         s3_pos=self.s3_1_1_1, s3_cash=self.s3_1_1_1)
            self._t_sell(days=1, instr=self.bond0, position=-5,
                         stl_ccy=self.usd, principal=10., carry=0., overheads=-0.,
                         p=self.p2, acc_pos=self.a1_2, acc_cash=self.a1_2, acc_interim=self.a1_2,
                         s1_pos=self.s1_1_1_3, s1_cash=self.s1_1_1_3,
                         s2_pos=self.s2_1_1_3, s2_cash=self.s2_1_1_3,
                         s3_pos=self.s3_1_1_3, s3_cash=self.s3_1_1_3)

        if self._cash_inflow in trns:
            self._t_cash_in(days=1, trn_ccy=self.eur, stl_ccy=self.eur, position=1000, fx_rate=1.3,
                            p=self.p1, acc_pos=self.a1_1, acc_cash=self.a1_1, acc_interim=self.a1_1,
                            s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1,
                            s2_pos=self.s2_1_1_1, s2_cash=self.s2_1_1_1,
                            s3_pos=self.s3_1_1_1, s3_cash=self.s3_1_1_1)
            self._t_cash_in(days=1, trn_ccy=self.eur, stl_ccy=self.eur, position=1000, fx_rate=1.3,
                            p=self.p2, acc_pos=self.a1_2, acc_cash=self.a1_2, acc_interim=self.a1_2,
                            s1_pos=self.s1_1_1_2, s1_cash=self.s1_1_1_2,
                            s2_pos=self.s2_1_1_2, s2_cash=self.s2_1_1_2,
                            s3_pos=self.s3_1_1_2, s3_cash=self.s3_1_1_2)

        if self._cash_outflow in trns:
            self._t_cash_out(days=1, trn_ccy=self.eur, stl_ccy=self.usd, position=-100, fx_rate=1.0,
                             p=self.p1, acc_pos=self.a1_1, acc_cash=self.a1_1, acc_interim=self.a1_1,
                             s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1,
                             s2_pos=self.s2_1_1_1, s2_cash=self.s2_1_1_1,
                             s3_pos=self.s3_1_1_1, s3_cash=self.s3_1_1_1)
            self._t_cash_out(days=1, trn_ccy=self.eur, stl_ccy=self.usd, position=-100, fx_rate=1.0,
                             p=self.p2, acc_pos=self.a1_2, acc_cash=self.a1_2, acc_interim=self.a1_2,
                             s1_pos=self.s1_1_1_2, s1_cash=self.s1_1_1_2,
                             s2_pos=self.s2_1_1_2, s2_cash=self.s2_1_1_2,
                             s3_pos=self.s3_1_1_2, s3_cash=self.s3_1_1_2)

        if self._fx_tade in trns:
            self._t_fx_tade(days=1, trn_ccy=self.gbp, position=100,
                            stl_ccy=self.chf, principal=-140,
                            p=self.p1, acc_pos=self.a1_1, acc_cash=self.a1_1, acc_interim=self.a1_1,
                            s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1,
                            s2_pos=self.s2_1_1_1, s2_cash=self.s2_1_1_1,
                            s3_pos=self.s3_1_1_1, s3_cash=self.s3_1_1_1,
                            notes='fx1')
            self._t_fx_tade(days=1, trn_ccy=self.gbp, position=100,
                            stl_ccy=self.chf, principal=-140,
                            p=self.p2, acc_pos=self.a1_2, acc_cash=self.a1_2, acc_interim=self.a1_2,
                            s1_pos=self.s1_1_1_2, s1_cash=self.s1_1_1_2,
                            s2_pos=self.s2_1_1_2, s2_cash=self.s2_1_1_2,
                            s3_pos=self.s3_1_1_2, s3_cash=self.s3_1_1_2,
                            notes='fx2')

        if self._instrument_pl in trns:
            self._t_instr_pl(days=1, instr=self.bond1, position=0.,
                             stl_ccy=self.chf, principal=0., carry=11., overheads=-1.,
                             p=self.p1, acc_pos=self.a1_1, acc_cash=self.a1_1, acc_interim=self.a1_1,
                             s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1,
                             s2_pos=self.s2_1_1_1, s2_cash=self.s2_1_1_1,
                             s3_pos=self.s3_1_1_1, s3_cash=self.s3_1_1_1)
            self._t_instr_pl(days=1, instr=self.bond1, position=0.,
                             stl_ccy=self.chf, principal=0., carry=11., overheads=-1.,
                             p=self.p2, acc_pos=self.a1_2, acc_cash=self.a1_2, acc_interim=self.a1_2,
                             s1_pos=self.s1_1_1_2, s1_cash=self.s1_1_1_2,
                             s2_pos=self.s2_1_1_2, s2_cash=self.s2_1_1_2,
                             s3_pos=self.s3_1_1_2, s3_cash=self.s3_1_1_2)

        if self._transaction_pl in trns:
            self._t_trn_pl(days=1, stl_ccy=self.rub, principal=0., carry=-900., overheads=-100.,
                           p=self.p1, acc_pos=self.a1_1, acc_cash=self.a1_1, acc_interim=self.a1_1,
                           s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1,
                           s2_pos=self.s2_1_1_1, s2_cash=self.s2_1_1_1,
                           s3_pos=self.s3_1_1_1, s3_cash=self.s3_1_1_1,
                           notes='trnpl1')
            self._t_trn_pl(days=1, stl_ccy=self.rub, principal=0., carry=-900., overheads=-100.,
                           p=self.p2, acc_pos=self.a1_2, acc_cash=self.a1_2, acc_interim=self.a1_2,
                           s1_pos=self.s1_1_1_2, s1_cash=self.s1_1_1_2,
                           s2_pos=self.s2_1_1_2, s2_cash=self.s2_1_1_2,
                           s3_pos=self.s3_1_1_2, s3_cash=self.s3_1_1_2,
                           notes='trnpl2')

        if 'ignore' in fields:
            self._simple_run('mode - IGNORE - all',
                             report_currency=self.cad,
                             report_date=self._d(14),
                             portfolio_mode=Report.MODE_IGNORE,
                             account_mode=Report.MODE_IGNORE,
                             strategy1_mode=Report.MODE_IGNORE,
                             strategy2_mode=Report.MODE_IGNORE,
                             strategy3_mode=Report.MODE_IGNORE)

        if 'portfolio' in fields:
            self._simple_run('mode - INDEPENDENT - portfolio',
                             report_currency=self.cad,
                             report_date=self._d(14),
                             portfolio_mode=Report.MODE_INDEPENDENT,
                             account_mode=Report.MODE_IGNORE,
                             strategy1_mode=Report.MODE_IGNORE,
                             strategy2_mode=Report.MODE_IGNORE,
                             strategy3_mode=Report.MODE_IGNORE)

        if 'account' in fields:
            self._simple_run('mode - INDEPENDENT - account',
                             report_currency=self.cad,
                             report_date=self._d(14),
                             portfolio_mode=Report.MODE_IGNORE,
                             account_mode=Report.MODE_INDEPENDENT,
                             strategy1_mode=Report.MODE_IGNORE,
                             strategy2_mode=Report.MODE_IGNORE,
                             strategy3_mode=Report.MODE_IGNORE)

        if 'strategy1' in fields:
            self._simple_run('mode - INDEPENDENT - strategy1',
                             report_currency=self.cad,
                             report_date=self._d(14),
                             portfolio_mode=Report.MODE_IGNORE,
                             account_mode=Report.MODE_IGNORE,
                             strategy1_mode=Report.MODE_INDEPENDENT,
                             strategy2_mode=Report.MODE_IGNORE,
                             strategy3_mode=Report.MODE_IGNORE)
            self._simple_run('mode - INTERDEPENDENT - strategy1',
                             report_currency=self.cad,
                             report_date=self._d(14),
                             portfolio_mode=Report.MODE_IGNORE,
                             account_mode=Report.MODE_IGNORE,
                             strategy1_mode=Report.MODE_INTERDEPENDENT,
                             strategy2_mode=Report.MODE_IGNORE,
                             strategy3_mode=Report.MODE_IGNORE)

        if 'strategy2' in fields:
            self._simple_run('mode - INDEPENDENT - strategy2',
                             report_currency=self.cad,
                             report_date=self._d(14),
                             portfolio_mode=Report.MODE_IGNORE,
                             account_mode=Report.MODE_IGNORE,
                             strategy1_mode=Report.MODE_IGNORE,
                             strategy2_mode=Report.MODE_INDEPENDENT,
                             strategy3_mode=Report.MODE_IGNORE)
            self._simple_run('mode - INTERDEPENDENT - strategy2',
                             report_currency=self.cad,
                             report_date=self._d(14),
                             portfolio_mode=Report.MODE_IGNORE,
                             account_mode=Report.MODE_IGNORE,
                             strategy1_mode=Report.MODE_IGNORE,
                             strategy2_mode=Report.MODE_INTERDEPENDENT,
                             strategy3_mode=Report.MODE_IGNORE)

        if 'strategy3' in fields:
            self._simple_run('mode - INDEPENDENT - strategy3',
                             report_currency=self.cad,
                             report_date=self._d(14),
                             portfolio_mode=Report.MODE_IGNORE,
                             account_mode=Report.MODE_IGNORE,
                             strategy1_mode=Report.MODE_IGNORE,
                             strategy2_mode=Report.MODE_IGNORE,
                             strategy3_mode=Report.MODE_INDEPENDENT)
            self._simple_run('mode - INTERDEPENDENT - strategy3',
                             report_currency=self.cad,
                             report_date=self._d(14),
                             portfolio_mode=Report.MODE_IGNORE,
                             account_mode=Report.MODE_IGNORE,
                             strategy1_mode=Report.MODE_IGNORE,
                             strategy2_mode=Report.MODE_IGNORE,
                             strategy3_mode=Report.MODE_INTERDEPENDENT)

        if 'all' in fields:
            self._simple_run('mode - INDEPENDENT - all',
                             report_currency=self.cad,
                             report_date=self._d(14),
                             portfolio_mode=Report.MODE_INDEPENDENT,
                             account_mode=Report.MODE_INDEPENDENT,
                             strategy1_mode=Report.MODE_INDEPENDENT,
                             strategy2_mode=Report.MODE_INDEPENDENT,
                             strategy3_mode=Report.MODE_INDEPENDENT)

        if 'full' in fields:
            modes = [Report.MODE_IGNORE, Report.MODE_INDEPENDENT, Report.MODE_INTERDEPENDENT]
            mode_names = ['IGNORE', 'INDEPENDENT', 'INTERDEPENDENT']
            for portfolio_index, portfolio_mode in enumerate(modes):
                if portfolio_mode in [Report.MODE_INTERDEPENDENT]:
                    continue
                for account_index, account_mode in enumerate(modes):
                    if account_mode in [Report.MODE_INTERDEPENDENT]:
                        continue
                    for strategy1_index, strategy1_mode in enumerate(modes):
                        for strategy2_index, strategy2_mode in enumerate(modes):
                            for strategy3_index, strategy3_mode in enumerate(modes):
                                name = 'modes - portfolio=%s, account=%s, strategy1=%s, strategy2=%s, strategy3=%s' % (
                                    mode_names[portfolio_index],
                                    mode_names[account_index],
                                    mode_names[strategy1_index],
                                    mode_names[strategy2_index],
                                    mode_names[strategy3_index],
                                )
                                self._simple_run(
                                    name,
                                    report_currency=self.cad,
                                    report_date=self._d(14),
                                    portfolio_mode=portfolio_mode,
                                    account_mode=account_mode,
                                    strategy1_mode=strategy1_mode,
                                    strategy2_mode=strategy2_mode,
                                    strategy3_mode=strategy3_mode
                                )
        pass

    def _test_allocations(self):
        # settings.DEBUG = True

        self._t_buy(instr=self.bond0, position=5,
                    stl_ccy=self.usd, principal=-10, carry=0, overheads=0,
                    alloc_bl=self.bond1, alloc_pl=self.stock1)

        self._t_buy(instr=self.bond0, position=5,
                    stl_ccy=self.usd, principal=-15, carry=0, overheads=0,
                    alloc_bl=self.bond2, alloc_pl=self.stock2)

        self._t_sell(instr=self.bond0, position=-5,
                     stl_ccy=self.usd, principal=20, carry=0, overheads=0,
                     alloc_bl=self.bond3, alloc_pl=self.stock3)

        mults = [0.0, 0.5, 1.0]
        mults_names = ['0/100', '50/50', '100/0']

        for mult_index, mult in enumerate(mults):
            name = 'allocation - %s' % (mults_names[mult_index],)
            self._simple_run(
                name,
                report_currency=self.cad,
                report_date=self._d(14),
                portfolio_mode=Report.MODE_IGNORE,
                account_mode=Report.MODE_IGNORE,
                strategy1_mode=Report.MODE_IGNORE,
                strategy2_mode=Report.MODE_IGNORE,
                strategy3_mode=Report.MODE_IGNORE,
                approach_multiplier=mult
            )

    def _test_allocations2(self):
        # settings.DEBUG = True
        self.bond0.price_multiplier = 0
        self.bond0.accrued_multiplier = 0
        self.bond0.save()

        bl_same_pl = False
        pl_same_bl = False

        self._t_buy(
            instr=self.bond0, position=8,
            stl_ccy=self.usd, principal=-10,
            alloc_bl=self.bond1 if not bl_same_pl else self.stock1,
            alloc_pl=self.stock1 if not pl_same_bl else self.bond1
        )

        self._t_buy(
            instr=self.bond0, position=7,
            stl_ccy=self.usd, principal=-11,
            alloc_bl=self.bond1 if not bl_same_pl else self.stock2,
            alloc_pl=self.stock2 if not pl_same_bl else self.bond1
        )

        self._t_buy(
            instr=self.bond0, position=6,
            stl_ccy=self.usd, principal=-12,
            alloc_bl=self.bond2 if not bl_same_pl else self.stock1,
            alloc_pl=self.stock1 if not pl_same_bl else self.bond2
        )

        self._t_buy(
            instr=self.bond0, position=5,
            stl_ccy=self.usd, principal=-13,
            alloc_bl=self.bond2 if not bl_same_pl else self.stock2,
            alloc_pl=self.stock2 if not pl_same_bl else self.bond2
        )

        self._t_sell(
            instr=self.bond0, position=-1,
            stl_ccy=self.usd, principal=1,
            alloc_bl=self.bond1 if not bl_same_pl else self.stock1,
            alloc_pl=self.stock1 if not pl_same_bl else self.bond1
        )

        self._t_sell(
            instr=self.bond0, position=-1,
            stl_ccy=self.usd, principal=1,
            alloc_bl=self.bond1 if not bl_same_pl else self.stock2,
            alloc_pl=self.stock2 if not pl_same_bl else self.bond1
        )

        self._t_sell(
            instr=self.bond0, position=-1,
            stl_ccy=self.usd, principal=1,
            alloc_bl=self.bond2 if not bl_same_pl else self.stock1,
            alloc_pl=self.stock1 if not pl_same_bl else self.bond2
        )

        self._t_sell(
            instr=self.bond0, position=-1,
            stl_ccy=self.usd, principal=1,
            alloc_bl=self.bond2 if not bl_same_pl else self.stock2,
            alloc_pl=self.stock2 if not pl_same_bl else self.bond2
        )

        self._simple_run(
            'allocation',
            report_currency=self.usd,
            report_date=self._d(21),
            portfolio_mode=Report.MODE_IGNORE,
            account_mode=Report.MODE_IGNORE,
            strategy1_mode=Report.MODE_IGNORE,
            strategy2_mode=Report.MODE_IGNORE,
            strategy3_mode=Report.MODE_IGNORE,
            trn_dump_all=True,
            trn_cols=self.TRN_COLS_MINI,
            item_cols=self.ITEM_COLS_MINI,
        )

    def _test_allocation_detailing(self):
        self._t_buy(instr=self.bond0, position=1, stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.)
        self._t_buy(instr=self.bond0, position=1, stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.,
                    alloc_bl=self.bond2, alloc_pl=self.bond2)

        self._t_buy(instr=self.bond1, position=1, stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.)
        self._t_buy(instr=self.bond1, position=1, stl_ccy=self.usd, principal=-10., carry=-0., overheads=-0.,
                    alloc_bl=self.bond2, alloc_pl=self.bond2)

        self._t_cash_in(trn_ccy=self.usd, stl_ccy=self.usd, position=1000, fx_rate=1.3, notes='N1')
        self._t_cash_in(trn_ccy=self.usd, stl_ccy=self.usd, position=1000, fx_rate=1.3, notes='N1',
                        alloc_bl=self.bond2, alloc_pl=self.bond2)

        self._t_cash_out(trn_ccy=self.usd, stl_ccy=self.usd, position=-1000, fx_rate=1.0, notes='N1')
        self._t_cash_out(trn_ccy=self.usd, stl_ccy=self.usd, position=-1000, fx_rate=1.0, notes='N1',
                         alloc_bl=self.bond2, alloc_pl=self.bond2)

        self._t_fx_tade(trn_ccy=self.usd, position=100, stl_ccy=self.usd, principal=-140, notes='N1')
        self._t_fx_tade(trn_ccy=self.usd, position=100, stl_ccy=self.usd, principal=-140, notes='N1',
                        alloc_bl=self.bond2, alloc_pl=self.bond2)

        self._t_trn_pl(stl_ccy=self.usd, principal=0., carry=-900., overheads=-100., notes='N1')
        self._t_trn_pl(stl_ccy=self.usd, principal=0., carry=-900., overheads=-100., notes='N1',
                       alloc_bl=self.bond2, alloc_pl=self.bond2)

        trn_cols = self.TRN_COLS_ALL
        item_cols = self.ITEM_COLS_ALL

        trn_cols = ['pk', 'trn_cls', 'instr', 'pos_size', 'alloc_bl', 'alloc_pl']
        item_cols = ['group_code', 'type_code', 'subtype_code', 'user_code', 'instr', 'alloc', 'pos_size',
                     'market_value_res',
                     'total_res']

        self._simple_run('test_allocation_detailing - balance - allocation_detailing', report_type=Report.TYPE_BALANCE,
                         report_currency=self.cad, report_date=self._d(14),
                         trn_dump_all=False, trn_cols=trn_cols, item_cols=item_cols,
                         allocation_detailing=True, pl_include_zero=True)

        self._simple_run('test_allocation_detailing - balance - no_allocation_detailing',
                         report_type=Report.TYPE_BALANCE,
                         report_currency=self.cad, report_date=self._d(14),
                         trn_dump_all=False, trn_cols=trn_cols, item_cols=item_cols,
                         allocation_detailing=False, pl_include_zero=True)

        self._simple_run('test_allocation_detailing - p&l - allocation_detailing', report_type=Report.TYPE_PL,
                         report_currency=self.cad, report_date=self._d(14),
                         trn_dump_all=False, trn_cols=trn_cols, item_cols=item_cols,
                         allocation_detailing=True, pl_include_zero=True)

        self._simple_run('test_allocation_detailing - p&l - no_allocation_detailing', report_type=Report.TYPE_PL,
                         report_currency=self.cad, report_date=self._d(14),
                         trn_dump_all=False, trn_cols=trn_cols, item_cols=item_cols,
                         allocation_detailing=False, pl_include_zero=True)

    # ------------------------------------------------------------------------------------------------------------------

    def _test_buy_sell_max(self):
        b1 = self._t_buy(instr=self.bond0, days=5, position=5, principal=-10., carry=-0., overheads=-0.)
        s1 = self._t_sell(instr=self.bond0, days=10, position=-5, principal=20.0, carry=0.0, overheads=0.0)
        b2 = self._t_buy(instr=self.bond0, days=15, position=5, principal=-15.0, carry=-0.0, overheads=-0.0)
        s2 = self._t_sell(instr=self.bond0, days=20, position=-5, principal=20.0, carry=0.0, overheads=0.0)

        cost_variants = [
            self._avco,
            # self._fifo,
        ]

        trns_variants = [
            # [b1, s1],
            # [b1, b2, s1],
            [b1, b2, s2],
            # [b1, s1, s2],
            # [b1, s1, b2],
            # [b1, s1, b2, s2],
        ]

        # self._dump_hist()

        for cost_m in cost_variants:
            for trns in trns_variants:
                name = 'test_buy_sell/%s' % (cost_m.system_code,)
                self._simple_run(name, trns=trns, cost_method=cost_m, report_date=self._d(25))

    def _test_buy_sell_3(self):
        self._t_cash_in(trn_ccy=self.eur, position=1000, fx_rate=1.3)
        self._t_buy(instr=self.bond1, position=100,
                    stl_ccy=self.usd, principal=-180., carry=-5., overheads=-15.,
                    acc_date_days=3, cash_date_days=5)
        self._t_buy(instr=self.stock1, position=-200,
                    stl_ccy=self.rub, principal=1100., carry=0., overheads=-100.,
                    acc_date_days=5, cash_date_days=3)
        self._t_cash_out(trn_ccy=self.rub, position=-1000,
                         principal=0., carry=0., overheads=0.,
                         acc_date_days=6, cash_date_days=6,
                         fx_rate=1 / 75.)

        # r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(14))
        # b = ReportBuilder(instance=r)
        # b.build()
        # self._dump(b, 'test_balance_2')
        self._simple_run('test_buy_sell_3', report_date=self._d(14))

    def _test_build_position_only(self):
        self._t(t_class=self._cash_inflow, stl_ccy=self.usd, trn_ccy=self.usd, position=1000, fx_rate=1.0)

        self._t(t_class=self._buy,
                instr=self.bond0, position=100,
                stl_ccy=self.usd, principal=-180., carry=-5., overheads=-15.,
                acc_date_days=1, cash_date_days=1)

        self._t(t_class=self._buy,
                instr=self.bond1, position=100,
                stl_ccy=self.usd, principal=-180., carry=-5., overheads=-15.,
                acc_date_days=2, cash_date_days=2)

        self._t(t_class=self._sell,
                instr=self.bond1, position=-100,
                trn_ccy=self.rub,
                stl_ccy=self.chf, principal=180., carry=5., overheads=-15.,
                acc_date_days=3, cash_date_days=3)

        r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(14))
        b = ReportBuilder(instance=r)
        b.build_position_only()
        self._dump(b, 'test_build_position_only',
                   item_cols=['type_code', 'instr', 'ccy', 'prtfl', 'acc', 'str1', 'str2', 'str3', 'alloc_bl',
                              'alloc_pl', 'pos_size', ])

    def _test_avco_prtfl_0(self):
        self._t(t_class=self._buy, instr=self.bond0, position=5,
                stl_ccy=self.usd, principal=-10.0,
                acc_date_days=1, cash_date_days=1,
                p=self.p1,
                acc_pos=self.a1_1, acc_cash=self.a1_1,
                s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1)

        self._t(t_class=self._buy, instr=self.bond0, position=5,
                stl_ccy=self.usd, principal=-15.0,
                acc_date_days=2, cash_date_days=2,
                p=self.p1,
                acc_pos=self.a1_1, acc_cash=self.a1_1,
                s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1)

        self._t(t_class=self._sell, instr=self.bond0, position=-5,
                stl_ccy=self.usd, principal=20.0,
                acc_date_days=3, cash_date_days=3,
                p=self.p2,
                acc_pos=self.a1_1, acc_cash=self.a1_1,
                s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1)

        # r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(14),
        #            cost_method=self._avco,
        #            portfolio_mode=Report.MODE_IGNORE)
        # b = ReportBuilder(instance=r)
        # b.build()
        # self._dump(b, 'test_avco_prtfl_0: IGNORE')
        self._simple_run('test_avco_prtfl_0: IGNORE', report_date=self._d(14), cost_method=self._avco,
                         portfolio_mode=Report.MODE_IGNORE)

        # r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(14),
        #            cost_method=self._avco,
        #            portfolio_mode=Report.MODE_INDEPENDENT)
        # b = ReportBuilder(instance=r)
        # b.build()
        # self._dump(b, 'test_avco_prtfl_0: INDEPENDENT')
        self._simple_run('test_avco_prtfl_0: IGNORE', report_date=self._d(14), cost_method=self._avco,
                         portfolio_mode=Report.MODE_INDEPENDENT)

    def _test_avco_acc_0(self):
        self._t(t_class=self._buy, instr=self.bond0, position=5,
                stl_ccy=self.usd, principal=-10.0,
                acc_date_days=1, cash_date_days=1,
                p=self.p1,
                acc_pos=self.a1_1, acc_cash=self.a1_1,
                s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1)

        self._t(t_class=self._buy, instr=self.bond0, position=5,
                stl_ccy=self.usd, principal=-15.0,
                acc_date_days=2, cash_date_days=2,
                p=self.p1,
                acc_pos=self.a1_1, acc_cash=self.a1_1,
                s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1)

        self._t(t_class=self._sell, instr=self.bond0, position=-5,
                stl_ccy=self.usd, principal=20.0,
                acc_date_days=3, cash_date_days=3,
                p=self.p1,
                acc_pos=self.a1_2, acc_cash=self.a1_2,
                s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1)

        r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(14),
                   cost_method=self._avco,
                   account_mode=Report.MODE_IGNORE)
        b = ReportBuilder(instance=r)
        b.build_balance()
        self._dump(b, 'test_avco_acc_0: IGNORE')

        r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(14),
                   cost_method=self._avco,
                   account_mode=Report.MODE_INDEPENDENT)
        b = ReportBuilder(instance=r)
        b.build_balance()
        self._dump(b, 'test_avco_acc_0: INDEPENDENT')

    def _test_avco_str1_0(self):
        self._t(t_class=self._buy, instr=self.bond0, position=5,
                stl_ccy=self.usd, principal=-10.0,
                acc_date_days=1, cash_date_days=1,
                p=self.p1,
                acc_pos=self.a1_1, acc_cash=self.a1_1,
                s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1)

        self._t(t_class=self._buy, instr=self.bond0, position=5,
                stl_ccy=self.usd, principal=-15.0,
                acc_date_days=2, cash_date_days=2,
                p=self.p1,
                acc_pos=self.a1_1, acc_cash=self.a1_1,
                s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1)

        self._t(t_class=self._sell, instr=self.bond0, position=-5,
                stl_ccy=self.usd, principal=20.0,
                acc_date_days=3, cash_date_days=3,
                p=self.p1,
                acc_pos=self.a1_1, acc_cash=self.a1_1,
                s1_pos=self.s1_1_1_2, s1_cash=self.s1_1_1_2)

        r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(14),
                   cost_method=self._avco,
                   strategy1_mode=Report.MODE_INDEPENDENT)
        b = ReportBuilder(instance=r)
        b.build_balance()
        self._dump(b, 'test_avco_str1_0: NON_OFFSETTING')

        r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(14),
                   cost_method=self._avco,
                   strategy1_mode=Report.MODE_INTERDEPENDENT)
        b = ReportBuilder(instance=r)
        b.build_balance()
        self._dump(b, 'test_avco_str1_0: OFFSETTING')

    def _test_pl_0(self):
        self._t(t_class=self._cash_inflow, trn_ccy=self.usd, position=1000, fx_rate=1.3)

        self._t(t_class=self._buy, instr=self.bond0, position=100,
                stl_ccy=self.usd, principal=-180., carry=-5., overheads=-15.,
                acc_date_days=3, cash_date_days=5)

        r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(14))
        b = ReportBuilder(instance=r)
        b.build()
        self._dump(b, 'test_pl_0')

    def _test_pl_1(self):
        self._t(t_class=self._cash_inflow, trn_ccy=self.eur, position=1000, fx_rate=1.3)

        self._t(t_class=self._buy, instr=self.bond1, position=100,
                stl_ccy=self.usd, principal=-180., carry=-5., overheads=-15.,
                acc_date_days=3, cash_date_days=5)

        self._t(t_class=self._buy, instr=self.stock1, position=-200,
                stl_ccy=self.rub, principal=1100., carry=0., overheads=-100.,
                acc_date_days=5, cash_date_days=3)

        self._t(t_class=self._cash_outflow, trn_ccy=self.rub, position=-1000,
                principal=0., carry=0., overheads=0.,
                acc_date_days=6, cash_date_days=6, fx_rate=1 / 75.)

        self._t(t_class=self._instrument_pl, instr=self.stock1, position=0.,
                stl_ccy=self.chf, principal=0., carry=11., overheads=-1.,
                acc_date_days=7, cash_date_days=7)

        self._t(t_class=self._instrument_pl, instr=self.bond1, position=0.,
                stl_ccy=self.chf, principal=0., carry=20., overheads=0.,
                acc_date_days=8, cash_date_days=8)

        self._t(t_class=self._transaction_pl, position=0.,
                stl_ccy=self.rub, principal=0., carry=-900., overheads=-100.,
                acc_date_days=8, cash_date_days=8)

        r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(14))
        b = ReportBuilder(instance=r)
        b.build()
        self._dump(b, 'test_pl_1')

    def _test_pl_full_fx_fixed_buy_sell_1(self):
        instr = Instrument.objects.create(master_user=self.m, name="I1, RUB/RUB",
                                          instrument_type=self.m.instrument_type,
                                          pricing_currency=self.rub, price_multiplier=1.0,
                                          accrued_currency=self.rub, accrued_multiplier=1.0)

        # self.m.system_currency = self.cad
        # self.m.save()

        self._instr_hist(instr, self._d(101), 1.0, 1.0)
        self._instr_hist(instr, self._d(104), 240.0, 160.0)

        self._ccy_hist(self.gbp, self._d(101), 1.45)
        self._ccy_hist(self.gbp, self._d(104), 1.3)

        self._ccy_hist(self.eur, self._d(101), 1.25)
        self._ccy_hist(self.eur, self._d(104), 1.1)

        self._ccy_hist(self.rub, self._d(101), 1 / 60)
        self._ccy_hist(self.rub, self._d(104), 1 / 65)

        self._ccy_hist(self.chf, self._d(101), 1.15)
        self._ccy_hist(self.chf, self._d(104), 1.05)

        self._ccy_hist(self.cad, self._d(101), 1.1)
        self._ccy_hist(self.cad, self._d(104), 1.2)

        self._t(t_class=self._buy, instr=instr, position=5,
                stl_ccy=self.gbp, principal=-20.0, carry=-5.0,
                trn_ccy=self.rub, fx_rate=80,
                acc_date_days=101, cash_date_days=101)

        self._t(t_class=self._buy, instr=instr, position=5,
                stl_ccy=self.eur, principal=-22.0, carry=-8.0,
                trn_ccy=self.usd, fx_rate=1.3,
                acc_date_days=101, cash_date_days=101)

        self._t(t_class=self._sell, instr=instr, position=-5,
                stl_ccy=self.chf, principal=25.0, carry=9.0,
                trn_ccy=self.usd, fx_rate=1.1,
                acc_date_days=101, cash_date_days=101)

        # r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(104), report_currency=self.cad,
        #            cost_method=self._avco, approach_multiplier=1.0)
        # b = ReportBuilder(instance=r)
        # b.build_balance()
        # self._dump(b, 'test_pl_full_fx_fixed_buy_sell_1', trn_cols=self.TRN_COLS_ALL, item_cols=self.ITEM_COLS_ALL)
        trn_cols = self.TRN_COLS_ALL
        item_cols = self.ITEM_COLS_ALL
        item_cols = [x for x in item_cols if ('_loc' not in x) and ('opened' not in x) and ('closed' not in x)]
        self._simple_run(
            'test_pl_full_fx_fixed_buy_sell_1',
            report_currency=self.cad,
            report_date=self._d(104),
            cost_method=self._avco,
            portfolio_mode=Report.MODE_IGNORE,
            account_mode=Report.MODE_IGNORE,
            strategy1_mode=Report.MODE_IGNORE,
            strategy2_mode=Report.MODE_IGNORE,
            strategy3_mode=Report.MODE_IGNORE,
            trn_cols=trn_cols,
            item_cols=item_cols,
            approach_multiplier=1.0,
            trn_dump_all=False
        )

    def _test_pl_full_fx_fixed_cash_in_out_1(self):
        self._ccy_hist(self.gbp, self._d(101), 1.45)
        self._ccy_hist(self.gbp, self._d(104), 1.2)

        self._ccy_hist(self.chf, self._d(101), 1.15)
        self._ccy_hist(self.chf, self._d(104), 1.1)

        self._ccy_hist(self.cad, self._d(101), 0.85)
        self._ccy_hist(self.cad, self._d(104), 0.9)

        self._t(t_class=self._cash_inflow,
                trn_ccy=self.gbp, position=0,
                stl_ccy=self.chf, cash=100, fx_rate=0.75,
                acc_date_days=101, cash_date_days=101,
                alloc_bl=self.bond1, alloc_pl=self.bond2)

        # self._t(t_class=self._cash_inflow,
        #         trn_ccy=self.gbp, position=0,
        #         stl_ccy=self.rub, cash=100, fx_rate=0.75,
        #         acc_date_days=101, cash_date_days=101,
        #         alloc_bl=self.bond1, alloc_pl=self.bond2)

        # r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(104), report_currency=self.cad,
        #            cost_method=self._avco)
        # b = ReportBuilder(instance=r)
        # b.build_balance()
        # self._dump(b, 'test_pl_full_fx_fixed_cash_in_out_1')
        trn_cols = self.TRN_COLS_ALL
        item_cols = self.ITEM_COLS_ALL
        item_cols = [x for x in item_cols if ('_loc' not in x) and ('opened' not in x) and ('closed' not in x)]
        self._simple_run(
            'test_pl_full_fx_fixed_cash_in_out_1',
            report_currency=self.cad,
            report_date=self._d(104),
            cost_method=self._avco,
            portfolio_mode=Report.MODE_IGNORE,
            account_mode=Report.MODE_IGNORE,
            strategy1_mode=Report.MODE_IGNORE,
            strategy2_mode=Report.MODE_IGNORE,
            strategy3_mode=Report.MODE_IGNORE,
            trn_cols=trn_cols,
            item_cols=item_cols,
            approach_multiplier=1.0,
            trn_dump_all=False
        )

    def _test_pl_full_fx_fixed_instr_pl_1(self):
        self._ccy_hist(self.gbp, self._d(101), 1.45)
        self._ccy_hist(self.gbp, self._d(104), 1.2)

        self._ccy_hist(self.chf, self._d(101), 1.15)
        self._ccy_hist(self.chf, self._d(104), 1.1)

        self._ccy_hist(self.cad, self._d(101), 0.85)
        self._ccy_hist(self.cad, self._d(104), 0.9)

        self._t(t_class=self._instrument_pl,
                instr=self.bond0,
                trn_ccy=self.gbp, position=0,
                stl_ccy=self.chf, principal=0, carry=1000, overheads=-20, fx_rate=0.75,
                acc_date_days=101, cash_date_days=101,
                alloc_bl=self.bond1, alloc_pl=self.bond2)

        # r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(104), report_currency=self.cad,
        #            cost_method=self._avco)
        # b = ReportBuilder(instance=r)
        # b.build()
        # self._dump(b, 'test_pl_full_fx_fixed_instr_pl_1')
        trn_cols = self.TRN_COLS_ALL
        item_cols = self.ITEM_COLS_ALL
        item_cols = [x for x in item_cols if ('_loc' not in x) and ('opened' not in x) and ('closed' not in x)]
        self._simple_run(
            'test_pl_full_fx_fixed_instr_pl_1',
            report_currency=self.cad,
            report_date=self._d(104),
            cost_method=self._avco,
            portfolio_mode=Report.MODE_IGNORE,
            account_mode=Report.MODE_IGNORE,
            strategy1_mode=Report.MODE_IGNORE,
            strategy2_mode=Report.MODE_IGNORE,
            strategy3_mode=Report.MODE_IGNORE,
            trn_cols=trn_cols,
            item_cols=item_cols,
            approach_multiplier=1.0,
            trn_dump_all=False
        )

    def _test_pl_full_fx_fixed_trn_pl_1(self):
        self._ccy_hist(self.gbp, self._d(101), 1.45)
        self._ccy_hist(self.gbp, self._d(104), 1.2)

        self._ccy_hist(self.chf, self._d(101), 1.15)
        self._ccy_hist(self.chf, self._d(104), 1.1)

        self._ccy_hist(self.cad, self._d(101), 0.85)
        self._ccy_hist(self.cad, self._d(104), 0.9)

        self._t(t_class=self._transaction_pl,
                trn_ccy=self.gbp, position=0,
                stl_ccy=self.chf, carry=1000, overheads=-20, fx_rate=0.75,
                acc_date_days=101, cash_date_days=101,
                alloc_bl=self.bond1, alloc_pl=self.bond2)

        # r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(104), report_currency=self.cad,
        #            cost_method=self._avco)
        # b = ReportBuilder(instance=r)
        # b.build()
        # self._dump(b, 'test_pl_full_fx_fixed_trn_pl_1')
        trn_cols = self.TRN_COLS_ALL
        item_cols = self.ITEM_COLS_ALL
        item_cols = [x for x in item_cols if ('_loc' not in x) and ('opened' not in x) and ('closed' not in x)]
        self._simple_run(
            'test_pl_full_fx_fixed_trn_pl_1',
            report_currency=self.cad,
            report_date=self._d(104),
            cost_method=self._avco,
            portfolio_mode=Report.MODE_IGNORE,
            account_mode=Report.MODE_IGNORE,
            strategy1_mode=Report.MODE_IGNORE,
            strategy2_mode=Report.MODE_IGNORE,
            strategy3_mode=Report.MODE_IGNORE,
            trn_cols=trn_cols,
            item_cols=item_cols,
            approach_multiplier=1.0,
            trn_dump_all=False
        )

    def _test_pl_full_fx_fixed_fx_trade_1(self):
        self._ccy_hist(self.gbp, self._d(101), 1.45)
        self._ccy_hist(self.gbp, self._d(104), 1.2)

        self._ccy_hist(self.chf, self._d(101), 1.15)
        self._ccy_hist(self.chf, self._d(104), 1.1)

        self._ccy_hist(self.cad, self._d(101), 0.85)
        self._ccy_hist(self.cad, self._d(104), 0.9)

        self._ccy_hist(self.rub, self._d(101), 1 / 60)
        self._ccy_hist(self.rub, self._d(104), 1 / 65)

        self._t(t_class=self._fx_tade,
                trn_ccy=self.gbp, position=100,
                stl_ccy=self.chf, principal=-140,
                acc_date_days=101, cash_date_days=101,
                alloc_bl=self.bond1, alloc_pl=self.bond2)

        # self._t(t_class=self._fx_tade,
        #         trn_ccy=self.gbp, position=100,
        #         stl_ccy=self.rub, principal=-140,
        #         acc_date_days=101, cash_date_days=101,
        #         alloc_bl=self.bond1, alloc_pl=self.bond2)

        # r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(104), report_currency=self.cad,
        #            cost_method=self._avco)
        # b = ReportBuilder(instance=r)
        # b.build()
        # self._dump(b, 'test_pl_full_fx_fixed_fx_trade_1')
        trn_cols = self.TRN_COLS_ALL
        trn_cols = [x for x in trn_cols if ('_loc' not in x) and ('opened' not in x) and ('closed' not in x)]
        item_cols = self.ITEM_COLS_ALL
        item_cols = [x for x in item_cols if ('_loc' not in x) and ('opened' not in x) and ('closed' not in x)]
        self._simple_run(
            'test_pl_full_fx_fixed_fx_trade_1',
            report_currency=self.cad,
            report_date=self._d(104),
            cost_method=self._avco,
            portfolio_mode=Report.MODE_IGNORE,
            account_mode=Report.MODE_IGNORE,
            strategy1_mode=Report.MODE_IGNORE,
            strategy2_mode=Report.MODE_IGNORE,
            strategy3_mode=Report.MODE_IGNORE,
            trn_cols=trn_cols,
            item_cols=item_cols,
            approach_multiplier=1.0,
            # trn_dump_all=False
        )

    def _test_mismatch_0(self):
        for i in range(0, 2):
            self._t(t_class=self._buy,
                    instr=self.bond0, position=100,
                    stl_ccy=self.cad, cash=-10, principal=0, carry=0, overheads=0,
                    p=self.p1, acc_pos=self.a1_1,
                    link_instr=self.bond1)

            self._t(t_class=self._buy,
                    instr=self.bond0, position=100,
                    stl_ccy=self.chf, cash=0, principal=-10, carry=0, overheads=0,
                    p=self.p1, acc_pos=self.a1_1,
                    link_instr=self.bond1)

            self._t(t_class=self._buy,
                    instr=self.bond0, position=100,
                    stl_ccy=self.usd, cash=0, principal=0, carry=10, overheads=0,
                    p=self.p2, acc_pos=self.a1_2,
                    link_instr=self.bond1)

            self._t(t_class=self._buy,
                    instr=self.bond0, position=100,
                    stl_ccy=self.rub, cash=0, principal=0, carry=0, overheads=10,
                    p=self.p2, acc_pos=self.a1_2,
                    link_instr=self.bond1)

        r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(14))
        b = ReportBuilder(instance=r)
        b.build_balance()
        self._dump(b, 'test_mismatch_0')

    def _test_approach_alloc_0(self):
        # settings.DEBUG = True

        self.bond0.user_code = 'I1'
        self.bond0.price_multiplier = 5.0
        self.bond0.accrued_multiplier = 0.0
        self.bond0.save()
        self.bond1.user_code = 'A1'
        self.bond1.save()
        self.bond2.user_code = 'A2'
        self.bond2.save()
        self.bond3.user_code = 'A3'
        self.bond3.save()
        self._t(t_class=self._buy,
                instr=self.bond0, position=5,
                stl_ccy=self.usd, principal=-10, carry=0, overheads=0,
                alloc_bl=self.bond1, alloc_pl=self.bond1)

        self._t(t_class=self._buy,
                instr=self.bond0, position=5,
                stl_ccy=self.usd, principal=-15, carry=0, overheads=0,
                alloc_bl=self.bond2, alloc_pl=self.bond2)

        self._t(t_class=self._sell,
                instr=self.bond0, position=-5,
                stl_ccy=self.usd, principal=20, carry=0, overheads=0,
                alloc_bl=self.bond3, alloc_pl=self.bond3)

        r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(10),
                   approach_multiplier=1.0)
        b = ReportBuilder(instance=r)
        b.build_balance()
        self._dump(b, 'test_approach_alloc_0')

    def _test_approach_alloc_1(self):
        self.bond0.user_code = 'instr1'
        self.bond0.save()
        self.bond1.user_code = 'A1'
        self.bond1.save()
        self.bond2.user_code = 'A2'
        self.bond2.save()
        self.bond3.user_code = 'A3'
        self.bond3.save()

        self._t(t_class=self._buy,
                instr=self.bond0, position=5,
                stl_ccy=self.usd, principal=-100, carry=0, overheads=0,
                alloc_bl=self.bond1, alloc_pl=self.bond2)

        self._t(t_class=self._buy,
                instr=self.bond0, position=5,
                stl_ccy=self.usd, principal=-150, carry=0, overheads=0,
                alloc_bl=self.bond1, alloc_pl=self.bond2)

        self._t(t_class=self._sell,
                instr=self.bond0, position=-10,
                stl_ccy=self.usd, principal=450, carry=0, overheads=0,
                alloc_bl=self.bond1, alloc_pl=self.bond2)

        r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(0),
                   approach_multiplier=1.0)
        b = ReportBuilder(instance=r)
        b.build_balance()
        self._dump(b, 'test_approach_alloc_1')

    def test_approach_str1_0(self):
        self.bond0.user_code = 'I1'
        self.bond0.price_multiplier = 5.0
        self.bond0.accrued_multiplier = 0.0
        self.bond0.save()
        self.bond1.user_code = 'A1'
        self.bond1.save()
        self.bond2.user_code = 'A2'
        self.bond2.save()
        self.bond3.user_code = 'A3'
        self.bond3.save()
        approach_multiplier = 1.0

        self._t(t_class=self._buy,
                instr=self.bond0, position=5,
                stl_ccy=self.usd, principal=-10, carry=0, overheads=0,
                alloc_bl=self.bond1, alloc_pl=self.bond1,
                s1_pos=self.s1_1_1_1)

        self._t(t_class=self._buy,
                instr=self.bond0, position=5,
                stl_ccy=self.usd, principal=-15, carry=0, overheads=0,
                alloc_bl=self.bond2, alloc_pl=self.bond2,
                s1_pos=self.s1_1_1_2)

        self._t(t_class=self._sell,
                instr=self.bond0, position=-5,
                stl_ccy=self.usd, principal=20, carry=0, overheads=0,
                alloc_bl=self.bond3, alloc_pl=self.bond3,
                s1_pos=self.s1_1_1_3)

        r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(0),
                   approach_multiplier=approach_multiplier,
                   strategy1_mode=Report.MODE_INDEPENDENT)
        b = ReportBuilder(instance=r)
        b.build_balance()
        self._dump(b, 'test_approach_str1_0: STRATEGY_INDEPENDENT')

        r = Report(master_user=self.m, pricing_policy=self.pp, report_date=self._d(0),
                   approach_multiplier=approach_multiplier,
                   strategy1_mode=Report.MODE_INTERDEPENDENT)
        b = ReportBuilder(instance=r)
        b.build_balance()
        self._dump(b, 'test_approach_str1_0: STRATEGY_INTERDEPENDENT')

    def _test_instr_contract_for_difference(self):
        tinstr = InstrumentType.objects.create(master_user=self.m,
                                               instrument_class_id=InstrumentClass.CONTRACT_FOR_DIFFERENCE, name='cfd1')
        instr = Instrument.objects.create(master_user=self.m, name="cfd, USD/USD", instrument_type=tinstr,
                                          pricing_currency=self.usd, price_multiplier=1.0,
                                          accrued_currency=self.usd, accrued_multiplier=1.0)

        t0 = self._t(t_class=self._buy, instr=instr, position=3, acc_date_days=1, cash_date_days=1,
                     stl_ccy=self.usd, cash=0, principal=-3600000, carry=-5000, overheads=-100)
        t1 = self._t(t_class=self._buy, instr=instr, position=2, acc_date_days=2, cash_date_days=2,
                     stl_ccy=self.usd, cash=0, principal=-2450000, carry=-2000, overheads=-100)
        t2 = self._t(t_class=self._buy, instr=instr, position=1, acc_date_days=3, cash_date_days=3,
                     stl_ccy=self.usd, cash=0, principal=-1230000, carry=-1000, overheads=-100)
        t3 = self._t(t_class=self._sell, instr=instr, position=-1, acc_date_days=4, cash_date_days=4,
                     stl_ccy=self.usd, cash=0, principal=1250000, carry=8000, overheads=-100)
        t4 = self._t(t_class=self._sell, instr=instr, position=-3, acc_date_days=5, cash_date_days=5,
                     stl_ccy=self.usd, cash=0, principal=3825000, carry=9000, overheads=-100)

        from poms.transactions.utils import calc_cash_for_contract_for_difference
        calc_cash_for_contract_for_difference(transaction=None,
                                              instrument=instr,
                                              portfolio=self.m.portfolio,
                                              account=self.m.account,
                                              member=None,
                                              is_calculate_for_newer=False,
                                              is_calculate_for_all=True,
                                              save=True)

    def _test_xnpv_xirr_duration(self):
        from poms.common.formula_accruals import f_xnpv, f_xirr, f_duration
        from datetime import date

        # dates = [date(2008, 1, 1), date(2008, 3, 1), date(2008, 10, 30), date(2009, 2, 15), date(2009, 4, 1), ]
        # values = [-10000, 2750, 4250, 3250, 2750, ]

        # dates = [date(2016, 2, 16), date(2016, 3, 10), date(2016, 9, 1), date(2017, 1, 17), ]
        # values = [-90, 5, 5, 105, ]

        dates = [date(2016, 2, 16), date(2016, 3, 10), date(2016, 9, 1), date(2017, 1, 17), ]
        values = [-90, 5, 5, 105, ]
        data = [(d, v) for d, v in zip(dates, values)]

        # xnpv    : 16.7366702148651
        # xirr    : 0.3291520343150294
        # duration: 0.6438341602180792
        _l.debug('>')
        _l.debug('xnpv.1: %s', f_xnpv(data, 0.09))
        _l.debug('xirr.1: %s', f_xirr(data))
        # _l.debug('xirr.2: %s', f_xirr(data, method='newton'))
        _l.debug('duration.1: %s', f_duration(data))

        import timeit
        for i in range(100, 1000, 100):
            _l.debug('timeit.xirr.1.skip: %s -> %s', i, timeit.Timer(lambda: f_xirr(data)).timeit(i))

        ti1 = Instrument.objects.create(master_user=self.m, name="a", instrument_type=self.m.instrument_type,
                                        pricing_currency=self.usd, price_multiplier=1.0,
                                        accrued_currency=self.usd, accrued_multiplier=1.0,
                                        maturity_date=date(2017, 1, 1), maturity_price=100)
        AccrualCalculationSchedule.objects.create(instrument=ti1,
                                                  accrual_start_date=date(2016, 1, 1),
                                                  first_payment_date=date(2016, 2, 1),
                                                  accrual_size=5,
                                                  accrual_calculation_model_id=AccrualCalculationModel.ACT_365,
                                                  periodicity_id=Periodicity.MONTHLY,
                                                  periodicity_n=1)
        _l.debug('get_future_accrual_payments.1: %s', ti1.get_future_accrual_payments())
        _l.debug('get_future_accrual_payments.2: %s', ti1.get_future_accrual_payments(begin_date=date(2016, 2, 27)))
        _l.debug('get_future_accrual_payments.2: %s', ti1.get_future_accrual_payments(begin_date=date(2016, 3, 1)))
        data = [(date(2016, 3, 14), 83)]
        _l.debug('get_future_accrual_payments.2: %s',
                 ti1.get_future_accrual_payments(data=data, begin_date=date(2016, 3, 15)))
        _l.debug('get_future_accrual_payments.2: %s', ti1.get_future_accrual_payments(data=data))

    def _test_xnpv_xirr_duration_perf(self):
        from poms.common.formula_accruals import f_xirr
        from datetime import date

        dates = [date(2016, 2, 16), date(2016, 3, 10), date(2016, 9, 1), date(2017, 1, 17), ]
        values = [-90, 5, 5, 105, ]
        data = [(d, v) for d, v in zip(dates, values)]

        import timeit

        _l.debug('-' * 79)
        _l.debug('xirr:')
        # for method in ['newton', 'brentq']:
        #     _l.debug('  method: %s', method)
        #     for i in range(1000, 30000, 1000):
        #         _l.debug('    %s -> %s', i, timeit.Timer(lambda: f_xirr(data, method=method)).timeit(i))
        for i in range(1000, 30000, 1000):
            _l.debug('    %s -> %s', i, timeit.Timer(lambda: f_xirr(data)).timeit(i))

    def _test_pl_date_interval_1(self):
        show_trns = False

        self._t(t_class=self._buy, instr=self.bond0, position=100,
                stl_ccy=self.usd, principal=-180., carry=-5., overheads=-15.,
                acc_date_days=1, cash_date_days=1)

        self._t(t_class=self._sell, instr=self.bond0, position=-50,
                stl_ccy=self.usd, principal=90., carry=2.5, overheads=-15.,
                acc_date_days=11, cash_date_days=11)

        self._t(t_class=self._sell, instr=self.bond0, position=-50,
                stl_ccy=self.usd, principal=90., carry=2.5, overheads=-15.,
                acc_date_days=21, cash_date_days=21)

        pl_first_date = self._d(10)
        # report_date = self._d(12)
        report_date = self._d(22)

        r = Report(master_user=self.m, pricing_policy=self.pp, report_date=pl_first_date)
        b = ReportBuilder(instance=r)
        b.build_balance()
        self._dump(b, 'test_pl_date_interval_1: pl_first_date', show_trns=show_trns)

        r = Report(master_user=self.m, pricing_policy=self.pp, report_date=report_date)
        b = ReportBuilder(instance=r)
        b.build_balance()
        self._dump(b, 'test_pl_date_interval_1: report_date', show_trns=show_trns)

        r = Report(master_user=self.m, pricing_policy=self.pp, pl_first_date=pl_first_date, report_date=report_date)
        b = ReportBuilder(instance=r)
        b.build_balance()
        self._dump(b, 'test_pl_date_interval_1: pl_first_date abd report_date', show_trns=show_trns)

    def _test_performance(self):
        # from django.conf import settings
        # settings.DEBUG = True

        ltcls = list(TransactionClass.objects.all())
        ltt = list(TransactionType.objects.filter(master_user=self.m).all())
        linstr = list(Instrument.objects.filter(master_user=self.m).all())
        lccy = list(Currency.objects.filter(master_user=self.m).all())
        lp = list(Portfolio.objects.filter(master_user=self.m).all())
        lacc = list(Account.objects.filter(master_user=self.m).all())
        ls1 = list(Strategy1.objects.filter(master_user=self.m).all())
        ls2 = list(Strategy2.objects.filter(master_user=self.m).all())
        ls3 = list(Strategy3.objects.filter(master_user=self.m).all())
        lr = list(Responsible.objects.filter(master_user=self.m).all())
        lc = list(Counterparty.objects.filter(master_user=self.m).all())

        days = 1
        code = 1
        for g in range(0, 10):
            _l.info('group: %s', g)

            ctrns = []
            trns = []
            for i in range(0, 100):
                # ct = ComplexTransaction(
                #     transaction_type=random.choice(ltt),
                #     date=self._d(days),
                #     status=ComplexTransaction.PRODUCTION,
                #     code=code
                # )
                ct = None

                transaction_class = random.choice(ltcls)

                if transaction_class.id == TransactionClass.BUY:
                    position_size_with_sign = random.randint(0, 1000)
                elif transaction_class.id == TransactionClass.SELL:
                    position_size_with_sign = - random.randint(0, 1000)
                else:
                    position_size_with_sign = 0
                principal_with_sign = random.randint(0, 1000)
                carry_with_sign = random.randint(0, 1000)
                overheads_with_sign = -random.randint(0, 100)

                t = Transaction(
                    master_user=self.m,
                    complex_transaction=ct,
                    complex_transaction_order=1,
                    transaction_code=code,
                    transaction_class=transaction_class,
                    instrument=random.choice(linstr),
                    transaction_currency=random.choice(lccy),
                    position_size_with_sign=position_size_with_sign,
                    settlement_currency=random.choice(lccy),
                    cash_consideration=principal_with_sign + carry_with_sign + overheads_with_sign,
                    principal_with_sign=principal_with_sign,
                    carry_with_sign=carry_with_sign,
                    overheads_with_sign=overheads_with_sign,
                    transaction_date=self._d(days),
                    accounting_date=self._d(days),
                    cash_date=self._d(days),
                    portfolio=random.choice(lp),
                    account_position=random.choice(lacc),
                    account_cash=random.choice(lacc),
                    account_interim=random.choice(lacc),
                    strategy1_position=random.choice(ls1),
                    strategy1_cash=random.choice(ls1),
                    strategy2_position=random.choice(ls2),
                    strategy2_cash=random.choice(ls2),
                    strategy3_position=random.choice(ls3),
                    strategy3_cash=random.choice(ls3),
                    responsible=random.choice(lr),
                    counterparty=random.choice(lc),
                    linked_instrument=random.choice(linstr),
                    allocation_balance=random.choice(linstr),
                    allocation_pl=random.choice(linstr),
                )

                if ct:
                    ctrns.append(ct)
                if t:
                    trns.append(t)

                # days += 1
                code += 1

            if ctrns:
                ComplexTransaction.objects.bulk_create(ctrns)
            if trns:
                Transaction.objects.bulk_create(trns)

        def as_json(r):
            from poms.reports.builders.balance_serializers import ReportSerializer

            _l.debug('----------------------')

            t1 = time.perf_counter()
            serializer = ReportSerializer(instance=r, many=False, context={'master_user': self.m, 'member': self.mm})
            data = serializer.data
            t2 = time.perf_counter()
            _l.debug('serialize: time=%s', t2 - t1)

            t1 = time.perf_counter()
            json_data = json.dumps(data, cls=DjangoJSONEncoder)
            t2 = time.perf_counter()
            _l.debug('json: len=%s, time=%s', len(json_data), t2 - t1)

            t1 = time.perf_counter()
            zjson_data = zlib.compress(json_data.encode())
            t2 = time.perf_counter()
            _l.debug('xjson: len=%s, time=%s', len(zjson_data), t2 - t1)

        r = Report(master_user=self.m, member=self.mm, report_currency=self.cad, report_date=self._d(14),
                   pricing_policy=self.pp)
        b = ReportBuilder(instance=r)
        b.build_balance(full=True)
        as_json(r)

        # r = Report(master_user=self.m, member=self.mm, report_currency=self.cad, report_date=self._d(14),
        #            pricing_policy=self.pp)
        # b = ReportBuilder(instance=r)
        # b.build_pl(full=True)
        # as_json(r)
        pass

    def _test_ytm(self):
        instr = self._instr('instr_ytm', pricing_ccy=self.gbp, price_mult=0.01, accrued_ccy=self.eur,
                            accrued_mult=0.005, maturity_date=date(2017, 12, 31), maturity_price=50)

        InstrumentFactorSchedule.objects.create(instrument=instr, effective_date=date(2016, 5, 11), factor_value=1.0)
        InstrumentFactorSchedule.objects.create(instrument=instr, effective_date=date(2016, 11, 11), factor_value=0.75)
        InstrumentFactorSchedule.objects.create(instrument=instr, effective_date=date(2017, 5, 15), factor_value=0.25)

        AccrualCalculationSchedule.objects.create(
            instrument=instr,
            accrual_start_date=date(2016, 5, 11),
            first_payment_date=date(2016, 8, 9),
            accrual_size=-25.0,
            accrual_calculation_model=AccrualCalculationModel.objects.get(pk=AccrualCalculationModel.ACT_365),
            periodicity=Periodicity.objects.get(pk=Periodicity.QUARTERLY),
            periodicity_n=1,
        )
        AccrualCalculationSchedule.objects.create(
            instrument=instr,
            accrual_start_date=date(2017, 5, 14),
            first_payment_date=date(2017, 6, 13),
            accrual_size=15.0,
            accrual_calculation_model=AccrualCalculationModel.objects.get(pk=AccrualCalculationModel.ACT_365),
            periodicity=Periodicity.objects.get(pk=Periodicity.QUARTERLY),
            periodicity_n=1,
        )

        # test_date = date(2016, 8, 1)
        test_date = date(2017, 5, 7)
        _l.info('test_date: %s', test_date)

        self._ccy_hist(self.gbp, test_date, 1.4)
        self._ccy_hist(self.eur, test_date, 1.1)

        data = instr.get_future_coupons(begin_date=test_date, with_maturity=False, factor=True)
        for d, v in data:
            _l.info('1: %s -> %s', d, v)

        data = instr.get_future_coupons(begin_date=test_date, with_maturity=False, factor=False)
        for d, v in data:
            _l.info('2: %s -> %s', d, v)

        class DummyReport:
            report_date = None

        class DummyYTM(YTMMixin):
            instr = None
            report = DummyReport()
            instr_price_cur_principal_price = None
            instr_pricing_ccy_cur_fx = None
            instr_accrued_ccy_cur_fx = None

            def get_instr_ytm_data_d0_v0(self, dt):
                return dt, -(
                    self.instr_price_cur_principal_price *
                    self.instr.price_multiplier *
                    self.instr.get_factor(dt)
                )

            def get_instr_ytm_x0(self, dt):
                try:
                    accrual_size = self.instr.get_accrual_size(dt)
                    return (accrual_size * self.instr.accrued_multiplier) * \
                           (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx) / \
                           (self.instr_price_cur_principal_price * self.instr.price_multiplier)
                except ArithmeticError:
                    return 0

        ytm = DummyYTM()
        ytm.instr = instr
        ytm.report.report_date = test_date
        ytm.instr_price_cur_principal_price = 47
        ytm.instr_pricing_ccy_cur_fx = 1.4
        ytm.instr_accrued_ccy_cur_fx = 1.1

        data = ytm.get_instr_ytm_data()
        for d, v in data:
            _l.info('3: %s -> %s', d, v)

        _l.info('4: %s', ytm.get_instr_ytm())

            # cpns = instr.get_future_coupons(begin_date=date(2017, 5, 7), with_maturity=False)
            # for d, v in cpns:
            #     _l.info('2.: %s -> %s', d,v)

    def _test_from_csv_td_1(self):
        test_prefix = 'td_2'
        base_path = os.path.join(settings.BASE_DIR, 'poms', 'reports', 'tests_data')
        load_from_csv(
            master_user=self.m,
            instr=os.path.join(base_path, '%s_instrument.csv' % test_prefix),
            instr_price_hist=os.path.join(base_path, '%s_price_history.csv' % test_prefix),
            ccy_fx_rate=os.path.join(base_path, '%s_fx_history.csv' % test_prefix),
            trn=os.path.join(base_path, '%s_transactions.csv' % test_prefix)
        )
        # Transaction.objects.filter(master_user=self.m).exclude(transaction_class_id=TransactionClass.TRANSACTION_PL).delete()
        # Transaction.objects.filter(master_user=self.m).exclude(transaction_code__in=[7859, 7860]).delete()
        # Transaction.objects.filter(master_user=self.m).exclude(
        #     instrument__user_code__in=['CH0336352825'],
        # ).delete()

        cost_method = self._avco

        if test_prefix == 'td_1':
            report_dates = [
                date(2017, 3, 10),  # 1,  2,  3
                date(2017, 3, 15),  # 4,  5,  6
                date(2017, 3, 25),  # 7,  8,  9
                date(2017, 3, 28),  # 10, 11, 12
            ]
        elif test_prefix == 'td_2':
            report_dates = [
                date(2017, 2, 3),  # 1,  2,  3
                date(2017, 2, 7),  # 4,  5,  6
                date(2017, 2, 15),  # 7,  8,  9
                date(2017, 2, 23),  # 10, 11, 12
            ]
        else:
            report_dates = []
        report_currencies = [
            Currency.objects.get(master_user=self.m, user_code='USD'),  # 1, 4, 7, 10
            Currency.objects.get(master_user=self.m, user_code='EUR'),  # 2, 5, 8, 11
            Currency.objects.get(master_user=self.m, user_code='GBP'),  # 3, 6, 9, 12
        ]
        # portfolio_modes = [
        #     Report.MODE_IGNORE,
        #     Report.MODE_INDEPENDENT,
        # ]
        # account_modes = [
        #     Report.MODE_IGNORE,
        #     Report.MODE_INDEPENDENT,
        # ]
        # strategy1_modes = [
        #     Report.MODE_IGNORE,
        #     Report.MODE_INDEPENDENT,
        #     Report.MODE_INTERDEPENDENT,
        # ]
        # strategy2_modes = [
        #     Report.MODE_IGNORE,
        #     Report.MODE_INDEPENDENT,
        #     Report.MODE_INTERDEPENDENT,
        # ]
        # strategy3_modes = [
        #     Report.MODE_IGNORE,
        #     Report.MODE_INDEPENDENT,
        #     Report.MODE_INTERDEPENDENT,
        # ]
        approach_multipliers = [0.0, 0.5, 1.0]

        approach_map = {
            '0/100': 0.0,
            '50/50': 0.5,
            '100/0': 1.0,
        }

        bl_consolidations = [
            # {
            #     'portfolio_mode': Report.MODE_IGNORE,
            #     'account_mode': Report.MODE_IGNORE,
            #     'strategy1_mode': Report.MODE_IGNORE,
            #     'strategy2_mode': Report.MODE_IGNORE,
            #     'strategy3_mode': Report.MODE_IGNORE,
            #     'show_transaction_details': True,
            # },
            {
                'portfolio_mode': Report.MODE_INDEPENDENT,
                'account_mode': Report.MODE_INDEPENDENT,
                'strategy1_mode': Report.MODE_INDEPENDENT,
                'strategy2_mode': Report.MODE_INDEPENDENT,
                'strategy3_mode': Report.MODE_INDEPENDENT,
                'show_transaction_details': True,
            },
            {
                'portfolio_mode': Report.MODE_INDEPENDENT,
                'account_mode': Report.MODE_INDEPENDENT,
                'strategy1_mode': Report.MODE_IGNORE,
                'strategy2_mode': Report.MODE_IGNORE,
                'strategy3_mode': Report.MODE_IGNORE,
                'show_transaction_details': True,
            },
            {
                'portfolio_mode': Report.MODE_INDEPENDENT,
                'account_mode': Report.MODE_IGNORE,
                'strategy1_mode': Report.MODE_IGNORE,
                'strategy2_mode': Report.MODE_IGNORE,
                'strategy3_mode': Report.MODE_IGNORE,
                'show_transaction_details': True,
            },
            {
                'portfolio_mode': Report.MODE_IGNORE,
                'account_mode': Report.MODE_INDEPENDENT,
                'strategy1_mode': Report.MODE_IGNORE,
                'strategy2_mode': Report.MODE_IGNORE,
                'strategy3_mode': Report.MODE_IGNORE,
                'show_transaction_details': True,
            },
        ]
        pl_consolidations = bl_consolidations + [
            {
                'portfolio_mode': Report.MODE_INDEPENDENT,
                'account_mode': Report.MODE_INDEPENDENT,
                'strategy1_mode': Report.MODE_INTERDEPENDENT,
                'strategy2_mode': Report.MODE_INTERDEPENDENT,
                'strategy3_mode': Report.MODE_INTERDEPENDENT,
                'show_transaction_details': True,
            },
        ]
        pl_consolidations = []

        trn_cols = [
            'pk', 'trn_code', 'trn_cls', 'multiplier', 'instr', 'trn_ccy', 'pos_size', 'stl_ccy', 'cash', 'principal',
            'carry', 'overheads', 'ref_fx', 'acc_date', 'cash_date', 'prtfl', 'acc_pos', 'acc_cash', 'acc_interim',
            'str1_pos', 'str1_cash', 'str2_pos', 'str2_cash', 'str3_pos', 'str3_cash', 'link_instr', 'alloc_bl',
            'alloc_pl', 'trade_price', 'notes', 'report_ccy_cur_fx', 'report_ccy_cash_hist_fx',
            'report_ccy_acc_hist_fx', 'instr_price_cur_principal_price', 'instr_price_cur_accrued_price',
            'instr_pricing_ccy_cur_fx', 'instr_accrued_ccy_cur_fx', 'trn_ccy_cash_hist_fx', 'trn_ccy_acc_hist_fx',
            'trn_ccy_cur_fx', 'stl_ccy_cash_hist_fx', 'stl_ccy_acc_hist_fx', 'stl_ccy_cur_fx',
        ]
        item_cols = [
            'type_code', 'subtype_code', 'instr', 'ccy', 'trn_ccy', 'prtfl', 'acc', 'str1', 'str2', 'str3',
            'pricing_ccy', 'last_notes', 'mismatch', 'mismatch_prtfl', 'mismatch_acc', 'alloc_bl', 'alloc_pl',
            'report_ccy_cur_fx', 'instr_price_cur_principal_price', 'instr_price_cur_accrued_price',
            'instr_pricing_ccy_cur_fx', 'instr_accrued_ccy_cur_fx', 'ccy_cur_fx', 'pricing_ccy_cur_fx',
            'instr_principal_res', 'instr_accrued_res', 'exposure_res', 'exposure_loc', 'instr_accrual',
            'instr_accrual_accrued_price', 'pos_size', 'market_value_res', 'market_value_loc', 'cost_res', 'ytm',
            'modified_duration', 'ytm_at_cost', 'time_invested_days', 'time_invested', 'gross_cost_res',
            'gross_cost_loc', 'net_cost_res', 'net_cost_loc', 'principal_invested_res', 'principal_invested_loc',
            'amount_invested_res', 'amount_invested_loc', 'pos_return_res', 'pos_return_loc', 'net_pos_return_res',
            'net_pos_return_loc', 'daily_price_change', 'mtd_price_change', 'principal_res', 'carry_res',
            'overheads_res', 'total_res', 'principal_loc', 'carry_loc', 'overheads_loc', 'total_loc',
            'principal_closed_res', 'carry_closed_res', 'overheads_closed_res', 'total_closed_res',
            'principal_closed_loc', 'carry_closed_loc', 'overheads_closed_loc', 'total_closed_loc',
            'principal_opened_res', 'carry_opened_res', 'overheads_opened_res', 'total_opened_res',
            'principal_opened_loc', 'carry_opened_loc', 'overheads_opened_loc', 'total_opened_loc', 'principal_fx_res',
            'carry_fx_res', 'overheads_fx_res', 'total_fx_res', 'principal_fx_loc', 'carry_fx_loc', 'overheads_fx_loc',
            'total_fx_loc', 'principal_fx_closed_res', 'carry_fx_closed_res', 'overheads_fx_closed_res',
            'total_fx_closed_res', 'principal_fx_closed_loc', 'carry_fx_closed_loc', 'overheads_fx_closed_loc',
            'total_fx_closed_loc', 'principal_fx_opened_res', 'carry_fx_opened_res', 'overheads_fx_opened_res',
            'total_fx_opened_res', 'principal_fx_opened_loc', 'carry_fx_opened_loc', 'overheads_fx_opened_loc',
            'total_fx_opened_loc', 'principal_fixed_res', 'carry_fixed_res', 'overheads_fixed_res', 'total_fixed_res',
            'principal_fixed_loc', 'carry_fixed_loc', 'overheads_fixed_loc', 'total_fixed_loc',
            'principal_fixed_closed_res', 'carry_fixed_closed_res', 'overheads_fixed_closed_res',
            'total_fixed_closed_res', 'principal_fixed_closed_loc', 'carry_fixed_closed_loc',
            'overheads_fixed_closed_loc', 'total_fixed_closed_loc', 'principal_fixed_opened_res',
            'carry_fixed_opened_res', 'overheads_fixed_opened_res', 'total_fixed_opened_res',
            'principal_fixed_opened_loc', 'carry_fixed_opened_loc', 'overheads_fixed_opened_loc',
            'total_fixed_opened_loc', 'group_code', 'detail_trn',
            'user_code', 'name',
        ]

        # trn_cols = trn_cols + ['ytm', ]
        # trn_cols = ['pk', 'trn_code', 'trn_cls', 'instr', 'pos_size', 'is_cloned', 'is_hidden', 'trade_price', 'ytm', 'weighted_ytm',
        #             'remaining_pos_size_percent', 'remaining_pos_size', 'balance_pos_size', 'multiplier']

        # trn_cols = self.TRN_COLS_ALL
        # item_cols = self.ITEM_COLS_ALL

        # trn_cols = [x for x in trn_cols if x not in
        #             {'rolling_pos_size', 'remaining_pos_size', 'remaining_pos_size_percent', 'trn_date', 'str2_pos',
        #              'str2_cash', 'str3_pos', 'str3_cash'}]
        #
        # item_cols = [x for x in item_cols if x not in
        #              {'subtype_code', 'str2', 'str3', 'last_notes', 'mismatch_prtfl', 'mismatch_acc', 'alloc_bl',
        #               'alloc_pl', 'instr_accrual', 'mismatch', 'report_ccy_cur_fx'}]

        # trn_cols = [x for x in trn_cols if '_loc' not in x]
        # item_cols = [x for x in item_cols if '_loc' not in x]

        # item_cols = ['type_code', 'instr', 'ccy', 'trn_ccy', 'prtfl', 'acc', 'str1', 'pricing_ccy',]
        # item_cols += ['pos_return_loc', 'net_pos_return_loc',]

        balance_reports = []
        pl_reports = []

        for report_date in report_dates:
            _l.warn('%s', report_date)
            for report_currency in report_currencies:
                _l.warn('\t%s', report_currency)
                for bl_consolidation in bl_consolidations:
                    consolidation = bl_consolidation.copy()
                    _l.warn('\t\t%s', sorted(consolidation.items()))
                    # _l.warn('1 bl: date=%s, ccy=%s, consolidation=%s',
                    #         report_date, report_currency, sorted(consolidation.items()))
                    bal = self._simple_run(
                        None,
                        build_balance_for_tests=True,
                        report_type=Report.TYPE_BALANCE,
                        report_currency=report_currency,
                        report_date=report_date,
                        cost_method=cost_method,
                        trn_cols=trn_cols,
                        item_cols=item_cols,
                        **consolidation
                    )
                    balance_reports.append(bal)

                for pl_consolidation in pl_consolidations:
                    consolidation = pl_consolidation.copy()
                    _l.warn('\t\t%s', sorted(consolidation.items()))
                    # _l.warn('2 pl: date=%s, ccy=%s, consolidation=%s',
                    #         report_date, report_currency, sorted(consolidation.items()))

                    strategy1_mode = consolidation['strategy1_mode']
                    strategy2_mode = consolidation['strategy2_mode']
                    strategy3_mode = consolidation['strategy3_mode']
                    if strategy1_mode == Report.MODE_INTERDEPENDENT or \
                                    strategy2_mode == Report.MODE_INTERDEPENDENT or \
                                    strategy3_mode == Report.MODE_INTERDEPENDENT:
                        approach_multipliers0 = approach_multipliers
                    else:
                        approach_multipliers0 = [0.5]

                    for approach_multiplier in approach_multipliers0:
                        # _l.warn('\tapproach=%s', approach_multiplier)
                        _l.warn('\t\t\t%s', approach_multiplier)
                        pl = self._simple_run(
                            None,
                            report_type=Report.TYPE_PL,
                            report_currency=report_currency,
                            report_date=report_date,
                            cost_method=cost_method,
                            trn_cols=trn_cols,
                            item_cols=item_cols,
                            approach_multiplier=approach_multiplier,
                            **consolidation
                        )
                        pl_reports.append(pl)

        # for report_date in report_dates:
        #     for report_currency in report_currencies:
        #         for portfolio_mode in portfolio_modes:
        #             for account_mode in account_modes:
        #                 for strategy1_mode in strategy1_modes:
        #                     for strategy2_mode in strategy2_modes:
        #                         for strategy3_mode in strategy3_modes:
        #                             if strategy1_mode == Report.MODE_INTERDEPENDENT or \
        #                                             strategy2_mode == Report.MODE_INTERDEPENDENT or \
        #                                             strategy3_mode == Report.MODE_INTERDEPENDENT:
        #                                 approach_multipliers0 = approach_multipliers
        #                             else:
        #                                 approach_multipliers0 = [0.5]
        #
        #                             for approach_multiplier in approach_multipliers0:
        #                                 _l.warn(
        #                                     'date=%s, ccy=%s, prtfl=%s, acc=%s, str1=%s, str2=%s, str3=%s, approach=%s',
        #                                     report_date, report_currency, portfolio_mode, account_mode, strategy1_mode,
        #                                     strategy2_mode, strategy3_mode, approach_multiplier)
        #                                 bal = self._simple_run(
        #                                     None,
        #                                     report_type=Report.TYPE_BALANCE,
        #                                     report_currency=report_currency,
        #                                     report_date=report_date,
        #                                     cost_method=cost_method,
        #                                     portfolio_mode=portfolio_mode,
        #                                     account_mode=account_mode,
        #                                     strategy1_mode=strategy1_mode,
        #                                     strategy2_mode=strategy2_mode,
        #                                     strategy3_mode=strategy3_mode,
        #                                     approach_multiplier=approach_multiplier,
        #                                     trn_cols=trn_cols,
        #                                     item_cols=item_cols
        #                                 )
        #                                 balance_reports.append(bal)
        #
        #                                 pl = self._simple_run(
        #                                     None,
        #                                     report_type=Report.TYPE_PL,
        #                                     report_currency=report_currency,
        #                                     report_date=report_date,
        #                                     cost_method=cost_method,
        #                                     portfolio_mode=portfolio_mode,
        #                                     account_mode=account_mode,
        #                                     strategy1_mode=strategy1_mode,
        #                                     strategy2_mode=strategy2_mode,
        #                                     strategy3_mode=strategy3_mode,
        #                                     approach_multiplier=approach_multiplier,
        #                                     trn_cols=trn_cols,
        #                                     item_cols=item_cols
        #                                 )
        #                                 pl_reports.append(pl)

        _l.warn('write results')
        # self._write_results(balance_reports, '%s_balance.xlsx' % test_prefix,
        #                     trn_cols=trn_cols, item_cols=item_cols)
        # self._write_results(pl_reports, '%s_pl_report.xlsx' % test_prefix,
        #                     trn_cols=trn_cols, item_cols=item_cols)
        pass
