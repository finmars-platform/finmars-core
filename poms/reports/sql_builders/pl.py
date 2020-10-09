import logging
import time

from django.db import connection

from poms.accounts.models import Account
from poms.currencies.models import Currency, CurrencyHistory
from poms.instruments.models import Instrument, CostMethod
from poms.portfolios.models import Portfolio
from poms.reports.builders.balance_item import Report
from poms.reports.builders.base_builder import BaseReportBuilder
from poms.reports.models import BalanceReportCustomField
from poms.users.models import EcosystemDefault

from django.conf import settings

_l = logging.getLogger('poms.reports')


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


class PLReportBuilderSql:

    def __init__(self, instance=None):

        _l.debug('ReportBuilderSql init')

        self.instance = instance

        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self.instance.master_user)

        _l.info('self.instance master_user %s' % self.instance.master_user)
        _l.info('self.instance report_date %s' % self.instance.report_date)

    def build_balance(self):
        st = time.perf_counter()

        self.instance.items = []

        if self.instance.cost_method.id == CostMethod.FIFO:
            self.build_positions_fifo()

        if self.instance.cost_method.id == CostMethod.AVCO:
            self.build_positions_avco()

        # self.build_cash()

        _l.info('items total %s' % len(self.instance.items))

        _l.info('build_st done: %s', "{:3.3f}".format(time.perf_counter() - st))

        self.add_data_items()

        return self.instance

    def get_position_consolidation_for_select(self, prefix=''):

        result = []

        if self.instance.portfolio_mode == Report.MODE_INDEPENDENT:
            result.append(prefix + "portfolio_id")

        if self.instance.account_mode == Report.MODE_INDEPENDENT:
            result.append(prefix + "account_position_id")

        if self.instance.strategy1_mode == Report.MODE_INDEPENDENT:
            result.append(prefix + "strategy1_position_id")

        if self.instance.strategy2_mode == Report.MODE_INDEPENDENT:
            result.append(prefix + "strategy2_position_id")

        if self.instance.strategy3_mode == Report.MODE_INDEPENDENT:
            result.append(prefix + "strategy3_position_id")

        resultString = ''

        if len(result):
            resultString = ", ".join(result) + ', '

        return resultString

    def get_final_consolidation_columns(self):

        result = []

        #(q2.instrument_id) as instrument_id,

        if self.instance.portfolio_mode == Report.MODE_INDEPENDENT:
            result.append("(q2.portfolio_id) as portfolio_id")

        if self.instance.account_mode == Report.MODE_INDEPENDENT:
            result.append("(q2.account_position_id) as account_position_id")

        if self.instance.strategy1_mode == Report.MODE_INDEPENDENT:
            result.append("(q2.strategy1_position_id) as strategy1_position_id")

        if self.instance.strategy2_mode == Report.MODE_INDEPENDENT:
            result.append("(q2.strategy2_position_id) as strategy2_position_id")

        if self.instance.strategy3_mode == Report.MODE_INDEPENDENT:
            result.append("(q2.strategy3_position_id) as strategy3_position_id")

        resultString = ''

        if len(result):
            resultString = ", ".join(result) + ', '

        return resultString


    def get_where_expression_for_position_consolidation(self, prefix, prefix_second):

        result = []

        if self.instance.portfolio_mode == Report.MODE_INDEPENDENT:
            result.append(prefix + "portfolio_id = " + prefix_second + "portfolio_id")

        if self.instance.account_mode == Report.MODE_INDEPENDENT:
            result.append(prefix + "account_position_id = " + prefix_second + "account_position_id")

        if self.instance.strategy1_mode == Report.MODE_INDEPENDENT:
            result.append(prefix + "strategy1_position_id = " + prefix_second + "strategy1_position_id")

        if self.instance.strategy2_mode == Report.MODE_INDEPENDENT:
            result.append(prefix + "strategy2_position_id = " + prefix_second + "strategy2_position_id")

        if self.instance.strategy3_mode == Report.MODE_INDEPENDENT:
            result.append(prefix + "strategy3_position_id = " + prefix_second + "strategy3_position_id")

        resultString = ''

        if len(result):
            resultString = " and ".join(result) + ' and '

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

    def get_fx_trades_and_fx_variations_transaction_filter_sql_string(self):

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
            result_string = result_string + ' and '
            result_string = result_string + ' and '.join(filter_sql_list)

        _l.info('get_transaction_filter_sql_string %s' % result_string)

        return result_string

    def get_source_query(self):

        # language=PostgreSQL
        query = """
        with 
            pl_transactions_with_ttype_filtered as (
                select * from pl_transactions_with_ttype
                {transaction_filter_sql_string}
            ),
        
            transactions_ordered as (
                select 
                   row_number() 
                   over (partition by {tt_consolidation_columns} tt.instrument_id order by ttype,tt.accounting_date) as rn,
                   row_number()
                   over (partition by  tt.instrument_id order by tt.accounting_date) as rn_total,
                   tt.accounting_date,
                   tt.ttype,
                   tt.transaction_class_id,
                   tt.position_size_with_sign,
                   tt.principal_with_sign,
                   tt.carry_with_sign,
                   tt.overheads_with_sign,
                   {tt_consolidation_columns}
                   tt.instrument_id,
                   tt.transaction_currency_id,
                   tt.settlement_currency_id,
                   
                   tt.reference_fx_rate,
                   
                   buy_tr.buy_positions_total_size,
                   sell_tr.sell_positions_total_size
                                       
                from (select 
                         accounting_date,
                         transaction_class_id,
                         position_size_with_sign,
                         principal_with_sign,
                         carry_with_sign,
                         overheads_with_sign,
                         {consolidation_columns}
                         instrument_id,
                         
                         transaction_currency_id,
                         settlement_currency_id,
                         
                         reference_fx_rate,
                         
                         ttype
                         from pl_transactions_with_ttype_filtered 
                         where 
                            master_user_id='{master_user_id}'::int and 
                            accounting_date <= '{report_date}') as tt
                             left join
                           (select 
                                    instrument_id, 
                                    {consolidation_columns} 
                                    coalesce(abs(sum(position_size_with_sign)), 0) as sell_positions_total_size
                            from pl_transactions_with_ttype_filtered 
                            where 
                                master_user_id = '{master_user_id}' and 
                                accounting_date <= '{report_date}' and 
                                position_size_with_sign < 0
                            group by 
                                {consolidation_columns} 
                                instrument_id) as sell_tr 
                            using ({consolidation_columns} instrument_id)
                             left join
                           (select 
                                instrument_id, 
                                {consolidation_columns} 
                                coalesce(abs(sum(position_size_with_sign)), 0) as buy_positions_total_size
                            from pl_transactions_with_ttype_filtered 
                            where 
                                master_user_id= '{master_user_id}' and 
                                accounting_date <= '{report_date}' and 
                                position_size_with_sign > 0
                            group by 
                                {consolidation_columns} 
                                instrument_id) as buy_tr 
                            using ({consolidation_columns} instrument_id)
                     ),
        
            transactions_with_multipliers as (
               select 
                   rn,
                   rn_total,
                   accounting_date,
                   transaction_class_id,
                   
                   {consolidation_columns}
                   instrument_id,
                   position_size_with_sign,
                   principal_with_sign,
                   carry_with_sign,
                   overheads_with_sign,
                   
                   
                   rolling_position_size,
                   sell_positions_total_size,
                   buy_positions_total_size,
                   min_closed,
                   
                   transaction_currency_id,
                   settlement_currency_id,
                   
                   reference_fx_rate,
                   
                   ('{report_date}'::date - accounting_date::date) as day_delta,
                   
                   case
                     when abs(rolling_position_size) <= min_closed
                       then 1
                     else
                       case
                         when abs((min_closed - abs(rolling_position_size))) < abs(position_size_with_sign)
                           then 1 - abs((min_closed - abs(rolling_position_size)) / position_size_with_sign)
                         else
                           0
                         end
                     end as multiplier
            
               from (
                    select 
                        rn,
                        rn_total,
                        ttype,
                        accounting_date,
                        transaction_class_id,
                        position_size_with_sign,
                        principal_with_sign,
                        carry_with_sign,
                        overheads_with_sign,
                         
                        {consolidation_columns}
                        instrument_id,
                        transaction_currency_id,
                        settlement_currency_id,
                         
                        reference_fx_rate,
                         
                         sum(position_size_with_sign)
                             over (partition by instrument_id, {consolidation_columns} ttype order by rn) as rolling_position_size,
                         coalesce(sell_positions_total_size, 0) as sell_positions_total_size,
                         coalesce(buy_positions_total_size, 0) as buy_positions_total_size,
                         case
                           when coalesce(sell_positions_total_size, 0) < coalesce(buy_positions_total_size, 0)
                             then coalesce(sell_positions_total_size, 0)
                           else
                             coalesce(buy_positions_total_size, 0)
                           end
                        as min_closed
                      from transactions_ordered where transaction_class_id in (1,2)
                    ) as tt_fin
          ),
    
            transactions_all_with_multipliers as ( 
                (
                    (select 
                    
                        rn,
                        rn_total,
                        accounting_date,
                        transaction_class_id,
                        
                        {consolidation_columns}
                        instrument_id,
                        position_size_with_sign,

                        principal_with_sign,
                        carry_with_sign,
                        overheads_with_sign,
                        
                        rolling_position_size,
                        sell_positions_total_size,
                        buy_positions_total_size,
                        
                        transaction_currency_id,
                        settlement_currency_id,
                        
                        reference_fx_rate,
                        
        
                        case 
                            when coalesce(opened_positions,0)=0
                                then 1
                                else 1-coalesce(rolling_position_size,0)/opened_positions
                        end as multiplier
                        
                    from (
                        select 
                        
                             *,
                             (
                                 select sum(tt_w_m.position_size_with_sign*(1-tt_w_m.multiplier))
                                 from transactions_with_multipliers tt_w_m
                                 where tt_w_m.rn_total < t_o.rn_total
                                   --- aggregation
            
                                   and 
                                   {transactions_all_with_multipliers_where_expression}
                                   tt_w_m.instrument_id = t_o.instrument_id
                                  -- and tt_w_m.portfolio_id = t_o.portfolio_id
                                  -- and tt_w_m.account_position_id = t_o.account_position_id
                             ) as rolling_position_size,
        
                             ( 
                                select sum(tt_w_m.position_size_with_sign) as open_position_pl
                                from transactions_with_multipliers tt_w_m
                                where
                                   --- aggregation
                                   {transactions_all_with_multipliers_where_expression}
                                   tt_w_m.instrument_id = t_o.instrument_id
                                 --  and tt_w_m.portfolio_id = t_o.portfolio_id
                                 --  and tt_w_m.account_position_id = t_o.account_position_id
                             ) as opened_positions
                        from transactions_ordered t_o
                        where 
                            t_o.transaction_class_id in (4)
                    ) as pl_pre_calc)
        
                    union all
        
                      (select 
                        
                       rn,
                       rn_total,
                       accounting_date,
                       transaction_class_id,
                       
                       {consolidation_columns}
                       instrument_id,
                       position_size_with_sign,
        
                       principal_with_sign,
                       carry_with_sign,
                       overheads_with_sign,
    
                       rolling_position_size,
                       sell_positions_total_size,
                       buy_positions_total_size,
                       
                       transaction_currency_id,
                       settlement_currency_id,
                       
                       reference_fx_rate,
                       
                       multiplier
                        
                        
                       from transactions_with_multipliers)
        
                  )
            ),
    
            transactions_unioned_table as (
                
                select 
                
                   rn,
                   accounting_date,
                   transaction_class_id,
                   
                   {consolidation_columns}
                   instrument_id,
                   position_size_with_sign,
                   
                   
                   rolling_position_size,
                   sell_positions_total_size,
                   buy_positions_total_size,
                   
                   transaction_currency_id,
                   settlement_currency_id,
                   
                   reference_fx_rate,
                   
                   case
                       when
                           transaction_currency_id = {default_currency_id}
                           then 1
                       else
                           (select fx_rate
                            from currencies_currencyhistory c_ch
                            where c_ch.date = accounting_date and
                               c_ch.currency_id = transaction_currency_id and
                               c_ch.pricing_policy_id = {pricing_policy_id}
                            limit 1)
                   end as trn_hist_fx,

                   case
                       when /* reporting ccy = system ccy*/ {report_currency_id} = {default_currency_id}
                           then 1
                       else
                           (select fx_rate
                            from currencies_currencyhistory c_ch
                            where c_ch.date = accounting_date and 
                                c_ch.currency_id = {report_currency_id} and
                                c_ch.pricing_policy_id = {pricing_policy_id}
                            limit 1)
                  end as rep_hist_fx,
                   
                   ('{report_date}'::date - accounting_date::date) as day_delta,
                
                   (principal_with_sign * reference_fx_rate) as principal_with_sign_invested,
                   (carry_with_sign * reference_fx_rate) as carry_with_sign_invested,
                   (overheads_with_sign * reference_fx_rate) as overheads_with_sign_invested,
                   
                   (principal_with_sign) as principal_with_sign,
                   (carry_with_sign) as carry_with_sign,
                   (overheads_with_sign) as overheads_with_sign,
                   
                   multiplier
                
                from transactions_all_with_multipliers
            
            )
    
        --- main query
        select 
        
            name,
            short_name,
            user_code,
            
            item_type,
            item_type_name,
      
            instrument_id,
            {consolidation_columns}
          
            position_size,
            
            position_return,
            net_position_return,
            
            net_cost_price,
            net_cost_price_loc,
                
            time_invested,

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
            name,
            short_name,
            user_code,
            
            item_type,
            item_type_name,
      
            instrument_id,
            {consolidation_columns}
          
            position_size,
            
            position_return,
            net_position_return,
            
            net_cost_price,
            net_cost_price_loc,
                
            time_invested,

            principal_opened,
            carry_opened,
            overheads_opened,
            total_opened,
            
            principal_closed,
            carry_closed,
            overheads_closed,
            total_closed,
            
            (principal_opened - principal_fixed_opened) as principal_fx_opened,
            (carry_opened - carry_fixed_opened) as carry_fx_opened,
            (overheads_opened - overheads_fixed_opened) as overheads_fx_opened,
            (total_opened - total_fixed_opened) as total_fx_opened,
            
            (principal_closed - principal_fixed_closed) as principal_fx_closed,
            (carry_closed - carry_fixed_closed) as carry_fx_closed,
            (overheads_closed - overheads_fixed_closed) as overheads_fx_closed,
            (total_closed - total_fixed_closed) as total_fx_closed,
            
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
            
            (principal_opened_loc - principal_fixed_opened_loc) as principal_fx_opened_loc,
            (carry_opened_loc - carry_fixed_opened_loc) as carry_fx_opened_loc,
            (overheads_opened_loc - overheads_fixed_opened_loc) as overheads_fx_opened_loc,
            (total_opened_loc - total_fixed_opened_loc) as total_fx_opened_loc,
            
            (principal_closed_loc - principal_fixed_closed_loc) as principal_fx_closed_loc,
            (carry_closed_loc - carry_fixed_closed_loc) as carry_fx_closed_loc,
            (overheads_closed_loc - overheads_fixed_closed_loc) as overheads_fx_closed_loc,
            (total_closed_loc - total_fixed_closed_loc) as total_fx_closed_loc,
            
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
                    name,
                    short_name,
                    user_code,
                    
                    (1) as item_type,
                    ('Instrument') as item_type_name,
              
                    instrument_id,
                    {consolidation_columns}

                    position_size,
                    
                    position_return,
                    net_position_return,
                    
                    net_cost_price,
                    net_cost_price_loc,
                        
                    time_invested,
                    
                    principal_opened,
                    carry_opened,
                    overheads_opened,
                    (principal_opened + carry_opened + overheads_opened) as total_opened,
                    
                    principal_closed,
                    carry_closed,
                    overheads_closed,
                    (principal_closed + carry_closed + overheads_closed) as total_closed,
                    
                    (0) as principal_fx_opened,
                    (0) as carry_fx_opened,
                    (0) as overheads_fx_opened,
                    (0) as total_fx_opened,
                    
                    (principal_closed - principal_fixed_closed)     as principal_fx_closed,
                    (carry_closed - carry_fixed_closed)             as carry_fx_closed,
                    (overheads_closed - overheads_fixed_closed)     as overheads_fx_closed,
                    (0)                                             as total_fx_closed, -- TODO calculate column
                    
                    principal_fixed_opened,
                    carry_fixed_opened,
                    overheads_fixed_opened,
                    (principal_fixed_opened + carry_fixed_opened + overheads_fixed_opened) as total_fixed_opened,
                    
                    principal_fixed_closed,
                    carry_fixed_closed,
                    overheads_fixed_closed,
                    (principal_fixed_closed + carry_fixed_closed + overheads_fixed_closed) as total_fixed_closed,
                    
                    -- loc

                    principal_opened_loc,
                    carry_opened_loc,
                    overheads_opened_loc,
                    (principal_opened_loc + carry_opened_loc + overheads_opened_loc)         as total_opened_loc,
                    
                    principal_closed_loc,
                    carry_closed_loc,
                    overheads_closed_loc,
                    (principal_closed_loc + carry_closed_loc + overheads_closed_loc)         as total_closed_loc,
                    
                    
                    -- calculated at level 1
                    (0) as principal_fx_opened_loc,
                    (0) as carry_fx_opened_loc,
                    (0) as overheads_fx_opened_loc,
                    (0) as total_fx_opened_loc,
                    
                    (0) as principal_fx_closed_loc,
                    (0) as carry_fx_closed_loc,
                    (0) as overheads_fx_closed_loc,
                    (0) as total_fx_closed_loc,
                    
                    principal_fixed_opened_loc,
                    carry_fixed_opened_loc,
                    overheads_fixed_opened_loc,
                    (principal_fixed_opened_loc + carry_fixed_opened_loc + overheads_fixed_opened_loc) as total_fixed_opened_loc,
                    
                    principal_fixed_closed_loc,
                    carry_fixed_closed_loc,
                    overheads_fixed_closed_loc,
                    (principal_fixed_closed_loc + carry_fixed_closed_loc + overheads_fixed_closed_loc) as total_fixed_closed_loc
                
                from (
                    select 
                    
                        instrument_id,
                        {consolidation_columns}
                        
                        name,
                        short_name,
                        user_code,
                        pricing_currency_id,
                        price_multiplier,
                        accrued_multiplier,
                        accrual_size,
                        cur_price,
                        cur_accr_price,
                        prc_cur_fx,
                        accr_cur_fx,
                        rep_cur_fx,
                        mv_principal,
                        mv_carry,
                        cross_loc_prc_fx,
                        
                        position_size,
                        position_size_opened,
                        
                        net_cost_price,
                        net_cost_price_loc,
                        
                        time_invested,
    
    
                        principal_closed,
                        carry_closed,
                        overheads_closed,
    
    
                        (mv_principal+principal_opened) as principal_opened,
                        (mv_carry+carry_opened)         as carry_opened,
                        overheads_opened,
    
    
                        (mv_principal + principal_fixed_opened) as principal_fixed_opened,
                        (mv_carry + carry_fixed_opened)         as carry_fixed_opened,
                        overheads_fixed_opened,
                        
                        principal_fixed_closed,
                        carry_fixed_closed,
                        overheads_fixed_closed,
                    
                        -- LOC
    
    
                        principal_closed*cross_loc_prc_fx as principal_closed_loc,
                        carry_closed*cross_loc_prc_fx as carry_closed_loc,
                        overheads_closed*cross_loc_prc_fx as overheads_closed_loc,
    
    
                        (mv_principal+principal_opened)*cross_loc_prc_fx as principal_opened_loc,
                        (mv_carry+carry_opened)*cross_loc_prc_fx as carry_opened_loc,
                        overheads_opened*cross_loc_prc_fx as overheads_opened_loc,
                        
                        (mv_principal + principal_fixed_opened) * cross_loc_prc_fx as principal_fixed_opened_loc,
                        (mv_carry + carry_fixed_opened) * cross_loc_prc_fx as carry_fixed_opened_loc,
                        overheads_fixed_opened * cross_loc_prc_fx as overheads_fixed_opened_loc,
    
                        principal_fixed_closed * cross_loc_prc_fx as principal_fixed_closed_loc,
                        carry_fixed_closed * cross_loc_prc_fx as carry_fixed_closed_loc,
                        overheads_fixed_closed * cross_loc_prc_fx as overheads_fixed_closed_loc,
    
                        case
                            when principal_fixed_opened != 0
                            then (((mv_principal+principal_opened) + (mv_carry+carry_opened)) / -principal_fixed_opened)
                            else 0
                        end as position_return,
                        
                        case
                            when principal_fixed_opened != 0
                            then (((mv_principal+principal_opened) + (mv_carry+carry_opened) + overheads_opened) / -principal_fixed_opened)
                            else 0
                        end as net_position_return,
        
                        mv_carry+mv_principal as mv
            
                from (
                    select 
                        instrument_id,
                         {consolidation_columns}
                
                        i.name,
                        i.short_name,
                        i.user_code,
                        i.pricing_currency_id,
                        i.price_multiplier,
                        i.accrued_multiplier,
                        i.accrual_size,
                        i.cur_price,
                        i.cur_accr_price,
                        i.prc_cur_fx,
                        i.accr_cur_fx,
                        rep_cur_fx,
                        (rep_cur_fx/i.prc_cur_fx) cross_loc_prc_fx,
    
                        position_size,
                        position_size_opened,
                        
                        principal_opened,
                        carry_opened,
                        overheads_opened,
                        
                        principal_closed,
                        carry_closed,
                        overheads_closed,
    
                        principal_fixed_opened,
                        carry_fixed_opened,
                        overheads_fixed_opened,
    
                        principal_fixed_closed,
                        carry_fixed_closed,
                        overheads_fixed_closed,
    
    
                        -- вроде, не используется
                        case
                            when position_size_opened > 0
                            then -((principal_opened + overheads_opened) / position_size_opened / i.price_multiplier)
                            else 0
                        end as net_cost_price,
                        -- испольщуется только эта
                        case
                            when position_size_opened > 0
                            then -((principal_opened + overheads_opened) / position_size_opened * rep_cur_fx / i.prc_cur_fx / i.price_multiplier)
                            else 0
                        end as net_cost_price_loc,
                
                        case
                            when position_size_opened > 0
                            then time_invested_sum / position_size_opened / 365
                            else 0
                        end as time_invested,
                    
                        -- mv precalc
                        (position_size_opened * coalesce(i.cur_price, 0) * i.price_multiplier * i.prc_cur_fx / rep_cur_fx) as mv_principal,
                        (position_size_opened * coalesce(i.cur_accr_price, 0) * i.accrued_multiplier * i.accr_cur_fx  / rep_cur_fx) as mv_carry,
    
                        (i.accrual_size * i.accrued_multiplier  / (i.cur_price * i.price_multiplier) ) as ytm
                
                    from (
                        select 
                        
                            instrument_id,
                            {consolidation_columns}
                            
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
            
                            SUM(position_size)                                                      as position_size,
                            SUM(position_size_opened)                                               as position_size_opened,
                            
                            SUM(principal_closed * stl_cur_fx / rep_cur_fx)                         as principal_closed,
                            SUM(carry_closed * stl_cur_fx / rep_cur_fx)                             as carry_closed,
                            SUM(overheads_closed * stl_cur_fx / rep_cur_fx)                         as overheads_closed,
                               
                            SUM(principal_opened * stl_cur_fx / rep_cur_fx)                as principal_opened,
                            SUM(carry_opened * stl_cur_fx / rep_cur_fx)                    as carry_opened,
                            SUM(overheads_opened * stl_cur_fx / rep_cur_fx)                as overheads_opened,
                            
                            SUM(time_invested)                                                      as time_invested_sum,
                            
                            SUM(principal_with_sign_invested * stlch.fx_rate * trnch.fx_rate )      as principal_with_sign_invested,
                            SUM(carry_with_sign_invested * stlch.fx_rate * trnch.fx_rate )          as carry_with_sign_invested,
                            SUM(overheads_with_sign_invested * stlch.fx_rate * trnch.fx_rate )      as overheads_with_sign_invested,
                            
                            SUM(principal_fixed_opened)                                             as principal_fixed_opened,
                            SUM(carry_fixed_opened)                                                 as carry_fixed_opened,
                            SUM(overheads_fixed_opened)                                             as overheads_fixed_opened,
                            
                            SUM(principal_fixed_closed)                                             as principal_fixed_closed,
                            SUM(carry_fixed_closed)                                                 as carry_fixed_closed,
                            SUM(overheads_fixed_closed)                                             as overheads_fixed_closed
    
                        from (
                            select 
                            
                                instrument_id,
                                {consolidation_columns}
                                
                                transaction_currency_id,
                                settlement_currency_id,
                                
                                case
                                   when
                                       tut.settlement_currency_id = {default_currency_id}
                                       then 1
                                   else
                                       (select fx_rate
                                        from currencies_currencyhistory c_ch
                                        where date = '{report_date}'
                                          and c_ch.currency_id = tut.settlement_currency_id
                                          and c_ch.pricing_policy_id = {pricing_policy_id}
                                        limit 1)
                                end as stl_cur_fx,
                                
                                case
                                   when /* reporting ccy = system ccy*/ {report_currency_id} = {default_currency_id}
                                       then 1
                                   else
                                       (select fx_rate
                                        from currencies_currencyhistory c_ch
                                        where date = '{report_date}'
                                          and c_ch.currency_id = {report_currency_id}
                                          and c_ch.pricing_policy_id = {pricing_policy_id}
                                        limit 1)
                                end as rep_cur_fx,
                       
                                SUM(position_size_with_sign)                                as position_size,
                                SUM(position_size_with_sign * (1 - multiplier))             as position_size_opened,
                       
                                SUM(principal_with_sign)                                    as principal,
                                SUM(carry_with_sign)                                        as carry,
                                SUM(overheads_with_sign)                                    as overheads,
                                
                                
                                SUM(principal_with_sign * multiplier)                       as principal_closed,
                                SUM(carry_with_sign * multiplier)                           as carry_closed,
                                SUM(overheads_with_sign * multiplier)                       as overheads_closed,
                                
                                
                                SUM(principal_with_sign * (1 - multiplier))                 as principal_opened,
                                
                                SUM(carry_with_sign * (1 - multiplier))                     as carry_opened,
                                
                                SUM(overheads_with_sign * (1 - multiplier))                 as overheads_opened,
                                
                                
                                SUM(principal_with_sign_invested * (1 - multiplier))        as principal_with_sign_invested,
                                SUM(carry_with_sign_invested * (1 - multiplier))            as carry_with_sign_invested,
                                SUM(overheads_with_sign_invested * (1 - multiplier))        as overheads_with_sign_invested,
                                
                                SUM(principal_with_sign_invested * (1 - multiplier) * trn_hist_fx / rep_hist_fx)        as principal_fixed_opened,
                                SUM(carry_with_sign_invested * (1 - multiplier) * trn_hist_fx / rep_hist_fx)            as carry_fixed_opened,
                                SUM(overheads_with_sign_invested * (1 - multiplier) * trn_hist_fx / rep_hist_fx)        as overheads_fixed_opened,
                                
                                SUM(principal_with_sign_invested * (multiplier) *trn_hist_fx / rep_hist_fx)             as principal_fixed_closed,
                                SUM(carry_with_sign_invested * (multiplier) *trn_hist_fx / rep_hist_fx)                 as carry_fixed_closed,
                                SUM(overheads_with_sign_invested * (multiplier) *trn_hist_fx / rep_hist_fx)             as overheads_fixed_closed,
    
                                SUM(day_delta * position_size_with_sign * (1-multiplier))   as time_invested 
                            from 
                                transactions_unioned_table tut
                            group by 
                                {consolidation_columns} instrument_id, transaction_currency_id, settlement_currency_id
                        ) as tt_without_fx_rates
                        left join (
                            select 
                                currency_id,
                        
                                case
                                    when currency_id = '{default_currency_id}'::int
                                    then 1
                                    else fx_rate
                                end as fx_rate
                            from 
                                currencies_currencyhistory as c_ch
                            where 
                                
                                date = '{report_date}' and 
                                c_ch.pricing_policy_id = {pricing_policy_id}
                        ) as trnch
                        on 
                            transaction_currency_id = trnch.currency_id
                        left join (
                            select 
                                currency_id,
                        
                                case
                                    when currency_id = '{default_currency_id}'::int
                                    then 1
                                    else fx_rate
                                end as fx_rate
                            from 
                                currencies_currencyhistory 
                            where 
                                date = '{report_date}'
                        ) as stlch
                        on 
                            settlement_currency_id = stlch.currency_id
                        group by 
                            {consolidation_columns} instrument_id
                    ) as tt_final_calculations
                    left join (
                        select 
                            *,
                            (select
                                accrual_size
                            from 
                                instruments_accrualcalculationschedule ias
                            where 
                                accrual_start_date <= '{report_date}' and 
                                ias.instrument_id = ii.id 
                            order by 
                                accrual_start_date 
                            desc limit 1) as accrual_size,
                            -- add pricing ccy current fx rate
                            case
                               when
                                   pricing_currency_id = {default_currency_id}
                                   then 1
                               else
                                   (select fx_rate
                                    from currencies_currencyhistory c_ch
                                    where date = '{report_date}'
                                      and c_ch.currency_id = pricing_currency_id
                                      and c_ch.pricing_policy_id = {pricing_policy_id}
                                    limit 1)
                            end as prc_cur_fx,
    
                            -- add accrued ccy current fx rate
                            case
                               when
                                   pricing_currency_id = {default_currency_id}
                                   then 1
                               else
                                   (select fx_rate
                                    from currencies_currencyhistory c_ch
                                    where date = '{report_date}'
                                      and c_ch.currency_id = accrued_currency_id
                                      and c_ch.pricing_policy_id = {pricing_policy_id}
                                    limit 1)
                            end as accr_cur_fx,
    
                           -- add current price
                           (select
                                principal_price
                            from
                                instruments_pricehistory iph
                            where
                                date = '{report_date}'
                                and iph.instrument_id=ii.id
    
                               ) as cur_price,
                              -- add current accrued
                            (select
                                accrued_price
                            from
                                instruments_pricehistory iph
                            where
                                date = '{report_date}'
                                and iph.instrument_id=ii.id
    
                               ) as cur_accr_price
        
                        from 
                            instruments_instrument ii
                    ) as i
                    on 
                        instrument_id = i.id
                ) as partially_calculated_columns
                ) as loc_calculated_columns
            
            ) as pre_final_union_position_calculations_level_0
        ) as pre_final_union_position_calculations_level_1
        
        union all
        
        -- union with FX Variations
        select 
        
            name,
            short_name,
            user_code,
            
            item_type,
            item_type_name,
      
            instrument_id,
            {consolidation_columns}
          
            position_size,
            
            position_return,
            net_position_return,
            
            net_cost_price,
            net_cost_price_loc,
                
            time_invested,
   
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
            
                name,
                short_name,
                user_code,
                
                item_type,
                item_type_name,
          
                instrument_id,
                {consolidation_columns}
              
                position_size,
                
                (0) as position_return,
                (0) as net_position_return,
                
                (0) as net_cost_price,
                (0) as net_cost_price_loc,
                    
                (0) as time_invested,
                
                principal_opened,
                carry_opened,
                overheads_opened,
                (principal_opened + carry_opened + overheads_opened) as total_opened,
                
                (0) as principal_closed,
                (0) as carry_closed,
                (0) as overheads_closed,
                (0) as total_closed,
                
                principal_fx_opened,
                carry_fx_opened,
                overheads_fx_opened,
                (principal_fx_opened + carry_fx_opened + overheads_fx_opened) as total_fx_opened,
                
                (0) as principal_fx_closed,
                (0) as carry_fx_closed,
                (0) as overheads_fx_closed,
                (0) as total_fx_closed,
                
                principal_fixed_opened,
                carry_fixed_opened,
                overheads_fixed_opened,
                (principal_fixed_opened + carry_fixed_opened + overheads_fixed_opened) as total_fixed_opened,
                
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
                    (notes) as name, 
                    (notes) as short_name,
                    (notes) as user_code,
                    
                    (3) as item_type,
                    ('FX Variations') as item_type_name,
                    
                    (-1) as instrument_id,
                    {consolidation_columns}
                    
                    (0) as position_size,
                    
                    sum(principal) as principal_opened,
                    sum(carry) as carry_opened,
                    sum(overheads) as overheads_opened,
                    
                    sum(principal_fx) as principal_fx_opened,
                    sum(carry_fx) as carry_fx_opened,
                    sum(overheads_fx) as overheads_fx_opened,
                    
                    sum(principal_fixed) as principal_fixed_opened,
                    sum(carry_fixed) as carry_fixed_opened,
                    sum(overheads_fixed) as overheads_fixed_opened
                    
                from (
                    select 
                        *,
                        
                        (cash_consideration * (stl_cur_fx / rep_cur_fx - reference_fx_rate * trn_hist_fx / rep_hist_fx))      as principal,
                        (0)                                                                                                   as principal_fixed,
                        (cash_consideration * (stl_cur_fx / rep_cur_fx - reference_fx_rate * trn_hist_fx / rep_hist_fx))      as principal_fx,
                        
                        (0)      as carry,
                        (0)      as carry_fixed,
                        (0)      as carry_fx,
                        
                        (0)      as overheads,
                        (0)      as overheads_fixed,
                        (0)      as overheads_fx
                
                      from (
                            select 
                                *,
                                case
                                   when
                                       svfx.settlement_currency_id = {default_currency_id} -- system currency
                                       then 1
                                   else
                                       (select fx_rate
                                        from currencies_currencyhistory c_ch
                                        where date = '{report_date}'
                                          and c_ch.currency_id = svfx.settlement_currency_id
                                          and c_ch.pricing_policy_id = {pricing_policy_id}
                                        limit 1)
                                end as stl_cur_fx,
                
                                case
                                   when
                                       svfx.transaction_currency_id = {default_currency_id} -- system currency
                                       then 1
                                   else
                                       (select fx_rate
                                        from currencies_currencyhistory c_ch
                                        where c_ch.date = svfx.accounting_date
                                          and c_ch.currency_id = svfx.transaction_currency_id
                                          and c_ch.pricing_policy_id = {pricing_policy_id}
                                        limit 1)
                                end as trn_hist_fx,
                
                                case
                                   when /* reporting ccy = system ccy*/ {report_currency_id} = {default_currency_id}
                                       then 1
                                   else
                                       (select fx_rate
                                        from currencies_currencyhistory c_ch
                                        where c_ch.date = svfx.accounting_date
                                          and c_ch.currency_id = {report_currency_id} 
                                          and c_ch.pricing_policy_id = {pricing_policy_id}
                                        limit 1)
                                end as rep_hist_fx,
                
                                case
                                   when /* reporting ccy = system ccy*/ {report_currency_id} = {default_currency_id}
                                       then 1
                                   else
                                       (select fx_rate
                                        from currencies_currencyhistory c_ch
                                        where date = '{report_date}'
                                          and c_ch.currency_id = {report_currency_id} 
                                          and c_ch.pricing_policy_id = {pricing_policy_id}
                                        limit 1)
                                end as rep_cur_fx
                            from pl_cash_fx_variations_transactions_with_ttype svfx
                            where svfx.transaction_class_id in (8, 9)
                              and accounting_date <= '{report_date}'
                              and master_user_id = {master_user_id}
                              {fx_trades_and_fx_variations_filter_sql_string}
                          /*put filters here*/
                           ) as cashin_base
                     ) as cahsin_aggr
                group by name, {consolidation_columns} instrument_id
            ) as fx_variations_grouped
        ) as pre_final_union_fx_variations_calculations_level_0
        
        -- union with FX Trades
        union all
        
        select 
            
            name,
            short_name,
            user_code,
            
            item_type,
            item_type_name,
      
            instrument_id,
            {consolidation_columns}
          
            position_size,
            
            position_return,
            net_position_return,
            
            net_cost_price,
            net_cost_price_loc,
                
            time_invested,
            
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
                
                name,
                short_name,
                user_code,
                
                item_type,
                item_type_name,
          
                instrument_id,
                {consolidation_columns}
              
                position_size,
                
                (0) as position_return,
                (0) as net_position_return,
                
                (0) as net_cost_price,
                (0) as net_cost_price_loc,
                    
                (0) as time_invested,
                
                principal_opened,
                carry_opened,
                overheads_opened,
                (principal_opened + carry_opened + overheads_opened) as total_opened,
                
                (0) as principal_closed,
                (0) as carry_closed,
                (0) as overheads_closed,
                (0) as total_closed,
                
                principal_fx_opened,
                carry_fx_opened,
                overheads_fx_opened,
                (principal_fx_opened + carry_fx_opened + overheads_fx_opened) as total_fx_opened,
                
                (0) as principal_fx_closed,
                (0) as carry_fx_closed,
                (0) as overheads_fx_closed,
                (0) as total_fx_closed,
                
                principal_fixed_opened,
                carry_fixed_opened,
                overheads_fixed_opened,
                (principal_fixed_opened + carry_fixed_opened + overheads_fixed_opened) as total_fixed_opened,
                
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
                    (notes) as name, 
                    (notes) as short_name,
                    (notes) as user_code,
                    
                    (4) as item_type,
                    ('FX Trades') as item_type_name,
                    
                    (-1) as instrument_id,
                    {consolidation_columns}
                    
        
                    (0) as position_size,
                    
                    sum(principal_with_sign * stl_cur_fx/rep_cur_fx) as principal_opened,
                    sum(carry_with_sign * stl_cur_fx/rep_cur_fx)     as carry_opened,
                    sum(overheads_with_sign * stl_cur_fx/rep_cur_fx) as overheads_opened,

                    sum(principal_with_sign * stl_cur_fx/rep_cur_fx) as principal_fx_opened,
                    sum(principal_with_sign * stl_cur_fx/rep_cur_fx) as carry_fx_opened,
                    sum(principal_with_sign * stl_cur_fx/rep_cur_fx) as overheads_fx_opened,
                     
                    (0) as principal_fixed_opened,
                    (0) as carry_fixed_opened,
                    (0) as overheads_fixed_opened

                from (
                    select 
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
                    from pl_cash_fx_trades_transactions_with_ttype sft where 
                              transaction_class_id in (1001,1002)
                              and accounting_date <= '{report_date}'
                              and master_user_id = {master_user_id}
                              {fx_trades_and_fx_variations_filter_sql_string}
                        ) as trades_w_fxrate
                
                group by 
                    name, {consolidation_columns} instrument_id order by name
            ) as fx_variatons_grouped
        ) as pre_final_union_fx_trades_calculations_level_0
            
        
            """

        return query

    def get_query_for_first_date(self):

        report_fx_rate = 1

        try:
            item = CurrencyHistory.objects.get(currency_id=self.instance.report_currency.id,
                                               date=self.instance.report_date)
            report_fx_rate = item.fx_rate
        except CurrencyHistory.DoesNotExist:
            report_fx_rate = 1

        report_fx_rate = str(report_fx_rate)

        _l.info('report_fx_rate %s' % report_fx_rate)

        transaction_filter_sql_string = self.get_transaction_filter_sql_string()
        fx_trades_and_fx_variations_filter_sql_string = self.get_fx_trades_and_fx_variations_transaction_filter_sql_string()

        query = self.get_source_query()

        query = query.format(report_date=self.instance.pl_first_date,
                             master_user_id=self.instance.master_user.id,
                             default_currency_id=self.ecosystem_defaults.currency_id,
                             report_currency_id=self.instance.report_currency.id,
                             pricing_policy_id=self.instance.pricing_policy.id,
                             report_fx_rate=report_fx_rate,
                             transaction_filter_sql_string=transaction_filter_sql_string,
                             fx_trades_and_fx_variations_filter_sql_string=fx_trades_and_fx_variations_filter_sql_string,
                             consolidation_columns=self.get_position_consolidation_for_select(),
                             tt_consolidation_columns=self.get_position_consolidation_for_select(prefix="tt."),
                             transactions_all_with_multipliers_where_expression=self.get_where_expression_for_position_consolidation(
                                 prefix="tt_w_m.", prefix_second="t_o.")
                             )

        return query

    def get_query_for_second_date(self):

        report_fx_rate = 1

        try:
            item = CurrencyHistory.objects.get(currency_id=self.instance.report_currency.id,
                                               date=self.instance.report_date)
            report_fx_rate = item.fx_rate
        except CurrencyHistory.DoesNotExist:
            report_fx_rate = 1

        report_fx_rate = str(report_fx_rate)

        _l.info('report_fx_rate %s' % report_fx_rate)

        transaction_filter_sql_string = self.get_transaction_filter_sql_string()
        fx_trades_and_fx_variations_filter_sql_string = self.get_fx_trades_and_fx_variations_transaction_filter_sql_string()

        query = self.get_source_query()

        query = query.format(report_date=self.instance.report_date,
                             master_user_id=self.instance.master_user.id,
                             default_currency_id=self.ecosystem_defaults.currency_id,
                             report_currency_id=self.instance.report_currency.id,
                             pricing_policy_id=self.instance.pricing_policy.id,
                             report_fx_rate=report_fx_rate,
                             transaction_filter_sql_string=transaction_filter_sql_string,
                             fx_trades_and_fx_variations_filter_sql_string=fx_trades_and_fx_variations_filter_sql_string,
                             consolidation_columns=self.get_position_consolidation_for_select(),
                             tt_consolidation_columns=self.get_position_consolidation_for_select(prefix="tt."),
                             transactions_all_with_multipliers_where_expression=self.get_where_expression_for_position_consolidation(
                                 prefix="tt_w_m.", prefix_second="t_o."))

        return query

    def build_positions_fifo(self):

        _l.info("build positions fifo ")

        with connection.cursor() as cursor:

            query_1 = self.get_query_for_first_date()
            query_2 = self.get_query_for_second_date()

            st = time.perf_counter()

            # q1 - pl first date
            # q2 - report date
            # language=PostgreSQL
            query = """select 
                            
                            (q2.name) as name,
                            (q2.short_name) as short_name,
                            (q2.user_code) as user_code,
                            
                            -- add optional account_position, strategy1 position etc
                            
                            (q2.instrument_id) as instrument_id,
                            
                            {final_consolidation_columns}
                            
                            (q2.position_size) as position_size, -- ?
                            
                            (q2.position_return) as position_return,
                            (q2.net_position_return) as net_position_return,
                            
                            (q2.net_cost_price) as net_cost_price,
                            (q2.net_cost_price_loc) as net_cost_price_loc,
                                
                            (q2.time_invested) as time_invested,
                            
                            (q2.item_type) as item_type,
                            (q2.item_type_name) as item_type_name,
                            
                            (q2.principal_opened - coalesce(q1.principal_opened, 0)) as principal_opened,
                            (q2.carry_opened - coalesce(q1.carry_opened, 0)) as carry_opened,
                            (q2.overheads_opened - coalesce(q1.overheads_opened, 0)) as overheads_opened,
                            (q2.total_opened - coalesce(q1.total_opened, 0)) as total_opened,
                            
                            (q2.principal_closed - coalesce(q1.principal_closed, 0)) as principal_closed,
                            (q2.carry_closed - coalesce(q1.carry_closed, 0)) as carry_closed,
                            (q2.overheads_closed - coalesce(q1.overheads_closed, 0)) as overheads_closed,
                            (q2.total_closed - coalesce(q1.total_closed, 0)) as total_closed,
                            
                            (q2.principal_fx_opened - coalesce(q1.principal_fx_opened, 0)) as principal_fx_opened,
                            (q2.carry_fx_opened - coalesce(q1.carry_fx_opened, 0)) as carry_fx_opened,
                            (q2.overheads_fx_opened - coalesce(q1.overheads_fx_opened, 0)) as overheads_fx_opened,
                            (q2.total_fx_opened - coalesce(q1.total_fx_opened, 0)) as total_fx_opened,
                            
                            (q2.principal_fx_closed - coalesce(q1.principal_fx_closed, 0)) as principal_fx_closed,
                            (q2.carry_fx_closed - coalesce(q1.carry_fx_closed, 0)) as carry_fx_closed,
                            (q2.overheads_fx_closed - coalesce(q1.overheads_fx_closed, 0)) as overheads_fx_closed,
                            (q2.total_fx_closed - coalesce(q1.total_fx_closed, 0)) as total_fx_closed,
                            
                            (q2.principal_fixed_opened - coalesce(q1.principal_fixed_opened, 0)) as principal_fixed_opened,
                            (q2.carry_fixed_opened - coalesce(q1.carry_fixed_opened, 0)) as carry_fixed_opened,
                            (q2.overheads_fixed_opened - coalesce(q1.overheads_fixed_opened, 0)) as overheads_fixed_opened,
                            (q2.total_fixed_opened - coalesce(q1.total_fixed_opened, 0)) as total_fixed_opened,
                            
                            (q2.principal_fixed_closed - coalesce(q1.principal_fixed_closed, 0)) as principal_fixed_closed,
                            (q2.carry_fixed_closed - coalesce(q1.carry_fixed_closed, 0)) as carry_fixed_closed,
                            (q2.overheads_fixed_closed - coalesce(q1.overheads_fixed_closed, 0)) as overheads_fixed_closed,
                            (q2.total_fixed_closed - coalesce(q1.total_fixed_closed, 0)) as total_fixed_closed,
                            
                            -- loc
                            
                            (q2.principal_opened_loc - coalesce(q1.principal_opened_loc, 0)) as principal_opened_loc,
                            (q2.carry_opened_loc - coalesce(q1.carry_opened_loc, 0)) as carry_opened_loc,
                            (q2.overheads_opened_loc - coalesce(q1.overheads_opened_loc, 0)) as overheads_opened_loc,
                            (q2.total_opened_loc - coalesce(q1.total_opened_loc, 0)) as total_opened_loc,
                            
                            (q2.principal_closed_loc - coalesce(q1.principal_closed_loc, 0)) as principal_closed_loc,
                            (q2.carry_closed_loc - coalesce(q1.carry_closed_loc, 0)) as carry_closed_loc,
                            (q2.overheads_closed_loc - coalesce(q1.overheads_closed_loc, 0)) as overheads_closed_loc,
                            (q2.total_closed_loc - coalesce(q1.total_closed_loc, 0)) as total_closed_loc,
                            
                            (q2.principal_fx_opened_loc - coalesce(q1.principal_fx_opened_loc, 0)) as principal_fx_opened_loc,
                            (q2.carry_fx_opened_loc - coalesce(q1.carry_fx_opened_loc, 0)) as carry_fx_opened_loc,
                            (q2.overheads_fx_opened_loc - coalesce(q1.overheads_fx_opened_loc, 0)) as overheads_fx_opened_loc,
                            (q2.total_fx_opened_loc - coalesce(q1.total_fx_opened_loc, 0)) as total_fx_opened_loc,
                            
                            (q2.principal_fx_closed_loc - coalesce(q1.principal_fx_closed_loc, 0)) as principal_fx_closed_loc,
                            (q2.carry_fx_closed_loc - coalesce(q1.carry_fx_closed_loc, 0)) as carry_fx_closed_loc,
                            (q2.overheads_fx_closed_loc - coalesce(q1.overheads_fx_closed_loc, 0)) as overheads_fx_closed_loc,
                            (q2.total_fx_closed_loc - coalesce(q1.total_fx_closed_loc, 0)) as total_fx_closed_loc,
                            
                            (q2.principal_fixed_opened_loc - coalesce(q1.principal_fixed_opened_loc, 0)) as principal_fixed_opened_loc,
                            (q2.carry_fixed_opened_loc - coalesce(q1.carry_fixed_opened_loc, 0)) as carry_fixed_opened_loc,
                            (q2.overheads_fixed_opened_loc - coalesce(q1.overheads_fixed_opened_loc, 0)) as overheads_fixed_opened_loc,
                            (q2.total_fixed_opened_loc - coalesce(q1.total_fixed_opened_loc, 0)) as total_fixed_opened_loc,
                            
                            (q2.principal_fixed_closed_loc - coalesce(q1.principal_fixed_closed_loc, 0)) as principal_fixed_closed_loc,
                            (q2.carry_fixed_closed_loc - coalesce(q1.carry_fixed_closed_loc, 0)) as carry_fixed_closed_loc,
                            (q2.overheads_fixed_closed_loc - coalesce(q1.overheads_fixed_closed_loc, 0)) as overheads_fixed_closed_loc,
                            (q2.total_fixed_closed_loc - coalesce(q1.total_fixed_closed_loc, 0)) as total_fixed_closed_loc
                                
                       from ({query_report_date}) as q2 
                       left join ({query_first_date}) as q1 on q1.name = q2.name"""
            # left join ({query_first_date}) as q2 on q1.instrument_id = q2.instrument_id"""

            query = query.format(query_first_date=query_1,
                                 query_report_date=query_2,
                                 final_consolidation_columns=self.get_final_consolidation_columns())

            cursor.execute(query)

            _l.info('PL report query execute done: %s', "{:3.3f}".format(time.perf_counter() - st))

            query_str = str(cursor.query, 'utf-8')

            if settings.LOCAL:
                with open('/tmp/query_result.txt', 'w') as the_file:
                    the_file.write(query_str)

            # _l.info(query_str)

            result_tmp = dictfetchall(cursor)
            result = []

            ITEM_TYPE_INSTRUMENT = 1
            ITEM_TYPE_FX_VARIATIONS = 3
            ITEM_TYPE_FX_TRADES = 4

            for item in result_tmp:

                result_item_opened = item.copy()

                # result_item_opened['item_type'] = ITEM_INSTRUMENT
                # result_item_opened['item_type_code'] = "INSTR"
                # result_item_opened['item_type_name'] = "Instrument"

                if "portfolio_id" not in item:
                    result_item_opened['portfolio_id'] = self.ecosystem_defaults.portfolio_id

                if "account_position__id" not in item:
                    result_item_opened['account_position_id'] = self.ecosystem_defaults.account_id

                if "strategy1_position_id" not in item:
                    result_item_opened['strategy1_position_id'] = self.ecosystem_defaults.strategy1_id

                if "strategy2_position_id" not in item:
                    result_item_opened['strategy2_position_id'] = self.ecosystem_defaults.strategy2_id

                if "strategy3_position_id" not in item:
                    result_item_opened['strategy3_position_id'] = self.ecosystem_defaults.strategy3_id

                if result_item_opened['item_type'] == ITEM_TYPE_INSTRUMENT:
                    result_item_opened["item_group"] = 10
                    result_item_opened["item_group_code"] = "OPENED"
                    result_item_opened["item_group_name"] = "Opened"

                if result_item_opened['item_type'] == ITEM_TYPE_FX_VARIATIONS:
                    result_item_opened["item_group"] = 11  # TODO CHECK GROUP NUMBER
                    result_item_opened["item_group_code"] = "FX_VARIATIONS"
                    result_item_opened["item_group_name"] = "FX Variations"

                if result_item_opened['item_type'] == ITEM_TYPE_FX_TRADES:
                    result_item_opened["item_group"] = 12  # TODO CHECK GROUP NUMBER
                    result_item_opened["item_group_code"] = "FX_TRADES"
                    result_item_opened["item_group_name"] = "FX Trades"

                result_item_opened["principal"] = item["principal_opened"]
                result_item_opened["carry"] = item["carry_opened"]
                result_item_opened["overheads"] = item["overheads_opened"]
                result_item_opened["total"] = item["total_opened"]

                result_item_opened["principal_fx"] = item["principal_fx_opened"]
                result_item_opened["carry_fx"] = item["carry_fx_opened"]
                result_item_opened["overheads_fx"] = item["overheads_fx_opened"]
                result_item_opened["total_fx"] = item["total_fx_opened"]

                result_item_opened["principal_fixed"] = item["principal_fixed_opened"]
                result_item_opened["carry_fixed"] = item["carry_fixed_opened"]
                result_item_opened["overheads_fixed"] = item["overheads_fixed_opened"]
                result_item_opened["total_fixed"] = item["total_fixed_opened"]

                # loc

                result_item_opened["principal_loc"] = item["principal_opened_loc"]
                result_item_opened["carry_loc"] = item["carry_opened_loc"]
                result_item_opened["overheads_loc"] = item["overheads_opened_loc"]
                result_item_opened["total_loc"] = item["total_opened_loc"]

                result_item_opened["principal_fx_loc"] = item["principal_fx_opened_loc"]
                result_item_opened["carry_fx_loc"] = item["carry_fx_opened_loc"]
                result_item_opened["overheads_fx_loc"] = item["overheads_fx_opened_loc"]
                result_item_opened["total_fx_loc"] = item["total_fx_opened_loc"]

                result_item_opened["principal_fixed_loc"] = item["principal_fixed_opened_loc"]
                result_item_opened["carry_fixed_loc"] = item["carry_fixed_opened_loc"]
                result_item_opened["overheads_fixed_loc"] = item["overheads_fixed_opened_loc"]
                result_item_opened["total_fixed_loc"] = item["total_fixed_opened_loc"]



                #  CLOSED POSITIONS BELOW

                # TODO make it more readable

                has_opened_value = False

                if item["principal_opened"] is not None and item["principal_opened"] != 0:
                    has_opened_value = True

                if item["carry_opened"] is not None and item["carry_opened"] != 0:
                    has_opened_value = True

                if item["overheads_opened"] is not None and item["overheads_opened"] != 0:
                    has_opened_value = True

                has_closed_value = False

                if item["principal_closed"] is not None and item["principal_closed"] != 0:
                    has_closed_value = True

                if item["carry_closed"] is not None and item["carry_closed"] != 0:
                    has_closed_value = True

                if item["overheads_closed"] is not None and item["overheads_closed"] != 0:
                    has_closed_value = True

                if result_item_opened['item_type'] == ITEM_TYPE_FX_VARIATIONS and has_opened_value:
                    result.append(result_item_opened)

                if result_item_opened['item_type'] == ITEM_TYPE_FX_TRADES and has_opened_value:
                    result.append(result_item_opened)

                if result_item_opened['item_type'] == ITEM_TYPE_INSTRUMENT:
                    result.append(result_item_opened)

                if result_item_opened['item_type'] == ITEM_TYPE_INSTRUMENT and has_closed_value:

                    result_item_closed = item.copy()

                    # result_item_closed['item_type'] = ITEM_INSTRUMENT
                    # result_item_closed['item_type_code'] = "INSTR"
                    # result_item_closed['item_type_name'] = "Instrument"

                    if "portfolio_id" not in item:
                        result_item_closed['portfolio_id'] = self.ecosystem_defaults.portfolio_id

                    if "account_position__id" not in item:
                        result_item_closed['account_position_id'] = self.ecosystem_defaults.account_id

                    if "strategy1_position_id" not in item:
                        result_item_closed['strategy1_position_id'] = self.ecosystem_defaults.strategy1_id

                    if "strategy2_position_id" not in item:
                        result_item_closed['strategy2_position_id'] = self.ecosystem_defaults.strategy2_id

                    if "strategy3_position_id" not in item:
                        result_item_closed['strategy3_position_id'] = self.ecosystem_defaults.strategy3_id

                    result_item_closed["item_group"] = 11
                    result_item_closed["item_group_code"] = "CLOSED"
                    result_item_closed["item_group_name"] = "Closed"

                    result_item_closed["position_size"] = 0

                    result_item_closed["principal"] = item["principal_closed"]
                    result_item_closed["carry"] = item["carry_closed"]
                    result_item_closed["overheads"] = item["overheads_closed"]
                    result_item_closed["total"] = item["total_closed"]

                    result_item_closed["principal_fx"] = item["principal_fx_closed"]
                    result_item_closed["carry_fx"] = item["carry_fx_closed"]
                    result_item_closed["overheads_fx"] = item["overheads_fx_closed"]
                    result_item_closed["total_fx"] = item["total_fx_closed"]

                    result_item_closed["principal_fixed"] = item["principal_fixed_closed"]
                    result_item_closed["carry_fixed"] = item["carry_fixed_closed"]
                    result_item_closed["overheads_fixed"] = item["overheads_fixed_closed"]
                    result_item_closed["total_fixed"] = item["total_fixed_closed"]

                    # loc

                    result_item_closed["principal_loc"] = item["principal_opened_loc"]
                    result_item_closed["carry_loc"] = item["carry_opened_loc"]
                    result_item_closed["overheads_loc"] = item["overheads_opened_loc"]
                    result_item_closed["total_loc"] = item["total_opened_loc"]

                    result_item_closed["principal_fx_loc"] = item["principal_fx_opened_loc"]
                    result_item_closed["carry_fx_loc"] = item["carry_fx_opened_loc"]
                    result_item_closed["overheads_fx_loc"] = item["overheads_fx_opened_loc"]
                    result_item_closed["total_fx_loc"] = item["total_fx_opened_loc"]

                    result_item_closed["principal_fixed_loc"] = item["principal_fixed_opened_loc"]
                    result_item_closed["carry_fixed_loc"] = item["carry_fixed_opened_loc"]
                    result_item_closed["overheads_fixed_loc"] = item["overheads_fixed_opened_loc"]
                    result_item_closed["total_fixed_loc"] = item["total_fixed_opened_loc"]

                    result.append(result_item_closed)

            _l.info('build position result %s ' % len(result))

            self.instance.items = self.instance.items + result

    def build_positions_avco(self):

        _l.info("build positions avco")

        with connection.cursor() as cursor:

            query = """
                     with tt_cumul as (select rn,
                         ttype,
                         tt_ord.transaction_date,
                         tt_ord.transaction_class_id,
                         tt_ord.position_size_with_sign,
                         tt_ord.principal_with_sign,
                         tt_ord.instrument_id,
                         -- считаем накопительную сумму по инструменту
                         sum(tt_ord.position_size_with_sign) over (partition by tt_ord.instrument_id order by tt_ord.rn) as cumul,
                         sum(tt_ord.position_size_with_sign) over (partition by tt_ord.instrument_id order by tt_ord.rn)-position_size_with_sign as cumul_prev

                         -- нумеруем все транзакции по порядку по  дате.
                          from (select row_number() over (partition by tt.instrument_id order by tt.transaction_date) as rn,
                                       tt.transaction_date,
                                       tt.ttype,
                                       tt.transaction_class_id,
                                       tt.position_size_with_sign,
                                       tt.principal_with_sign,
                                       tt.instrument_id
                                       -- берем все транзакции и проставляем им тип исходя из знака position_size_with_sign
                                from pl_transactions_with_ttype  WHERE master_user_id = %s AND transaction_date <= %s as tt 
                               ) as tt_ord
                     )
                    -- основной запрос
        
                    select *, case
                      -- считаем прямые коэффициенты мультиплицирования по AVCO. Обрабатываем краевые условия
                                when rn = group_border and cumul = 0
                                  then 1
                                else
                                  case
                                    when  NOT (position_size_with_sign*cumul_prev<0) or rn=group_border
                                      then 1-exp(mult_coef_ln)
                                    else
                                      1
                                    end
                      end as mult
                    
                    from (
                           -- считаем инвертированный логарифмированный коэффициент по алгоритму Александра
                           select *, sum(mult_ln) over (partition by instrument_id order by rn desc) as mult_coef_ln
                    
                           from (select *,
                                        -- подсчет первоначальной таблицы коэффициентов для перемножения
                                        case
                                          when rn=group_border
                                            then
                                            case
                                              when NOT cumul_prev*position_size_with_sign = 0 and not cumul_prev+position_size_with_sign = 0
                                                then
                                                ln(1+(cumul_prev/position_size_with_sign))
                                              else
                                                0
                                              end
                                          else
                                            case
                                              when cumul_prev*position_size_with_sign < 0
                                                then
                                                ln(1+(position_size_with_sign/cumul_prev))
                                              else
                                                0
                                              end
                                          end as mult_ln
                                 from tt_cumul
                                        left join
                                      -- вычисляем границы групп (где меняется знак кумулятивный, либо 0)
                                        (select tt_in1.instrument_id, max(tt_in1.rn) as group_border
                                         from tt_cumul tt_in1
                                         where (tt_in1.cumul = 0 or tt_in1.cumul * tt_in1.cumul_prev < 0)
                                         group by tt_in1.instrument_id) as tt1 using (instrument_id)
                                 where rn > group_border
                                    or rn = group_border
                                ) as tt_mult_coef
                         ) as tt_mult
                  
                    union all
                    
                    select  *, 0 as mult_ln,0 as  mult_coef, 1 as mult
                    from tt_cumul
                           left join
                         (select tt_in1.instrument_id, max(tt_in1.rn) as group_border
                          from tt_cumul tt_in1
                          where (tt_in1.cumul = 0 or tt_in1.cumul * tt_in1.cumul_prev < 0)
                          group by tt_in1.instrument_id) as tt1 using (instrument_id)
                    where rn < group_border
                    order by instrument_id asc,rn desc;
            """

            cursor.execute(query, [self.instance.master_user.id, self.instance.report_date])

            _l.info("fetch position data")

            result = dictfetchall(cursor)

            _l.info('result %s' % result)

            ITEM_INSTRUMENT = 1

            # SOURCE_ITEMS - то что пришлет бэк

            # IF position * multiplier != 0 то добавляем строку как CLOSED из SOURCE ITEMS
            # IF position * (1 - multiplier) != 0 то добавляем строку как OPENED из SOURCE ITEMS

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
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).defer('object_permissions', 'responsibles', 'counterparties', 'transaction_types', 'accounts', 'tags') \
            .filter(master_user=self.instance.master_user) \
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

        _l.debug('_refresh_with_perms_optimized permissions done: %s',
                 "{:3.3f}".format(time.perf_counter() - permissions_st))

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

        _l.info('len instrument_ids %s' % len(instrument_ids))

        self.add_data_items_instruments(instrument_ids)
        self.add_data_items_portfolios(portfolio_ids)
        self.add_data_items_accounts(account_ids)
        self.add_data_items_currencies(currencies_ids)

        self.instance.custom_fields = BalanceReportCustomField.objects.filter(master_user=self.instance.master_user)

        _l.debug('_refresh_with_perms_optimized item relations done: %s',
                 "{:3.3f}".format(time.perf_counter() - item_relations_st))
