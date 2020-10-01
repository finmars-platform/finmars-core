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

        self.create_view_for_transactions()

        if self.instance.cost_method.id == CostMethod.FIFO:
            self.build_positions_fifo()

        if self.instance.cost_method.id == CostMethod.AVCO:
            self.build_positions_avco()

        # self.build_cash()

        _l.info('items total %s' % len(self.instance.items))

        _l.info('build_st done: %s', "{:3.3f}".format(time.perf_counter() - st))

        self.add_data_items()

        return self.instance

    def get_position_consolidation_for_select(self,prefix=''):

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

    def create_view_for_transactions(self):

        with connection.cursor() as cursor:

            query = """
                CREATE or REPLACE VIEW pl_transactions_with_ttype AS
                    SELECT
                           id,
                           master_user_id,
                           transaction_class_id,
                           
                           transaction_date,
                           accounting_date,
                           
                           position_size_with_sign,
                           principal_with_sign,
                           carry_with_sign,
                           overheads_with_sign,
                           instrument_id,
                           portfolio_id,
                           account_position_id,
                           account_cash_id,
                           strategy1_position_id,
                           strategy1_cash_id,
                           strategy2_position_id,
                           strategy2_cash_id,
                           strategy3_position_id,
                           strategy3_cash_id,
                           
                           transaction_currency_id,
                           settlement_currency_id,
                           
                           reference_fx_rate,
                           
                           case
                             when position_size_with_sign < 0
                               then 0
                             else 1
                             end as ttype
                    FROM transactions_transaction
                    WHERE transaction_class_id not in (6)
                    
                    UNION
                    
                    select
                      id,
                      master_user_id,
                      (1) as transaction_class_id,
                      
                      transaction_date,
                      accounting_date,
                      
                      position_size_with_sign,
                      (-principal_with_sign) as principal_with_sign,
                      (-carry_with_sign) as carry_with_sign,
                      (-overheads_with_sign) as overheads_with_sign,
                      instrument_id,
                      portfolio_id,
                      account_cash_id as account_position_id,
                      account_cash_id,
                      strategy1_cash_id as strategy1_position_id,
                      strategy1_cash_id,
                      strategy2_cash_id as strategy2_position_id,
                      strategy2_cash_id,
                      strategy3_cash_id as strategy3_position_id,
                      strategy3_cash_id,
                      
                      transaction_currency_id,
                      settlement_currency_id,
                      
                      reference_fx_rate,
                      
                      case
                        when position_size_with_sign < 0
                          then 0
                        else 1
                        end as ttype
                    from transactions_transaction
                    WHERE transaction_class_id in (6)
                    
                    UNION
                    
                    select
                      id,
                      master_user_id,
                      (2) as transaction_class_id,
                      
                      transaction_date,
                      accounting_date,
                      
                      (-position_size_with_sign) as position_size_with_sign,
                      principal_with_sign,
                      carry_with_sign,
                      overheads_with_sign,
                      instrument_id,
                      portfolio_id,
                      account_position_id,
                      account_position_id as account_cash_id,
                      strategy1_position_id,
                      strategy1_position_id as strategy1_cash_id,
                      strategy2_position_id,
                      strategy2_position_id as strategy2_cash_id,
                      strategy3_position_id,
                      strategy3_position_id as strategy3_cash_id,
                      
                      transaction_currency_id,
                      settlement_currency_id,
                      
                      reference_fx_rate,
                      
                      case
                        when (-position_size_with_sign) < 0 
                          then 0
                        else 1
                        end as ttype
                    from transactions_transaction
                    WHERE transaction_class_id in (6);            
            """

            cursor.execute(query, [self.instance.report_date,  self.instance.master_user.id])

    def build_positions_fifo(self):

        _l.info("build positions fifo ")

        report_fx_rate = 1

        try:
            item = CurrencyHistory.objects.get(currency_id=self.instance.report_currency.id, date=self.instance.report_date)
            report_fx_rate = item.fx_rate
        except CurrencyHistory.DoesNotExist:
            report_fx_rate = 1

        report_fx_rate = str(report_fx_rate)

        _l.info('report_fx_rate %s' % report_fx_rate)

        portfolio_filter_string = ''
        portfolio_filter_list = []

        if len(self.instance.portfolios):
            for portfolio in self.instance.portfolios:
                portfolio_filter_list.append(str(portfolio.id))
        else:
            for portfolio in Portfolio.objects.filter(master_user=self.instance.master_user):
                portfolio_filter_list.append(str(portfolio.id))

        portfolio_filter_string = ', '.join(portfolio_filter_list)

        _l.info('portfolio_filter_string %s' % portfolio_filter_string)

        with connection.cursor() as cursor:

            # language=PostgreSQL
            query = """
        with 
            pl_transactions_with_ttype_filtered as (
                select * from pl_transactions_with_ttype
                where portfolio_id in ({portfolio_filter_string})
            ),
        
            transactions_ordered as (
                select 
                   row_number() 
                   over (partition by {tt_consolidation_columns} tt.instrument_id order by ttype,tt.accounting_date) as rn,
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
                            transaction_class_id in (1,2) and 
                            master_user_id='{master_user_id}'::int and 
                            accounting_date <= '{report_date}') as tt
                             left join
                           (select 
                                    instrument_id, 
                                    {consolidation_columns} 
                                    coalesce(abs(sum(position_size_with_sign)), 0) as sell_positions_total_size
                            from pl_transactions_with_ttype_filtered 
                            where 
                                transaction_class_id in (1,2) and 
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
                                transaction_class_id in (1,2) and 
                                master_user_id= '{master_user_id}' and 
                                accounting_date <= '{report_date}' and 
                                position_size_with_sign > 0
                            group by 
                                {consolidation_columns} 
                                instrument_id) as buy_tr 
                            using ({consolidation_columns} instrument_id)
                     ),
        
            transactions_with_multipliers as (
               select rn,
               accounting_date,
               transaction_class_id,
               
               {consolidation_columns}
               instrument_id,
               position_size_with_sign,
               (principal_with_sign * reference_fx_rate) as principal_with_sign_invested,
               (carry_with_sign * reference_fx_rate) as carry_with_sign_invested,
               (overheads_with_sign * reference_fx_rate) as overheads_with_sign_invested,
               
               (principal_with_sign) as principal_with_sign,
               (carry_with_sign) as carry_with_sign,
               (overheads_with_sign) as overheads_with_sign,
               
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
        
        from (select rn,
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
          )
    
        --- main query
        select 
            *,
            (total * cross_rate)                as total_loc,
            (principal * cross_rate)            as principal_loc,
            (carry * cross_rate)                as carry_loc,
            (overheads  * cross_rate)           as overheads_loc,
            
            
            (total_closed * cross_rate)         as total_closed_loc,
            (total_opened * cross_rate)         as total_opened_loc
         
        from ( 
            select 
                *,
                (principal_opened + carry_opened + overheads_opened) as total_opened,
            
                -- loc start --
            
                (principal_opened + carry_opened + overheads_opened + principal_closed + carry_closed + overheads_closed) as total,
                (principal_opened + principal_closed)               as principal,
                (carry_opened + carry_closed)                       as carry,
                (overheads_opened + overheads_closed)               as overheads,
            
                (principal_closed  * cross_rate)                    as principal_closed_loc,
                (carry_closed  * cross_rate)                        as carry_closed_loc,
                (overheads_closed  * cross_rate)                    as overheads_closed_loc,
                
                (principal_opened  * cross_rate)                    as principal_opened_loc,
                (carry_opened  * cross_rate)                        as carry_opened_loc,
                (overheads_opened  * cross_rate)                    as overheads_opened_loc,
                
                -- loc end -- 

                case
                    when principal_opened != 0
                    then ((principal_opened + carry_opened) / -principal_opened)
                    else 0
                end as position_return,
                
                case
                    when principal_opened != 0
                    then ((principal_opened + carry_opened + overheads_opened) / -principal_opened)
                    else 0
                end as net_position_return
        
            from (
                select 
                    {consolidation_columns}
                    instrument_id,
            
                    i.name,
                    i.short_name,
                    i.user_code,
                    i.pricing_currency_id,
                    i.price_multiplier,
                    i.accrued_multiplier,
                    i.accrual_size,
            
                    iph.principal_price,
                    
                    ipch.fx_rate,
                    
                    position_size,
                    position_size_opened,
                    
                    (principal_closed + carry_closed + overheads_closed) as total_closed,
                    principal_closed,
                    carry_closed,
                    overheads_closed,
    
                    -- total opened calculated above
                    (position_size_opened * coalesce(iph.principal_price, 0) * i.price_multiplier * ipch.fx_rate / {report_fx_rate} + principal_opened) as principal_opened,
                    -- possible require join for accrued currency fx rate
                    (position_size_opened * coalesce(iph.accrued_price, 0) * i.accrued_multiplier * ipch.fx_rate / {report_fx_rate} + carry_opened) as carry_opened,
                    overheads_opened,
            
                    case
                        when position_size_opened > 0
                        then ((principal_opened + overheads_opened) / position_size_opened)
                        else 0
                    end as net_cost_price,
                
                    case
                        when position_size_opened > 0
                        then ((principal_opened + overheads_opened) / position_size_opened * {report_fx_rate} / ipch.fx_rate)
                        else 0
                    end as net_cost_price_loc,
            
                    case
                        when position_size_opened > 0
                        then time_invested_sum / position_size_opened / 365
                        else 0
                    end as time_invested,
                
                    -- used in market value calcualtions    
                    (position_size_opened * i.price_multiplier * iph.principal_price) as instr_principal,
                    -- used in market value calcualtions    
                    (position_size_opened * i.price_multiplier * iph.principal_price * ipch.fx_rate / {report_fx_rate}) as instr_principal_res,
                    
                    (position_size_opened * i.accrued_multiplier * iph.accrued_price) as instr_accrued,
                    (position_size_opened * i.accrued_multiplier * iph.accrued_price * ipch.fx_rate / {report_fx_rate}) as instr_accrued_res,
    
                    ({report_fx_rate} / ipch.fx_rate) as cross_rate,

                    (principal_with_sign_invested / ipch.fx_rate ) as principal_with_sign_invested,
                    (carry_with_sign_invested / ipch.fx_rate) as carry_with_sign_invested,
                    (overheads_with_sign_invested / ipch.fx_rate) as overheads_with_sign_invested,
            
                    (i.accrual_size * i.accrued_multiplier * ipch.fx_rate / iph.principal_price * i.price_multiplier * ipch.fx_rate) as ytm
            
                from (
                    select 
                        {consolidation_columns}
                        instrument_id,
        
                        SUM(position_size)                                                      as position_size,
                        SUM(position_size_opened)                                               as  position_size_opened,
                        
                        SUM(principal * stlch.fx_rate / {report_fx_rate}::int)                  as principal,
                        SUM(carry_closed * stlch.fx_rate / {report_fx_rate}::int)               as carry,
                        SUM(overheads * stlch.fx_rate / {report_fx_rate}::int)                  as overheads,
                           
                        
                        SUM(principal_closed * stlch.fx_rate / {report_fx_rate}::int)           as principal_closed,
                        SUM(carry_closed * stlch.fx_rate / {report_fx_rate}::int)               as carry_closed,
                        SUM(overheads_closed * stlch.fx_rate / {report_fx_rate}::int)           as overheads_closed,
                           
                        SUM(principal_opened * stlch.fx_rate / {report_fx_rate}::int)           as principal_opened,
                        SUM(carry_opened * stlch.fx_rate / {report_fx_rate}::int)               as carry_opened,
                        SUM(overheads_opened * stlch.fx_rate / {report_fx_rate}::int)           as overheads_opened,
                        
                        SUM(time_invested)                                                      as time_invested_sum,
                        
                        SUM(principal_with_sign_invested * stlch.fx_rate * trnch.fx_rate )      as principal_with_sign_invested,
                        SUM(carry_with_sign_invested * stlch.fx_rate * trnch.fx_rate )          as carry_with_sign_invested,
                        SUM(overheads_with_sign_invested * stlch.fx_rate * trnch.fx_rate )      as overheads_with_sign_invested

                    from (
                        select 
                            instrument_id,
                            {consolidation_columns}
                            transaction_currency_id,
                            settlement_currency_id,
                   
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
                            
                            SUM(day_delta * position_size_with_sign * (1-multiplier))   as time_invested 
                        from 
                            transactions_with_multipliers
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
                            currencies_currencyhistory 
                        where 
                            date = '{report_date}'
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
                        desc limit 1) as accrual_size
    
                    from 
                        instruments_instrument ii
                ) as i
                on 
                    instrument_id = i.id
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
                ) as ipch
                on 
                    i.pricing_currency_id = ipch.currency_id
                left join (
                    select 
                        (instrument_id) as iid,
                        principal_price,
                        accrued_price
                    from 
                        instruments_pricehistory 
                    where 
                        date = '{report_date}'
                ) as iph
                on 
                    i.id = iph.iid   
            ) as partially_calculated_columns
        ) as loc_calculated_columns
            """

            query = query.format(report_date=self.instance.report_date,
                                 master_user_id=self.instance.master_user.id,
                                 default_currency_id=self.ecosystem_defaults.currency_id,
                                 report_fx_rate=report_fx_rate,
                                 portfolio_filter_string=portfolio_filter_string,
                                 consolidation_columns=self.get_position_consolidation_for_select(),
                                 tt_consolidation_columns=self.get_position_consolidation_for_select(prefix="tt.")
                                 )



            cursor.execute(query)

            query_str = str(cursor.query, 'utf-8')

            _l.info(query_str)


            result_tmp = dictfetchall(cursor)
            result = []

            # _l.info('result %s' % tmp_result)

            ITEM_INSTRUMENT = 1

            for item in result_tmp:

                result_item_opened = item.copy()

                result_item_opened['item_type'] = ITEM_INSTRUMENT
                result_item_opened['item_type_code'] = "INSTR"
                result_item_opened['item_type_name'] = "Instrument"

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

                result_item_opened["item_group"] = 10
                result_item_opened["item_group_code"] = "OPENED"
                result_item_opened["item_group_name"] = "Opened"

                result_item_opened["position_size"] = item["position_size_opened"]
                result_item_opened["time_invested"] = item["time_invested"]
                result_item_opened["position_return"] = item["position_return"]

                result_item_opened["total"] = item["total_opened"]
                result_item_opened["principal"] = item["principal_opened"]
                result_item_opened["carry"] = item["carry_opened"]
                result_item_opened["overheads"] = item["overheads_opened"]

                result_item_opened["total_loc"] = item["total_opened_loc"]
                result_item_opened["principal_loc"] = item["principal_opened_loc"]
                result_item_opened["carry_loc"] = item["carry_opened_loc"]
                result_item_opened["overheads_loc"] = item["overheads_opened_loc"]



                result.append(result_item_opened)

                #  CLOSED POSITIONS BELOW

                result_item_closed = item.copy()

                result_item_closed['item_type'] = ITEM_INSTRUMENT
                result_item_closed['item_type_code'] = "INSTR"
                result_item_closed['item_type_name'] = "Instrument"

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
                result_item_opened["time_invested"] = item["time_invested"]
                result_item_opened["position_return"] = item["position_return"]
                result_item_opened["net_position_return"] = item["net_position_return"]
                result_item_opened["ytm"] = item["ytm"]

                result_item_closed["total"] = item["total_closed"]
                result_item_closed["principal"] = item["principal_closed"]
                result_item_closed["carry"] = item["carry_closed"]
                result_item_closed["overheads"] = item["overheads_closed"]

                result_item_closed["total_loc"] = item["total_closed_loc"]
                result_item_closed["principal_loc"] = item["principal_closed_loc"]
                result_item_closed["carry_loc"] = item["carry_closed_loc"]
                result_item_closed["overheads_loc"] = item["overheads_closed_loc"]

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
                  
                    union
                    
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

    def build_cash(self):

        _l.info("build cash")

        with connection.cursor() as cursor:

            consolidated_select_columns = self.get_cash_consolidation_for_select()

            query = """
                CREATE or REPLACE VIEW balance_cash_consolidation_matrix AS
                SELECT
                  portfolio_id,
                  account_cash_id,
                  strategy1_cash_id,
                  strategy2_cash_id,
                  strategy3_cash_id,
                  settlement_currency_id,
                  SUM(cash_consideration) as position_size
                FROM transactions_transaction
                WHERE transaction_date <= %s AND master_user_id = %s
                GROUP BY
                  portfolio_id,
                  account_cash_id,
                  strategy1_cash_id,
                  strategy2_cash_id,
                  strategy3_cash_id,
                  settlement_currency_id;
            """

            cursor.execute(query, [self.instance.report_date, self.instance.master_user.id])

            query = """
                SELECT 
                    t.*, 
                    c.name,
                    c.short_name,
                    c.user_code,
                    
                    (t.position_size * cch.fx_rate) as market_value
                FROM 
                    (SELECT
                      """ + consolidated_select_columns + """
                      settlement_currency_id,
                      SUM(position_size) as position_size
                    FROM balance_cash_consolidation_matrix
                    GROUP BY
                      """ + consolidated_select_columns + """
                      settlement_currency_id) AS t
                LEFT JOIN currencies_currency as c
                ON t.settlement_currency_id = c.id
                LEFT JOIN currencies_currencyhistory as cch
                ON t.settlement_currency_id = cch.currency_id
                WHERE cch.date = %s AND cch.pricing_policy_id = %s;
            """

            cursor.execute(query, [self.instance.report_date, self.instance.pricing_policy.id])

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

        _l.info('len instrument_ids %s' % len(instrument_ids))

        self.add_data_items_instruments(instrument_ids)
        self.add_data_items_portfolios(portfolio_ids)
        self.add_data_items_accounts(account_ids)
        self.add_data_items_currencies(currencies_ids)

        self.instance.custom_fields = BalanceReportCustomField.objects.filter(master_user=self.instance.master_user)

        _l.debug('_refresh_with_perms_optimized item relations done: %s', "{:3.3f}".format(time.perf_counter() - item_relations_st))
