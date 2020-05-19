import logging
from datetime import date

from django.conf import settings

from poms.common.utils import isclose

_l = logging.getLogger('poms.transactions')


def calc_cash_for_contract_for_difference(transaction, instrument, portfolio, account, member,
                                          is_calculate_for_newer=False, is_calculate_for_all=False, save=False):
    _l.debug('calc_cash_for_contract_for_difference: transaction=%s, instrument=%s, portfolio=%s, account=%s, '
             'member=%s, is_calculate_for_newer=%s, is_calculate_for_all=%s, save=%s',
             transaction.id if transaction else None,
             instrument.id if instrument else None,
             portfolio.id if portfolio else None,
             account.id if account else None,
             member.id if member else None,
             is_calculate_for_newer, is_calculate_for_all, save)

    from poms.instruments.models import CostMethod
    from poms.reports.builders.balance_item import Report
    from poms.reports.builders.balance_pl import ReportBuilder
    from poms.reports.builders.balance_virt_trn import VirtualTransaction

    def _get_id(obj):
        if obj is None:
            return None
        elif isinstance(obj, (int, float, str)):
            return int(obj)
        else:
            return obj.id

    def _make_filters(obj):
        if obj is None:
            return None
        else:
            return [_get_id(obj)]

    # queryset = Transaction.objects.all()

    if is_calculate_for_all or is_calculate_for_newer:
        report_date = date.max
    else:
        if transaction is None:
            return None
        report_date = transaction.accounting_date

    if transaction and instrument is None:
        instrument = transaction.instrument

    assert instrument is not None, "instrument must be specified"

    instruments = _make_filters(instrument)
    portfolios = _make_filters(portfolio)
    accounts = _make_filters(account)

    r = Report(master_user=instrument.master_user,
               member=member,
               instruments=instruments,
               portfolios=portfolios,
               accounts=accounts,
               portfolio_mode=Report.MODE_INDEPENDENT if portfolios else Report.MODE_IGNORE,
               account_mode=Report.MODE_INDEPENDENT if accounts else Report.MODE_IGNORE,
               strategy1_mode=Report.MODE_IGNORE,
               strategy2_mode=Report.MODE_IGNORE,
               strategy3_mode=Report.MODE_IGNORE,
               cost_method=CostMethod.objects.get(pk=CostMethod.FIFO),
               report_date=report_date,
               pricing_policy=None)
    rb = ReportBuilder(instance=r)

    rb._load_transactions()
    if transaction:
        add_this = transaction.id is None or not any(transaction.pk == t.pk for t in rb._transactions)
        if add_this:
            rb._transactions.append(VirtualTransaction(report=rb.instance, pricing_provider=rb.pricing_provider,
                                                   fx_rate_provider=rb.fx_rate_provider, trn=transaction))
            rb.sort_transactions()

    rb._calc_fifo_multipliers()

    if settings.DEBUG:
        VirtualTransaction.dumps(rb._transactions)

    processed = set()

    vt_older = -1
    vt_this = 0
    vt_newer = 1
    vt_state = vt_older
    for vt in rb._transactions:
        vt.cash += vt.overheads
        for vt_to, delta in vt.fifo_closed_by:
            if vt_to.lid not in processed:
                processed.add(vt_to.lid)
                # vt_to.cash += (vt_to.principal + vt_to.carry) * vt_to.fifo_multiplier + vt_to.overheads
                vt_to.cash += (vt_to.principal + vt_to.carry) * vt_to.fifo_multiplier
            vt_to.cash += (vt.principal + vt.carry) * delta

        if transaction:
            if vt_state == vt_this:
                vt_state = vt_newer
            elif (vt.pk == transaction.pk) or (transaction.pk is None and vt.pk is None):
                vt_state = vt_this

        t_save = False
        if is_calculate_for_all or (vt_state == vt_this) or (is_calculate_for_newer and vt_state == vt_newer):
            t_save = True

        if t_save and not isclose(vt.trn.cash_consideration, vt.cash):
            if settings.DEBUG:
                _l.debug('+ => %s: cash=(%s => %s)', vt, vt.trn.cash_consideration, vt.cash)
            vt.trn.cash_consideration = vt.cash
            if save:
                vt.trn.save()
                vt.pk = vt.trn.pk
        else:
            if settings.DEBUG:
                _l.debug('- => %s: cash=(%s <> %s)', vt, vt.trn.cash_consideration, vt.cash)
            pass

    if settings.DEBUG:
        VirtualTransaction.dumps(rb._transactions)

    return [vt.trn for vt in rb._transactions]
