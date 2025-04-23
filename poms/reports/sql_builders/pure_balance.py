import logging
import os
import time
from datetime import timedelta

from django.conf import settings
from django.db import connection

from celery import group

from poms.accounts.models import Account, AccountType
from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.common.utils import get_last_business_day
from poms.currencies.models import Currency
from poms.iam.utils import get_allowed_queryset
from poms.instruments.models import (
    Country,
    ExposureCalculationModel,
    Instrument,
    InstrumentType,
    LongUnderlyingExposure,
    ShortUnderlyingExposure,
)
from poms.portfolios.models import Portfolio
from poms.reports.common import Report
from poms.reports.models import BalanceReportCustomField, ReportInstanceModel
from poms.reports.sql_builders.helpers import (
    dictfetchall,
    get_cash_as_position_consolidation_for_select,
    get_cash_consolidation_for_select,
    get_fx_trades_and_fx_variations_transaction_filter_sql_string,
    get_pl_left_join_consolidation,
    get_position_consolidation_for_select,
    get_report_fx_rate,
    get_transaction_date_filter_for_initial_position_sql_string,
    get_transaction_filter_sql_string,
    get_where_expression_for_position_consolidation,
)
from poms.reports.sql_builders.pl import PLReportBuilderSql
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.users.models import EcosystemDefault

_l = logging.getLogger("poms.reports")


class PureBalanceReportBuilderSql:
    def __init__(self, instance=None):
        _l.debug("PureReportBuilderSql init")

        self.instance = instance

        self.instance.allocation_mode = Report.MODE_IGNORE

        self.ecosystem_defaults = EcosystemDefault.cache.get_cache(
            master_user_pk=self.instance.master_user.pk
        )

        _l.debug(
            f"self.instance master_user {self.instance.master_user} "
            f"report_date {self.instance.report_date}"
        )

        """
        TODO IAM_SECURITY_VERIFY need to check, if user somehow passes 
        id of object he has no access to we should throw error
        """

        """Important security methods"""
        # self.transform_to_allowed_portfolios()
        # self.transform_to_allowed_accounts()

    def transform_to_allowed_portfolios(self):
        if not len(self.instance.portfolios):
            self.instance.portfolios = get_allowed_queryset(
                self.instance.member, Portfolio.objects.all()
            )

    def transform_to_allowed_accounts(self):
        if not len(self.instance.accounts):
            self.instance.accounts = get_allowed_queryset(
                self.instance.member, Account.objects.all()
            )

    # For internal usage, when celery tasks got simple balances
    def build_balance_sync(self):
        st = time.perf_counter()

        self.instance.items = []

        self.serial_build()

        self.instance.execution_time = float("{:3.3f}".format(time.perf_counter() - st))

        _l.debug(f"items total {len(self.instance.items)}")

        relation_prefetch_st = time.perf_counter()

        self.instance.relation_prefetch_time = float(
            "{:3.3f}".format(time.perf_counter() - relation_prefetch_st)
        )

        _l.debug(f"build_st done: {self.instance.execution_time}")

        return self.instance

    def build_sync(self, celery_task):
        try:
            report_settings = celery_task.options_object

            instance = ReportInstanceModel(
                **report_settings, master_user=celery_task.master_user
            )

            with connection.cursor() as cursor:
                st = time.perf_counter()

                transaction_filter_sql_string = get_transaction_filter_sql_string(
                    instance
                )
                transaction_date_filter_for_initial_position_sql_string = (
                    get_transaction_date_filter_for_initial_position_sql_string(
                        instance.report_date,
                        has_where=bool(len(transaction_filter_sql_string)),
                    )
                )

                balance_q_consolidated_select_columns = (
                    get_position_consolidation_for_select(instance, prefix="balance_q.")
                )
                fx_trades_and_fx_variations_filter_sql_string = (
                    get_fx_trades_and_fx_variations_transaction_filter_sql_string(
                        instance
                    )
                )

                self.bday_yesterday_of_report_date = get_last_business_day(
                    instance.report_date - timedelta(days=1), to_string=True
                )

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
                            strategy3_position_id,
                            
                            allocation_balance_id,
                            allocation_pl_id
                            
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
                            strategy3_position_id,
                            allocation_balance_id,
                            allocation_pl_id
                            
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
                            strategy3_position_id,
                            allocation_balance_id,
                            allocation_pl_id
                            
                            
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
                            strategy3_position_id,
                            
                            allocation_balance_id,
                            allocation_pl_id
                            
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
                               as min_date,
                               
                               allocation_balance_id,
                               allocation_pl_id
                               
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
                               as min_date,
                               allocation_balance_id,
                               allocation_pl_id
                               
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
                               as min_date,
                               
                               allocation_balance_id,
                               allocation_pl_id
                               
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
                        {transaction_date_filter_for_initial_position_sql_string}
                    
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
                        
                        currency_id,
                        
                        item_type,
                        item_type_name,
                        
                        fx_rate,
                        
                        position_size,
                        nominal_position_size,
                            
                        market_value,
                        market_value_loc
            
                    
                    from (   
                    
                        select 
                         
                             (-1) as instrument_id,
                            {consolidated_cash_as_position_columns}
                            
                            (settlement_currency_id) as currency_id,
                                
                            (2) as item_type,
                            ('Currency') as item_type_name,
                            
                            (1) as price,
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
                            end as fx_rate,
                            
                                
                            position_size,
                            (position_size) as nominal_position_size,
                                      
                            c.name,
                            c.short_name,
                            c.user_code,
                            
                            (settlement_currency_id) as pricing_currency_id,
                
                                
                            market_value,
                            market_value_loc
                        
                        
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
 
                        currency_id,
                        
                        item_type,
                        item_type_name,
                        
                        fx_rate,
                        
                        position_size,
                        nominal_position_size,
                        
                        market_value,
                        market_value_loc
                        
                    from (
                        select 
                            balance_q.instrument_id,
                            {balance_q_consolidated_select_columns}
                        
                            name,
                            short_name,
                            user_code,
                            
                            pricing_currency_id,
           
                            (-1) as currency_id,
                            
                            item_type,
                            item_type_name,
                            
                            price,
                            fx_rate,
                            
                            position_size,
                            nominal_position_size,
                            
                            -- case
                            --      when instrument_class_id = 5
                            --          then (position_size * (instrument_principal_price - pl_q.principal_cost_price_loc) * price_multiplier * pch_fx_rate) / rep_cur_fx
                            --      else market_value / rep_cur_fx
                            --  end as market_value,
                             
                             
                            (market_value / rep_cur_fx) as market_value,
                
                            -- case
                            --     when instrument_class_id = 5
                            --         then (position_size * (instrument_principal_price - pl_q.principal_cost_price_loc) * price_multiplier)
                            --     else market_value / pch_fx_rate
                            -- end as market_value_loc
                            
                            (market_value / pch_fx_rate) as market_value_loc
                            
                        from (
                            select 
                        
                            instrument_id,
                            {consolidated_position_columns}
                            
                            position_size,
                            case when coalesce(factor,1) = 0
                                    then position_size
                                    else
                                        position_size / coalesce(factor,1)
                            end as nominal_position_size,
    
                            (1) as item_type,
                            ('Instrument') as item_type_name,
                            
                            (principal_price) as price,
                            (pch_fx_rate) as fx_rate,
        
                            name,
                            short_name,
                            user_code,
        
                            pricing_currency_id,
          
                            instrument_class_id,
                            
                            (principal_price) as instrument_principal_price,
                            (accrued_price) as instrument_accrued_price,
                
                            case when pricing_currency_id = {report_currency_id}
                                   then 1
                               else
                                   (rep_cur_fx/pch_fx_rate)
                            end as cross_loc_prc_fx,
                     
                            (position_size * principal_price * price_multiplier * pch_fx_rate + (position_size * accrued_price * ach_fx_rate * 1 * accrued_multiplier)) as market_value,
                            
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
                                    principal_price
                                from instruments_pricehistory
                                where 
                                    instrument_id=i.id and 
                                    date = '{bday_yesterday_of_report_date}' and
                                    pricing_policy_id = {pricing_policy_id})
                                as yesterday_principal_price,
                                
                                (select 
                                    factor
                                from instruments_pricehistory
                                where 
                                    instrument_id=i.id and 
                                    date = '{report_date}' and
                                    pricing_policy_id = {pricing_policy_id})
                                as factor,
                                
                                (select 
                                    ytm
                                from instruments_pricehistory
                                where 
                                    instrument_id=i.id and 
                                    date = '{report_date}' and
                                    pricing_policy_id = {pricing_policy_id})
                                as ytm,
                                
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
                                and transaction_class_id in (1,2,14)
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
                    
                    ) as joined_positions
                """

                consolidated_cash_columns = get_cash_consolidation_for_select(instance)
                consolidated_position_columns = get_position_consolidation_for_select(
                    instance
                )
                consolidated_cash_as_position_columns = (
                    get_cash_as_position_consolidation_for_select(instance)
                )

                _l.debug("consolidated_cash_columns %s" % consolidated_cash_columns)
                _l.debug(
                    "consolidated_position_columns %s" % consolidated_position_columns
                )
                _l.debug(
                    "consolidated_cash_as_position_columns %s"
                    % consolidated_cash_as_position_columns
                )

                query = query.format(
                    report_date=instance.report_date,
                    master_user_id=celery_task.master_user.id,
                    default_currency_id=self.ecosystem_defaults.currency_id,
                    report_currency_id=instance.report_currency.id,
                    pricing_policy_id=instance.pricing_policy.id,
                    consolidated_cash_columns=consolidated_cash_columns,
                    consolidated_position_columns=consolidated_position_columns,
                    consolidated_cash_as_position_columns=consolidated_cash_as_position_columns,
                    balance_q_consolidated_select_columns=balance_q_consolidated_select_columns,
                    transaction_filter_sql_string=transaction_filter_sql_string,
                    transaction_date_filter_for_initial_position_sql_string=transaction_date_filter_for_initial_position_sql_string,
                    fx_trades_and_fx_variations_filter_sql_string=fx_trades_and_fx_variations_filter_sql_string,
                    bday_yesterday_of_report_date=self.bday_yesterday_of_report_date,
                )

                cursor.execute(query)

                _l.debug(
                    "Balance report query execute done: %s",
                    "{:3.3f}".format(time.perf_counter() - st),
                )

                result = dictfetchall(cursor)

                updated_result = []

                for item in result:
                    result_item = {}

                    result_item["name"] = item["name"]
                    result_item["short_name"] = item["short_name"]
                    result_item["user_code"] = item["user_code"]
                    result_item["item_type"] = item["item_type"]
                    result_item["item_type_name"] = item["item_type_name"]

                    result_item["market_value"] = item["market_value"]

                    result_item["market_value_loc"] = item["market_value_loc"]

                    if "portfolio_id" not in item:
                        result_item["portfolio_id"] = (
                            self.ecosystem_defaults.portfolio_id
                        )
                    else:
                        result_item["portfolio_id"] = item["portfolio_id"]

                    if "account_cash_id" not in item:
                        result_item["account_cash_id"] = (
                            self.ecosystem_defaults.account_id
                        )
                    else:
                        result_item["account_cash_id"] = item["account_cash_id"]

                    if "strategy1_cash_id" not in item:
                        result_item["strategy1_cash_id"] = (
                            self.ecosystem_defaults.strategy1_id
                        )
                    else:
                        result_item["strategy1_cash_id"] = item["strategy1_cash_id"]

                    if "strategy2_cash_id" not in item:
                        result_item["strategy2_cash_id"] = (
                            self.ecosystem_defaults.strategy2_id
                        )
                    else:
                        result_item["strategy2_cash_id"] = item["strategy2_cash_id"]

                    if "strategy3_cash_id" not in item:
                        result_item["strategy3_cash_id"] = (
                            self.ecosystem_defaults.strategy3_id
                        )
                    else:
                        result_item["strategy3_cash_id"] = item["strategy3_cash_id"]

                    if "account_position_id" not in item:
                        result_item["account_position_id"] = (
                            self.ecosystem_defaults.account_id
                        )
                    else:
                        result_item["account_position_id"] = item["account_position_id"]

                    if "strategy1_position_id" not in item:
                        result_item["strategy1_position_id"] = (
                            self.ecosystem_defaults.strategy1_id
                        )
                    else:
                        result_item["strategy1_position_id"] = item[
                            "strategy1_position_id"
                        ]

                    if "strategy2_position_id" not in item:
                        result_item["strategy2_position_id"] = (
                            self.ecosystem_defaults.strategy2_id
                        )
                    else:
                        result_item["strategy2_position_id"] = item[
                            "strategy2_position_id"
                        ]

                    if "strategy3_position_id" not in item:
                        result_item["strategy3_position_id"] = (
                            self.ecosystem_defaults.strategy3_id
                        )
                    else:
                        result_item["strategy3_position_id"] = item[
                            "strategy3_position_id"
                        ]

                    if "allocation_pl_id" not in item:
                        result_item["allocation_pl_id"] = None
                    else:
                        result_item["allocation_pl_id"] = item["allocation_pl_id"]

                    result_item["instrument_id"] = item["instrument_id"]
                    result_item["currency_id"] = item["currency_id"]
                    result_item["pricing_currency_id"] = item["pricing_currency_id"]

                    result_item["fx_rate"] = item["fx_rate"]

                    # _l.debug('item %s' % item)
                    result_item["position_size"] = round(
                        item["position_size"], settings.ROUND_NDIGITS
                    )
                    # _l.debug('item["nominal_position_size"] %s' % item["nominal_position_size"])
                    if item["nominal_position_size"] is not None:
                        result_item["nominal_position_size"] = round(
                            item["nominal_position_size"], settings.ROUND_NDIGITS
                        )
                    else:
                        result_item["nominal_position_size"] = None

                    if round(item["position_size"], settings.ROUND_NDIGITS):
                        updated_result.append(result_item)

                _l.debug("build balance result %s " % len(result))

                _l.debug("single build done: %s" % (time.perf_counter() - st))

                return updated_result

        except Exception as e:
            raise e

    def serial_build(self):
        st = time.perf_counter()

        task = CeleryTask(
            master_user=self.instance.master_user,
            member=self.instance.member,
            verbose_name="Balance Report",
            type="calculate_balance_report",
            options_object={
                "report_date": self.instance.report_date,
                "portfolios_ids": [
                    instance.id for instance in self.instance.portfolios
                ],
                "accounts_ids": [instance.id for instance in self.instance.accounts],
                "strategies1_ids": [
                    instance.id for instance in self.instance.strategies1
                ],
                "strategies2_ids": [
                    instance.id for instance in self.instance.strategies2
                ],
                "strategies3_ids": [
                    instance.id for instance in self.instance.strategies3
                ],
                "report_currency_id": self.instance.report_currency.id,
                "pricing_policy_id": self.instance.pricing_policy.id,
                "cost_method_id": self.instance.cost_method.id,
                "show_balance_exposure_details": self.instance.show_balance_exposure_details,
                "portfolio_mode": self.instance.portfolio_mode,
                "account_mode": self.instance.account_mode,
                "strategy1_mode": self.instance.strategy1_mode,
                "strategy2_mode": self.instance.strategy2_mode,
                "strategy3_mode": self.instance.strategy3_mode,
                "allocation_mode": self.instance.allocation_mode,
            },
        )

        result = self.build_sync(task)

        # 'all_dicts' is now a list of all dicts returned by the tasks
        self.instance.items = result

        _l.debug("parallel_build done: %s", "{:3.3f}".format(time.perf_counter() - st))
