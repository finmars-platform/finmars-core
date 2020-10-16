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
from poms.reports.sql_builders.helpers import get_transaction_filter_sql_string, get_report_fx_rate, \
    get_fx_trades_and_fx_variations_transaction_filter_sql_string, get_where_expression_for_position_consolidation, \
    get_position_consolidation_for_select, get_pl_left_join_consolidation, dictfetchall
from poms.reports.sql_builders.pl import PLReportBuilderSql
from poms.users.models import EcosystemDefault
from django.conf import settings

_l = logging.getLogger('poms.reports')


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

        self.build()

        _l.info('items total %s' % len(self.instance.items))

        _l.info('build_st done: %s', "{:3.3f}".format(time.perf_counter() - st))

        self.add_data_items()

        return self.instance

    def build(self):

        _l.info("build cash")

        with connection.cursor() as cursor:

            consolidated_select_columns = self.get_cash_consolidation_for_select()

            st = time.perf_counter()
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
                    where accounting_date <= '{report_date}' /* REPORTING DATE */
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
                    where not (accounting_date <= '{report_date}' /* REPORTING DATE */
                      and '{report_date}' < cash_date)
                        
                ),
                
                filtered_transactions as (
                    
                    select * from unioned_interim_account_transactions
                    {transaction_filter_sql_string}
                
                )
                
                -- main query  
                
                -- Cash 
                select 
                
                    instrument_id,
                    {consolidated_select_columns}
                
                    name,
                    short_name,
                    user_code,
                    
                    item_type,
                    item_type_name,
                    
                    position_size,
                    market_value,
                    
                    net_cost_price,
                    net_cost_price_loc,
                    
                    ytm,
                    ytm_at_cost, 
                    
                    position_return,
                    net_position_return,
                    
                    time_invested,
                    return_annauly
                
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
                            
                        market_value,
                        
                        (0) as net_cost_price,
                        (0) as net_cost_price_loc,
                            
                        (0) as ytm,
                        (0) as ytm_at_cost, 
                            
                        (0) as position_return,
                        (0) as net_position_return,
                            
                        (0) as time_invested,
                        (0) as return_annauly
                     
                     
                     from (
                   
                        select 
                        
                            instrument_id,
                            {consolidated_select_columns}
                            settlement_currency_id,
                            
                            SUM(position_size) as position_size,
                            SUM(market_value) as market_value
                            
                        from (
                         -- Cash 
                            select 
                            
                                instrument_id,
                                {consolidated_select_columns}
                                settlement_currency_id,
    
                                position_size,
      
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
                                       (-1) as instrument_id,
                                      SUM(cash_consideration) as position_size
                                    from filtered_transactions
                                    where min_date <= '{report_date}' and master_user_id = {master_user_id}
                                    group by
                                      {consolidated_select_columns}
                                      settlement_currency_id, instrument_id
                                    ) as t
                                ) as t_with_report_fx_rate
                            
                            -- union with Transaction PL 
                            union all
                            
                            select 
                
                                instrument_id,
                                {consolidated_select_columns}
                                settlement_currency_id,
                            
                                position_size,
                                
                                (0) as market_value
        
                        
                            from (
                                select 
                                
                                    instrument_id,
                                    {consolidated_select_columns}
                                    
                                    settlement_currency_id,
                                    
                                    item_type,
                                    item_type_name,
                                    
                                    position_size,
                                     
                                    
                                    ccy.name,
                                    ccy.short_name,
                                    ccy.user_code,
                                    
                                    (0) as market_value,
                                
                                    (0) as net_cost_price,
                                    (0) as net_cost_price_loc,
                                    
                                    (0) as ytm,
                                    (0) as ytm_at_cost, 
                                    
                                    (0) as position_return,
                                    (0) as net_position_return,
                                    
                                    (0) as time_invested,
                                    (0) as return_annauly
                                
                                from (
                                    select 
                  
                                        (5) as item_type,
                                        ('Other') as item_type_name,
                                        
                                        (-1) as instrument_id,
                                        {consolidated_select_columns}
                                        
                                        settlement_currency_id,
                                        
                    
                                        sum(cash_consideration * stl_cur_fx/rep_cur_fx) as position_size,
                                        
                                        sum(principal_with_sign * stl_cur_fx/rep_cur_fx) as principal_opened,
                                        sum(carry_with_sign * stl_cur_fx/rep_cur_fx)     as carry_opened,
                                        sum(overheads_with_sign * stl_cur_fx/rep_cur_fx) as overheads_opened,
                    
                                        sum(principal_with_sign * stl_cur_fx/rep_cur_fx) as principal_fx_opened,
                                        sum(principal_with_sign * stl_cur_fx/rep_cur_fx) as carry_fx_opened,
                                        sum(principal_with_sign * stl_cur_fx/rep_cur_fx) as overheads_fx_opened,
                                         
                                        (0) as principal_fixed_opened,
                                        (0) as carry_fixed_opened,
                                        (0) as overheads_fixed_opened
                                    
                                    from (select 
                                            *,
                                            case when
                                            sft.settlement_currency_id={default_currency_id}
                                            then 1
                                            else
                                               (select  fx_rate
                                            from currencies_currencyhistory c_ch
                                            where date = '{report_date}'
                                              and c_ch.currency_id = sft.settlement_currency_id 
                                              and c_ch.pricing_policy_id = {pricing_policy_id}
                                              limit 1)
                                            end as stl_cur_fx,
                                            case
                                               when /* reporting ccy = system ccy*/ {report_currency_id} = {default_currency_id}
                                                   then 1
                                               else
                                                   (select  fx_rate
                                                    from currencies_currencyhistory c_ch
                                                    where date = '{report_date}' and 
                                                     c_ch.currency_id = {report_currency_id} and
                                                     c_ch.pricing_policy_id = {pricing_policy_id}
                                                     limit 1)
                                            end as rep_cur_fx
                                        from pl_cash_transaction_pl_transactions_with_ttype sft where 
                                                  transaction_class_id in (5)
                                                  and accounting_date <= '{report_date}'
                                                  and master_user_id = {master_user_id}
                                                  {fx_trades_and_fx_variations_filter_sql_string}
                                            ) as transaction_pl_w_fxrate
                                    group by 
                                        settlement_currency_id, {consolidated_select_columns} instrument_id order by settlement_currency_id
                                    ) as grouped_transaction_pl
                                left join currencies_currency as ccy on settlement_currency_id = ccy.id
                                ) as pre_final_union_transaction_pl_calculations_level_0
                            
                        ) as unioned_transaction_pl_with_cash 
                        
                        group by
                                  {consolidated_select_columns}
                                  settlement_currency_id, instrument_id
                        
                    ) as grouped_cash
                    
                    left join currencies_currency as c
                    ON grouped_cash.settlement_currency_id = c.id
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
                    market_value,
                    
                    net_cost_price,
                    net_cost_price_loc,
                    
                    ytm,
                    ytm_at_cost, 
                    
                    position_return,
                    net_position_return,
                    
                    time_invested,
                    return_annauly
                    
                from (
                    select 
                        balance_q.instrument_id,
                        {balance_q_consolidated_select_columns}
                    
                        name,
                        short_name,
                        user_code,
                        
                        item_type,
                        item_type_name,
                        
                        position_size,
                        market_value,
                        
                        net_cost_price,
                        net_cost_price_loc,
                        
                        ytm,
                        ytm_at_cost, 
                        
                        position_return,
                        net_position_return,
                        
                        time_invested,
                        return_annauly 
                        
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
                            where min_date <= '{report_date}' and master_user_id = {master_user_id}
                            group by
                              {consolidated_select_columns}
                              instrument_id) as t
                        left join instruments_instrument as i
                        ON instrument_id = i.id
                        ) as grouped
                    where position_size != 0
                    ) as balance_q
                    left join 
                        (select 
                                instrument_id, 
                                {consolidated_select_columns}
                                
                                net_cost_price,
                                net_cost_price_loc,
                                ytm, -- is missed 
                                ytm_at_cost, -- is missed
                                position_return,
                                net_position_return,
                                time_invested,
                                return_annauly --is missed   
                              from ({pl_query}) as pl 
                    ) as pl_q
                    on balance_q.instrument_id = pl_q.instrument_id {pl_left_join_consolidation}
                
                ) as joined_positions
            """

            transaction_filter_sql_string = get_transaction_filter_sql_string(self.instance)
            report_fx_rate = get_report_fx_rate(self.instance, self.instance.report_date)
            fx_trades_and_fx_variations_filter_sql_string = get_fx_trades_and_fx_variations_transaction_filter_sql_string(self.instance)
            transactions_all_with_multipliers_where_expression = get_where_expression_for_position_consolidation(self.instance,
                                                                                                                     prefix="tt_w_m.", prefix_second="t_o.")
            consolidation_columns = get_position_consolidation_for_select(self.instance)
            tt_consolidation_columns = get_position_consolidation_for_select(self.instance, prefix="tt.")
            balance_q_consolidated_select_columns = get_position_consolidation_for_select(self.instance, prefix="balance_q.")
            pl_left_join_consolidation = get_pl_left_join_consolidation(self.instance)
            fx_trades_and_fx_variations_filter_sql_string = get_fx_trades_and_fx_variations_transaction_filter_sql_string(
                self.instance)

            pl_query = PLReportBuilderSql.get_source_query(cost_method=self.instance.cost_method.id)

            _l.info('transaction_filter_sql_string: "%s"' % transaction_filter_sql_string)

            pl_query = pl_query.format(report_date=self.instance.report_date,
                                       master_user_id=self.instance.master_user.id,
                                       default_currency_id=self.ecosystem_defaults.currency_id,
                                       report_currency_id=self.instance.report_currency.id,
                                       pricing_policy_id=self.instance.pricing_policy.id,
                                       report_fx_rate=report_fx_rate,
                                       transaction_filter_sql_string=transaction_filter_sql_string,
                                       fx_trades_and_fx_variations_filter_sql_string=fx_trades_and_fx_variations_filter_sql_string,
                                       consolidation_columns=consolidation_columns,
                                       balance_q_consolidated_select_columns=balance_q_consolidated_select_columns,
                                       tt_consolidation_columns=tt_consolidation_columns,
                                       transactions_all_with_multipliers_where_expression=transactions_all_with_multipliers_where_expression,
                                       filter_query_for_balance_in_multipliers_table='')
                                       # filter_query_for_balance_in_multipliers_table=' where multiplier = 1') # TODO ask for right where expression

            query = query.format(report_date=self.instance.report_date,
                                 master_user_id=self.instance.master_user.id,
                                 default_currency_id=self.ecosystem_defaults.currency_id,
                                 report_currency_id=self.instance.report_currency.id,
                                 pricing_policy_id=self.instance.pricing_policy.id,
                                 consolidated_select_columns=consolidated_select_columns,
                                 balance_q_consolidated_select_columns=balance_q_consolidated_select_columns,
                                 transaction_filter_sql_string=transaction_filter_sql_string,
                                 pl_query=pl_query,
                                 pl_left_join_consolidation=pl_left_join_consolidation,
                                 fx_trades_and_fx_variations_filter_sql_string= fx_trades_and_fx_variations_filter_sql_string
                                 )

            cursor.execute(query)

            _l.info('Balance report query execute done: %s', "{:3.3f}".format(time.perf_counter() - st))

            query_str = str(cursor.query, 'utf-8')

            if settings.LOCAL:
                with open('/tmp/query_result.txt', 'w') as the_file:
                    the_file.write(query_str)


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
