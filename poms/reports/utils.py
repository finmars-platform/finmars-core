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

    if 'begin_date' in _data:
        report_options['begin_date'] = _data['begin_date']

    if 'date_field' in _data:
        report_options['date_field'] = _data['date_field']

    if 'end_date' in _data:
        report_options['end_date'] = _data['end_date']

    if 'report_date' in _data:
        report_options['report_date'] = _data['report_date']

    if 'pl_first_date' in _data:
        report_options['pl_first_date'] = _data['pl_first_date']

    if 'report_currency' in _data:
        report_options['report_currency'] = _data['report_currency']


    if 'pricing_policy' in _data:
        report_options['pricing_policy'] = _data['pricing_policy']

    if 'report_type' in _data:
        report_options['report_type'] = _data['report_type']

    if 'account_mode' in _data:
        report_options['account_mode'] = _data['account_mode']

    if 'portfolio_mode' in _data:
        report_options['portfolio_mode'] = _data['portfolio_mode']

    if 'strategy1_mode' in _data:
        report_options['strategy1_mode'] = _data['strategy1_mode']

    if 'strategy2_mode' in _data:
        report_options['strategy2_mode'] = _data['strategy2_mode']

    if 'strategy3_mode' in _data:
        report_options['strategy3_mode'] = _data['strategy3_mode']

    if 'custom_fields_to_calculate' in _data:
        report_options['custom_fields_to_calculate'] = _data['custom_fields_to_calculate']

    if 'complex_transaction_statuses_filter' in _data:
        report_options['complex_transaction_statuses_filter'] = _data['complex_transaction_statuses_filter']

    if 'cost_method' in _data:
        report_options['cost_method'] = _data['cost_method']

    if 'show_balance_exposure_details' in _data:
        report_options['show_balance_exposure_details'] = _data['show_balance_exposure_details']

    if 'show_transaction_details' in _data:
        report_options['show_transaction_details'] = _data['show_transaction_details']

    if 'approach_multiplier' in _data:
        report_options['approach_multiplier'] = _data['approach_multiplier']

    if 'portfolios' in _data:
        report_options['portfolios'] = _data['portfolios']


    if 'accounts' in _data:
        report_options['accounts'] = _data['accounts']

    if 'strategies1' in _data:
        report_options['strategies1'] = _data['strategies1']

    if 'strategies2' in _data:
        report_options['strategies2'] = _data['strategies2']

    if 'strategies3' in _data:
        report_options['strategies3'] = _data['strategies3']


    # Performance report field

    if 'calculation_type' in _data:
        report_options['calculation_type'] = _data['calculation_type']

    if 'segmentation_type' in _data:
        report_options['segmentation_type'] = _data['segmentation_type']

    if 'calculation_type' in _data:
        report_options['calculation_type'] = _data['calculation_type']

    if 'registers' in _data:
        report_options['registers'] = _data['registers']

    result = app + '_' + action + '_' + str(master_user.id) + '_' + str(member.id) + '_' + hashlib.md5(
        json.dumps(report_options, sort_keys=True).encode('utf-8')).hexdigest()

    return result
