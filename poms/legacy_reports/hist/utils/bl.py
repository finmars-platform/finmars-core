from __future__ import unicode_literals, division

from collections import OrderedDict, Counter, defaultdict


def get_data():
    data = [
        OrderedDict([
            ['type', 'CASH_IN'],
            ['instrument', 'USD'],
            ['position_with_sign', 250.0],
            ['price', float('NaN')],
            ['currency', float('NaN')],
            ['cash_flow', float('NaN')],
            ['principal_with_sign', float('NaN')],
            ['carry_with_sign', float('NaN')],
            ['overheads_with_sign', float('NaN')],
            ['ytm', float('NaN')],
            ['time_invested', float('NaN')],
        ]),
        OrderedDict([
            ['type', 'BUY'],
            ['instrument', 'I_1'],
            ['position_with_sign', 200.0],
            ['price', 0.95],
            ['currency', 'USD'],
            ['cash_flow', -208.0],
            ['principal_with_sign', -190.0],
            ['carry_with_sign', -15.0],
            ['overheads_with_sign', -3.0],
            ['ytm', 10.0],
            ['time_invested', 75],
        ]),
        OrderedDict([
            ['type', 'COUPON'],
            ['instrument', 'I_1'],
            ['position_with_sign', 0.0],
            ['price', 0.0],
            ['currency', 'USD'],
            ['cash_flow', 20.0],
            ['principal_with_sign', 0.0],
            ['carry_with_sign', 20.0],
            ['overheads_with_sign', 0.0],
            ['ytm', 12.0],
            ['time_invested', 50.0],
        ]),
        OrderedDict([
            ['type', 'SELL'],
            ['instrument', 'I_1'],
            ['position_with_sign', -100.0],
            ['price', 0.91],
            ['currency', 'USD'],
            ['cash_flow', 91.5],
            ['principal_with_sign', 91.0],
            ['carry_with_sign', 2.5],
            ['overheads_with_sign', -2.0],
            ['ytm', 8.0],
            ['time_invested', 30],
        ]),
        OrderedDict([
            ['type', 'BUY'],
            ['instrument', 'I_2'],
            ['position_with_sign', 200.0],
            ['price', 0.95],
            ['currency', 'EUR'],
            ['cash_flow', -208.0],
            ['principal_with_sign', -190.0],
            ['carry_with_sign', -15.0],
            ['overheads_with_sign', -3.0],
            ['ytm', 12.5],
            ['time_invested', 15.0],
        ]),
    ]
    return data


def get_data_ytm():
    data = [
        OrderedDict([
            ['type', 'CASH_IN'],
            ['instrument', 'USD'],
            ['position_with_sign', 250.0],
            ['price', float('NaN')],
            ['currency', float('NaN')],
            ['cash_flow', float('NaN')],
            ['principal_with_sign', float('NaN')],
            ['carry_with_sign', float('NaN')],
            ['overheads_with_sign', float('NaN')],
            ['avco', float('NaN')],
            ['ytm', float('NaN')],
            ['time_invested', float('NaN')],
        ]),
        OrderedDict([
            ['type', 'BUY'],
            ['instrument', 'I_1'],
            ['position_with_sign', 100.0],
            ['price', 0.95],
            ['currency', 'USD'],
            ['cash_flow', -208.0],
            ['principal_with_sign', -190.0],
            ['carry_with_sign', -15.0],
            ['overheads_with_sign', -3.0],
            ['avco', 1.0 / 3.0],
            ['ytm', 10.0],
            ['time_invested', 75],
        ]),
        OrderedDict([
            ['type', 'BUY'],
            ['instrument', 'I_1'],
            ['position_with_sign', 200.0],
            ['price', 0.92],
            ['currency', 'USD'],
            ['cash_flow', -20.0],
            ['principal_with_sign', 0.0],
            ['carry_with_sign', -20.0],
            ['overheads_with_sign', 0.0],
            ['avco', 1.0 / 3.0],
            ['ytm', 12.0],
            ['time_invested', 50.0],
        ]),
        OrderedDict([
            ['type', 'SELL'],
            ['instrument', 'I_1'],
            ['position_with_sign', -100.0],
            ['price', 0.91],
            ['currency', 'USD'],
            ['cash_flow', 91.5],
            ['principal_with_sign', 91.0],
            ['carry_with_sign', 2.5],
            ['overheads_with_sign', -2.0],
            ['avco', 1.0],
            ['ytm', 8.0],
            ['time_invested', 30],
        ]),
        OrderedDict([
            ['type', 'BUY'],
            ['instrument', 'I_2'],
            ['position_with_sign', 200.0],
            ['price', 0.95],
            ['currency', 'EUR'],
            ['cash_flow', -208.0],
            ['principal_with_sign', -190.0],
            ['carry_with_sign', -15.0],
            ['overheads_with_sign', -3.0],
            ['avco', 0.0],
            ['ytm', 12.5],
            ['time_invested', 15.0],
        ]),
    ]
    return data


def show(m, message=None):
    if isinstance(m, list):
        print('-' * 79)
        if message:
            print(message)
        for t in m:
            if isinstance(t, (dict, OrderedDict)):
                s = []
                for k, v in t.items():
                    s.append('%s=%s' % (k, v))
                print(', '.join(s))
            else:
                print(t)
    elif isinstance(m, (dict, OrderedDict)):
        print('-' * 79)
        if message:
            print(message)
        s = []
        for k, v in m.items():
            s.append('%s=%s' % (k, v))
        print(', '.join(s))
    else:
        print('-' * 79)
        if message:
            print(message)
        print(m)


def build_balance():
    transactions = get_data()

    show(transactions)

    c_invested = Counter()
    c_cash = Counter()
    c_position = Counter()
    for t in transactions:
        t_type = t['type']

        if t_type == 'CASH_IN':
            c_cash[t['instrument']] += t['position_with_sign']
            c_invested[t['instrument']] += t['position_with_sign']
        elif t_type in ['BUY', 'SELL']:
            c_cash[t['currency']] += t['cash_flow']
            c_position[t['instrument']] += t['position_with_sign']
        elif t_type == 'COUPON':
            c_cash[t['currency']] += t['cash_flow']

    show(c_position)
    show(c_cash)
    show(c_invested)
    # c_cash = [[k, v] for k, v in c_cash.items()]
    # c_position = [[k, v] for k, v in c_position.items()]

    # show(sorted(c_cash))
    # show(sorted(c_position))
    return c_cash, c_position, c_invested


def get_accured_interest_instr_ccy(k):
    if k == 'I_1':
        return 8.3
    elif k == 'I_2':
        return 4.8
    return 1.0


def get_price(k):
    if k == 'I_1':
        return 0.98
    elif k == 'I_2':
        return 1.02
    return 1.0


def get_currency(k):
    if k == 'I_1':
        return 'USD'
    elif k == 'I_2':
        return 'EUR'
    return k


def get_fx_rate(k):
    if k == ['USD', 'i_1']:
        return 1.0
    elif k in ['EUR', 'I_2']:
        return 1.3
    return 1.0


def build_balance_mkt():
    c_cash, c_position, c_invested = build_balance()

    def mk(instrument_currency, balance, price=None, accured_interest_instr_ccy=0.0):
        return OrderedDict([
            ['instrument', instrument_currency],
            ['balance', balance],
            ['price', price],
            ['accured_interest_instr_ccy', accured_interest_instr_ccy]
        ])

    data = [mk(k, v, 1.0, 0.0) for k, v in sorted(c_cash.items())]
    data += [mk(k, v, get_price(k), get_accured_interest_instr_ccy(k)) for k, v in sorted(c_position.items())]

    value = 0.0
    for d in data:
        d['principal_instr_ccy'] = d['balance'] * d['price']
        d['mkt_val_local'] = d['principal_instr_ccy'] + d['accured_interest_instr_ccy']

        d['ccy'] = get_currency(d['instrument'])
        d['fx_rate'] = get_fx_rate(d['ccy'])
        d['mkt_val'] = d['mkt_val_local'] * d['fx_rate']

        value += d['mkt_val']

    invested = 0.0
    for k, v in c_invested.items():
        invested += get_fx_rate(k) * v

    show(data)
    print('-' * 79)
    print('invested -> %s' % invested)
    print('value -> %s' % value)
    print('P&L -> %s' % (value - invested))

    print('-' * 79)
    print('invested -> %s' % (1 / get_fx_rate('EUR') * invested,))
    print('value -> %s' % (1 / get_fx_rate('EUR') * value,))
    print('P&L -> %s' % (1 / get_fx_rate('EUR') * (value - invested),))

    return data


def build_p_l():
    transactions = get_data()

    balances = defaultdict(OrderedDict)
    for t in transactions:
        t_type = t['type']
        if t_type in ['BUY', 'SELL']:
            # b = balances.get(t['instrument'], OrderedDict())
            # balances[t['instrument']] = b
            b = balances[t['instrument']]
            b['instrument'] = t['instrument']
            b['position_with_sign'] = b.get('position_with_sign', 0) + t['position_with_sign']
            # b['principal_with_sign'] = b.get('principal_with_sign', 0) + t['principal_with_sign']
            # b['carry_with_sign'] = b.get('carry_with_sign', 0) + t['carry_with_sign']
            # b['overheads_with_sign'] = b.get('overheads_with_sign', 0) + t['overheads_with_sign']

    show(list(balances.values()))

    for k, b in balances.items():
        b['price'] = get_price(b['instrument'])
        b['principal_with_sign'] = b['position_with_sign'] * b['price']
        # b['carry_with_sign'] = get_accured_interest_instr_ccy(b['instrument'])
        b['carry_with_sign'] = get_accured_interest_instr_ccy(b['instrument'])
        b['overheads_with_sign'] = 0.0

    show(list(balances.values()))

    principal_with_sign = Counter()
    carry_with_sign = Counter()
    overheads_with_sign = Counter()

    for t in transactions:
        t_type = t['type']
        if t_type in ['BUY', 'SELL', 'COUPON']:
            t['ccy'] = get_currency(t['instrument'])
            t['fx_rate'] = get_fx_rate(t['ccy'])

            principal_with_sign['all'] += t['principal_with_sign'] * t['fx_rate']
            carry_with_sign['all'] += t['carry_with_sign'] * t['fx_rate']
            overheads_with_sign['all'] += t['overheads_with_sign'] * t['fx_rate']

            principal_with_sign[t['instrument']] += t['principal_with_sign'] * t['fx_rate']
            carry_with_sign[t['instrument']] += t['carry_with_sign'] * t['fx_rate']
            overheads_with_sign[t['instrument']] += t['overheads_with_sign'] * t['fx_rate']

    for k, b in balances.items():
        b['ccy'] = get_currency(b['instrument'])
        b['fx_rate'] = get_fx_rate(b['ccy'])

        principal_with_sign['all'] += b['principal_with_sign'] * b['fx_rate']
        carry_with_sign['all'] += b['carry_with_sign'] * b['fx_rate']
        overheads_with_sign['all'] += b['overheads_with_sign'] * b['fx_rate']

        principal_with_sign[b['instrument']] += b['principal_with_sign'] * b['fx_rate']
        carry_with_sign[b['instrument']] += b['carry_with_sign'] * b['fx_rate']
        overheads_with_sign[b['instrument']] += b['overheads_with_sign'] * b['fx_rate']

    show(transactions)
    show(list(balances.values()))
    show(principal_with_sign, message='principal_with_sign')
    show(carry_with_sign, message='carry_with_sign')
    show(overheads_with_sign, message='overheads_with_sign')

    print('-' * 79)
    print('principal_with_sign -> %s' % principal_with_sign['all'])
    print('carry_with_sign -> %s' % carry_with_sign['all'])
    print('overheads_with_sign -> %s' % overheads_with_sign['all'])
    print('total -> %s' % (principal_with_sign['all'] + carry_with_sign['all'] + overheads_with_sign['all']), )

    print('-' * 79)
    print('principal_with_sign -> %s' % (1 / get_fx_rate('EUR') * principal_with_sign['all'],))
    print('carry_with_sign -> %s' % (1 / get_fx_rate('EUR') * carry_with_sign['all'],))
    print('overheads_with_sign -> %s' % (1 / get_fx_rate('EUR') * (overheads_with_sign['all']),))
    print('total -> %s' % (
        1 / get_fx_rate('EUR') * (principal_with_sign['all'] + carry_with_sign['all'] + overheads_with_sign['all']),))


def build_cost():
    transactions = get_data()

    def get_currency(k):
        if k == 'I_1':
            return 'EUR'
        elif k == 'I_2':
            return 'GDB'
        return k

    def get_fx_rate(k):
        if k in ['EUR', 'I_1']:
            return 1.3
        elif k in ['GDB', 'I_2']:
            return 1.6
        return 1.0

    costs = defaultdict(OrderedDict)
    for t in transactions:
        if t['instrument'] == 'I_1' and t['type'] == 'BUY':
            t['avco'] = 0.5
        elif t['instrument'] == 'I_1' and t['type'] == 'SELL':
            t['avco'] = 1
        elif t['instrument'] == 'I_2' and t['type'] == 'BUY':
            t['avco'] = 0.
        elif t['type'] == 'COUPON':
            t['avco'] = 0.
        else:
            t['avco'] = float('NaN')

        t['remaining'] = t['position_with_sign'] * (1 - t['avco'])
        t['remaining_position_cost'] = t['principal_with_sign'] * (1 - t['avco'])

        t['ccy'] = get_currency(t['instrument'])
        t['fx_rate'] = get_fx_rate(t['instrument'])
        t['remaining_position_cost_ccy'] = get_fx_rate(t['instrument']) * t['remaining_position_cost']

        if t['type'] in ['BUY', 'SELL', 'COUPON']:
            cost = costs[t['instrument']]
            cost['instrument'] = t['instrument']
            cost['position'] = cost.get('position', 0) + t['position_with_sign']
            cost['cost'] = cost.get('cost', 0) + t['remaining_position_cost_ccy']

    for cost in costs.values():
        cost['cost_price'] = cost['cost'] / cost['position']

    show(transactions)
    show(sorted(costs.values(), key=lambda x: x['instrument']))


def build_ytm():
    transactions = get_data_ytm()

    balance = Counter()
    for t in transactions:
        if t['type'] in ['BUY', 'SELL']:
            balance[t['instrument']] += t['position_with_sign']
    show(balance)

    ytm = Counter()
    time_invested = Counter()
    for t in transactions:
        if t['type'] in ['BUY', 'SELL']:
            t['remaining'] = t['position_with_sign'] * (1 - t['avco'])
            t['remaining%'] = t['remaining'] / balance[t['instrument']]
            t['weight_ytm'] = t['ytm'] * t['remaining%']
            t['weight_time_invested'] = t['time_invested'] * t['remaining%']
            ytm[t['instrument']] += t['weight_ytm']
            time_invested[t['instrument']] += t['weight_time_invested']

    show(transactions)
    show(ytm, 'ytm')
    show(time_invested, 'time_invested')


if __name__ == "__main__":
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "poms_app.settings")
    import django

    django.setup()

    # build_balance()
    # build_balance_mkt()
    # build_p_l()
    # build_cost()
    # build_ytm()

    from base import AbstractReport

    AbstractReport([1, 2, 3]).dump_transactions()
