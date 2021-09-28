import hashlib
import json
import logging

_l = logging.getLogger('poms.reports')


def sprint_table(data, headers=None, floatfmt=None, showindex=None):
    try:
        import pandas
    except ImportError:
        pandas = None
    if pandas:
        with pandas.option_context('display.max_rows', 10000,
                                   'display.max_columns', 10000,
                                   'display.float_format', '{:.4f}'.format,
                                   'display.line_width', 10000):
            df = pandas.DataFrame(data=data, columns=headers)
            # df.index += 1
            return df.to_string(index=False)
    import tabulate
    if not floatfmt:
        floatfmt = '.4f'
    if not showindex:
        showindex = 'default'
    return tabulate.tabulate(data, headers=headers, floatfmt=floatfmt, showindex=showindex)


def generate_report_unique_hash(app, action, data, master_user, member):
    _data = data.copy()

    result = ''

    report_options = {}

    report_options['master_user'] = master_user.id
    report_options['member'] = member.id

    report_options['begin_date'] = _data['begin_date']
    report_options['date_field'] = _data['date_field']
    report_options['end_date'] = _data['end_date']
    report_options['report_date'] = _data['report_date']

    report_options['report_currency'] = _data['report_currency']
    report_options['pricing_policy'] = _data['pricing_policy']
    report_options['report_type'] = _data['report_type']

    report_options['account_mode'] = _data['account_mode']
    report_options['portfolio_mode'] = _data['portfolio_mode']
    report_options['strategy1_mode'] = _data['strategy1_mode']
    report_options['strategy2_mode'] = _data['strategy2_mode']
    report_options['strategy3_mode'] = _data['strategy3_mode']

    report_options['custom_fields_to_calculate'] = _data['custom_fields_to_calculate']
    report_options['cost_method'] = _data['cost_method']
    report_options['show_balance_exposure_details'] = _data['show_balance_exposure_details']
    report_options['show_transaction_details'] = _data['show_transaction_details']
    report_options['approach_multiplier'] = _data['approach_multiplier']

    report_options['portfolios'] = _data['portfolios']
    report_options['accounts'] = _data['accounts']
    report_options['strategies1'] = _data['strategies1']
    report_options['strategies2'] = _data['strategies2']
    report_options['strategies3'] = _data['strategies3']

    result = app + '_' + action + '_' + str(master_user.id) + '_' + str(member.id) + '_' + hashlib.md5(
        json.dumps(report_options, sort_keys=True).encode('utf-8')).hexdigest()

    return result
