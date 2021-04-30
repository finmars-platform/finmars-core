import logging
import time

from django.db import connection

from poms.accounts.models import Account
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, InstrumentType, LongUnderlyingExposure, ShortUnderlyingExposure, \
    ExposureCalculationModel
from poms.portfolios.models import Portfolio
from poms.reports.builders.balance_item import Report
from poms.reports.builders.base_builder import BaseReportBuilder
from poms.reports.models import BalanceReportCustomField
from poms.reports.sql_builders.helpers import get_transaction_filter_sql_string, get_report_fx_rate, \
    get_fx_trades_and_fx_variations_transaction_filter_sql_string, get_where_expression_for_position_consolidation, \
    get_position_consolidation_for_select, get_pl_left_join_consolidation, dictfetchall, \
    get_cash_consolidation_for_select, get_cash_as_position_consolidation_for_select
from poms.reports.sql_builders.pl import PLReportBuilderSql
from poms.users.models import EcosystemDefault
from django.conf import settings

_l = logging.getLogger('poms.reports')


class BalanceReportBuilderSql:

    def __init__(self, instance=None):

        _l.debug('ReportBuilderSql init')

        self.instance = instance

        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self.instance.master_user)

        _l.debug('self.instance master_user %s' % self.instance.master_user)
        _l.debug('self.instance report_date %s' % self.instance.report_date)

    def build_balance(self):
        st = time.perf_counter()

        self.instance.items = []

        self.build()

        _l.debug('items total %s' % len(self.instance.items))

        _l.debug('build_st done: %s', "{:3.3f}".format(time.perf_counter() - st))

        self.add_data_items()

        return self.instance

    def build(self):

        _l.debug("build cash")

        with connection.cursor() as cursor:

            st = time.perf_counter()

            pl_query = PLReportBuilderSql.get_source_query(cost_method=self.instance.cost_method.id)

            transaction_filter_sql_string = get_transaction_filter_sql_string(self.instance)
            report_fx_rate = get_report_fx_rate(self.instance, self.instance.report_date)
            fx_trades_and_fx_variations_filter_sql_string = get_fx_trades_and_fx_variations_transaction_filter_sql_string(self.instance)
            transactions_all_with_multipliers_where_expression = get_where_expression_for_position_consolidation(self.instance,
                                                                                                                 prefix="tt_w_m.", prefix_second="t_o.")
            consolidation_columns = get_position_consolidation_for_select(self.instance)
            tt_consolidation_columns = get_position_consolidation_for_select(self.instance, prefix="tt.")
            tt_in1_consolidation_columns = get_position_consolidation_for_select(self.instance, prefix="tt_in1.")
            balance_q_consolidated_select_columns = get_position_consolidation_for_select(self.instance, prefix="balance_q.")
            pl_left_join_consolidation = get_pl_left_join_consolidation(self.instance)
            fx_trades_and_fx_variations_filter_sql_string = get_fx_trades_and_fx_variations_transaction_filter_sql_string(
                self.instance)

            _l.debug('report_date: "%s"' % self.instance.report_date)
            _l.debug('report_fx_rate: "%s"' % report_fx_rate)
            _l.debug('default_currency_id: "%s"' % self.ecosystem_defaults.currency_id)
            _l.debug('report_currency: "%s"' % self.instance.report_currency.id)
            _l.debug('pricing_policy: "%s"' % self.instance.pricing_policy.id)
            _l.debug('transaction_filter_sql_string: "%s"' % transaction_filter_sql_string)
            _l.debug('fx_trades_and_fx_variations_filter_sql_string: "%s"' % fx_trades_and_fx_variations_filter_sql_string)
            _l.debug('consolidation_columns: "%s"' % consolidation_columns)
            _l.debug('balance_q_consolidated_select_columns: "%s"' % balance_q_consolidated_select_columns)
            _l.debug('tt_consolidation_columns: "%s"' % tt_consolidation_columns)
            _l.debug('tt_in1_consolidation_columns: "%s"' % tt_in1_consolidation_columns)
            _l.debug('transactions_all_with_multipliers_where_expression: "%s"' % transactions_all_with_multipliers_where_expression)

            pl_query = pl_query.format(report_date=self.instance.report_date,
                                       master_user_id=self.instance.master_user.id,
                                       default_currency_id=self.instance.master_user.system_currency_id,
                                       report_currency_id=self.instance.report_currency.id,
                                       pricing_policy_id=self.instance.pricing_policy.id,
                                       report_fx_rate=report_fx_rate,
                                       transaction_filter_sql_string=transaction_filter_sql_string,
                                       fx_trades_and_fx_variations_filter_sql_string=fx_trades_and_fx_variations_filter_sql_string,
                                       consolidation_columns=consolidation_columns,
                                       balance_q_consolidated_select_columns=balance_q_consolidated_select_columns,
                                       tt_consolidation_columns=tt_consolidation_columns,
                                       tt_in1_consolidation_columns=tt_in1_consolidation_columns,
                                       transactions_all_with_multipliers_where_expression=transactions_all_with_multipliers_where_expression,
                                       filter_query_for_balance_in_multipliers_table='')
            # filter_query_for_balance_in_multipliers_table=' where multiplier = 1') # TODO ask for right where expression

            ######################################

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
                        cash_consideration,
                        
                        strategy1_cash_id,
                        strategy2_cash_id,
                        strategy3_cash_id,
                        
                        strategy1_position_id,
                        strategy2_position_id,
                        strategy3_position_id
                        
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
                        cash_consideration,
                        
                        strategy1_cash_id,
                        strategy2_cash_id,
                        strategy3_cash_id,
                        
                        strategy1_position_id,
                        strategy2_position_id,
                        strategy3_position_id
                        
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
                        cash_consideration,
                        
                        strategy1_cash_id,
                        strategy2_cash_id,
                        strategy3_cash_id,
                        
                        strategy1_position_id,
                        strategy2_position_id,
                        strategy3_position_id
                        
                    from pl_cash_fx_variations_transactions_with_ttype
                    
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
                        cash_consideration,
                        
                        strategy1_cash_id,
                        strategy2_cash_id,
                        strategy3_cash_id,
                        
                        strategy1_position_id,
                        strategy2_position_id,
                        strategy3_position_id
                        
                    from pl_cash_transaction_pl_transactions_with_ttype
                  
                ),
                
                unioned_interim_account_transactions as (
                    
                    select 
                           id,
                           master_user_id,
                           
                           instrument_id,
                           portfolio_id,
                           
                           transaction_class_id,
              
                           strategy1_cash_id,
                           strategy2_cash_id,
                           strategy3_cash_id,
                           
                           
                           strategy1_position_id,
                           strategy2_position_id,
                           strategy3_position_id,
                           
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
                           
                           transaction_class_id,
                           
                           strategy1_cash_id,
                           strategy2_cash_id,
                           strategy3_cash_id,
                           
                           strategy1_position_id,
                           strategy2_position_id,
                           strategy3_position_id,
                           
                           
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
                           
                           transaction_class_id,
                           
                           strategy1_cash_id,
                           strategy2_cash_id,
                           strategy3_cash_id,
                           
                           strategy1_position_id,
                           strategy2_position_id,
                           strategy3_position_id,
                    
                           position_size_with_sign,
                           cash_consideration,
                           settlement_currency_id,
                           accounting_date,
                           cash_date,
                    
                           account_position_id,
                           account_cash_id,
                           account_interim_id,
                           
                           case 
                                when cash_date < accounting_date
                                then cash_date
                                else accounting_date
                           end
                           as min_date
                           
                    from unioned_transactions_for_balance
                    --where not (accounting_date <= '{report_date}' /* REPORTING DATE */
                    --  and '{report_date}' < cash_date)
                    where not ( (accounting_date <= '{report_date}' 
                      and '{report_date}' < cash_date) 
                      or (cash_date  <= '{report_date}' and '{report_date}' < accounting_date)) 
                        
                ),
                
                filtered_transactions as (
                    
                    select * from unioned_interim_account_transactions
                    {transaction_filter_sql_string}
                
                )
                
                -- main query  
                
                -- Cash 
                select 
                
                    instrument_id,
                    {consolidated_position_columns}
                
                    name,
                    short_name,
                    user_code,
                    
                    pricing_currency_id,
                    instrument_pricing_currency_fx_rate,
                    instrument_accrued_currency_fx_rate,
                    
                    instrument_principal_price,
                    instrument_accrued_price,
                    
                    currency_id,
                    
                    item_type,
                    item_type_name,
                    
                    position_size,
                    
                    co_directional_exposure_currency_id,
                    counter_directional_exposure_currency_id,
                    
                    exposure_calculation_model_id,
                    long_underlying_exposure_id,
                    short_underlying_exposure_id,
                
                    has_second_exposure_currency,
                    
                    market_value,
                    market_value_loc,
                    
                    exposure,
                    exposure_loc,
                    
                    exposure_delta_adjusted,
                    exposure_long_underlying_zero,
                    exposure_long_underlying_price,
                    exposure_long_underlying_price_delta,
                    exposure_long_underlying_fx_rate,
                    exposure_long_underlying_fx_rate_delta,
                    
                    exposure_short_underlying_zero,
                    exposure_short_underlying_price,
                    exposure_short_underlying_price_delta,
                    exposure_short_underlying_fx_rate,
                    exposure_short_underlying_fx_rate_delta,
                    
                    exposure_2,
                    exposure_2_loc,
                    
                    net_cost_price,
                    net_cost_price_loc,
                    
                    gross_cost_price,
                    gross_cost_price_loc,
                    
                    principal_invested,
                    principal_invested_loc,
                    
                    amount_invested,
                    amount_invested_loc,
                    
                    position_return,
                    net_position_return,
                    time_invested,
                    
                    ytm,
                    modified_duration,
                    ytm_at_cost,
                    return_annually,
        
                    principal_opened,
                    carry_opened,
                    overheads_opened,
                    total_opened,
                    
                    principal_closed,
                    carry_closed,
                    overheads_closed,
                    total_closed,
                    
                    principal_fx_opened,
                    carry_fx_opened,
                    overheads_fx_opened,
                    total_fx_opened,
                    
                    principal_fx_closed,
                    carry_fx_closed,
                    overheads_fx_closed,
                    total_fx_closed,
                    
                    principal_fixed_opened,
                    carry_fixed_opened,
                    overheads_fixed_opened,
                    total_fixed_opened,
                    
                    principal_fixed_closed,
                    carry_fixed_closed,
                    overheads_fixed_closed,
                    total_fixed_closed,
                    
                    -- loc
                    
                    principal_opened_loc,
                    carry_opened_loc,
                    overheads_opened_loc,
                    total_opened_loc,
                    
                    principal_closed_loc,
                    carry_closed_loc,
                    overheads_closed_loc,
                    total_closed_loc,
                    
                    principal_fx_opened_loc,
                    carry_fx_opened_loc,
                    overheads_fx_opened_loc,
                    total_fx_opened_loc,
                    
                    principal_fx_closed_loc,
                    carry_fx_closed_loc,
                    overheads_fx_closed_loc,
                    total_fx_closed_loc,
                    
                    principal_fixed_opened_loc,
                    carry_fixed_opened_loc,
                    overheads_fixed_opened_loc,
                    total_fixed_opened_loc,
                    
                    principal_fixed_closed_loc,
                    carry_fixed_closed_loc,
                    overheads_fixed_closed_loc,
                    total_fixed_closed_loc
                
                from (   
                
                    select 
                     
                         (-1) as instrument_id,
                        {consolidated_cash_as_position_columns}
                        
                        (settlement_currency_id) as currency_id,
                            
                        (2) as item_type,
                        ('Currency') as item_type_name,
                            
                        position_size,
                                  
                        c.name,
                        c.short_name,
                        c.user_code,
                        
                        (-1) as pricing_currency_id,
                        (0) as instrument_pricing_currency_fx_rate,
                        (0) as instrument_accrued_currency_fx_rate,
                        (0) as instrument_principal_price,
                        (0) as instrument_accrued_price,
                        
                        (c.id) as co_directional_exposure_currency_id,
                        (-1) as counter_directional_exposure_currency_id,
                        
                        (-1) as exposure_calculation_model_id,
                        (-1) as long_underlying_exposure_id,
                        (-1) as short_underlying_exposure_id,
                    
                        (false) as has_second_exposure_currency,
                            
                        market_value,
                        market_value_loc,
                        
                        exposure,
                        exposure_loc,
                        
                        (0) as exposure_delta_adjusted,
                        (0) as exposure_long_underlying_zero,
                        (0) as exposure_long_underlying_price,
                        (0) as exposure_long_underlying_price_delta,
                        (0) as exposure_long_underlying_fx_rate,
                        (0) as exposure_long_underlying_fx_rate_delta,
                        
                        (0) as exposure_short_underlying_zero,
                        (0) as exposure_short_underlying_price,
                        (0) as exposure_short_underlying_price_delta,
                        (0) as exposure_short_underlying_fx_rate,
                        (0) as exposure_short_underlying_fx_rate_delta,
                        
                        (0) as exposure_2,
                        (0) as exposure_2_loc,
                        
                        (0) as net_cost_price,
                        (0) as net_cost_price_loc,
                        
                        (0) as gross_cost_price,
                        (0) as gross_cost_price_loc,
                        
                        (0) as principal_invested,
                        (0) as principal_invested_loc,
                        
                        (0) as amount_invested,
                        (0) as amount_invested_loc,
                            
                        (0) as position_return,
                        (0) as net_position_return,
                        (0) as time_invested,
                        
                        (0) as ytm,
                        (0) as modified_duration,
                        (0) as ytm_at_cost,
                        (0) as return_annually,
                        
                        (0) as principal_opened,
                        (0) as carry_opened,
                        (0) as overheads_opened,
                        (0) as total_opened,
                        
                        (0) as principal_closed,
                        (0) as carry_closed,
                        (0) as overheads_closed,
                        (0) as total_closed,
                        
                        (0) as principal_fx_opened,
                        (0) as carry_fx_opened,
                        (0) as overheads_fx_opened,
                        (0) as total_fx_opened,
                        
                        (0) as principal_fx_closed,
                        (0) as carry_fx_closed,
                        (0) as overheads_fx_closed,
                        (0) as total_fx_closed,
                        
                        (0) as principal_fixed_opened,
                        (0) as carry_fixed_opened,
                        (0) as overheads_fixed_opened,
                        (0) as total_fixed_opened,
                        
                        (0) as principal_fixed_closed,
                        (0) as carry_fixed_closed,
                        (0) as overheads_fixed_closed,
                        (0) as total_fixed_closed,
                        
                        -- loc
                        
                        (0) as principal_opened_loc,
                        (0) as carry_opened_loc,
                        (0) as overheads_opened_loc,
                        (0) as total_opened_loc,
                        
                        (0) as principal_closed_loc,
                        (0) as carry_closed_loc,
                        (0) as overheads_closed_loc,
                        (0) as total_closed_loc,
                        
                        (0) as principal_fx_opened_loc,
                        (0) as carry_fx_opened_loc,
                        (0) as overheads_fx_opened_loc,
                        (0) as total_fx_opened_loc,
                        
                        (0) as principal_fx_closed_loc,
                        (0) as carry_fx_closed_loc,
                        (0) as overheads_fx_closed_loc,
                        (0) as total_fx_closed_loc,
                        
                        (0) as principal_fixed_opened_loc,
                        (0) as carry_fixed_opened_loc,
                        (0) as overheads_fixed_opened_loc,
                        (0) as total_fixed_opened_loc,
                        
                        (0) as principal_fixed_closed_loc,
                        (0) as carry_fixed_closed_loc,
                        (0) as overheads_fixed_closed_loc,
                        (0) as total_fixed_closed_loc
                    
                     from (
                   
                        select 
                        
                            {consolidated_cash_columns}
                            settlement_currency_id,
                            
                            SUM(position_size) as position_size,
                            SUM(market_value) as market_value,
                            SUM(market_value_loc) as market_value_loc,
                            
                            SUM(exposure) as exposure,
                            SUM(exposure_loc) as exposure_loc
                            
                        from (
                         -- Cash 
                            select 
                            
                                instrument_id,
                                {consolidated_cash_columns}
                                settlement_currency_id,
    
                                position_size,
      
                                (t_with_report_fx_rate.position_size * stl_fx_rate / report_fx_rate) as market_value,
                                (t_with_report_fx_rate.position_size * stl_fx_rate) as market_value_loc,
                                
                                (t_with_report_fx_rate.position_size * stl_fx_rate / report_fx_rate) as exposure,
                                (t_with_report_fx_rate.position_size * stl_fx_rate) as exposure_loc
                                 
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
                                      {consolidated_cash_columns}
                                      settlement_currency_id,
                                       (-1) as instrument_id,
                                      SUM(cash_consideration) as position_size
                                    from filtered_transactions
                                    where min_date <= '{report_date}' and master_user_id = {master_user_id}
                                    group by
                                      {consolidated_cash_columns}
                                      settlement_currency_id, instrument_id
                                    ) as t
                                ) as t_with_report_fx_rate
                            
                        ) as unioned_transaction_pl_with_cash 
                        
                        group by
                                  {consolidated_cash_columns}
                                  settlement_currency_id
                        
                    ) as grouped_cash
                    
                    left join currencies_currency as c
                    ON grouped_cash.settlement_currency_id = c.id
                    where position_size != 0
                    
                ) as pre_final_union_cash_calculations_level_0
                
                union all
                
                -- Positions
                select 
                    
                    instrument_id,
                    {consolidated_position_columns}
                
                    name,
                    short_name,
                    user_code,
                    
                    pricing_currency_id,
                    instrument_pricing_currency_fx_rate,
                    instrument_accrued_currency_fx_rate,
                    
                    instrument_principal_price,
                    instrument_accrued_price,
                    
                    currency_id,
                    
                    item_type,
                    item_type_name,
                    
                    position_size,
                    
                    co_directional_exposure_currency_id,
                    counter_directional_exposure_currency_id,
                    
                    exposure_calculation_model_id,
                    long_underlying_exposure_id,
                    short_underlying_exposure_id,
                
                    has_second_exposure_currency,
                    
                    market_value,
                    market_value_loc,
                    
                    exposure,
                    exposure_loc,
                    
                    exposure_delta_adjusted,
                    exposure_long_underlying_zero,
                    exposure_long_underlying_price,
                    exposure_long_underlying_price_delta,
                    exposure_long_underlying_fx_rate,
                    exposure_long_underlying_fx_rate_delta,
                    
                    exposure_short_underlying_zero,
                    exposure_short_underlying_price,
                    exposure_short_underlying_price_delta,
                    exposure_short_underlying_fx_rate,
                    exposure_short_underlying_fx_rate_delta,
                    
                    exposure_2,
                    exposure_2_loc,
                    
                    net_cost_price,
                    net_cost_price_loc,
                    
                    gross_cost_price,
                    gross_cost_price_loc,
                    
                    principal_invested,
                    principal_invested_loc,
                    
                    amount_invested,
                    amount_invested_loc,
                    
                    position_return,
                    net_position_return,
                    time_invested,
                    
                    ytm,
                    modified_duration,
                    ytm_at_cost,
                    return_annually,
        
                    principal_opened,
                    carry_opened,
                    overheads_opened,
                    total_opened,
                    
                    principal_closed,
                    carry_closed,
                    overheads_closed,
                    total_closed,
                    
                    principal_fx_opened,
                    carry_fx_opened,
                    overheads_fx_opened,
                    total_fx_opened,
                    
                    principal_fx_closed,
                    carry_fx_closed,
                    overheads_fx_closed,
                    total_fx_closed,
                    
                    principal_fixed_opened,
                    carry_fixed_opened,
                    overheads_fixed_opened,
                    total_fixed_opened,
                    
                    principal_fixed_closed,
                    carry_fixed_closed,
                    overheads_fixed_closed,
                    total_fixed_closed,
                    
                    -- loc
                    
                    principal_opened_loc,
                    carry_opened_loc,
                    overheads_opened_loc,
                    total_opened_loc,
                    
                    principal_closed_loc,
                    carry_closed_loc,
                    overheads_closed_loc,
                    total_closed_loc,
                    
                    principal_fx_opened_loc,
                    carry_fx_opened_loc,
                    overheads_fx_opened_loc,
                    total_fx_opened_loc,
                    
                    principal_fx_closed_loc,
                    carry_fx_closed_loc,
                    overheads_fx_closed_loc,
                    total_fx_closed_loc,
                    
                    principal_fixed_opened_loc,
                    carry_fixed_opened_loc,
                    overheads_fixed_opened_loc,
                    total_fixed_opened_loc,
                    
                    principal_fixed_closed_loc,
                    carry_fixed_closed_loc,
                    overheads_fixed_closed_loc,
                    total_fixed_closed_loc
                    
                from (
                    select 
                        balance_q.instrument_id,
                        {balance_q_consolidated_select_columns}
                    
                        name,
                        short_name,
                        user_code,
                        
                        pricing_currency_id,
                        instrument_pricing_currency_fx_rate,
                        instrument_accrued_currency_fx_rate,
                        
                        instrument_principal_price,
                        instrument_accrued_price,
                        
                        (-1) as currency_id,
                        
                        item_type,
                        item_type_name,
                        
                        position_size,
                        
                        exposure_calculation_model_id,
                        co_directional_exposure_currency_id,
                        counter_directional_exposure_currency_id,
                        
                        long_underlying_exposure_id,
                        short_underlying_exposure_id,
            
                        has_second_exposure_currency,
                        
                        case
                             when instrument_class_id = 5
                                 then (position_size * (instrument_principal_price - pl_q.principal_cost_price_loc) * price_multiplier * pch_fx_rate) / rep_cur_fx
                             else market_value / rep_cur_fx
                         end as market_value,
            
                        case
                             when instrument_class_id = 5
                                 then (position_size * (instrument_principal_price - pl_q.principal_cost_price_loc) * price_multiplier)
                             else market_value / pch_fx_rate
                        end as market_value_loc,
            
                        (exposure / rep_cur_fx) as exposure,
                        (exposure_2 / rep_cur_fx) as exposure_2,
                        (exposure_delta_adjusted / rep_cur_fx) as exposure_delta_adjusted,
                        
                        exposure_long_underlying_zero,
                        exposure_long_underlying_price,
                        exposure_long_underlying_price_delta,
                        exposure_long_underlying_fx_rate,
                        exposure_long_underlying_fx_rate_delta,
                        
                        exposure_short_underlying_zero,
                        exposure_short_underlying_price,
                        exposure_short_underlying_price_delta,
                        exposure_short_underlying_fx_rate,
                        exposure_short_underlying_fx_rate_delta,
                        
                        (exposure / ec1_fx_rate) as exposure_loc,
                        (exposure_2 / ec2_fx_rate) as exposure_2_loc,
                        
                        /* instrument_long_delta */
                        /* instrument_short_delta */
                        
                        net_cost_price,
                        net_cost_price_loc,
                        
                        gross_cost_price,
                        gross_cost_price_loc,
                        
                        principal_invested,
                        principal_invested_loc,
                        
                        amount_invested,
                        amount_invested_loc,
                        
                        position_return,
                        net_position_return,
                        time_invested,
                        
                        ytm,
                        modified_duration,
                        ytm_at_cost,
                        return_annually,
            
                        principal_opened,
                        carry_opened,
                        overheads_opened,
                        total_opened,
                        
                        principal_closed,
                        carry_closed,
                        overheads_closed,
                        total_closed,
                        
                        principal_fx_opened,
                        carry_fx_opened,
                        overheads_fx_opened,
                        total_fx_opened,
                        
                        principal_fx_closed,
                        carry_fx_closed,
                        overheads_fx_closed,
                        total_fx_closed,
                        
                        principal_fixed_opened,
                        carry_fixed_opened,
                        overheads_fixed_opened,
                        total_fixed_opened,
                        
                        principal_fixed_closed,
                        carry_fixed_closed,
                        overheads_fixed_closed,
                        total_fixed_closed,
                        
                        -- loc
                        
                        principal_opened_loc,
                        carry_opened_loc,
                        overheads_opened_loc,
                        total_opened_loc,
                        
                        principal_closed_loc,
                        carry_closed_loc,
                        overheads_closed_loc,
                        total_closed_loc,
                        
                        principal_fx_opened_loc,
                        carry_fx_opened_loc,
                        overheads_fx_opened_loc,
                        total_fx_opened_loc,
                        
                        principal_fx_closed_loc,
                        carry_fx_closed_loc,
                        overheads_fx_closed_loc,
                        total_fx_closed_loc,
                        
                        principal_fixed_opened_loc,
                        carry_fixed_opened_loc,
                        overheads_fixed_opened_loc,
                        total_fixed_opened_loc,
                        
                        principal_fixed_closed_loc,
                        carry_fixed_closed_loc,
                        overheads_fixed_closed_loc,
                        total_fixed_closed_loc
                        
                    from (
                        select 
                    
                        instrument_id,
                        {consolidated_position_columns}
                        
                        position_size,

                        (1) as item_type,
                        ('Instrument') as item_type_name,
    
                        name,
                        short_name,
                        user_code,
    
                        pricing_currency_id,
                        (pch_fx_rate) as instrument_pricing_currency_fx_rate,
                        (ach_fx_rate) as instrument_accrued_currency_fx_rate,
                        
                        instrument_class_id,
                        co_directional_exposure_currency_id,
                        counter_directional_exposure_currency_id,
                        
                        exposure_calculation_model_id,
                        long_underlying_exposure_id,
                        short_underlying_exposure_id,

                        has_second_exposure_currency,
    
                        case when pricing_currency_id = {report_currency_id}
                               then 1
                           else
                               (rep_cur_fx/pch_fx_rate)
                        end as cross_loc_prc_fx,
    
                        (principal_price) as instrument_principal_price,
                        (accrued_price) as instrument_accrued_price,
                        
                        (long_delta) as instrument_long_delta,
                        (short_delta) as instrument_short_delta,
    
                        (position_size * principal_price * price_multiplier * pch_fx_rate + (position_size * accrued_price * ach_fx_rate * 1 * accrued_multiplier)) as market_value,
                        (position_size * principal_price * price_multiplier * pch_fx_rate + (position_size * accrued_price * ach_fx_rate * 1 * accrued_multiplier)) as exposure,

                        -(position_size * principal_price * price_multiplier * pch_fx_rate + (position_size * accrued_price * ach_fx_rate * 1 * accrued_multiplier)) as exposure_2,
                        
                        /* Position * (Price * Multiplier * Long Delta * Pricing to Exposure FX Rate + Accrued * Multiplier * Accrued to Exposure FX Rate) */
                        (position_size * principal_price * price_multiplier * pch_fx_rate * long_delta + (position_size * accrued_price * ach_fx_rate * 1 * accrued_multiplier)) as exposure_delta_adjusted,
                        
                        (0) as exposure_long_underlying_zero,
                        (underlying_long_multiplier * lui_principal_price * lui_price_multiplier + underlying_long_multiplier * lui_accrued_price * lui_accrued_multiplier) as exposure_long_underlying_price,
                        (underlying_long_multiplier * long_delta * lui_principal_price * lui_price_multiplier + underlying_long_multiplier * lui_accrued_price * lui_accrued_multiplier) as exposure_long_underlying_price_delta,
                        (underlying_long_multiplier * ec1_fx_rate) as exposure_long_underlying_fx_rate,
                        (underlying_long_multiplier * long_delta * ec1_fx_rate) as exposure_long_underlying_fx_rate_delta,
                        
                        /*Market Value Long Underlying Exposure
                        1) "Zero":
                        =0
                        
                        2) "Long Underlying Instrument Price Exposure":
                         Long Underlying Multiplier* [Long Underlying Instrument].[Price] * [Long Underlying Instrument].[Price Multiplier] + Long Underlying Multiplier * [Long Underlying Instrument].[Accrued] * [Long Underlying Instrument].[Accrued Multiplier]

                        
                        3) "Long Underlying Instrument Price Delta-adjusted Exposure":
                        Long Underlying Multiplier * Long Delta * [Long Underlying Instrument].[Price] * [Long Underlying Instrument].[Price Multiplier] + Long Underlying Multiplier * [Long Underlying Instrument].[Accrued] * [Long Underlying Instrument].[Accrued Multiplier]

                        4) "Long Underlying Currency FX Rate Exposure": 
                         Long Underlying Multiplier * [Long Underlying Currency].[FX Rate]
                        
                        5) "Long Underlying Currency FX Rate Delta-adjusted Exposure": 
                        Long Underlying Multiplier * Long Delta * [Long Underlying Currency].[FX Rate]
                        
                        */
                        
                        (0) as exposure_short_underlying_zero,
                        (underlying_short_multiplier * sui_principal_price * sui_price_multiplier + underlying_short_multiplier * sui_accrued_price * sui_accrued_multiplier) as exposure_short_underlying_price,
                        (underlying_short_multiplier * short_delta * sui_principal_price * sui_price_multiplier + underlying_short_multiplier * sui_accrued_price * sui_accrued_multiplier) as exposure_short_underlying_price_delta,
                        (underlying_short_multiplier * ec1_fx_rate) as exposure_short_underlying_fx_rate,
                        (underlying_short_multiplier * short_delta * ec1_fx_rate) as exposure_short_underlying_fx_rate_delta,
                        
                        price_multiplier,
                        pch_fx_rate,
                        rep_cur_fx,
                        ec1_fx_rate,
                        ec2_fx_rate
                        
                    from (
                        select
                            instrument_id,
                            {consolidated_position_columns}
                            
                            position_size,
                            
                            i.name,
                            i.short_name,
                            i.user_code,
                            i.pricing_currency_id,
                            i.price_multiplier,
                            i.accrued_multiplier,
                            
                            i.exposure_calculation_model_id,
                            i.underlying_long_multiplier,
                            i.underlying_short_multiplier,
                            
                            i.co_directional_exposure_currency_id,
                            i.counter_directional_exposure_currency_id,
                            
                            i.long_underlying_exposure_id,
                            i.short_underlying_exposure_id,
                            
                            it.instrument_class_id,

                            it.has_second_exposure_currency,
                            
                            
                            (lui.price_multiplier) as lui_price_multiplier,
                            (lui.accrued_multiplier) as lui_accrued_multiplier,
                            
                            (sui.price_multiplier) as sui_price_multiplier,
                            (sui.accrued_multiplier) as sui_accrued_multiplier,
                            
                            (select 
                                principal_price
                            from instruments_pricehistory
                            where 
                                instrument_id=lui.id and 
                                date = '{report_date}' and
                                pricing_policy_id = {pricing_policy_id})
                            as lui_principal_price,
                            
                            (select 
                                accrued_price
                            from instruments_pricehistory
                            where 
                                instrument_id=lui.id and 
                                date = '{report_date}' and
                                pricing_policy_id = {pricing_policy_id})
                            as lui_accrued_price,
                            
                            (select 
                                principal_price
                            from instruments_pricehistory
                            where 
                                instrument_id=sui.id and 
                                date = '{report_date}' and
                                pricing_policy_id = {pricing_policy_id})
                            as sui_principal_price,
                            
                            (select 
                                accrued_price
                            from instruments_pricehistory
                            where 
                                instrument_id=sui.id and 
                                date = '{report_date}' and
                                pricing_policy_id = {pricing_policy_id})
                            as sui_accrued_price,
                            
                            case when i.co_directional_exposure_currency_id = {report_currency_id}
                                        then 1
                                    else
                                        (select
                                             fx_rate
                                         from currencies_currencyhistory
                                         where
                                                 currency_id = i.co_directional_exposure_currency_id and
                                                 date = '{report_date}' and
                                                 pricing_policy_id = {pricing_policy_id}
                                        )
                                   end as ec1_fx_rate,

                               case when i.counter_directional_exposure_currency_id = {report_currency_id}
                                        then 1
                                    else
                                        (select
                                             fx_rate
                                         from currencies_currencyhistory
                                         where
                                                 currency_id = i.counter_directional_exposure_currency_id and
                                                 date = '{report_date}' and
                                                 pricing_policy_id = {pricing_policy_id}
                                        )
                                end as ec2_fx_rate,
                            
                            case
                                   when {report_currency_id} = {default_currency_id}
                                       then 1
                                   else
                                       (select fx_rate
                                        from currencies_currencyhistory c_ch
                                        where date = '{report_date}'
                                          and c_ch.currency_id = {report_currency_id}
                                          and c_ch.pricing_policy_id = {pricing_policy_id}
                                        limit 1)
                            end as rep_cur_fx,
                            
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
                            
                            case when i.accrued_currency_id = {default_currency_id}
                                then 1
                                else
                                    (select
                                fx_rate
                             from currencies_currencyhistory
                             where
                                currency_id = i.accrued_currency_id and
                                date = '{report_date}' and
                                pricing_policy_id = {pricing_policy_id}
                            )
                            end as ach_fx_rate,
                                
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
                            as accrued_price,
                            
                            (select 
                                long_delta
                            from instruments_pricehistory
                            where 
                                instrument_id=i.id and 
                                date = '{report_date}' and
                                pricing_policy_id = {pricing_policy_id})
                            as long_delta,
                            
                            (select 
                                short_delta
                            from instruments_pricehistory
                            where 
                                instrument_id=i.id and 
                                date = '{report_date}' and
                                pricing_policy_id = {pricing_policy_id})
                            as short_delta
                            
                        from
                            (select
                              {consolidated_position_columns}
                              instrument_id,
                              SUM(position_size_with_sign) as position_size
                            from filtered_transactions 
                            where min_date <= '{report_date}' 
                            and master_user_id = {master_user_id}
                            and transaction_class_id in (1,2)
                            group by
                              {consolidated_position_columns}
                              instrument_id) as t
                        left join instruments_instrument as i
                        ON instrument_id = i.id
                        left join instruments_instrument as lui
                        ON i.long_underlying_instrument_id = lui.id
                        left join instruments_instrument as sui
                        ON i.short_underlying_instrument_id = sui.id
                        left join instruments_instrumenttype as it
                        ON i.instrument_type_id = it.id
                        ) as grouped
                    where position_size != 0
                    ) as balance_q
                    left join 
                        (select 
                                instrument_id, 
                                {consolidated_position_columns}
                                
                                net_cost_price,
                                net_cost_price_loc,
                                principal_cost_price_loc,
                                gross_cost_price,
                                gross_cost_price_loc,
                                
                                principal_invested,
                                principal_invested_loc,  
                                
                                amount_invested,
                                amount_invested_loc,
                                
                                position_return,
                                net_position_return,
                                time_invested,
                                
                                ytm,
                                modified_duration,
                                ytm_at_cost,
                                return_annually,
                    
                                principal_opened,
                                carry_opened,
                                overheads_opened,
                                total_opened,
                                
                                principal_closed,
                                carry_closed,
                                overheads_closed,
                                total_closed,
                                
                                principal_fx_opened,
                                carry_fx_opened,
                                overheads_fx_opened,
                                total_fx_opened,
                                
                                principal_fx_closed,
                                carry_fx_closed,
                                overheads_fx_closed,
                                total_fx_closed,
                                
                                principal_fixed_opened,
                                carry_fixed_opened,
                                overheads_fixed_opened,
                                total_fixed_opened,
                                
                                principal_fixed_closed,
                                carry_fixed_closed,
                                overheads_fixed_closed,
                                total_fixed_closed,
                                
                                -- loc
                                
                                principal_opened_loc,
                                carry_opened_loc,
                                overheads_opened_loc,
                                total_opened_loc,
                                
                                principal_closed_loc,
                                carry_closed_loc,
                                overheads_closed_loc,
                                total_closed_loc,
                                
                                principal_fx_opened_loc,
                                carry_fx_opened_loc,
                                overheads_fx_opened_loc,
                                total_fx_opened_loc,
                                
                                principal_fx_closed_loc,
                                carry_fx_closed_loc,
                                overheads_fx_closed_loc,
                                total_fx_closed_loc,
                                
                                principal_fixed_opened_loc,
                                carry_fixed_opened_loc,
                                overheads_fixed_opened_loc,
                                total_fixed_opened_loc,
                                
                                principal_fixed_closed_loc,
                                carry_fixed_closed_loc,
                                overheads_fixed_closed_loc,
                                total_fixed_closed_loc
                                
                              from ({pl_query}) as pl 
                    ) as pl_q
                    on balance_q.instrument_id = pl_q.instrument_id {pl_left_join_consolidation}
                
                ) as joined_positions
            """

            consolidated_cash_columns = get_cash_consolidation_for_select(self.instance)
            consolidated_position_columns = get_position_consolidation_for_select(self.instance)
            consolidated_cash_as_position_columns = get_cash_as_position_consolidation_for_select(self.instance)

            _l.debug('consolidated_cash_columns %s' % consolidated_cash_columns)
            _l.debug('consolidated_position_columns %s' % consolidated_position_columns)
            _l.debug('consolidated_cash_as_position_columns %s' % consolidated_cash_as_position_columns)

            query = query.format(report_date=self.instance.report_date,
                                 master_user_id=self.instance.master_user.id,
                                 default_currency_id=self.instance.master_user.system_currency_id,
                                 report_currency_id=self.instance.report_currency.id,
                                 pricing_policy_id=self.instance.pricing_policy.id,

                                 consolidated_cash_columns=consolidated_cash_columns,
                                 consolidated_position_columns=consolidated_position_columns,
                                 consolidated_cash_as_position_columns=consolidated_cash_as_position_columns,

                                 balance_q_consolidated_select_columns=balance_q_consolidated_select_columns,
                                 transaction_filter_sql_string=transaction_filter_sql_string,

                                 pl_query=pl_query,
                                 pl_left_join_consolidation=pl_left_join_consolidation,
                                 fx_trades_and_fx_variations_filter_sql_string= fx_trades_and_fx_variations_filter_sql_string
                                 )


            if settings.SERVER_TYPE == 'local':
                with open('/tmp/query_raw.txt', 'w') as the_file:
                    the_file.write(query)

            cursor.execute(query)

            _l.debug('Balance report query execute done: %s', "{:3.3f}".format(time.perf_counter() - st))

            query_str = str(cursor.query, 'utf-8')

            if settings.SERVER_TYPE == 'local':
                with open('/tmp/query_result.txt', 'w') as the_file:
                    the_file.write(query_str)


            result = dictfetchall(cursor)

            ITEM_TYPE_INSTRUMENT = 1
            ITEM_TYPE_FX_VARIATIONS = 3
            ITEM_TYPE_FX_TRADES = 4
            ITEM_TYPE_TRANSACTION_PL = 5
            ITEM_TYPE_MISMATCH = 6
            ITEM_TYPE_EXPOSURE_COPY = 7

            updated_result = []

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

                item["exposure_currency_id"] = item["co_directional_exposure_currency_id"]

                item['position_size'] = round(item['position_size'], settings.ROUND_NDIGITS)

                # Position * ( Long Underlying Exposure - Short Underlying Exposure)
                # "Underlying Long/Short Exposure - Split":
                # Position * Long Underlying Exposure
                # -Position * Short Underlying Exposure

                long = 0
                short = 0

                if item["long_underlying_exposure_id"] == LongUnderlyingExposure.ZERO:
                    long = item["exposure_long_underlying_zero"]
                if item["long_underlying_exposure_id"] == LongUnderlyingExposure.LONG_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE:
                    long = item["exposure_short_underlying_price"]
                if item["long_underlying_exposure_id"] == LongUnderlyingExposure.LONG_UNDERLYING_INSTRUMENT_PRICE_DELTA:
                    long = item["exposure_long_underlying_price_delta"]
                if item["long_underlying_exposure_id"] == LongUnderlyingExposure.LONG_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE:
                    long = item["exposure_long_underlying_fx_rate"]
                if item["long_underlying_exposure_id"] == LongUnderlyingExposure.LONG_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE:
                    long = item["exposure_long_underlying_fx_rate_delta"]

                if item["short_underlying_exposure_id"] == ShortUnderlyingExposure.ZERO:
                    short = item["exposure_short_underlying_zero"]
                if item["short_underlying_exposure_id"] == ShortUnderlyingExposure.SHORT_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE:
                    short = item["exposure_short_underlying_price"]
                if item["short_underlying_exposure_id"] == ShortUnderlyingExposure.SHORT_UNDERLYING_INSTRUMENT_PRICE_DELTA:
                    short = item["exposure_short_underlying_price_delta"]
                if item["short_underlying_exposure_id"] == ShortUnderlyingExposure.SHORT_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE:
                    short = item["exposure_short_underlying_fx_rate"]
                if item["short_underlying_exposure_id"] == ShortUnderlyingExposure.SHORT_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE:
                    short = item["exposure_short_underlying_fx_rate_delta"]

                if item["exposure_calculation_model_id"] == ExposureCalculationModel.UNDERLYING_LONG_SHORT_EXPOSURE_NET:
                    item["exposure"] = item["position_size"] * (long - short)

                # (i )   Position * Long Underlying Exposure
                # (ii)  -Position * Short Underlying Exposure

                if item["exposure_calculation_model_id"] == ExposureCalculationModel.UNDERLYING_LONG_SHORT_EXPOSURE_SPLIT:
                    item["exposure"] = item["position_size"] * long



                if item['position_size']:

                    updated_result.append(item)

                    if ITEM_TYPE_INSTRUMENT == 1:

                        if item['has_second_exposure_currency'] and self.instance.show_balance_exposure_details:

                            new_exposure_item = {
                                "name": item["name"],
                                "user_code": item["user_code"],
                                "short_name": item["short_name"],
                                "pricing_currency_id": item["pricing_currency_id"],
                                "currency_id": item["currency_id"],
                                "instrument_id": item["instrument_id"],
                                "portfolio_id": item["portfolio_id"],


                                "account_cash_id": item["account_cash_id"],
                                "strategy1_cash_id": item["strategy1_cash_id"],
                                "strategy2_cash_id": item["strategy2_cash_id"],
                                "strategy3_cash_id": item["strategy3_cash_id"],

                                "account_position_id": item["account_position_id"],
                                "strategy1_position_id": item["strategy1_position_id"],
                                "strategy2_position_id": item["strategy2_position_id"],
                                "strategy3_position_id": item["strategy3_position_id"],

                                "instrument_pricing_currency_fx_rate": None,
                                "instrument_accrued_currency_fx_rate": None,
                                "instrument_principal_price": None,
                                "instrument_accrued_price": None,

                                "market_value": None,
                                "market_value_loc": None,

                                "item_type": 7,
                                "item_type_name": "Exposure",
                                "exposure": item["exposure_2"],
                                "exposure_loc": item["exposure_2_loc"],
                                "exposure_currency_id": item["counter_directional_exposure_currency_id"]
                            }

                            if item["exposure_calculation_model_id"] == ExposureCalculationModel.UNDERLYING_LONG_SHORT_EXPOSURE_SPLIT:
                                new_exposure_item["exposure"] = -item["position_size"] * short

                            new_exposure_item["position_size"] = None
                            new_exposure_item["ytm"] = None
                            new_exposure_item["ytm_at_cost"] = None
                            new_exposure_item["modified_duration"] = None
                            new_exposure_item["return_annually"] = None

                            new_exposure_item["position_return"] = None
                            new_exposure_item["net_position_return"] = None

                            new_exposure_item["net_cost_price"] = None
                            new_exposure_item["net_cost_price_loc"] = None
                            new_exposure_item["gross_cost_price"] = None
                            new_exposure_item["gross_cost_price_loc"] = None

                            new_exposure_item["principal_invested"] = None
                            new_exposure_item["principal_invested_loc"] = None

                            new_exposure_item["amount_invested"] = None
                            new_exposure_item["amount_invested_loc"] = None

                            new_exposure_item["time_invested"] = None
                            new_exposure_item["return_annually"] = None

                            # performance

                            new_exposure_item["principal_opened"] = None
                            new_exposure_item["carry_opened"] = None
                            new_exposure_item["overheads_opened"] = None
                            new_exposure_item["total_opened"] = None

                            new_exposure_item["principal_fx_opened"] = None
                            new_exposure_item["carry_fx_opened"] = None
                            new_exposure_item["overheads_fx_opened"] = None
                            new_exposure_item["total_fx_opened"] = None

                            new_exposure_item["principal_fixed_opened"] = None
                            new_exposure_item["carry_fixed_opened"] = None
                            new_exposure_item["overheads_fixed_opened"] = None
                            new_exposure_item["total_fixed_opened"] = None

                            # loc started

                            new_exposure_item["principal_opened_loc"] = None
                            new_exposure_item["carry_opened_loc"] = None
                            new_exposure_item["overheads_opened_loc"] = None
                            new_exposure_item["total_opened_loc"] = None

                            new_exposure_item["principal_fx_opened_loc"] = None
                            new_exposure_item["carry_fx_opened_loc"] = None
                            new_exposure_item["overheads_fx_opened_loc"] = None
                            new_exposure_item["total_fx_opened_loc"] = None

                            new_exposure_item["principal_fixed_opened_loc"] = None
                            new_exposure_item["carry_fixed_opened_loc"] = None
                            new_exposure_item["overheads_fixed_opened_loc"] = None
                            new_exposure_item["total_fixed_opened_loc"] = None

                            new_exposure_item["principal_closed"] = None
                            new_exposure_item["carry_closed"] = None
                            new_exposure_item["overheads_closed"] = None
                            new_exposure_item["total_closed"] = None

                            new_exposure_item["principal_fx_closed"] = None
                            new_exposure_item["carry_fx_closed"] = None
                            new_exposure_item["overheads_fx_closed"] = None
                            new_exposure_item["total_fx_closed"] = None

                            new_exposure_item["principal_fixed_closed"] = None
                            new_exposure_item["carry_fixed_closed"] = None
                            new_exposure_item["overheads_fixed_closed"] = None
                            new_exposure_item["total_fixed_closed"] = None

                            # loc started

                            new_exposure_item["principal_closed_loc"] = None
                            new_exposure_item["carry_closed_loc"] = None
                            new_exposure_item["overheads_closed_loc"] = None
                            new_exposure_item["total_closed_loc"] = None

                            new_exposure_item["principal_fx_closed_loc"] = None
                            new_exposure_item["carry_fx_closed_loc"] = None
                            new_exposure_item["overheads_fx_closed_loc"] = None
                            new_exposure_item["total_fx_closed_loc"] = None

                            new_exposure_item["principal_fixed_closed_loc"] = None
                            new_exposure_item["carry_fixed_closed_loc"] = None
                            new_exposure_item["overheads_fixed_closed_loc"] = None
                            new_exposure_item["total_fixed_closed_loc"] = None

                            updated_result.append(new_exposure_item)

            _l.debug('build cash result %s ' % len(result))

            self.instance.items = updated_result

    def add_data_items_instruments(self, ids):

        self.instance.item_instruments = Instrument.objects.prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).filter(master_user=self.instance.master_user) \
            .filter(id__in=ids)

    def add_data_items_instrument_types(self, instruments):

        ids = []

        for instrument in instruments:
            ids.append(instrument.instrument_type_id)

        print('add_data_items_instrument_types %s' % ids)

        self.instance.item_instrument_types = InstrumentType.objects.prefetch_related(
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

        self.instance.item_accounts = Account.objects.prefetch_related(
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
            if 'exposure_currency_id' in item:
                currencies_ids.append(item['exposure_currency_id'])

        self.add_data_items_instruments(instrument_ids)
        self.add_data_items_portfolios(portfolio_ids)
        self.add_data_items_accounts(account_ids)
        self.add_data_items_currencies(currencies_ids)

        self.add_data_items_instrument_types(self.instance.item_instruments)

        self.instance.custom_fields = BalanceReportCustomField.objects.filter(master_user=self.instance.master_user)

        _l.debug('_refresh_with_perms_optimized item relations done: %s', "{:3.3f}".format(time.perf_counter() - item_relations_st))
