import logging
import time

from django.db import connection

from poms.accounts.models import Account
from poms.currencies.models import Currency
from poms.instruments.models import Instrument
from poms.portfolios.models import Portfolio
from poms.reports.builders.balance_item import Report
from poms.reports.builders.base_builder import BaseReportBuilder
from poms.reports.models import BalanceReportCustomField
from poms.users.models import EcosystemDefault

_l = logging.getLogger('poms.reports')

def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

class BalanceReportBuilderSql:

    def __init__(self, instance=None):

        _l.debug('ReportBuilderSql init')

        self.instance = instance

        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self.instance.master_user)

        _l.info('self.instance master_user %s' % self.instance.master_user)
        _l.info('self.instance report_date %s' % self.instance.report_date)


    def build_balance(self):
        st = time.perf_counter()

        self.instance.items = []

        # self.build_positions()
        # self.build_cash()

        self.build()

        _l.info('items total %s' % len(self.instance.items))

        _l.info('build_st done: %s', "{:3.3f}".format(time.perf_counter() - st))

        self.add_data_items()

        return self.instance

    def get_position_consolidation_for_select(self):

        result = []

        if self.instance.portfolio_mode == Report.MODE_INDEPENDENT:
            result.append("portfolio_id")

        if self.instance.account_mode == Report.MODE_INDEPENDENT:
            result.append("account_position_id")

        if self.instance.strategy1_mode == Report.MODE_INDEPENDENT:
            result.append("strategy1_position_id")

        if self.instance.strategy2_mode == Report.MODE_INDEPENDENT:
            result.append("strategy2_position_id")

        if self.instance.strategy3_mode == Report.MODE_INDEPENDENT:
            result.append("strategy3_position_id")

        resultString = ''

        if len(result):
            resultString = ", ".join(result) + ', '

        return resultString

    def build(self):

        _l.info("build cash")

        with connection.cursor() as cursor:

            consolidated_select_columns = self.get_cash_consolidation_for_select()
            transaction_filter_sql_string = self.get_transaction_filter_sql_string()

            # language=PostgreSQL
            query = """
                
                with unioned_transactions_for_balance as (
                    
                    select 
                        id,
                        master_user_id,
                    
                        instrument_id,
                        portfolio_id,
                        transaction_class_id,
                        
                        transaction_date,
                        accounting_date,
                        cash_date,
                        
                        account_cash_id,
                        account_position_id,
                        account_interim_id,
                        
                        transaction_currency_id,
                        settlement_currency_id,
                        
                        position_size_with_sign,
                        cash_consideration
                        
                    from pl_transactions_with_ttype
                    
                    union all
                    
                    select 
                        id,
                        master_user_id,
                        
                        instrument_id,
                        portfolio_id,
                        transaction_class_id,
                        
                        transaction_date,
                        accounting_date,
                        cash_date,
                        
                        account_cash_id,
                        account_position_id,
                        account_interim_id,
                        
                        transaction_currency_id,
                        settlement_currency_id,
                        
                        (0) as position_size_with_sign,
                        cash_consideration
                        
                    from pl_cash_fx_trades_transactions_with_ttype
                    
                    union all
                    
                    select 
                        id,
                        master_user_id,
                        
                        instrument_id,
                        portfolio_id,
                        transaction_class_id,
                        
                        transaction_date,
                        accounting_date,
                        cash_date,
                        
                        account_cash_id,
                        account_position_id,
                        account_interim_id,
                        
                        transaction_currency_id,
                        settlement_currency_id,
                        
                        position_size_with_sign,
                        cash_consideration
                        
                    from pl_cash_fx_variations_transactions_with_ttype
                    
                
                ),
                
                unioned_interim_account_transactions as (
                    
                    select 
                           id,
                           master_user_id,
                           
                           instrument_id,
                           portfolio_id,
                           account_cash_id,
                           -- TODO add consolidation columns
                           --strategy1_cash_id,
                           --strategy2_cash_id,
                           --strategy2_cash_id,
                           
                           position_size_with_sign,
                           /* не нужны для БАЛАНСА
                           principal_with_sign,
                           carry_with_sign,
                           overheads,
                            */
                           cash_consideration,
                           settlement_currency_id,
                           accounting_date,
                           cash_date,
                           account_position_id,
                           -- modification
                           account_interim_id as account_cash_id,
                           account_interim_id,
                           
                           case 
                                when cash_date < accounting_date
                                then cash_date
                                else accounting_date
                           end
                           as min_date
                           
                    -- добавить остальные поля
                    from unioned_transactions_for_balance -- USE TOTAL VIEW HERE
                    where accounting_Date <= '{report_date}' /* REPORTING DATE */
                      and '{report_date}' < cash_date
                    
                    -- case 2
                    union all
                    select 
                            id,
                            master_user_id,
                    
                           instrument_id,
                           portfolio_id,
                           account_cash_id,
                           -- TODO add consolidation columns
                           -- modification
                           0 as position_size_with_sign,
                           (-cash_consideration) as cash_consideration,
                           settlement_currency_id,
                           accounting_date,
                           cash_date,
                           account_position_id,
                           -- modification
                           account_interim_id as account_cash_id,
                           account_interim_id,
                           
                           case 
                                when cash_date < accounting_date
                                then cash_date
                                else accounting_date
                           end
                           as min_date
                           
                    from unioned_transactions_for_balance
                    where cash_date  <= '{report_date}'  /* REPORTING DATE */
                      and '{report_date}' < accounting_Date
                
                    union all
                    
                    select 
                            id,
                            master_user_id,
                    
                           instrument_id,
                           portfolio_id,
                           account_cash_id,
                           -- TODO add consolidation columns
                    
                           position_size_with_sign,
                           cash_consideration,
                           settlement_currency_id,
                           accounting_date,
                           cash_date,
                    
                           account_position_id,
                           account_interim_id,
                           account_interim_id,
                           
                           case 
                                when cash_date < accounting_date
                                then cash_date
                                else accounting_date
                           end
                           as min_date
                           
                    from unioned_transactions_for_balance
                    where not (accounting_Date <= '{report_date}' /* REPORTING DATE */
                      and '{report_date}' < cash_date)
                        
                ),
                
                filtered_transactions as (
                    
                    select * from unioned_interim_account_transactions
                    {transaction_filter_sql_string}
                
                )
                
                -- main query  
                select 
                    
                    instrument_id,
                    {consolidated_select_columns}
                
                    name,
                    short_name,
                    user_code,
                    
                    item_type,
                    item_type_name,
                    
                    position_size,
                    market_value
                    
                from (        
                    select 
                        
                        (-1) as instrument_id,
                        {consolidated_select_columns}
                        
                        (2) as item_type,
                        ('Currency') as item_type_name,
                        
                        position_size,
                         
                        
                        c.name,
                        c.short_name,
                        c.user_code,
                        
                        (t_with_report_fx_rate.position_size * stl_fx_rate / report_fx_rate) as market_value
                    from 
                        (select 
                            *,
                            case when {report_currency_id} = {default_currency_id}
                                then 1
                                else
                                    (select
                                fx_rate
                             from currencies_currencyhistory
                             where
                                currency_id = {report_currency_id} and
                                date = '{report_date}' and
                                pricing_policy_id = {pricing_policy_id}
                            )
                                end as report_fx_rate,
    
                            case when settlement_currency_id = {default_currency_id}
                                then 1
                                else
                                    (select
                                fx_rate
                             from currencies_currencyhistory
                             where
                                currency_id = settlement_currency_id and
                                date = '{report_date}' and
                                pricing_policy_id = {pricing_policy_id}
                            )
                                end as stl_fx_rate
                        from (
                            select
                              {consolidated_select_columns}
                              settlement_currency_id,
                              SUM(cash_consideration) as position_size
                            from filtered_transactions
                            where min_date <= '{report_date}' and master_user_id = {master_user_id}
                            group by
                              {consolidated_select_columns}
                              settlement_currency_id 
                            ) as t
                        ) as t_with_report_fx_rate
                    left join currencies_currency as c
                    ON t_with_report_fx_rate.settlement_currency_id = c.id
                    where position_size != 0
                ) as pre_final_union_cash_calculations_level_0
                
                union all
                
                select 
                    
                    instrument_id,
                    {consolidated_select_columns}
                
                    name,
                    short_name,
                    user_code,
                    
                    item_type,
                    item_type_name,
                    
                    position_size,
                    market_value
                    
                from (
                    select 
                    
                        instrument_id,
                        {consolidated_select_columns}
                        
                        position_size,
                        
                        (1) as item_type,
                        ('Instrument') as item_type_name,
                        
                        name,
                        short_name,
                        user_code,
                        pricing_currency_id,
                        
             
                        (position_size * principal_price * price_multiplier * pch_fx_rate + (position_size * accrued_price * pch_fx_rate * 1 * accrued_multiplier)) as market_value
                    from (
                        select
                            instrument_id,
                            {consolidated_select_columns}
                            
                            position_size,
                            
                            i.name,
                            i.short_name,
                            i.user_code,
                            i.pricing_currency_id,
                            i.price_multiplier,
                            i.accrued_multiplier,
                            
                            case when i.pricing_currency_id = {default_currency_id}
                                then 1
                                else
                                    (select
                                fx_rate
                             from currencies_currencyhistory
                             where
                                currency_id = i.pricing_currency_id and
                                date = '{report_date}' and
                                pricing_policy_id = {pricing_policy_id}
                            )
                            end as pch_fx_rate,
                                
                            (select 
                                principal_price
                            from instruments_pricehistory
                            where 
                                instrument_id=i.id and 
                                date = '{report_date}' and
                                pricing_policy_id = {pricing_policy_id})
                            as principal_price,
                            
                            (select 
                                accrued_price
                            from instruments_pricehistory
                            where 
                                instrument_id=i.id and 
                                date = '{report_date}' and
                                pricing_policy_id = {pricing_policy_id} )
                            as accrued_price
                            
                        from
                            (select
                              {consolidated_select_columns}
                              instrument_id,
                              SUM(position_size_with_sign) as position_size
                            from filtered_transactions
                            group by
                              {consolidated_select_columns}
                              instrument_id) as t
                        left join instruments_instrument as i
                        ON instrument_id = i.id
                        ) as grouped
                    where position_size != 0
                    
                ) as pre_final_union_positions_calculations_level_0
                 
            """

            query = query.format(report_date=self.instance.report_date,
                                 master_user_id=self.instance.master_user.id,
                                 default_currency_id=self.ecosystem_defaults.currency_id,
                                 report_currency_id=self.instance.report_currency.id,
                                 pricing_policy_id=self.instance.pricing_policy.id,
                                 consolidated_select_columns=consolidated_select_columns,
                                 transaction_filter_sql_string=transaction_filter_sql_string

                                 )

            cursor.execute(query)

            query_str = str(cursor.query, 'utf-8')
            _l.info(query_str)

            result = dictfetchall(cursor)

            for item in result:

                # item["currency_id"] = item["settlement_currency_id"]

                if "portfolio_id" not in item:
                    item["portfolio_id"] = self.ecosystem_defaults.portfolio_id

                if "account_cash_id" not in item:
                    item["account_cash_id"] = self.ecosystem_defaults.account_id

                if "strategy1_cash_id" not in item:
                    item["strategy1_cash_id"] = self.ecosystem_defaults.strategy1_id

                if "strategy2_cash_id" not in item:
                    item["strategy2_cash_id"] = self.ecosystem_defaults.strategy2_id

                if "strategy3_cash_id" not in item:
                    item["strategy3_cash_id"] = self.ecosystem_defaults.strategy3_id

                if "account_position_id" not in item:
                    item["account_position_id"] = self.ecosystem_defaults.account_id

                if "strategy1_position_id" not in item:
                    item["strategy1_position_id"] = self.ecosystem_defaults.strategy1_id

                if "strategy2_position_id" not in item:
                    item["strategy2_position_id"] = self.ecosystem_defaults.strategy2_id

                if "strategy3_position_id" not in item:
                    item["strategy3_position_id"] = self.ecosystem_defaults.strategy3_id

            _l.info('build cash result %s ' % len(result))

            self.instance.items = result

    def build_positions_old(self):

        _l.info("build positions")

        with connection.cursor() as cursor:

            consolidated_select_columns = self.get_position_consolidation_for_select()

            query = """
                with balance_position_consolidation_matrix as 
                    (SELECT
                  portfolio_id,
                  account_position_id,
                  strategy1_position_id,
                  strategy2_position_id,
                  strategy3_position_id,
                  instrument_id,
                  SUM(position_size_with_sign) as position_size
                FROM pl_transactions_with_ttype WHERE transaction_date <= %s AND master_user_id = %s
                GROUP BY
                  portfolio_id,
                  account_position_id,
                  strategy1_position_id,
                  strategy2_position_id,
                  strategy3_position_id,
                  instrument_id)
                
            
                SELECT 
                    t.*, 
                    
                    i.name,
                    i.short_name,
                    i.user_code,
                    i.pricing_currency_id,
                    
                    (t.position_size * iph.principal_price * i.price_multiplier * cch.fx_rate + (t.position_size * iph.accrued_price * cch.fx_rate * 1 * i.accrued_multiplier)) as market_value
                FROM 
                    (SELECT
                      """ + consolidated_select_columns + """
                      instrument_id,
                      SUM(position_size) as position_size
                    FROM balance_position_consolidation_matrix
                    GROUP BY
                      """ + consolidated_select_columns + """
                      instrument_id) as t
                LEFT JOIN instruments_instrument as i
                ON t.instrument_id = i.id
                LEFT JOIN instruments_pricehistory as iph
                ON t.instrument_id = iph.instrument_id
                LEFT JOIN currencies_currencyhistory as cch
                ON i.pricing_currency_id = cch.currency_id
                WHERE cch.date = %s AND iph.date = %s AND cch.pricing_policy_id = %s;
            """

            cursor.execute(query, [
                    self.instance.report_date, self.instance.master_user.id,
                    self.instance.report_date, self.instance.report_date, self.instance.pricing_policy.id])

            _l.info("fetch position data")

            result = dictfetchall(cursor)

            ITEM_INSTRUMENT = 1

            for item in result:
                item['item_type'] = ITEM_INSTRUMENT
                item['item_type_code'] = "INSTR"
                item['item_type_name'] = "Instrument"

                if "portfolio_id" not in item:
                    item['portfolio_id'] = self.ecosystem_defaults.portfolio_id

                if "account_position__id" not in item:
                    item['account_position_id'] = self.ecosystem_defaults.account_id

                if "strategy1_position_id" not in item:
                    item['strategy1_position_id'] = self.ecosystem_defaults.strategy1_id

                if "strategy2_position_id" not in item:
                    item['strategy2_position_id'] = self.ecosystem_defaults.strategy2_id

                if "strategy3_position_id" not in item:
                    item['strategy3_position_id'] = self.ecosystem_defaults.strategy3_id

            _l.info('build position result %s ' % len(result))

            self.instance.items = self.instance.items + result

    def get_cash_consolidation_for_select(self):

        result = []

        if self.instance.portfolio_mode == Report.MODE_INDEPENDENT:
            result.append("portfolio_id")

        if self.instance.account_mode == Report.MODE_INDEPENDENT:
            result.append("account_cash_id")

        if self.instance.strategy1_mode == Report.MODE_INDEPENDENT:
            result.append("strategy1_cash_id")

        if self.instance.strategy2_mode == Report.MODE_INDEPENDENT:
            result.append("strategy2_cash_id")

        if self.instance.strategy3_mode == Report.MODE_INDEPENDENT:
            result.append("strategy3_cash_id")

        resultString = ''

        if len(result):
            resultString = ", ".join(result) + ', '

        return resultString

    def get_transaction_filter_sql_string(self):

        result_string = ''

        filter_sql_list = []

        portfolios_ids = []
        accounts_ids = []
        strategies1_ids = []
        strategies2_ids = []
        strategies3_ids = []

        if len(self.instance.portfolios):
            for portfolio in self.instance.portfolios:
                portfolios_ids.append(str(portfolio.id))

            filter_sql_list.append('portfolio_id in (' + ', '.join(portfolios_ids) + ')')

        if len(self.instance.accounts):
            for account in self.instance.accounts:
                accounts_ids.append(str(account.id))

            filter_sql_list.append('account_position_id in (' + ', '.join(accounts_ids) + ')')

        if len(self.instance.strategies1):
            for strategy in self.instance.strategies1:
                strategies1_ids.append(str(strategy.id))

            filter_sql_list.append('strategy1_position_id in (' + ', '.join(strategies1_ids) + ')')

        if len(self.instance.strategies2):
            for strategy in self.instance.strategies2:
                strategies2_ids.append(str(strategy.id))

            filter_sql_list.append('strategy2_position_id in (' + ', '.join(strategies2_ids) + ')')

        if len(self.instance.strategies3):
            for strategy in self.instance.strategies3:
                strategies3_ids.append(str(strategy.id))

            filter_sql_list.append('strategy2_position_id in (' + ', '.join(strategies2_ids) + ')')

        if len(filter_sql_list):
            result_string = result_string + 'where '
            result_string = result_string + ' and '.join(filter_sql_list)

        _l.info('get_transaction_filter_sql_string %s' % result_string)

        return result_string

    def build_cash_old(self):

        _l.info("build cash")

        with connection.cursor() as cursor:

            consolidated_select_columns = self.get_cash_consolidation_for_select()
            transaction_filter_sql_string = self.get_transaction_filter_sql_string()

            query = """
                
                with unioned_transactions_for_balance as (
                    
                    select 
                        id,
                        master_user_id,
                    
                        instrument_id,
                        portfolio_id,
                        transaction_class_id,
                        
                        transaction_date,
                        accounting_date,
                        cash_date,
                        
                        account_cash_id,
                        account_position_id,
                        account_interim_id,
                        
                        transaction_currency_id,
                        settlement_currency_id,
                        
                        position_size_with_sign,
                        cash_consideration
                        
                    from pl_transactions_with_ttype
                    
                    union all
                    
                    select 
                        id,
                        master_user_id,
                        
                        instrument_id,
                        portfolio_id,
                        transaction_class_id,
                        
                        transaction_date,
                        accounting_date,
                        cash_date,
                        
                        account_cash_id,
                        account_position_id,
                        account_interim_id,
                        
                        transaction_currency_id,
                        settlement_currency_id,
                        
                        (0) as position_size_with_sign,
                        cash_consideration
                        
                    from pl_cash_fx_trades_transactions_with_ttype
                    
                    union all
                    
                    select 
                        id,
                        master_user_id,
                        
                        instrument_id,
                        portfolio_id,
                        transaction_class_id,
                        
                        transaction_date,
                        accounting_date,
                        cash_date,
                        
                        account_cash_id,
                        account_position_id,
                        account_interim_id,
                        
                        transaction_currency_id,
                        settlement_currency_id,
                        
                        position_size_with_sign,
                        cash_consideration
                        
                    from pl_cash_fx_variations_transactions_with_ttype
                    
                
                ),
                
                unioned_interim_account_transactions as (
                    
                    select 
                           id,
                           master_user_id,
                           
                           portfolio_id,
                           account_cash_id,
                           -- TODO add consolidation columns
                           --strategy1_cash_id,
                           --strategy2_cash_id,
                           --strategy2_cash_id,
                           
                           position_size_with_sign,
                           /* не нужны для БАЛАНСА
                           principal_with_sign,
                           carry_with_sign,
                           overheads,
                            */
                           cash_consideration,
                           settlement_currency_id,
                           accounting_date,
                           cash_date,
                           account_position_id,
                           -- modification
                           account_interim_id as account_cash_id,
                           account_interim_id,
                           
                           case 
                                when cash_date < accounting_date
                                then cash_date
                                else accounting_date
                           end
                           as min_date
                           
                    -- добавить остальные поля
                    from unioned_transactions_for_balance -- USE TOTAL VIEW HERE
                    where accounting_Date <= '{report_date}' /* REPORTING DATE */
                      and '{report_date}' < cash_date
                    
                    -- case 2
                    union all
                    select 
                            id,
                            master_user_id,
                    
                           portfolio_id,
                           account_cash_id,
                           -- TODO add consolidation columns
                           -- modification
                           0 as position_size_with_sign,
                           (-cash_consideration) as cash_consideration,
                           settlement_currency_id,
                           accounting_date,
                           cash_date,
                           account_position_id,
                           -- modification
                           account_interim_id as account_cash_id,
                           account_interim_id,
                           
                           case 
                                when cash_date < accounting_date
                                then cash_date
                                else accounting_date
                           end
                           as min_date
                           
                    from unioned_transactions_for_balance
                    where cash_date  <= '{report_date}'  /* REPORTING DATE */
                      and '{report_date}' < accounting_Date
                
                    union all
                    
                    select 
                            id,
                            master_user_id,
                    
                           portfolio_id,
                           account_cash_id,
                           -- TODO add consolidation columns
                    
                           position_size_with_sign,
                           cash_consideration,
                           settlement_currency_id,
                           accounting_date,
                           cash_date,
                    
                           account_position_id,
                           account_interim_id,
                           account_interim_id,
                           
                           case 
                                when cash_date < accounting_date
                                then cash_date
                                else accounting_date
                           end
                           as min_date
                           
                    from unioned_transactions_for_balance
                    where not (accounting_Date <= '{report_date}' /* REPORTING DATE */
                      and '{report_date}' < cash_date)
                        
                ),
                
                filtered_transactions as (
                    
                    select * from unioned_interim_account_transactions
                    {transaction_filter_sql_string}
                
                )
                            
                select 
                    t_with_report_fx_rate.*, 
                    c.name,
                    c.short_name,
                    c.user_code,
                    
                    (t_with_report_fx_rate.position_size * stl_fx_rate / report_fx_rate) as market_value
                from 
                    (select 
                        *,
                        case when {report_currency_id} = {default_currency_id}
                            then 1
                            else
                                (select
                            fx_rate
                         from currencies_currencyhistory
                         where
                            currency_id = {report_currency_id} and
                            date = '{report_date}' and
                            pricing_policy_id = {pricing_policy_id}
                        )
                            end as report_fx_rate,

                        case when settlement_currency_id = {default_currency_id}
                            then 1
                            else
                                (select
                            fx_rate
                         from currencies_currencyhistory
                         where
                            currency_id = settlement_currency_id and
                            date = '{report_date}' and
                            pricing_policy_id = {pricing_policy_id}
                        )
                            end as stl_fx_rate
                    from (
                        select
                          {consolidated_select_columns}
                          settlement_currency_id,
                          SUM(cash_consideration) as position_size
                        from filtered_transactions
                        where min_date <= '{report_date}' and master_user_id = {master_user_id}
                        group by
                          {consolidated_select_columns}
                          settlement_currency_id 
                        ) as t
                    ) as t_with_report_fx_rate
                left join currencies_currency as c
                ON t_with_report_fx_rate.settlement_currency_id = c.id
                
            """

            query = query.format(report_date=self.instance.report_date,
                                 master_user_id=self.instance.master_user.id,
                                 default_currency_id=self.ecosystem_defaults.currency_id,
                                 report_currency_id=self.instance.report_currency.id,
                                 pricing_policy_id=self.instance.pricing_policy.id,
                                 consolidated_select_columns=consolidated_select_columns,
                                 transaction_filter_sql_string=transaction_filter_sql_string

                                 )

            cursor.execute(query)

            query_str = str(cursor.query, 'utf-8')
            _l.info(query_str)

            result = dictfetchall(cursor)

            ITEM_CURRENCY = 2

            for item in result:
                item["item_type"] = ITEM_CURRENCY
                item["item_type_code"] = "CCY"
                item["item_type_name"] = "Currency"

                item["currency_id"] = item["settlement_currency_id"]

                if "portfolio_id" not in item:
                    item["portfolio_id"] = self.ecosystem_defaults.portfolio_id

                if "account_cash_id" not in item:
                    item["account_cash_id"] = self.ecosystem_defaults.account_id

                if "strategy1_cash_id" not in item:
                    item["strategy1_cash_id"] = self.ecosystem_defaults.strategy1_id

                if "strategy2_cash_id" not in item:
                    item["strategy2_cash_id"] = self.ecosystem_defaults.strategy2_id

                if "strategy3_cash_id" not in item:
                    item["strategy3_cash_id"] = self.ecosystem_defaults.strategy3_id

            _l.info('build cash result %s ' % len(result))

            self.instance.items = self.instance.items + result

    def add_data_items_instruments(self, ids):

        self.instance.item_instruments = Instrument.objects.select_related(
            'instrument_type',
            'instrument_type__instrument_class',
            'pricing_currency',
            'accrued_currency',
            'payment_size_detail',
            'daily_pricing_model',
            'price_download_scheme',
            'price_download_scheme__provider',
        ).prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).filter(master_user=self.instance.master_user) \
            .filter(id__in=ids)

    def add_data_items_portfolios(self, ids):

        self.instance.item_portfolios = Portfolio.objects.prefetch_related(
            'attributes'
        ).defer('object_permissions', 'responsibles', 'counterparties', 'transaction_types', 'accounts', 'tags') \
            .filter(master_user=self.instance.master_user)\
            .filter(
            id__in=ids)

    def add_data_items_accounts(self, ids):

        self.instance.item_accounts = Account.objects.select_related('type').prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).defer('object_permissions').filter(master_user=self.instance.master_user).filter(id__in=ids)

    def add_data_items_currencies(self, ids):

        self.instance.item_currencies = Currency.objects.prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).filter(master_user=self.instance.master_user).filter(id__in=ids)

    def add_data_items(self):

        instance_relations_st = time.perf_counter()

        _l.debug('_refresh_with_perms_optimized instance relations done: %s',
                 "{:3.3f}".format(time.perf_counter() - instance_relations_st))

        permissions_st = time.perf_counter()

        _l.debug('_refresh_with_perms_optimized permissions done: %s', "{:3.3f}".format(time.perf_counter() - permissions_st))

        item_relations_st = time.perf_counter()

        instrument_ids = []
        portfolio_ids = []
        account_ids = []
        currencies_ids = []

        for item in self.instance.items:

            if 'portfolio_id' in item and item['portfolio_id'] != '-':
                portfolio_ids.append(item['portfolio_id'])

            if 'instrument_id' in item:
                instrument_ids.append(item['instrument_id'])

            if 'account_position_id' in item and item['account_position_id'] != '-':
                account_ids.append(item['account_position_id'])
            if 'account_cash_id' in item and item['account_cash_id'] != '-':
                account_ids.append(item['account_cash_id'])

            if 'currency_id' in item:
                currencies_ids.append(item['currency_id'])
            if 'pricing_currency_id' in item:
                currencies_ids.append(item['pricing_currency_id'])

        self.add_data_items_instruments(instrument_ids)
        self.add_data_items_portfolios(portfolio_ids)
        self.add_data_items_accounts(account_ids)
        self.add_data_items_currencies(currencies_ids)

        self.instance.custom_fields = BalanceReportCustomField.objects.filter(master_user=self.instance.master_user)

        _l.debug('_refresh_with_perms_optimized item relations done: %s', "{:3.3f}".format(time.perf_counter() - item_relations_st))
