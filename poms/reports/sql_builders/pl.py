import logging
import os
import time
from datetime import date, timedelta

from celery import group
from django.conf import settings
from django.db import connection

from poms.accounts.models import Account, AccountType
from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.common.utils import get_closest_bday_of_yesterday, get_last_business_day, \
    get_last_business_day_of_previous_year, get_last_business_day_in_previous_quarter, get_last_business_day_of_previous_month
from poms.currencies.models import Currency
from poms.iam.utils import get_allowed_queryset
from poms.instruments.models import Instrument, CostMethod, InstrumentType, Country
from poms.portfolios.models import Portfolio
from poms.reports.common import Report
from poms.reports.models import PLReportCustomField, ReportInstanceModel
from poms.reports.sql_builders.helpers import get_transaction_filter_sql_string, get_report_fx_rate, \
    get_fx_trades_and_fx_variations_transaction_filter_sql_string, get_where_expression_for_position_consolidation, \
    get_position_consolidation_for_select, dictfetchall, get_transaction_date_filter_for_initial_position_sql_string
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.transactions.models import Transaction
from poms.users.models import EcosystemDefault

_l = logging.getLogger('poms.reports')


class PLReportBuilderSql:

    def __init__(self, instance=None):

        _l.debug('ReportBuilderSql init')

        self.instance = instance

        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self.instance.master_user)

        _l.debug('self.instance master_user %s' % self.instance.master_user)
        _l.debug('self.instance report_date %s' % self.instance.report_date)

        '''TODO IAM_SECURITY_VERIFY need to check, if user somehow passes id of object he has no access to we should throw error'''

        '''Important security methods'''
        self.transform_to_allowed_portfolios()
        self.transform_to_allowed_accounts()

        if not self.instance.pl_first_date and not self.instance.period_type:
            _l.info("No pl_first_date, no period_type settings to ytd")
            self.instance.period_type = 'ytd'

        if not self.instance.pl_first_date and self.instance.period_type:

            _l.info("No pl_first_date, calculating by period_type...")

            if self.instance.period_type == 'inception':
                # TODO wtf is first transaction when multi portfolios?
                # TODO ask oleg what to do with inception
                # szhitenev 2023-12-04

                first_portfolio = self.instance.portfolios.first()

                self.instance.pl_first_date = get_last_business_day(
                    first_portfolio.first_transaction_date - timedelta(days=1),
                    )
            elif self.instance.period_type == 'ytd':
                self.instance.pl_first_date = get_last_business_day_of_previous_year(self.instance.report_date)

            elif self.instance.period_type == 'qtd':
                self.instance.pl_first_date = get_last_business_day_in_previous_quarter(self.instance.report_date)

            elif self.instance.period_type == 'mtd':
                self.instance.pl_first_date = get_last_business_day_of_previous_month(self.instance.report_date)

            elif self.instance.period_type == 'daily':
                self.instance.pl_first_date = get_last_business_day(self.instance.report_date - timedelta(days=1))

    def transform_to_allowed_portfolios(self):

        if not len(self.instance.portfolios):
            self.instance.portfolios = get_allowed_queryset(self.instance.member, Portfolio.objects.all())

    def transform_to_allowed_accounts(self):

        if not len(self.instance.accounts):
            self.instance.accounts = get_allowed_queryset(self.instance.member, Account.objects.all())

    def get_first_transaction(self):

        try:

            portfolios = []

            transaction = Transaction.objects.all().first()

            return transaction.transaction_date

        except Exception as e:
            _l.error("Could not find first transaction date")
            return None

    def build_report(self):
        st = time.perf_counter()

        self.instance.items = []

        self.report_date = self.instance.report_date

        if not self.instance.report_date:
            self.report_date = get_closest_bday_of_yesterday()

        self.bday_yesterday_of_report_date = get_last_business_day(self.report_date - timedelta(days=1), to_string=True)

        self.instance.first_transaction_date = self.get_first_transaction()

        pl_first_date = self.instance.pl_first_date

        if not pl_first_date or pl_first_date == date.min:
            self.instance.pl_first_date = self.instance.first_transaction_date

        _l.info('self.instance.report_date %s' % self.instance.report_date)
        _l.info('self.instance.pl_first_date %s' % self.instance.pl_first_date)

        self.parallel_build()

        self.instance.execution_time = float("{:3.3f}".format(time.perf_counter() - st))

        _l.debug('items total %s' % len(self.instance.items))

        _l.debug('build_st done: %s', "{:3.3f}".format(time.perf_counter() - st))

        relation_prefetch_st = time.perf_counter()

        self.add_data_items()

        self.instance.relation_prefetch_time = float("{:3.3f}".format(time.perf_counter() - relation_prefetch_st))

        return self.instance

    @staticmethod
    def get_final_consolidation_columns(instance):

        result = []

        # (q2.instrument_id) as instrument_id,

        if instance.portfolio_mode == Report.MODE_INDEPENDENT:
            result.append("(q2.portfolio_id) as portfolio_id")

        if instance.account_mode == Report.MODE_INDEPENDENT:
            result.append("(q2.account_position_id) as account_position_id")

        if instance.strategy1_mode == Report.MODE_INDEPENDENT:
            result.append("(q2.strategy1_position_id) as strategy1_position_id")

        if instance.strategy2_mode == Report.MODE_INDEPENDENT:
            result.append("(q2.strategy2_position_id) as strategy2_position_id")

        if instance.strategy3_mode == Report.MODE_INDEPENDENT:
            result.append("(q2.strategy3_position_id) as strategy3_position_id")

        if instance.allocation_mode == Report.MODE_INDEPENDENT:
            result.append("(q2.allocation_pl_id) as allocation_pl_id")

        resultString = ''

        if len(result):
            resultString = ", ".join(result) + ', '

        return resultString

    @staticmethod
    def get_final_consolidation_where_filters_columns(instance):

        result = []

        if instance.portfolio_mode == Report.MODE_INDEPENDENT:
            result.append("q2.portfolio_id = q1.portfolio_id")

        if instance.account_mode == Report.MODE_INDEPENDENT:
            result.append("q2.account_position_id = q1.account_position_id")

        if instance.strategy1_mode == Report.MODE_INDEPENDENT:
            result.append("q2.strategy1_position_id = q1.strategy1_position_id")

        if instance.strategy2_mode == Report.MODE_INDEPENDENT:
            result.append("q2.strategy2_position_id = q1.strategy2_position_id")

        if instance.strategy3_mode == Report.MODE_INDEPENDENT:
            result.append("q2.strategy3_position_id = q1.strategy3_position_id")

        resultString = ''

        if len(result):
            resultString = resultString + 'and '
            resultString = resultString + " and ".join(result)

        return resultString

    @staticmethod
    def inject_fifo_with():

        _l.debug("Injecting fifo calculation algorithm")

        # language=PostgreSQL
        query = """
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
                   transaction_ytm,
                   
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
                        transaction_ytm,
                         
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
                      from transactions_ordered where transaction_class_id in (1,2) and position_size_with_sign != 0
                    ) as tt_fin
          ),
        """

        return query

    @staticmethod
    def inject_avco_with():

        _l.debug("Injecting avco calculation algorithm")

        # language=PostgreSQL
        query = """
        
        avco_rolling as (
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
               
               transaction_currency_id,
               settlement_currency_id,
               
               reference_fx_rate,
               transaction_ytm,
              
               sum(position_size_with_sign) over (partition by {consolidation_columns} instrument_id  order by rn_total) as rolling_position_size,
               sum(position_size_with_sign) over (partition by {consolidation_columns} instrument_id  order by rn_total)-position_size_with_sign as rolling_position_size_prev
         
           from transactions_ordered where transaction_class_id in (1,2) and position_size_with_sign != 0
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
  
           transaction_currency_id,
           settlement_currency_id,
           
           reference_fx_rate,
           transaction_ytm,
           
           ('{report_date}'::date - accounting_date::date) as day_delta,
  
           mult_coef_ln,
           
          case
              -- считаем прямые коэффициенты мультиплицирования по AVCO. Обрабатываем краевые условия
              when rn_total = group_border and rolling_position_size = 0
                  then 1
              else
                  case
                  when  NOT (position_size_with_sign*rolling_position_size_prev<0) or rn_total=group_border
                      then 1-exp(mult_coef_ln)
              else
                  1
              end
          end as multiplier
        
         from (
              -- считаем инвертированный логарифмированный коэффициент по алгоритму Александра
                  select *, sum(mult_ln) over (partition by {consolidation_columns} instrument_id  order by rn_total desc) as mult_coef_ln

                  from (select *,
                   -- подсчет первоначальной таблицы коэффициентов для перемножения
                               case
                                   when rn_total=group_border
                                   then
                                       case
                                           when NOT rolling_position_size_prev * position_size_with_sign = 0 and not rolling_position_size_prev + position_size_with_sign = 0
                                              then
                                                  ln(1+(rolling_position_size_prev / position_size_with_sign))
                                              else
                                                  0
                                           end
                                  else
                                      case
                                        when rolling_position_size_prev*position_size_with_sign < 0
                                          then
                                                  ln(1+(position_size_with_sign / rolling_position_size_prev))
                                          else
                                          0
                                      end
                                   end as mult_ln
                        from avco_rolling
                                 left join
                            -- вычисляем границы групп (где меняется знак кумулятивный, либо 0)
                             (select 
                                {tt_in1_consolidation_columns}
                                tt_in1.instrument_id, max(tt_in1.rn_total) as group_border
                              from avco_rolling tt_in1
                              where (tt_in1.rolling_position_size * tt_in1.rolling_position_size_prev <= 0)
                              group by {tt_in1_consolidation_columns} tt_in1.instrument_id) as tt1 using ({consolidation_columns} instrument_id)
                        where rn_total > group_border
                           or rn_total = group_border
                        ) as tt_mult_coef
          ) as tt_mult
        
          union
        
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
  
           transaction_currency_id,
           settlement_currency_id,
           
           reference_fx_rate,
           transaction_ytm,
           
           ('{report_date}'::date - accounting_date::date) as day_delta, 

           0 as mult_coef, 
           1 as multiplier
              
          from avco_rolling
          left join
              (select 
                    {tt_in1_consolidation_columns}
                    tt_in1.instrument_id, 
                    max(tt_in1.rn_total) as group_border
                      from avco_rolling tt_in1
                      where (tt_in1.rolling_position_size * tt_in1.rolling_position_size_prev <= 0)
                      group by {tt_in1_consolidation_columns} tt_in1.instrument_id) as tt1 using ({consolidation_columns} instrument_id)
          where rn_total < group_border
          order by {consolidation_columns} instrument_id asc,rn_total desc
        ),
        """

        return query

    # Used in Balance Report (balance.py)
    @staticmethod
    def get_source_query(cost_method):

        cost_method_with = ''

        if cost_method == CostMethod.AVCO:
            cost_method_with = PLReportBuilderSql.inject_avco_with()

        if cost_method == CostMethod.FIFO:
            cost_method_with = PLReportBuilderSql.inject_fifo_with()

        # language=PostgreSQL
        query = """
        with 
            pl_transactions_with_ttype_filtered as (
                select * from pl_transactions_with_ttype
                {transaction_filter_sql_string}
                {transaction_date_filter_for_initial_position_sql_string}
            ),
        
            transactions_ordered as (
                select 
                   row_number() 
                   over (partition by {tt_consolidation_columns} tt.instrument_id order by ttype,tt.accounting_date,tt.transaction_code) as rn,
                   row_number()
                   over (partition by {tt_consolidation_columns} tt.instrument_id order by tt.accounting_date,ttype,tt.transaction_code) as rn_total, -- used for core avco calc
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
                   tt.transaction_ytm,
                   
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
                         
                         transaction_code,
                         
                         transaction_currency_id,
                         settlement_currency_id,
                         
                         reference_fx_rate,
                         (ytm_at_cost) as transaction_ytm, -- Very important! Just not to be confused between price history ytm and transaction ytm
                         
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
            
            -- for mismatch
            transactions_to_base_currency as (
                select
                    linked_instrument_id,
                    settlement_currency_id,
                    {consolidation_columns}
                    position_size_with_sign,
                    principal_with_sign*stl_fx_rate as principal_with_sign,
                    carry_with_sign*stl_fx_rate as carry_with_sign,
                    overheads_with_sign*stl_fx_rate as overheads_with_sign,
                    cash_consideration*stl_fx_rate as cash_consideration
                from
                     (
                        select
                               linked_instrument_id,
                               settlement_currency_id,
                               (select fx_rate
                                 from currencies_currencyhistory cch
                                 where cch.currency_id = settlement_currency_id
                                   and cch.date = '{report_date}'
                                   and cch.pricing_policy_id = {pricing_policy_id}
                                    /* and pricing policy= */
                                 ) as stl_fx_rate,
                                {consolidation_columns}
                               sum(position_size_with_sign) as position_size_with_sign,
                               sum(principal_with_sign) as principal_with_sign,
                               sum(carry_with_sign) as carry_with_sign,
                               sum(overheads_with_sign) as overheads_with_sign,
                               sum(cash_consideration) as cash_consideration
                          from pl_transactions_with_ttype_filtered
                          group by linked_instrument_id, {consolidation_columns} settlement_currency_id
                
                    ) as pre_aggregate
            ),
        
            """ + cost_method_with + """
    
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
                        
                        (0) as amount_principal_with_sign,
                        (0) as amount_carry_with_sign,
                        
                        rolling_position_size,
  
                        transaction_currency_id,
                        settlement_currency_id,
                        
                        reference_fx_rate,
                        transaction_ytm,
                        
        
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
                                where  tt_w_m.rn_total < t_o.rn_total
                                        and
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
                       
                       (principal_with_sign) as amount_principal_with_sign,
                       (carry_with_sign) as amount_carry_with_sign,
    
                       rolling_position_size,
                       
                       transaction_currency_id,
                       settlement_currency_id,
                       
                       reference_fx_rate,
                       transaction_ytm,
                       
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

                   
                   transaction_currency_id,
                   settlement_currency_id,
                   
                   reference_fx_rate,
                   transaction_ytm,
                   
                   
                   /*
                     make trn_hist_fx rep_hist_fx calculations optional
                     add flag to report settings (calculate_fixed_columns)
                     
                   */
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
                   
                   (amount_principal_with_sign * reference_fx_rate) as amount_principal_with_sign_invested,
                   (amount_carry_with_sign * reference_fx_rate) as amount_carry_with_sign_invested,
                   
                   (principal_with_sign) as principal_with_sign,
                   (carry_with_sign) as carry_with_sign,
                   (overheads_with_sign) as overheads_with_sign,
                   
                   multiplier
                
                from transactions_all_with_multipliers
                {filter_query_for_balance_in_multipliers_table}
            
            )
    
        --- main query
        select 
        
            name,
            short_name,
            user_code,
            
            item_type,
            item_type_name,
      
            currency_id,
            instrument_id,
            {consolidation_columns}
        
            co_directional_exposure_currency_id,
            pricing_currency_id,
            instrument_pricing_currency_fx_rate,
            instrument_accrued_currency_fx_rate,    
            instrument_principal_price,
            instrument_accrued_price,
            instrument_factor, 
            instrument_ytm,   
            daily_price_change,
          
            position_size,
            nominal_position_size,
            
            position_return,
            position_return_loc,
            net_position_return,
            net_position_return_loc,
            
            position_return_fixed,
            position_return_fixed_loc,
            net_position_return_fixed,
            net_position_return_fixed_loc,
            
            net_cost_price,
            net_cost_price_loc,
            principal_cost_price_loc,
            
            gross_cost_price,
            gross_cost_price_loc,
            
            principal_invested,
            principal_invested_loc,
            
            amount_invested,
            amount_invested_loc,
            
            principal_invested_fixed,
            principal_invested_fixed_loc,
            
            amount_invested_fixed,
            amount_invested_fixed_loc,
                
            time_invested,
            
            ytm,
            modified_duration,
            ytm_at_cost,
            return_annually,
            return_annually_fixed,
            
            market_value,
            exposure,
            
            market_value_loc,
            exposure_loc,

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
            total_fixed_closed_loc,
            
            mismatch
                        
        from (
            select 
            name,
            short_name,
            user_code,
            
            item_type,
            item_type_name,
      
            (-1) as currency_id,
            instrument_id,
            {consolidation_columns}
            
            co_directional_exposure_currency_id,
            pricing_currency_id,
            instrument_pricing_currency_fx_rate,
            instrument_accrued_currency_fx_rate,    
            instrument_principal_price,
            instrument_accrued_price,   
            instrument_factor,
            instrument_ytm,
            daily_price_change,
          
            position_size,
            nominal_position_size,
            
            position_return,
            position_return_loc,
            net_position_return,
            net_position_return_loc,
            
            position_return_fixed,
            position_return_fixed_loc,
            net_position_return_fixed,
            net_position_return_fixed_loc,
            
            net_cost_price,
            net_cost_price_loc,
            principal_cost_price_loc,
            
            gross_cost_price,
            gross_cost_price_loc,
            
            principal_invested,
            principal_invested_loc,
            
            amount_invested,
            amount_invested_loc,
            
            principal_invested_fixed,
            principal_invested_fixed_loc,
            
            amount_invested_fixed,
            amount_invested_fixed_loc,
                
            time_invested,
            
            ytm,
            modified_duration,
            ytm_at_cost,
            return_annually,
            return_annually_fixed,
            
            
            market_value,
            exposure,
            
            market_value_loc,
            exposure_loc,

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
            total_fixed_closed_loc,
            
            (0) as mismatch
            
            from (
                select 
                    name,
                    short_name,
                    user_code,
                    
                    (1) as item_type,
                    ('Instrument') as item_type_name,
              
                    instrument_id,
                    {consolidation_columns}
                    
                    
                    co_directional_exposure_currency_id,
                    pricing_currency_id,
                    instrument_pricing_currency_fx_rate,
                    instrument_accrued_currency_fx_rate,    
                    instrument_principal_price,
                    instrument_accrued_price,  
                    instrument_factor,
                    instrument_ytm,
                    daily_price_change, 

                    position_size,
                    nominal_position_size,
                    
                    position_return,
                    position_return_loc,
                    net_position_return,
                    net_position_return_loc,
                    
                    position_return_fixed,
                    position_return_fixed_loc,
                    net_position_return_fixed,
                    net_position_return_fixed_loc,
                    
                    net_cost_price,
                    net_cost_price_loc,
                    principal_cost_price_loc,
                    
                    gross_cost_price,
                    gross_cost_price_loc,
                    
                    principal_invested,
                    principal_invested_loc,
                    
                    amount_invested,
                    amount_invested_loc,
                    
                    principal_invested_fixed,
                    principal_invested_fixed_loc,
                    
                    amount_invested_fixed,
                    amount_invested_fixed_loc,
                        
                    time_invested,
                    
                    
                    ytm,
                    modified_duration,
                    ytm_at_cost,

                    case
                        when time_invested != 0
                        then (position_return / time_invested)
                        else 0
                    end as return_annually,
                    
                    case
                        when time_invested != 0
                        then (position_return_fixed / time_invested)
                        else 0
                    end as return_annually_fixed,
                    
                    market_value,
                    exposure,
                    
                    market_value_loc,
                    exposure_loc,
                    
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
                    ((principal_closed - principal_fixed_closed) + (carry_closed - carry_fixed_closed) + (overheads_closed - overheads_fixed_closed)) as total_fx_closed,
                    
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
                        co_directional_exposure_currency_id,
                        pricing_currency_id,
                        price_multiplier,
                        accrued_multiplier,
                        accrual_size,
                        (cur_price) as instrument_principal_price,
                        (cur_accr_price) as instrument_accrued_price,
                        (cur_factor) as instrument_factor,
                        (cur_ytm) as instrument_ytm,
                        case when coalesce(yesterday_price,0) = 0
                                then 0
                                else
                                    (cur_price - yesterday_price) / yesterday_price
                        end as daily_price_change,
                        (prc_cur_fx) as instrument_pricing_currency_fx_rate,
                        (accr_cur_fx) as instrument_accrued_currency_fx_rate,
                        rep_cur_fx,
                        mv_principal,
                        mv_carry,
                        cross_loc_prc_fx,
                        
                        position_size,
                        -- (position_size / cur_factor) as nominal_position_size,
                        case when coalesce(cur_factor,1) = 0
                                then position_size
                                else
                                    position_size / coalesce(cur_factor,1)
                        end as nominal_position_size,
                        position_size_opened,
                        
                        net_cost_price,
                        net_cost_price_loc,
                        principal_cost_price_loc,
                        
                        gross_cost_price,
                        gross_cost_price_loc,
                        
                        time_invested,
                        
                        
                        ytm,
                        modified_duration,
                        ytm_at_cost,
    
    
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
                            when amount_invested != 0
                            then (((mv_principal+principal_opened) + (mv_carry+carry_opened)) / -amount_invested) -- check for minus
                            else 0
                        end as position_return,
                        
                        case
                            when amount_invested != 0
                            then ((((mv_principal+principal_opened) + (mv_carry+carry_opened)) / -amount_invested) * cross_loc_prc_fx)
                            else 0
                        end as position_return_loc,
                        
                        case
                            when amount_invested != 0
                            then (((mv_principal+principal_opened) + (mv_carry+carry_opened) + overheads_opened) / -amount_invested) -- check for minus
                            else 0
                        end as net_position_return,
                        
                        case
                            when amount_invested != 0
                            then ((((mv_principal+principal_opened) + (mv_carry+carry_opened) + overheads_opened) / -amount_invested) * cross_loc_prc_fx)
                            else 0
                        end as net_position_return_loc, -- probably not needed
    
                        case
                            when amount_invested_fixed != 0
                            then (((mv_principal+principal_fixed_opened) + (mv_carry+carry_fixed_opened)) / -amount_invested_fixed) -- check for minus
                            else 0
                        end as position_return_fixed,
                        
                        case
                            when amount_invested_fixed != 0
                            then ((((mv_principal+principal_fixed_opened) + (mv_carry+carry_fixed_opened)) / -amount_invested_fixed) * cross_loc_prc_fx)
                            else 0
                        end as position_return_fixed_loc,
                        
                        case
                            when amount_invested_fixed != 0
                            then (((mv_principal+principal_fixed_opened) + (mv_carry+carry_fixed_opened) + overheads_fixed_opened) / -amount_invested_fixed) -- check for minus
                            else 0
                        end as net_position_return_fixed,
                        
                        case
                            when amount_invested_fixed != 0
                            then ((((mv_principal+principal_fixed_opened) + (mv_carry+carry_fixed_opened) + overheads_fixed_opened) / -amount_invested_fixed) * cross_loc_prc_fx)
                            else 0
                        end as net_position_return_fixed_loc, -- probably not needed
        
                        -- will be taken from balance
                        -- mv_carry+mv_principal as market_value,
                        mv_carry+mv_principal as exposure,
                        
                        case
                             when instrument_class_id = 5
                                 then (position_size * (instrument_principal_price - principal_cost_price_loc) * price_multiplier * pch_fx_rate) / rep_cur_fx + mv_carry
                             else mv_carry+mv_principal
                         end as market_value,
            
                        case
                             when instrument_class_id = 5
                                 then (position_size * (instrument_principal_price - principal_cost_price_loc) * price_multiplier) + mv_carry
                             else (mv_carry+mv_principal) * cross_loc_prc_fx
                        end as market_value_loc,
                        
                        
                        -- (mv_carry+mv_principal) * cross_loc_prc_fx as market_value_loc,
                        (mv_carry+mv_principal) * cross_loc_prc_fx as exposure_loc,
                        
                        principal_invested,
                        principal_invested * cross_loc_prc_fx as principal_invested_loc,
                        
                        amount_invested,
                        amount_invested * cross_loc_prc_fx as amount_invested_loc,
                        
                        principal_invested_fixed,
                        principal_invested_fixed * cross_loc_prc_fx as principal_invested_fixed_loc,
                        
                        amount_invested_fixed,
                        amount_invested_fixed * cross_loc_prc_fx as amount_invested_fixed_loc
                        
                from (
                        select 
                            instrument_id,
                             {consolidation_columns}
                    
                            i.name,
                            i.short_name,
                            i.user_code,
                            i.pricing_currency_id,
                            i.co_directional_exposure_currency_id,
                            i.price_multiplier,
                            i.accrued_multiplier,
                            i.accrual_size,
                            i.cur_price,
                            i.yesterday_price,
                            i.cur_factor,
                            i.cur_ytm,
                            i.cur_accr_price,
                            i.prc_cur_fx,
                            i.accr_cur_fx,
                            
                            i.ytm,
                            i.modified_duration,
                            
                            it.instrument_class_id,
                            
                            
                            (select 
                                principal_price
                            from instruments_pricehistory
                            where 
                                instrument_id=i.id and 
                                date = '{report_date}' and
                                pricing_policy_id = {pricing_policy_id})
                            as instrument_principal_price,
                            
                            (select 
                                factor
                            from instruments_pricehistory
                            where 
                                instrument_id=i.id and 
                                date = '{report_date}' and
                                pricing_policy_id = {pricing_policy_id})
                            as instrument_factor,
                            
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
                            
                            case
                                when position_size != 0
                                then ytm_at_cost / position_size
                                else 0
                            end as ytm_at_cost,
                            
                            rep_cur_fx,
                            (rep_cur_fx / i.prc_cur_fx) cross_loc_prc_fx,
        
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
                                when position_size_opened != 0 and i.price_multiplier != 0
                                then -((principal_opened) / position_size_opened / i.price_multiplier)
                                else 0
                            end as net_cost_price,
                            -- испольщуется только эта
                            case
                                when position_size_opened != 0 and i.price_multiplier != 0
                                then -((principal_opened) / position_size_opened * rep_cur_fx / i.prc_cur_fx / i.price_multiplier)
                                else 0
                            end as net_cost_price_loc,
                            
                            case
                                when position_size_opened != 0 and i.price_multiplier != 0
                                    then -((principal_opened) / position_size_opened * rep_cur_fx / i.prc_cur_fx / i.price_multiplier)
                                else 0
                            end as principal_cost_price_loc, -- wtf?
                            
                            
                            -- вроде, не используется
                            case
                                when position_size_opened != 0 and i.price_multiplier != 0
                                then -((principal_opened + overheads_opened) / position_size_opened / i.price_multiplier)
                                else 0
                            end as gross_cost_price,
                            -- испольщуется только эта
                            case
                                when position_size_opened != 0 and i.price_multiplier != 0
                                then -((principal_opened + overheads_opened) / position_size_opened * rep_cur_fx / i.prc_cur_fx / i.price_multiplier)
                                else 0
                            end as gross_cost_price_loc,
                            
                            case
                                when position_size_opened != 0
                                then time_invested_sum / position_size_opened / 365
                                else 0
                            end as time_invested,
                        
                            -- mv precalc
                                (position_size_opened * coalesce(i.cur_price, 0) * i.price_multiplier * i.prc_cur_fx / rep_cur_fx) as mv_principal,
                                (position_size_opened * coalesce(i.cur_accr_price, 0) * i.accrued_multiplier * i.accr_cur_fx  / rep_cur_fx) as mv_carry,
        
                            -- (i.accrual_size * i.accrued_multiplier  / (i.cur_price * i.price_multiplier) ) as ytm,
                            
                            (amount_principal_with_sign_invested) as principal_invested,
                            (amount_principal_with_sign_invested + amount_carry_with_sign_invested) as amount_invested,
                    
                            (amount_principal_with_sign_invested_fixed) as principal_invested_fixed,
                            (amount_principal_with_sign_invested_fixed + amount_carry_with_sign_invested_fixed) as amount_invested_fixed
                            
    
                    
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
                                
                                SUM(amount_principal_with_sign_invested * stl_cur_fx / rep_cur_fx)      as amount_principal_with_sign_invested,
                                SUM(amount_carry_with_sign_invested * stl_cur_fx / rep_cur_fx)      as amount_carry_with_sign_invested,
                                
                                SUM(time_invested)                                                      as time_invested_sum,
                                
                                --SUM(principal_with_sign_invested * stlch.fx_rate * trnch.fx_rate )      as principal_with_sign_invested,
                                --SUM(carry_with_sign_invested * stlch.fx_rate * trnch.fx_rate )          as carry_with_sign_invested,
                                --SUM(overheads_with_sign_invested * stlch.fx_rate * trnch.fx_rate )      as overheads_with_sign_invested,
                                
                                --SUM(principal_with_sign_invested * stl_cur_fx * trn_cur_fx )      as principal_with_sign_invested,
                                --SUM(carry_with_sign_invested * stl_cur_fx * trn_cur_fx )          as carry_with_sign_invested,
                                --SUM(overheads_with_sign_invested * stl_cur_fx * trn_cur_fx )      as overheads_with_sign_invested,
                                -- fixed below
                                SUM(principal_with_sign_invested)      as principal_with_sign_invested, -- possibly missing pricing fx multiply 
                                SUM(carry_with_sign_invested)          as carry_with_sign_invested,
                                SUM(overheads_with_sign_invested)      as overheads_with_sign_invested,
                                
                                SUM(amount_principal_with_sign_invested_fixed)      as amount_principal_with_sign_invested_fixed,
                                SUM(amount_carry_with_sign_invested_fixed)      as amount_carry_with_sign_invested_fixed,
                                
                                SUM(principal_fixed_opened)                                             as principal_fixed_opened,
                                SUM(carry_fixed_opened)                                                 as carry_fixed_opened,
                                SUM(overheads_fixed_opened)                                             as overheads_fixed_opened,
                                
                                SUM(principal_fixed_closed)                                             as principal_fixed_closed,
                                SUM(carry_fixed_closed)                                                 as carry_fixed_closed,
                                SUM(overheads_fixed_closed)                                             as overheads_fixed_closed,
                                SUM(ytm_at_cost)                                             as ytm_at_cost
        
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
                                       when
                                           tut.transaction_currency_id = {default_currency_id}
                                           then 1
                                       else
                                           (select fx_rate
                                            from currencies_currencyhistory c_ch
                                            where date = '{report_date}'
                                              and c_ch.currency_id = tut.transaction_currency_id
                                              and c_ch.pricing_policy_id = {pricing_policy_id}
                                            limit 1)
                                    end as trn_cur_fx,
                                    
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
                                    
                                    SUM(amount_principal_with_sign_invested * (1 - multiplier))        as amount_principal_with_sign_invested,
                                    SUM(amount_carry_with_sign_invested * (1 - multiplier))            as amount_carry_with_sign_invested,
                                    
                                    -- fixed part below
                                    SUM(principal_with_sign_invested * (1 - multiplier) * trn_hist_fx / rep_hist_fx)        as principal_with_sign_invested, -- wrong name, should be fixed
                                    SUM(carry_with_sign_invested * (1 - multiplier) * trn_hist_fx / rep_hist_fx)            as carry_with_sign_invested, -- wrong name, should be fixed
                                    SUM(overheads_with_sign_invested * (1 - multiplier) * trn_hist_fx / rep_hist_fx)        as overheads_with_sign_invested, -- wrong name, should be fixed
                                    
                                    SUM(amount_principal_with_sign_invested * (1 - multiplier) * trn_hist_fx / rep_hist_fx)        as amount_principal_with_sign_invested_fixed,
                                    SUM(amount_carry_with_sign_invested * (1 - multiplier) * trn_hist_fx / rep_hist_fx)            as amount_carry_with_sign_invested_fixed,
                                    
                                    
                                    SUM(principal_with_sign_invested * (1 - multiplier) * trn_hist_fx / rep_hist_fx)        as principal_fixed_opened,
                                    SUM(carry_with_sign_invested * (1 - multiplier) * trn_hist_fx / rep_hist_fx)            as carry_fixed_opened,
                                    SUM(overheads_with_sign_invested * (1 - multiplier) * trn_hist_fx / rep_hist_fx)        as overheads_fixed_opened,
                                    
                                    SUM(principal_with_sign_invested * (multiplier) *trn_hist_fx / rep_hist_fx)             as principal_fixed_closed,
                                    SUM(carry_with_sign_invested * (multiplier) *trn_hist_fx / rep_hist_fx)                 as carry_fixed_closed,
                                    SUM(overheads_with_sign_invested * (multiplier) *trn_hist_fx / rep_hist_fx)             as overheads_fixed_closed,
        
                                    SUM(day_delta * position_size_with_sign * (1-multiplier))   as time_invested, 
                                    SUM(transaction_ytm * position_size_with_sign * (1-multiplier))   as ytm_at_cost
                                    
                                    
                                from 
                                    transactions_unioned_table tut
                                where accounting_date <= '{report_date}'
                                group by 
                                    {consolidation_columns} instrument_id, transaction_currency_id, settlement_currency_id
                            ) as tt_without_fx_rates
                            /*left join (
                                select 
                                    currency_id,
                            
                                    case
                                        when currency_id = {default_currency_id}
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
                                        when currency_id = {default_currency_id}
                                        then 1
                                        else fx_rate
                                    end as fx_rate
                                from 
                                    currencies_currencyhistory 
                                where 
                                    date = '{report_date}'
                            ) as stlch
                            on 
                                settlement_currency_id = stlch.currency_id */
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
                                
                                -- add modified_duration
                               (select
                                    ytm
                                from
                                    instruments_pricehistory iph
                                where
                                    date = '{report_date}'
                                    and iph.instrument_id=ii.id
                                    and iph.pricing_policy_id = {pricing_policy_id}
                                   ) as ytm,
                                   
                                -- add modified_duration
                               (select
                                    modified_duration
                                from
                                    instruments_pricehistory iph
                                where
                                    date = '{report_date}'
                                    and iph.instrument_id=ii.id
                                    and iph.pricing_policy_id = {pricing_policy_id}
                                   ) as modified_duration,
        
                               -- add current price
                               (select
                                    principal_price
                                from
                                    instruments_pricehistory iph
                                where
                                    date = '{report_date}'
                                    and iph.instrument_id=ii.id
                                    and iph.pricing_policy_id = {pricing_policy_id}
                                   ) as cur_price,
                                   
                               (select
                                    principal_price
                                from
                                    instruments_pricehistory iph
                                where
                                    date = '{bday_yesterday_of_report_date}'
                                    and iph.instrument_id=ii.id
                                    and iph.pricing_policy_id = {pricing_policy_id}
                                   ) as yesterday_price,   
                                
                                   
                               (select
                                    factor
                                from
                                    instruments_pricehistory iph
                                where
                                    date = '{report_date}'
                                    and iph.instrument_id=ii.id
                                    and iph.pricing_policy_id = {pricing_policy_id}
                                   ) as cur_factor,
                                (select
                                    ytm
                                from
                                    instruments_pricehistory iph
                                where
                                    date = '{report_date}'
                                    and iph.instrument_id=ii.id
                                    and iph.pricing_policy_id = {pricing_policy_id}
                                   ) as cur_ytm,
                                  -- add current accrued
                                (select
                                    accrued_price
                                from
                                    instruments_pricehistory iph
                                where
                                    date = '{report_date}'
                                    and iph.instrument_id=ii.id
                                    and iph.pricing_policy_id = {pricing_policy_id}
                                   ) as cur_accr_price
            
                            from 
                                instruments_instrument ii
                        ) as i
                        on 
                            instrument_id = i.id
                        left join instruments_instrumenttype as it
                        ON i.instrument_type_id = it.id
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
      
            currency_id,
            instrument_id,
            {consolidation_columns}

            co_directional_exposure_currency_id,
            pricing_currency_id,
            instrument_pricing_currency_fx_rate,
            instrument_accrued_currency_fx_rate,    
            instrument_principal_price,
            instrument_accrued_price, 
            instrument_factor,
            instrument_ytm,
            daily_price_change,
          
            position_size,
            nominal_position_size,
            
            position_return,
            position_return_loc,
            net_position_return,
            net_position_return_loc,
            
            position_return_fixed,
            position_return_fixed_loc,
            net_position_return_fixed,
            net_position_return_fixed_loc,
            
            net_cost_price,
            net_cost_price_loc,
            principal_cost_price_loc,
            
            gross_cost_price,
            gross_cost_price_loc,
            
            principal_invested,
            principal_invested_loc,
            
            amount_invested,
            amount_invested_loc,       
            
            principal_invested_fixed,
            principal_invested_fixed_loc,
            
            amount_invested_fixed,
            amount_invested_fixed_loc,        
                
            time_invested,
            
            ytm,
            modified_duration,
            ytm_at_cost,
            return_annually,
            return_annually_fixed,
            
            market_value,
            exposure,
            
            market_value_loc,
            exposure_loc,
   
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
            total_fixed_closed_loc,
            
            mismatch
            
        from (
            select 
            
                name,
                short_name,
                user_code,
                
                item_type,
                item_type_name,
          
                currency_id, 
                instrument_id,
                {consolidation_columns}
              
                (-1) as co_directional_exposure_currency_id,
                (-1) as pricing_currency_id,
                (0) as instrument_pricing_currency_fx_rate,
                (0) as instrument_accrued_currency_fx_rate,    
                (0) as instrument_principal_price,
                (0) as instrument_accrued_price, 
                (1) as instrument_factor,
                (0) as instrument_ytm,
                (0) as daily_price_change,

                position_size,
                (position_size) as nominal_position_size,
                
                (0) as position_return,
                (0) as position_return_loc,
                (0) as net_position_return,
                (0) as net_position_return_loc,
                
                (0) as position_return_fixed,
                (0) as position_return_fixed_loc,
                (0) as net_position_return_fixed,
                (0) as net_position_return_fixed_loc,
                
                (0) as net_cost_price,
                (0) as net_cost_price_loc,
                (0) as principal_cost_price_loc,
                
                (0) as gross_cost_price,
                (0) as gross_cost_price_loc,
                
                (0) as principal_invested,
                (0) as principal_invested_loc,
                
                (0) as amount_invested,
                (0) as amount_invested_loc,
                
                (0) as principal_invested_fixed,
                (0) as principal_invested_fixed_loc,
                
                (0) as amount_invested_fixed,
                (0) as amount_invested_fixed_loc,
                    
                (0) as time_invested,
                
                (0) as ytm,
                (0) as modified_duration,
                (0) as ytm_at_cost,
                (0) as return_annually,
                (0) as return_annually_fixed,
                
                (0) as market_value,
                (0) as exposure,
                
                (0) as market_value_loc,
                (0) as exposure_loc,
                
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
                (0) as total_fixed_closed_loc,
            
                (0) as mismatch
            
            from (
                select 
                    (notes) as name, 
                    (notes) as short_name,
                    (notes) as user_code,
                    
                    (3) as item_type,
                    ('FX Variations') as item_type_name,
                    
                    (-1) as currency_id,
                    (-1) as instrument_id,
                    {consolidation_columns}
                    
                    (0) as position_size,
                    (0) as nominal_position_size,
                    
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
                            where svfx.transaction_class_id in (8, 9, 12, 13)
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
      
            currency_id,
            instrument_id,
            {consolidation_columns}

            co_directional_exposure_currency_id,
            pricing_currency_id,
            instrument_pricing_currency_fx_rate,
            instrument_accrued_currency_fx_rate,    
            instrument_principal_price,
            instrument_accrued_price, 
            instrument_factor,
            instrument_ytm,
            daily_price_change,
          
            position_size,
            nominal_position_size,
            
            position_return,
            position_return_loc,
            net_position_return,
            net_position_return_loc,
            
            position_return_fixed,
            position_return_fixed_loc,
            net_position_return_fixed,
            net_position_return_fixed_loc,
            
            net_cost_price,
            net_cost_price_loc,
            principal_cost_price_loc,
            
            gross_cost_price,
            gross_cost_price_loc,
            
            principal_invested,
            principal_invested_loc,
            
            amount_invested,
            amount_invested_loc,   
            
            principal_invested_fixed,
            principal_invested_fixed_loc,
            
            amount_invested_fixed,
            amount_invested_fixed_loc,
                
            time_invested,
            
            ytm,
            modified_duration,
            ytm_at_cost,
            return_annually,
            return_annually_fixed,
            
            market_value,
            exposure,
            
            market_value_loc,
            exposure_loc,

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
            total_fixed_closed_loc,
            
            mismatch
            
        from (
            select 
                
                name,
                short_name,
                user_code,
                
                item_type,
                item_type_name,
          
                currency_id,
                instrument_id,
                {consolidation_columns}
                
                (-1) as co_directional_exposure_currency_id,
                (-1) as pricing_currency_id,
                (0) as instrument_pricing_currency_fx_rate,
                (0) as instrument_accrued_currency_fx_rate,    
                (0) as instrument_principal_price,
                (0) as instrument_accrued_price, 
                (1) as instrument_factor,
                (0) as instrument_ytm,
                (0) as daily_price_change,
              
                position_size,
                nominal_position_size,
                
                (0) as position_return,
                (0) as position_return_loc,
                (0) as net_position_return,
                (0) as net_position_return_loc,
                
                (0) as position_return_fixed,
                (0) as position_return_fixed_loc,
                (0) as net_position_return_fixed,
                (0) as net_position_return_fixed_loc,
            
                
                (0) as net_cost_price,
                (0) as net_cost_price_loc,
                (0) as principal_cost_price_loc,
                
                (0) as gross_cost_price,
                (0) as gross_cost_price_loc,
                
                (0) as principal_invested,
                (0) as principal_invested_loc,
                
                (0) as amount_invested,
                (0) as amount_invested_loc,
                
                (0) as principal_invested_fixed,
                (0) as principal_invested_fixed_loc,
                
                (0) as amount_invested_fixed,
                (0) as amount_invested_fixed_loc,
                    
                (0) as time_invested,
                
                (0) as ytm,
                (0) as modified_duration,
                (0) as ytm_at_cost,
                (0) as return_annually,
                (0) as return_annually_fixed,
                
                (0) as market_value,
                (0) as exposure,
                
                (0) as market_value_loc,
                (0) as exposure_loc,

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
                (0) as total_fixed_closed_loc,
            
                (0) as mismatch
        
            from (
                select 
                    (notes) as name, 
                    (notes) as short_name,
                    (notes) as user_code,
                    
                    (4) as item_type,
                    ('FX Trades') as item_type_name,
                    
                    (-1) as currency_id,
                    (-1) as instrument_id,
                    {consolidation_columns}
                    
        
                    (0) as position_size,
                    (0) as nominal_position_size,
                    
                    sum(principal_with_sign * stl_cur_fx / rep_cur_fx) as principal_opened,
                    sum(carry_with_sign * stl_cur_fx / rep_cur_fx)     as carry_opened,
                    sum(overheads_with_sign * stl_cur_fx / rep_cur_fx) as overheads_opened,

                    sum(principal_with_sign * stl_cur_fx / rep_cur_fx) as principal_fx_opened,
                    sum(carry_with_sign * stl_cur_fx / rep_cur_fx) as carry_fx_opened,
                    sum(overheads_with_sign * stl_cur_fx / rep_cur_fx) as overheads_fx_opened,
                     
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
            
         -- union with Transaction PL 
        union all
        
        select 
        
            name,
            short_name,
            user_code,
            
            item_type,
            item_type_name,
      
            currency_id,
            instrument_id,
            {consolidation_columns}
          
            co_directional_exposure_currency_id,
            pricing_currency_id,
            instrument_pricing_currency_fx_rate,
            instrument_accrued_currency_fx_rate,    
            instrument_principal_price,
            instrument_accrued_price, 
            instrument_factor,
            instrument_ytm,
            daily_price_change,

            position_size,
            nominal_position_size,
            
            position_return,
            position_return_loc,
            net_position_return,
            net_position_return_loc,
            
            position_return_fixed,
            position_return_fixed_loc,
            net_position_return_fixed,
            net_position_return_fixed_loc,
            
            net_cost_price,
            net_cost_price_loc,
            principal_cost_price_loc,
            
            gross_cost_price,
            gross_cost_price_loc,
            
            principal_invested,
            principal_invested_loc,
            
            amount_invested,
            amount_invested_loc,   
            
            principal_invested_fixed,
            principal_invested_fixed_loc,
            
            amount_invested_fixed,
            amount_invested_fixed_loc,
                
            time_invested,
            
            ytm,
            modified_duration,
            ytm_at_cost,
            return_annually,
            return_annually_fixed,
            
            market_value,
            exposure,
            
            market_value_loc,
            exposure_loc,
   
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
            total_fixed_closed_loc,
            
            mismatch
            
        from (
            select 
            
                name,
                short_name,
                user_code,
                
                item_type,
                item_type_name,
          
                currency_id,
                instrument_id,
                {consolidation_columns}

                (-1) as co_directional_exposure_currency_id,
                (-1) as pricing_currency_id,
                (0) as instrument_pricing_currency_fx_rate,
                (0) as instrument_accrued_currency_fx_rate,    
                (0) as instrument_principal_price,
                (0) as instrument_accrued_price, 
                (1) as instrument_factor,
                (0) as instrument_ytm,
                (0) as daily_price_change,
              
                position_size,
                nominal_position_size,
                
                (0) as position_return,
                (0) as position_return_loc,
                (0) as net_position_return,
                (0) as net_position_return_loc,
                
                (0) as position_return_fixed,
                (0) as position_return_fixed_loc,
                (0) as net_position_return_fixed,
                (0) as net_position_return_fixed_loc,
                
                (0) as net_cost_price,
                (0) as net_cost_price_loc,
                (0) as principal_cost_price_loc,
                
                (0) as gross_cost_price,
                (0) as gross_cost_price_loc,
                
                (0) as principal_invested,
                (0) as principal_invested_loc,
                
                (0) as amount_invested,
                (0) as amount_invested_loc,
                
                (0) as principal_invested_fixed,
                (0) as principal_invested_fixed_loc,
                
                (0) as amount_invested_fixed,
                (0) as amount_invested_fixed_loc,
                    
                (0) as time_invested,
                
                (0) as ytm,
                (0) as modified_duration,
                (0) as ytm_at_cost,
                (0) as return_annually,
                (0) as return_annually_fixed,
                
                (0) as market_value,
                (0) as exposure,
                
                (0) as market_value_loc,
                (0) as exposure_loc,
                
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
                (0) as total_fixed_closed_loc,
            
                (0) as mismatch
            
            from (
                select 
                    (notes) as name, 
                    (notes) as short_name,
                    (notes) as user_code,
                    
                    (5) as item_type,
                    ('Other') as item_type_name,
                    
                    (-1) as currency_id,
                    (-1) as instrument_id,
                    {consolidation_columns}
                    
        
                    (0) as position_size,
                    (0) as nominal_position_size,
                    
                    sum(principal_with_sign * stl_cur_fx / rep_cur_fx) as principal_opened,
                    sum(carry_with_sign * stl_cur_fx / rep_cur_fx)     as carry_opened,
                    sum(overheads_with_sign * stl_cur_fx / rep_cur_fx) as overheads_opened,

                    sum(principal_with_sign * stl_cur_fx / rep_cur_fx) as principal_fx_opened,
                    sum(principal_with_sign * stl_cur_fx / rep_cur_fx) as carry_fx_opened,
                    sum(principal_with_sign * stl_cur_fx / rep_cur_fx) as overheads_fx_opened,
                     
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
                    name, {consolidation_columns} instrument_id order by name
                ) as grouped_transaction_pl
            ) as pre_final_union_transaction_pl_calculations_level_0
        
         -- union with Mismatch 
        union all
        
        select 
        
            name,
            short_name,
            user_code,
            
            item_type,
            item_type_name,
      
            currency_id,
            instrument_id,
            {consolidation_columns}

            co_directional_exposure_currency_id,
            pricing_currency_id,
            instrument_pricing_currency_fx_rate,
            instrument_accrued_currency_fx_rate,    
            instrument_principal_price,
            instrument_accrued_price, 
            instrument_factor,
            instrument_ytm,
            daily_price_change,
          
            position_size,
            nominal_position_size,
            
            position_return,
            position_return_loc,
            net_position_return,
            net_position_return_loc,
            
            position_return_fixed,
            position_return_fixed_loc,
            net_position_return_fixed,
            net_position_return_fixed_loc,
            
            net_cost_price,
            net_cost_price_loc,
            principal_cost_price_loc,
            
            gross_cost_price,
            gross_cost_price_loc,
            
            principal_invested,
            principal_invested_loc,
            
            amount_invested,
            amount_invested_loc,   
            
            principal_invested_fixed,
            principal_invested_fixed_loc,
            
            amount_invested_fixed,
            amount_invested_fixed_loc,
                
            time_invested,
            
            ytm,
            modified_duration,
            ytm_at_cost,
            return_annually,
            return_annually_fixed,
            
            market_value,
            exposure,
            
            market_value_loc,
            exposure_loc,
   
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
            total_fixed_closed_loc,
            
            mismatch
            
        from (
            select 
            
                name,
                short_name,
                user_code,
                
                item_type,
                item_type_name,
          
                currency_id,
                instrument_id,
                {consolidation_columns}

                (-1) as co_directional_exposure_currency_id,
                (-1) as pricing_currency_id,
                (0) as instrument_pricing_currency_fx_rate,
                (0) as instrument_accrued_currency_fx_rate,    
                (0) as instrument_principal_price,
                (0) as instrument_accrued_price, 
                (1) as instrument_factor,
                (0) as instrument_ytm,
                (0) as daily_price_change,
              
                position_opened as position_size,
                (position_opened) as nominal_position_size, 
                
                (0) as position_return,
                (0) as position_return_loc,
                (0) as net_position_return,
                (0) as net_position_return_loc,
                
                (0) as position_return_fixed,
                (0) as position_return_fixed_loc,
                (0) as net_position_return_fixed,
                (0) as net_position_return_fixed_loc,
                
                (0) as net_cost_price,
                (0) as net_cost_price_loc,
                (0) as principal_cost_price_loc,
                
                (0) as gross_cost_price,
                (0) as gross_cost_price_loc,
                
                (0) as principal_invested,
                (0) as principal_invested_loc,
                
                (0) as amount_invested,
                (0) as amount_invested_loc,
                
                (0) as principal_invested_fixed,
                (0) as principal_invested_fixed_loc,
                
                (0) as amount_invested_fixed,
                (0) as amount_invested_fixed_loc,
                    
                (0) as time_invested,
                
                (0) as ytm,
                (0) as modified_duration,
                (0) as ytm_at_cost,
                (0) as return_annually,
                (0) as return_annually_fixed,
                
                (0) as market_value,
                (0) as exposure,
                
                (0) as market_value_loc,
                (0) as exposure_loc,

                
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
                (0) as  total_fixed_opened,
                
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
                (0) as total_fixed_closed_loc,
                
                (mismatch_closed+position_opened*coalesce((cur_price*price_multiplier*pricing_fx+cur_accrued*accrued_multiplier*accrued_fx),0))/reporting_fx as mismatch
            
            from (
                 select 
                    (ii.name) as name, 
                    (ii.short_name) as short_name,
                    (ii.user_code) as user_code,
                    
                    (6) as item_type,
                    ('Mismatch') as item_type_name,
                    
                    (-1) as currency_id,
                    (ii.id) as instrument_id,
                    {consolidation_columns}
                    
                    linked_instrument_id,
                    mismatch_closed,
                    position_opened,
                    
                    ii.price_multiplier,
                    ii.accrued_multiplier,
                    (select principal_price
                     from instruments_pricehistory iph
                     where iph.instrument_id = linked_instrument_id
                       and iph.date = '{report_date}'
                       and iph.pricing_policy_id = {pricing_policy_id}
                     ) as cur_price,
                    (select accrued_price
                     from instruments_pricehistory iph
                     where iph.instrument_id = linked_instrument_id
                       and iph.date = '{report_date}'
                       and iph.pricing_policy_id = {pricing_policy_id}
                     ) as cur_accrued,
    
                    case when
                    ii.pricing_currency_id={default_currency_id} 
                    then 1
                    else
                    (select fx_rate
                     from currencies_currencyhistory cch
                     where cch.currency_id = ii.pricing_currency_id
                       and cch.date = '{report_date}'
                       and cch.pricing_policy_id = {pricing_policy_id}
                    )
                    end                           as pricing_fx,
                    case when
                        ii.accrued_currency_id={default_currency_id} 
                    then 1
                    else
                    (select fx_rate
                     from currencies_currencyhistory cch
                     where cch.currency_id = ii.accrued_currency_id
                       and cch.date = '{report_date}'
                       and cch.pricing_policy_id = {pricing_policy_id}
                    )
                        end                          as accrued_fx,
                    case when
                    {report_currency_id}={default_currency_id}
                    then 1
                    else
                    (select fx_rate
                     from currencies_currencyhistory cch
                     where cch.currency_id = {report_currency_id} 
                       and cch.date = '{report_date}'
                       and cch.pricing_policy_id = {pricing_policy_id}
                    )
                    end                           as reporting_fx
        
        
                 from (
                          select 
                            'mismatch'                   as group_type_name,
                            linked_instrument_id,
                            {consolidation_columns}
                            sum(cash_consideration - principal_with_sign - carry_with_sign -
                                     overheads_with_sign)     as mismatch_closed,
                            sum(position_size_with_sign) as position_opened
        
                          from transactions_to_base_currency
        
        
        -- группировать по linked_instrument_id {consolidation_columns}
                          group by {consolidation_columns} linked_instrument_id -- add aggregation here --
                          having not abs(sum(
                                      cash_consideration - principal_with_sign - carry_with_sign - overheads_with_sign)) <
                                     0.01 -- add rounding (i.e. 0.01)
        
                      ) as mismatch_1_stage
                          left join
                      instruments_instrument ii on linked_instrument_id = ii.id
             ) as mismatch_2_stage
        ) as pre_final_union_transaction_pl_calculations_level_0
        
            """

        return query

    @staticmethod
    def get_query_for_first_date(instance):

        ecosystem_defaults = EcosystemDefault.objects.get(master_user=instance.master_user)

        report_fx_rate = get_report_fx_rate(instance, instance.pl_first_date)

        _l.debug('report_fx_rate %s' % report_fx_rate)

        transaction_filter_sql_string = get_transaction_filter_sql_string(instance)
        transaction_date_filter_for_initial_position_sql_string = get_transaction_date_filter_for_initial_position_sql_string(
            instance.report_date, has_where=bool(len(transaction_filter_sql_string)))
        fx_trades_and_fx_variations_filter_sql_string = get_fx_trades_and_fx_variations_transaction_filter_sql_string(
            instance)
        transactions_all_with_multipliers_where_expression = get_where_expression_for_position_consolidation(
            instance,
            prefix="tt_w_m.", prefix_second="t_o.")
        consolidation_columns = get_position_consolidation_for_select(instance)
        tt_consolidation_columns = get_position_consolidation_for_select(instance, prefix="tt.")
        tt_in1_consolidation_columns = get_position_consolidation_for_select(instance, prefix="tt_in1.")

        query = PLReportBuilderSql.get_source_query(cost_method=instance.cost_method.id)

        query = query.format(report_date=instance.pl_first_date,
                             master_user_id=instance.master_user.id,
                             default_currency_id=ecosystem_defaults.currency_id,
                             report_currency_id=instance.report_currency.id,
                             pricing_policy_id=instance.pricing_policy.id,
                             report_fx_rate=report_fx_rate,
                             transaction_filter_sql_string=transaction_filter_sql_string,
                             transaction_date_filter_for_initial_position_sql_string=transaction_date_filter_for_initial_position_sql_string,
                             fx_trades_and_fx_variations_filter_sql_string=fx_trades_and_fx_variations_filter_sql_string,
                             consolidation_columns=consolidation_columns,
                             tt_consolidation_columns=tt_consolidation_columns,
                             tt_in1_consolidation_columns=tt_in1_consolidation_columns,
                             transactions_all_with_multipliers_where_expression=transactions_all_with_multipliers_where_expression,
                             filter_query_for_balance_in_multipliers_table='',
                             bday_yesterday_of_report_date=instance.bday_yesterday_of_report_date
                             )

        return query

    @staticmethod
    def get_query_for_second_date(instance):

        report_fx_rate = get_report_fx_rate(instance, instance.report_date)
        ecosystem_defaults = EcosystemDefault.objects.get(master_user=instance.master_user)

        _l.debug('report_fx_rate %s' % report_fx_rate)

        transaction_filter_sql_string = get_transaction_filter_sql_string(instance)
        transaction_date_filter_for_initial_position_sql_string = get_transaction_date_filter_for_initial_position_sql_string(
            instance.report_date, has_where=bool(len(transaction_filter_sql_string)))
        fx_trades_and_fx_variations_filter_sql_string = get_fx_trades_and_fx_variations_transaction_filter_sql_string(
            instance)
        transactions_all_with_multipliers_where_expression = get_where_expression_for_position_consolidation(
            instance,
            prefix="tt_w_m.", prefix_second="t_o.")
        consolidation_columns = get_position_consolidation_for_select(instance)
        tt_consolidation_columns = get_position_consolidation_for_select(instance,
                                                                         prefix="tt.")

        tt_in1_consolidation_columns = get_position_consolidation_for_select(instance, prefix="tt_in1.")

        query = PLReportBuilderSql.get_source_query(cost_method=instance.cost_method.id)

        query = query.format(report_date=instance.report_date,
                             master_user_id=instance.master_user.id,
                             default_currency_id=ecosystem_defaults.currency_id,
                             report_currency_id=instance.report_currency.id,
                             pricing_policy_id=instance.pricing_policy.id,
                             report_fx_rate=report_fx_rate,
                             transaction_filter_sql_string=transaction_filter_sql_string,
                             transaction_date_filter_for_initial_position_sql_string=transaction_date_filter_for_initial_position_sql_string,
                             fx_trades_and_fx_variations_filter_sql_string=fx_trades_and_fx_variations_filter_sql_string,
                             consolidation_columns=consolidation_columns,
                             tt_consolidation_columns=tt_consolidation_columns,
                             tt_in1_consolidation_columns=tt_in1_consolidation_columns,
                             transactions_all_with_multipliers_where_expression=transactions_all_with_multipliers_where_expression,
                             filter_query_for_balance_in_multipliers_table='',
                             bday_yesterday_of_report_date=instance.bday_yesterday_of_report_date
                             )

        return query

    @finmars_task(name='reports.build_pl_report', bind=True)
    def build(self, task_id, *args, **kwargs):

        try:

            st = time.perf_counter()

            celery_task = CeleryTask.objects.get(id=task_id)

            report_settings = celery_task.options_object

            instance = ReportInstanceModel(**report_settings, master_user=celery_task.master_user)

            with connection.cursor() as cursor:

                query_1 = PLReportBuilderSql.get_query_for_first_date(instance)
                query_2 = PLReportBuilderSql.get_query_for_second_date(instance)

                ecosystem_defaults = EcosystemDefault.objects.get(master_user=celery_task.master_user)

                st = time.perf_counter()

                # q1 - pl first date
                # q2 - report date
                # language=PostgreSQL
                query = """select 
                                
                                (q2.name) as name,
                                (q2.short_name) as short_name,
                                (q2.user_code) as user_code,
                                (q2.item_type) as item_type,
                                
                                -- add optional account_position, strategy1 position etc
                                
                                (q2.instrument_id) as instrument_id,
                                (q2.currency_id) as currency_id,
                                (q2.co_directional_exposure_currency_id) as co_directional_exposure_currency_id,
                                
                                {final_consolidation_columns}
                                
                                (q2.position_size) as position_size, -- ?
                                (q2.nominal_position_size) as nominal_position_size,
                                
                                (q2.position_return) as position_return,
                                (q2.position_return_loc) as position_return_loc,
                                (q2.net_position_return) as net_position_return,
                                (q2.net_position_return_loc) as net_position_return_loc,
                                
                                (q2.position_return_fixed) as position_return_fixed,
                                (q2.position_return_fixed_loc) as position_return_fixed_loc,
                                (q2.net_position_return_fixed) as net_position_return_fixed,
                                (q2.net_position_return_fixed_loc) as net_position_return_fixed_loc,
                                
                                (q2.net_cost_price) as net_cost_price,
                                (q2.net_cost_price_loc) as net_cost_price_loc,
                                
                                (q2.gross_cost_price) as gross_cost_price,
                                (q2.gross_cost_price_loc) as gross_cost_price_loc,
                                
                                (q2.principal_invested) as principal_invested,
                                (q2.principal_invested_loc) as principal_invested_loc,
                                
                                (q2.amount_invested) as amount_invested,
                                (q2.amount_invested_loc) as amount_invested_loc,
                                
                                (q2.principal_invested_fixed) as principal_invested_fixed,
                                (q2.principal_invested_fixed_loc) as principal_invested_fixed_loc,
                                
                                (q2.amount_invested_fixed) as amount_invested_fixed,
                                (q2.amount_invested_fixed_loc) as amount_invested_fixed_loc,
                                    
                                (q2.time_invested) as time_invested,
                                
                                (q2.pricing_currency_id) as pricing_currency_id,
                                (q2.instrument_pricing_currency_fx_rate) as instrument_pricing_currency_fx_rate,
                                (q2.instrument_accrued_currency_fx_rate) as instrument_accrued_currency_fx_rate,
                                
                                (q2.instrument_principal_price) as instrument_principal_price,
                                (q2.instrument_accrued_price) as instrument_accrued_price,
                                (q2.instrument_factor) as instrument_factor,
                                (q2.instrument_ytm) as instrument_ytm,
                                (q2.daily_price_change) as daily_price_change,
                                
                                
                                (q2.ytm) as ytm,
                                (q2.modified_duration) as modified_duration,
                                (q2.ytm_at_cost) as ytm_at_cost,
                                (q2.return_annually) as return_annually,
                                (q2.return_annually_fixed) as return_annually_fixed,
                                
                                (q2.market_value) as market_value,
                                (q2.exposure) as exposure,
                                
                                (q2.market_value_loc) as market_value_loc,
                                (q2.exposure_loc) as exposure_loc,
                                
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
                                (q2.total_fixed_closed_loc - coalesce(q1.total_fixed_closed_loc, 0)) as total_fixed_closed_loc,
                                
                                (q2.mismatch - coalesce(q1.mismatch, 0)) as mismatch
                                    
                           from ({query_report_date}) as q2 
                           left join ({query_first_date}) as q1 on q1.name = q2.name and q1.item_type = q2.item_type and q1.instrument_id = q2.instrument_id {final_consolidation_where_filters}"""

                query = query.format(query_first_date=query_1,
                                     query_report_date=query_2,
                                     final_consolidation_columns=PLReportBuilderSql.get_final_consolidation_columns(
                                         instance),
                                     final_consolidation_where_filters=PLReportBuilderSql.get_final_consolidation_where_filters_columns(
                                         instance)
                                     )

                if settings.SERVER_TYPE == 'local':
                    with open(os.path.join(settings.BASE_DIR, 'query_result_before_execution_pl.txt'), 'w') as the_file:
                        the_file.write(query)

                cursor.execute(query)

                _l.debug('PL report query execute done: %s', "{:3.3f}".format(time.perf_counter() - st))

                query_str = str(cursor.query, 'utf-8')

                if settings.SERVER_TYPE == 'local':
                    with open(os.path.join(settings.BASE_DIR, '/tmp/query_result_pl.txt'), 'w') as the_file:
                        the_file.write(query_str)

                result_tmp_raw = dictfetchall(cursor)
                result_tmp = []
                result = []

                ITEM_TYPE_INSTRUMENT = 1
                ITEM_TYPE_FX_VARIATIONS = 3
                ITEM_TYPE_FX_TRADES = 4
                ITEM_TYPE_TRANSACTION_PL = 5
                ITEM_TYPE_MISMATCH = 6

                ITEM_GROUP_OPENED = 10
                ITEM_GROUP_FX_VARIATIONS = 11
                ITEM_GROUP_FX_TRADES = 12
                ITEM_GROUP_OTHER = 13
                ITEM_GROUP_MISMATCH = 14
                ITEM_GROUP_CLOSED = 15

                for item in result_tmp_raw:

                    item['position_size'] = round(item['position_size'], settings.ROUND_NDIGITS)
                    item['nominal_position_size'] = round(item['nominal_position_size'], settings.ROUND_NDIGITS)

                    if item['item_type'] == ITEM_TYPE_MISMATCH:
                        if item['position_size'] and item['total_opened']:
                            if item['instrument_id'] != ecosystem_defaults.instrument_id:
                                result_tmp.append(item)
                    else:
                        result_tmp.append(item)

                # _l.info("WTF??")

                # index = 0

                for item in result_tmp:

                    # if 'Pfizer' in item['user_code']:
                    #     _l.info("WTF??? item %s ______  %s" %  (index, item))
                    #     index = index + 1
                    # result_item_opened = item.copy()
                    result_item_opened = {}

                    result_item_opened['name'] = item['name']
                    result_item_opened['short_name'] = item['short_name']
                    result_item_opened['user_code'] = item['user_code']
                    result_item_opened['item_type'] = item['item_type']
                    result_item_opened['item_type_name'] = item['item_type_name']

                    result_item_opened['market_value'] = item['market_value']
                    result_item_opened['exposure'] = item['exposure']

                    result_item_opened['market_value_loc'] = item['market_value_loc']
                    result_item_opened['exposure_loc'] = item['exposure_loc']

                    result_item_opened['ytm'] = item['ytm']
                    result_item_opened['ytm_at_cost'] = item['ytm_at_cost']
                    result_item_opened['modified_duration'] = item['modified_duration']
                    result_item_opened['time_invested'] = item['time_invested']

                    result_item_opened['amount_invested'] = item['amount_invested']
                    result_item_opened['amount_invested_loc'] = item['amount_invested_loc']

                    result_item_opened['principal_invested'] = item['principal_invested']
                    result_item_opened['principal_invested_loc'] = item['principal_invested_loc']

                    result_item_opened['amount_invested_fixed'] = item['amount_invested_fixed']
                    result_item_opened['amount_invested_fixed_loc'] = item['amount_invested_fixed_loc']

                    result_item_opened['principal_invested_fixed'] = item['principal_invested_fixed']
                    result_item_opened['principal_invested_fixed_loc'] = item['principal_invested_fixed_loc']

                    result_item_opened['gross_cost_price'] = item['gross_cost_price']
                    result_item_opened['gross_cost_price_loc'] = item['gross_cost_price_loc']

                    result_item_opened['net_cost_price'] = item['net_cost_price']
                    result_item_opened['net_cost_price_loc'] = item['net_cost_price_loc']

                    result_item_opened['position_return'] = item['position_return']
                    result_item_opened['position_return_loc'] = item['position_return_loc']

                    result_item_opened['net_position_return'] = item['net_position_return']
                    result_item_opened['net_position_return_loc'] = item['net_position_return_loc']

                    result_item_opened['position_return_fixed'] = item['position_return_fixed']
                    result_item_opened['position_return_fixed_loc'] = item['position_return_fixed_loc']

                    result_item_opened['net_position_return_fixed'] = item['net_position_return_fixed']
                    result_item_opened['net_position_return_fixed_loc'] = item['net_position_return_fixed_loc']

                    result_item_opened['position_size'] = item['position_size']
                    result_item_opened['nominal_position_size'] = item['nominal_position_size']

                    result_item_opened['mismatch'] = item['mismatch']

                    result_item_opened['instrument_id'] = item['instrument_id']

                    if "portfolio_id" not in item:
                        result_item_opened['portfolio_id'] = ecosystem_defaults.portfolio_id
                    else:
                        result_item_opened['portfolio_id'] = item['portfolio_id']

                    if "account_position_id" not in item:
                        result_item_opened['account_position_id'] = ecosystem_defaults.account_id
                    else:
                        result_item_opened['account_position_id'] = item['account_position_id']

                    if "strategy1_position_id" not in item:
                        result_item_opened['strategy1_position_id'] = ecosystem_defaults.strategy1_id
                    else:
                        result_item_opened['strategy1_position_id'] = item['strategy1_position_id']

                    if "strategy2_position_id" not in item:
                        result_item_opened['strategy2_position_id'] = ecosystem_defaults.strategy2_id
                    else:
                        result_item_opened['strategy2_position_id'] = item['strategy2_position_id']

                    if "strategy3_position_id" not in item:
                        result_item_opened['strategy3_position_id'] = ecosystem_defaults.strategy3_id
                    else:
                        result_item_opened['strategy3_position_id'] = item['strategy3_position_id']

                    if 'allocation_pl_id' in item:

                        if item['allocation_pl_id'] == ecosystem_defaults.instrument_id:
                            result_item_opened['allocation_pl_id'] = ecosystem_defaults.instrument_id
                        elif item['allocation_pl_id'] == None:

                            if item['instrument_id'] == None:
                                result_item_opened['allocation_pl_id'] = ecosystem_defaults.instrument_id
                            else:
                                result_item_opened['allocation_pl_id'] = item['instrument_id']
                        else:
                            result_item_opened['allocation_pl_id'] = item['allocation_pl_id']

                        # Before 2023-10-10
                        # if item['allocation_pl_id'] == ecosystem_defaults.instrument_id or \
                        #         item['allocation_pl_id'] == None or item['allocation_pl_id'] == -1:
                        #
                        #     if item['instrument_id'] != None and item['instrument_id'] != -1:
                        #         pass
                        #         # TODO ASK Oleg if its right?
                        #         # result_item_opened['allocation_pl_id'] = item['instrument_id']
                        #         result_item_opened['allocation_pl_id'] = item['allocation_pl_id']
                        #     else:
                        #         # convert None to '-'
                        #         result_item_opened['allocation_pl_id'] = ecosystem_defaults.instrument_id
                        # else:
                        #     # TODO do not remove that, its really important
                        #     result_item_opened['allocation_pl_id'] = item['allocation_pl_id']
                    else:
                        result_item_opened['allocation_pl_id'] = ecosystem_defaults.instrument_id

                    if result_item_opened['item_type'] == ITEM_TYPE_INSTRUMENT:
                        result_item_opened["item_group"] = ITEM_GROUP_OPENED
                        result_item_opened["item_group_code"] = "OPENED"
                        result_item_opened["item_group_name"] = "Opened"

                    if result_item_opened['item_type'] == ITEM_TYPE_FX_VARIATIONS:
                        result_item_opened["item_group"] = ITEM_GROUP_FX_VARIATIONS
                        result_item_opened["item_group_code"] = "FX_VARIATIONS"
                        result_item_opened["item_group_name"] = "FX Variations"

                    if result_item_opened['item_type'] == ITEM_TYPE_FX_TRADES:
                        result_item_opened["item_group"] = ITEM_GROUP_FX_TRADES
                        result_item_opened["item_group_code"] = "FX_TRADES"
                        result_item_opened["item_group_name"] = "FX Trades"

                    if result_item_opened['item_type'] == ITEM_TYPE_TRANSACTION_PL:
                        result_item_opened["item_group"] = ITEM_GROUP_OTHER
                        result_item_opened["item_group_code"] = "OTHER"
                        result_item_opened["item_group_name"] = "Other"

                    if result_item_opened['item_type'] == ITEM_TYPE_MISMATCH:
                        result_item_opened["item_group"] = ITEM_GROUP_MISMATCH
                        result_item_opened["item_group_code"] = "MISMATCH"
                        result_item_opened["item_group_name"] = "Mismatch"

                    result_item_opened["exposure_currency_id"] = item["co_directional_exposure_currency_id"]
                    result_item_opened["pricing_currency_id"] = item["pricing_currency_id"]
                    result_item_opened["instrument_pricing_currency_fx_rate"] = item[
                        "instrument_pricing_currency_fx_rate"]
                    result_item_opened["instrument_accrued_currency_fx_rate"] = item[
                        "instrument_accrued_currency_fx_rate"]
                    result_item_opened["instrument_principal_price"] = item["instrument_principal_price"]
                    result_item_opened["instrument_accrued_price"] = item["instrument_accrued_price"]
                    result_item_opened["instrument_factor"] = item["instrument_factor"]
                    result_item_opened["instrument_ytm"] = item["instrument_ytm"]
                    result_item_opened["daily_price_change"] = item["daily_price_change"]

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

                    if result_item_opened['item_type'] == ITEM_TYPE_TRANSACTION_PL and has_opened_value:
                        result.append(result_item_opened)

                    if result_item_opened['item_type'] == ITEM_TYPE_MISMATCH:
                        result.append(result_item_opened)

                    if result_item_opened['item_type'] == ITEM_TYPE_INSTRUMENT and item["position_size"] != 0:
                        result.append(result_item_opened)

                    if result_item_opened['item_type'] == ITEM_TYPE_INSTRUMENT and has_closed_value:

                        _l.info("PL opened position has closed value")

                        # result_item_closed = item.copy()
                        # result_item_closed = copy.deepcopy(item)

                        result_item_closed = {}

                        # result_item_closed['item_type'] = ITEM_INSTRUMENT
                        # result_item_closed['item_type_code'] = "INSTR"
                        # result_item_closed['item_type_name'] = "Instrument"

                        result_item_closed['name'] = item['name']
                        result_item_closed['short_name'] = item['short_name']
                        result_item_closed['user_code'] = item['user_code']
                        result_item_closed['item_type'] = item['item_type']
                        result_item_closed['item_type_name'] = item['item_type_name']

                        result_item_closed['market_value'] = 0
                        result_item_closed['exposure'] = item['exposure']

                        result_item_closed['market_value_loc'] = 0
                        result_item_closed['exposure_loc'] = item['exposure_loc']

                        result_item_closed['ytm'] = item['ytm']
                        result_item_closed['ytm_at_cost'] = item['ytm_at_cost']
                        result_item_closed['modified_duration'] = item['modified_duration']
                        result_item_closed['time_invested'] = item['time_invested']

                        result_item_closed['amount_invested'] = item['amount_invested']
                        result_item_closed['amount_invested_loc'] = item['amount_invested_loc']

                        result_item_closed['principal_invested'] = item['principal_invested']
                        result_item_closed['principal_invested_loc'] = item['principal_invested_loc']

                        result_item_closed['amount_invested_fixed'] = item['amount_invested_fixed']
                        result_item_closed['amount_invested_fixed_loc'] = item['amount_invested_fixed_loc']

                        result_item_closed['principal_invested_fixed'] = item['principal_invested_fixed']
                        result_item_closed['principal_invested_fixed_loc'] = item['principal_invested_fixed_loc']

                        result_item_closed['gross_cost_price'] = item['gross_cost_price']
                        result_item_closed['gross_cost_price_loc'] = item['gross_cost_price_loc']

                        result_item_closed['net_cost_price'] = item['net_cost_price']
                        result_item_closed['net_cost_price_loc'] = item['net_cost_price_loc']

                        result_item_closed['position_return'] = item['position_return']
                        result_item_closed['position_return_loc'] = item['position_return_loc']

                        result_item_closed['net_position_return'] = item['net_position_return']
                        result_item_closed['net_position_return_loc'] = item['net_position_return_loc']

                        result_item_closed['position_return_fixed'] = item['position_return_fixed']
                        result_item_closed['position_return_fixed_loc'] = item['position_return_fixed_loc']

                        result_item_closed['net_position_return_fixed'] = item['net_position_return_fixed']
                        result_item_closed['net_position_return_fixed_loc'] = item['net_position_return_fixed_loc']

                        result_item_closed['position_size'] = item['position_size']
                        result_item_closed['mismatch'] = item['mismatch']

                        result_item_closed['exposure'] = item['exposure']
                        result_item_closed['ytm'] = item['ytm']
                        result_item_closed['ytm_at_cost'] = item['ytm_at_cost']
                        result_item_closed['modified_duration'] = item['modified_duration']
                        result_item_closed['time_invested'] = item['time_invested']

                        result_item_closed['amount_invested_fixed'] = item['amount_invested_fixed']
                        result_item_closed['amount_invested_fixed_loc'] = item['amount_invested_fixed_loc']

                        result_item_closed['principal_invested_fixed'] = item['principal_invested_fixed']
                        result_item_closed['principal_invested_fixed_loc'] = item['principal_invested_fixed_loc']

                        result_item_closed['gross_cost_price'] = item['gross_cost_price']
                        result_item_closed['gross_cost_price_loc'] = item['gross_cost_price_loc']

                        result_item_closed['net_cost_price'] = item['net_cost_price']
                        result_item_closed['net_cost_price_loc'] = item['net_cost_price_loc']

                        result_item_closed['position_size'] = item['position_size']
                        result_item_closed['mismatch'] = item['mismatch']

                        result_item_closed['instrument_id'] = item['instrument_id']

                        if "portfolio_id" not in item:
                            result_item_closed['portfolio_id'] = ecosystem_defaults.portfolio_id
                        else:
                            result_item_closed['portfolio_id'] = item['portfolio_id']

                        if "account_position_id" not in item:
                            result_item_closed['account_position_id'] = ecosystem_defaults.account_id
                        else:
                            result_item_closed['account_position_id'] = item['account_position_id']

                        if "strategy1_position_id" not in item:
                            result_item_closed['strategy1_position_id'] = ecosystem_defaults.strategy1_id
                        else:
                            result_item_closed['strategy1_position_id'] = item['strategy1_position_id']

                        if "strategy2_position_id" not in item:
                            result_item_closed['strategy2_position_id'] = ecosystem_defaults.strategy2_id
                        else:
                            result_item_closed['strategy2_position_id'] = item['strategy2_position_id']

                        if "strategy3_position_id" not in item:
                            result_item_closed['strategy3_position_id'] = ecosystem_defaults.strategy3_id
                        else:
                            result_item_closed['strategy3_position_id'] = item['strategy3_position_id']

                        # if "allocation_pl_id" not in item:
                        #     result_item_closed['allocation_pl_id'] = None
                        # else:
                        #     result_item_closed['allocation_pl_id'] = item['instrument_id']

                        # if 'allocation_pl_id' in item:
                        #
                        #     if item['allocation_pl_id'] == ecosystem_defaults.instrument_id or item['allocation_pl_id'] == None or item['allocation_pl_id'] == -1:
                        #
                        #         if item['instrument_id'] != None and item['instrument_id'] != -1:
                        #
                        #             result_item_closed['allocation_pl_id'] = item['instrument_id']
                        #
                        #         else:
                        #
                        #             # convert None to '-'
                        #             result_item_closed['allocation_pl_id'] = ecosystem_defaults.instrument_id
                        #
                        #     else:
                        #         # TODO do not remove that, its really important
                        #         result_item_closed['allocation_pl_id'] = item['allocation_pl_id']
                        # else:
                        #     result_item_closed['allocation_pl_id'] = ecosystem_defaults.instrument_id

                        if 'allocation_pl_id' in item:

                            if item['allocation_pl_id'] == ecosystem_defaults.instrument_id:
                                result_item_closed['allocation_pl_id'] = ecosystem_defaults.instrument_id
                            elif item['allocation_pl_id'] == None:

                                if item['instrument_id'] == None:
                                    result_item_closed['allocation_pl_id'] = ecosystem_defaults.instrument_id
                                else:
                                    result_item_closed['allocation_pl_id'] = item['instrument_id']
                            else:
                                result_item_closed['allocation_pl_id'] = item['allocation_pl_id']

                            # Before 2023-10-10
                            # if item['allocation_pl_id'] == ecosystem_defaults.instrument_id or \
                            #         item['allocation_pl_id'] == None or item['allocation_pl_id'] == -1:
                            #
                            #     if item['instrument_id'] != None and item['instrument_id'] != -1:
                            #         pass
                            #         # TODO ASK Oleg if its right?
                            #         # result_item_opened['allocation_pl_id'] = item['instrument_id']
                            #         result_item_opened['allocation_pl_id'] = item['allocation_pl_id']
                            #     else:
                            #         # convert None to '-'
                            #         result_item_opened['allocation_pl_id'] = ecosystem_defaults.instrument_id
                            # else:
                            #     # TODO do not remove that, its really important
                            #     result_item_opened['allocation_pl_id'] = item['allocation_pl_id']
                        else:
                            result_item_closed['allocation_pl_id'] = ecosystem_defaults.instrument_id

                        result_item_closed["item_group"] = ITEM_GROUP_CLOSED
                        result_item_closed["item_group_code"] = "CLOSED"
                        result_item_closed["item_group_name"] = "Closed"

                        result_item_closed["exposure_currency_id"] = item["co_directional_exposure_currency_id"]
                        result_item_closed["pricing_currency_id"] = item["pricing_currency_id"]
                        result_item_closed["instrument_pricing_currency_fx_rate"] = item[
                            "instrument_pricing_currency_fx_rate"]
                        result_item_closed["instrument_accrued_currency_fx_rate"] = item[
                            "instrument_accrued_currency_fx_rate"]
                        result_item_closed["instrument_principal_price"] = item["instrument_principal_price"]
                        result_item_closed["instrument_accrued_price"] = item["instrument_accrued_price"]
                        result_item_closed["instrument_factor"] = item["instrument_factor"]
                        result_item_closed["instrument_ytm"] = item["instrument_ytm"]
                        result_item_closed["daily_price_change"] = item["daily_price_change"]

                        result_item_closed["position_size"] = 0
                        result_item_closed["nominal_position_size"] = 0

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

                        result_item_closed["principal_loc"] = item["principal_closed_loc"]
                        result_item_closed["carry_loc"] = item["carry_closed_loc"]
                        result_item_closed["overheads_loc"] = item["overheads_closed_loc"]
                        result_item_closed["total_loc"] = item["total_closed_loc"]

                        result_item_closed["principal_fx_loc"] = item["principal_fx_closed_loc"]
                        result_item_closed["carry_fx_loc"] = item["carry_fx_closed_loc"]
                        result_item_closed["overheads_fx_loc"] = item["overheads_fx_closed_loc"]
                        result_item_closed["total_fx_loc"] = item["total_fx_closed_loc"]

                        result_item_closed["principal_fixed_loc"] = item["principal_fixed_closed_loc"]
                        result_item_closed["carry_fixed_loc"] = item["carry_fixed_closed_loc"]
                        result_item_closed["overheads_fixed_loc"] = item["overheads_fixed_closed_loc"]
                        result_item_closed["total_fixed_loc"] = item["total_fixed_closed_loc"]

                        result.append(result_item_closed)

                _l.debug('build position result %s ' % len(result))

                _l.info('single build done: %s' % (time.perf_counter() - st))

                celery_task.status = CeleryTask.STATUS_DONE
                celery_task.save()

                return result

        except Exception as e:
            celery_task.status = CeleryTask.STATUS_ERROR
            celery_task.save()
            raise e

    def build_sync(self, task_id):

        celery_task = CeleryTask.objects.filter(id=task_id).first()
        if not celery_task:
            _l.error(f"Invalid celery task_id={task_id}")
            return

        try:


            return self.build(task_id)


        except Exception as e:
            celery_task.status = CeleryTask.STATUS_ERROR
            celery_task.save()
            raise e

    def parallel_build(self):

        st = time.perf_counter()

        tasks = []

        if self.instance.portfolio_mode == Report.MODE_INDEPENDENT:

            for portfolio in self.instance.portfolios:
                task = CeleryTask.objects.create(
                    master_user=self.instance.master_user,
                    member=self.instance.member,
                    verbose_name="PL Report",
                    type="calculate_pl_report",
                    options_object={
                        "report_date": self.instance.report_date,
                        "pl_first_date": self.instance.pl_first_date,
                        "bday_yesterday_of_report_date": self.bday_yesterday_of_report_date,
                        "portfolios_ids": [portfolio.id],
                        "accounts_ids": [instance.id for instance in self.instance.accounts],
                        "strategies1_ids": [instance.id for instance in self.instance.strategies1],
                        "strategies2_ids": [instance.id for instance in self.instance.strategies2],
                        "strategies3_ids": [instance.id for instance in self.instance.strategies3],
                        "report_currency_id": self.instance.report_currency.id,
                        "pricing_policy_id": self.instance.pricing_policy.id,
                        "cost_method_id": self.instance.cost_method.id,
                        "show_balance_exposure_details": self.instance.show_balance_exposure_details,
                        "portfolio_mode": self.instance.portfolio_mode,
                        "account_mode": self.instance.account_mode,
                        "strategy1_mode": self.instance.strategy1_mode,
                        "strategy2_mode": self.instance.strategy2_mode,
                        "strategy3_mode": self.instance.strategy3_mode,
                        "allocation_mode": self.instance.allocation_mode
                    }
                )

                tasks.append(task)

        else:

            task = CeleryTask.objects.create(
                master_user=self.instance.master_user,
                member=self.instance.member,
                verbose_name="PL Report",
                type="calculate_pl_report",
                options_object={
                    "report_date": self.instance.report_date,
                    "pl_first_date": self.instance.pl_first_date,
                    "bday_yesterday_of_report_date": self.bday_yesterday_of_report_date,
                    "portfolios_ids": [instance.id for instance in self.instance.portfolios],
                    "accounts_ids": [instance.id for instance in self.instance.accounts],
                    "strategies1_ids": [instance.id for instance in self.instance.strategies1],
                    "strategies2_ids": [instance.id for instance in self.instance.strategies2],
                    "strategies3_ids": [instance.id for instance in self.instance.strategies3],
                    "report_currency_id": self.instance.report_currency.id,
                    "pricing_policy_id": self.instance.pricing_policy.id,
                    "cost_method_id": self.instance.cost_method.id,
                    "show_balance_exposure_details": self.instance.show_balance_exposure_details,
                    "portfolio_mode": self.instance.portfolio_mode,
                    "account_mode": self.instance.account_mode,
                    "strategy1_mode": self.instance.strategy1_mode,
                    "strategy2_mode": self.instance.strategy2_mode,
                    "strategy3_mode": self.instance.strategy3_mode,
                    "allocation_mode": self.instance.allocation_mode
                }
            )

            tasks.append(task)

        _l.info("Going to run %s tasks" % len(tasks))

        # Run the group of tasks
        job = group(self.build.s(task_id=task.id, context={
            "realm_code": self.instance.master_user.realm_code,
            "space_code": self.instance.master_user.space_code
        }) for task in tasks)

        group_result = job.apply_async()
        # Wait for all tasks to finish and get their results
        group_result.join()

        # Retrieve results
        all_dicts = []
        for result in group_result.results:
            # Each result is an AsyncResult instance.
            # You can get the result of the task with its .result property.
            all_dicts.extend(result.result)

        for task in tasks:
            # refresh the task instance to get the latest status from the database
            task.refresh_from_db()

            if task.status != CeleryTask.STATUS_ERROR:
                task.delete()

        # 'all_dicts' is now a list of all dicts returned by the tasks
        self.instance.items = all_dicts

        _l.info('parallel_build done: %s',
                "{:3.3f}".format(time.perf_counter() - st))

    def build_pl_sync(self):
        st = time.perf_counter()

        self.instance.items = []

        self.serial_build()

        self.instance.execution_time = float("{:3.3f}".format(time.perf_counter() - st))

        _l.debug('items total %s' % len(self.instance.items))

        relation_prefetch_st = time.perf_counter()

        if not self.instance.only_numbers:
            self.add_data_items()

        self.instance.relation_prefetch_time = float("{:3.3f}".format(time.perf_counter() - relation_prefetch_st))

        _l.debug('build_st done: %s' % self.instance.execution_time)

        return self.instance

    def serial_build(self):

        st = time.perf_counter()

        self.instance.bday_yesterday_of_report_date = get_last_business_day(self.instance.report_date - timedelta(days=1), to_string=True)

        task = CeleryTask.objects.create(
            master_user=self.instance.master_user,
            member=self.instance.member,
            verbose_name="PL Report",
            type="calculate_pl_report",
            options_object={
                "report_date": self.instance.report_date,
                "pl_first_date": self.instance.pl_first_date,
                "bday_yesterday_of_report_date": self.instance.bday_yesterday_of_report_date,
                "portfolios_ids": [instance.id for instance in self.instance.portfolios],
                "accounts_ids": [instance.id for instance in self.instance.accounts],
                "strategies1_ids": [instance.id for instance in self.instance.strategies1],
                "strategies2_ids": [instance.id for instance in self.instance.strategies2],
                "strategies3_ids": [instance.id for instance in self.instance.strategies3],
                "report_currency_id": self.instance.report_currency.id,
                "pricing_policy_id": self.instance.pricing_policy.id,
                "cost_method_id": self.instance.cost_method.id,
                "show_balance_exposure_details": self.instance.show_balance_exposure_details,
                "portfolio_mode": self.instance.portfolio_mode,
                "account_mode": self.instance.account_mode,
                "strategy1_mode": self.instance.strategy1_mode,
                "strategy2_mode": self.instance.strategy2_mode,
                "strategy3_mode": self.instance.strategy3_mode,
                "allocation_mode": self.instance.allocation_mode
            }
        )

        result = self.build_sync(task.id)

        # 'all_dicts' is now a list of all dicts returned by the tasks
        self.instance.items = result

        _l.info('parallel_build done: %s',
                "{:3.3f}".format(time.perf_counter() - st))

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
            "country",
            "owner"
            # 'price_download_scheme',
            # 'price_download_scheme__provider',
        ).prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).filter(master_user=self.instance.master_user) \
            .filter(id__in=ids)

    def add_data_items_instrument_types(self, instruments):

        ids = []

        for instrument in instruments:
            ids.append(instrument.instrument_type_id)

        self.instance.item_instrument_types = InstrumentType.objects.select_related("owner").prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).filter(master_user=self.instance.master_user) \
            .filter(id__in=ids)

    def add_data_items_countries(self, instruments):
        ids = []

        for instrument in instruments:
            ids.append(instrument.country_id)

        self.instance.item_countries = (
            Country.objects
            .all()
        )

    def add_data_items_portfolios(self, ids):

        self.instance.item_portfolios = Portfolio.objects.select_related("owner").prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).defer('responsibles', 'counterparties', 'transaction_types', 'accounts') \
            .filter(master_user=self.instance.master_user) \
            .filter(
            id__in=ids)

    def add_data_items_accounts(self, ids):

        self.instance.item_accounts = Account.objects.select_related('type', "owner").prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).filter(master_user=self.instance.master_user).filter(id__in=ids)

    def add_data_items_account_types(self, accounts):

        ids = []

        for account in accounts:
            ids.append(account.type_id)

        self.instance.item_account_types = AccountType.objects.select_related("owner").prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).filter(master_user=self.instance.master_user) \
            .filter(id__in=ids)

    def add_data_items_currencies(self, ids):

        self.instance.item_currencies = Currency.objects.select_related("country", "owner").prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).filter(master_user=self.instance.master_user).filter(id__in=ids)

    def add_data_items_strategies1(self, ids):
        self.instance.item_strategies1 = Strategy1.objects.select_related("owner").prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).filter(master_user=self.instance.master_user).filter(id__in=ids)

    def add_data_items_strategies2(self, ids):
        self.instance.item_strategies2 = Strategy2.objects.select_related("owner").prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).filter(master_user=self.instance.master_user).filter(id__in=ids)

    def add_data_items_strategies3(self, ids):
        self.instance.item_strategies3 = Strategy3.objects.select_related("owner").prefetch_related(
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

        strategies1_ids = []
        strategies2_ids = []
        strategies3_ids = []

        for item in self.instance.items:

            if 'portfolio_id' in item and item['portfolio_id'] != '-':
                portfolio_ids.append(item['portfolio_id'])

            if 'instrument_id' in item:
                instrument_ids.append(item['instrument_id'])
                try:
                    instrument_ids.append(item['allocation_pl_id'])
                except Exception as e:
                    _l.info('no allocation_pl_id %s' % item)

            if 'account_position_id' in item and item['account_position_id'] != '-':
                account_ids.append(item['account_position_id'])
            if 'account_cash_id' in item and item['account_cash_id'] != '-':
                account_ids.append(item['account_cash_id'])

            if 'currency_id' in item:
                currencies_ids.append(item['currency_id'])
            if 'pricing_currency_id' in item:
                currencies_ids.append(item['pricing_currency_id'])

            if 'strategy1_position_id' in item:
                strategies1_ids.append(item['strategy1_position_id'])

            if 'strategy2_position_id' in item:
                strategies2_ids.append(item['strategy2_position_id'])

            if 'strategy3_position_id' in item:
                strategies3_ids.append(item['strategy3_position_id'])

            if 'strategy1_cash_id' in item:
                strategies1_ids.append(item['strategy1_cash_id'])

            if 'strategy2_cash_id' in item:
                strategies2_ids.append(item['strategy2_cash_id'])

            if 'strategy3_cash_id' in item:
                strategies3_ids.append(item['strategy3_cash_id'])

        _l.debug('len instrument_ids %s' % len(instrument_ids))

        self.add_data_items_instruments(instrument_ids)
        self.add_data_items_portfolios(portfolio_ids)
        self.add_data_items_accounts(account_ids)

        self.add_data_items_currencies(currencies_ids)
        self.add_data_items_strategies1(strategies1_ids)
        self.add_data_items_strategies2(strategies2_ids)
        self.add_data_items_strategies3(strategies3_ids)

        self.add_data_items_instrument_types(self.instance.item_instruments)
        self.add_data_items_countries(self.instance.item_instruments)
        self.add_data_items_account_types(self.instance.item_accounts)

        self.instance.custom_fields = PLReportCustomField.objects.filter(master_user=self.instance.master_user)

        _l.debug('_refresh_with_perms_optimized item relations done: %s',
                 "{:3.3f}".format(time.perf_counter() - item_relations_st))
