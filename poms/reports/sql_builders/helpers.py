from poms.currencies.models import CurrencyHistory
from poms.reports.builders.balance_item import Report


def get_transaction_filter_sql_string(instance):

    result_string = ''

    filter_sql_list = []

    portfolios_ids = []
    accounts_ids = []
    strategies1_ids = []
    strategies2_ids = []
    strategies3_ids = []

    if len(instance.portfolios):
        for portfolio in instance.portfolios:
            portfolios_ids.append(str(portfolio.id))

        filter_sql_list.append('portfolio_id in (' + ', '.join(portfolios_ids) + ')')

    if len(instance.accounts):
        for account in instance.accounts:
            accounts_ids.append(str(account.id))

        filter_sql_list.append('account_position_id in (' + ', '.join(accounts_ids) + ')')

    if len(instance.strategies1):
        for strategy in instance.strategies1:
            strategies1_ids.append(str(strategy.id))

        filter_sql_list.append('strategy1_position_id in (' + ', '.join(strategies1_ids) + ')')

    if len(instance.strategies2):
        for strategy in instance.strategies2:
            strategies2_ids.append(str(strategy.id))

        filter_sql_list.append('strategy2_position_id in (' + ', '.join(strategies2_ids) + ')')

    if len(instance.strategies3):
        for strategy in instance.strategies3:
            strategies3_ids.append(str(strategy.id))

        filter_sql_list.append('strategy2_position_id in (' + ', '.join(strategies2_ids) + ')')

    if len(filter_sql_list):
        result_string = result_string + 'where '
        result_string = result_string + ' and '.join(filter_sql_list)

    return result_string


def get_report_fx_rate(instance, date):

    report_fx_rate = 1

    try:
        item = CurrencyHistory.objects.get(currency_id=instance.report_currency.id,
                                           date=date)
        report_fx_rate = item.fx_rate
    except CurrencyHistory.DoesNotExist:
        report_fx_rate = 1

    report_fx_rate = str(report_fx_rate)

    return report_fx_rate


def get_fx_trades_and_fx_variations_transaction_filter_sql_string(instance):

    result_string = ''

    filter_sql_list = []

    portfolios_ids = []
    accounts_ids = []
    strategies1_ids = []
    strategies2_ids = []
    strategies3_ids = []

    if len(instance.portfolios):
        for portfolio in instance.portfolios:
            portfolios_ids.append(str(portfolio.id))

        filter_sql_list.append('portfolio_id in (' + ', '.join(portfolios_ids) + ')')

    if len(instance.accounts):
        for account in instance.accounts:
            accounts_ids.append(str(account.id))

        filter_sql_list.append('account_position_id in (' + ', '.join(accounts_ids) + ')')

    if len(instance.strategies1):
        for strategy in instance.strategies1:
            strategies1_ids.append(str(strategy.id))

        filter_sql_list.append('strategy1_position_id in (' + ', '.join(strategies1_ids) + ')')

    if len(instance.strategies2):
        for strategy in instance.strategies2:
            strategies2_ids.append(str(strategy.id))

        filter_sql_list.append('strategy2_position_id in (' + ', '.join(strategies2_ids) + ')')

    if len(instance.strategies3):
        for strategy in instance.strategies3:
            strategies3_ids.append(str(strategy.id))

        filter_sql_list.append('strategy2_position_id in (' + ', '.join(strategies2_ids) + ')')

    if len(filter_sql_list):
        result_string = result_string + ' and '
        result_string = result_string + ' and '.join(filter_sql_list)

    return result_string


def get_where_expression_for_position_consolidation(instance, prefix, prefix_second):

    result = []

    if instance.portfolio_mode == Report.MODE_INDEPENDENT:
        result.append(prefix + "portfolio_id = " + prefix_second + "portfolio_id")

    if instance.account_mode == Report.MODE_INDEPENDENT:
        result.append(prefix + "account_position_id = " + prefix_second + "account_position_id")

    if instance.strategy1_mode == Report.MODE_INDEPENDENT:
        result.append(prefix + "strategy1_position_id = " + prefix_second + "strategy1_position_id")

    if instance.strategy2_mode == Report.MODE_INDEPENDENT:
        result.append(prefix + "strategy2_position_id = " + prefix_second + "strategy2_position_id")

    if instance.strategy3_mode == Report.MODE_INDEPENDENT:
        result.append(prefix + "strategy3_position_id = " + prefix_second + "strategy3_position_id")

    resultString = ''

    if len(result):
        resultString = " and ".join(result) + ' and '

    return resultString


def get_position_consolidation_for_select(instance, prefix=''):

    result = []

    if instance.portfolio_mode == Report.MODE_INDEPENDENT:
        result.append(prefix + "portfolio_id")

    if instance.account_mode == Report.MODE_INDEPENDENT:
        result.append(prefix + "account_position_id")

    if instance.strategy1_mode == Report.MODE_INDEPENDENT:
        result.append(prefix + "strategy1_position_id")

    if instance.strategy2_mode == Report.MODE_INDEPENDENT:
        result.append(prefix + "strategy2_position_id")

    if instance.strategy3_mode == Report.MODE_INDEPENDENT:
        result.append(prefix + "strategy3_position_id")

    resultString = ''

    if len(result):
        resultString = ", ".join(result) + ', '

    return resultString


def get_pl_left_join_consolidation(instance):
    result = []

    if instance.portfolio_mode == Report.MODE_INDEPENDENT:
        result.append("balance_q.portfolio_id = pl_q.portfolio_id")

    if instance.account_mode == Report.MODE_INDEPENDENT:
        result.append("balance_q.account_position_id = pl_q.account_position_id")

    if instance.strategy1_mode == Report.MODE_INDEPENDENT:
        result.append("balance_q.strategy1_position_id = pl_q.strategy1_position_id")

    if instance.strategy2_mode == Report.MODE_INDEPENDENT:
        result.append("balance_q.strategy2_position_id = pl_q.strategy2_position_id")

    if instance.strategy3_mode == Report.MODE_INDEPENDENT:
        result.append("balance_q.strategy3_position_id = pl_q.strategy3_position_id")

    resultString = ''

    if len(result):
        resultString = resultString + 'and '
        resultString = resultString +  " and ".join(result)

    return resultString
