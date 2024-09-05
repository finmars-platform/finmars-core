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


class BalanceReportBuilderSql:
    def __init__(self, instance=None):
        _l.debug("ReportBuilderSql init")

        self.instance = instance

        self.instance.allocation_mode = Report.MODE_IGNORE

        self.ecosystem_defaults = EcosystemDefault.objects.get(
            master_user=self.instance.master_user
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
        self.transform_to_allowed_portfolios()
        self.transform_to_allowed_accounts()

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

        if not self.instance.only_numbers:
            self.add_data_items()

        self.instance.relation_prefetch_time = float(
            "{:3.3f}".format(time.perf_counter() - relation_prefetch_st)
        )

        _l.debug(f"build_st done: {self.instance.execution_time}")

        return self.instance

    def build_balance(self):
        st = time.perf_counter()

        self.instance.items = []

        self.parallel_build()

        self.instance.execution_time = float("{:3.3f}".format(time.perf_counter() - st))

        _l.debug(f"items total {len(self.instance.items)}")

        relation_prefetch_st = time.perf_counter()

        if not self.instance.only_numbers:
            self.add_data_items()

        self.instance.relation_prefetch_time = float(
            "{:3.3f}".format(time.perf_counter() - relation_prefetch_st)
        )

        _l.debug(f"build_st done: {self.instance.execution_time}")

        return self.instance

    def build_sync(self, task_id):
        celery_task = CeleryTask.objects.filter(id=task_id).first()
        if not celery_task:
            _l.error(f"Invalid celery task_id={task_id}")
            return

        try:
            report_settings = celery_task.options_object

            instance = ReportInstanceModel(
                **report_settings, master_user=celery_task.master_user
            )

            # _l.debug('report_settings %s' % report_settings)

            with connection.cursor() as cursor:
                st = time.perf_counter()

                ecosystem_defaults = EcosystemDefault.objects.get(
                    master_user=celery_task.master_user
                )

                pl_query = PLReportBuilderSql.get_source_query(
                    cost_method=instance.cost_method.id
                )

                transaction_filter_sql_string = get_transaction_filter_sql_string(
                    instance
                )
                transaction_date_filter_for_initial_position_sql_string = (
                    get_transaction_date_filter_for_initial_position_sql_string(
                        instance.report_date,
                        has_where=bool(len(transaction_filter_sql_string)),
                    )
                )
                report_fx_rate = get_report_fx_rate(instance, instance.report_date)
                # fx_trades_and_fx_variations_filter_sql_string = get_fx_trades_and_fx_variations_transaction_filter_sql_string(
                #     report_settings)
                transactions_all_with_multipliers_where_expression = (
                    get_where_expression_for_position_consolidation(
                        instance, prefix="tt_w_m.", prefix_second="t_o."
                    )
                )
                consolidation_columns = get_position_consolidation_for_select(instance)
                tt_consolidation_columns = get_position_consolidation_for_select(
                    instance, prefix="tt."
                )
                tt_in1_consolidation_columns = get_position_consolidation_for_select(
                    instance, prefix="tt_in1."
                )
                balance_q_consolidated_select_columns = (
                    get_position_consolidation_for_select(instance, prefix="balance_q.")
                )
                pl_left_join_consolidation = get_pl_left_join_consolidation(instance)
                fx_trades_and_fx_variations_filter_sql_string = (
                    get_fx_trades_and_fx_variations_transaction_filter_sql_string(
                        instance
                    )
                )

                self.bday_yesterday_of_report_date = get_last_business_day(
                    instance.report_date - timedelta(days=1), to_string=True
                )

                pl_query = pl_query.format(
                    report_date=instance.report_date,
                    master_user_id=celery_task.master_user.id,
                    default_currency_id=ecosystem_defaults.currency_id,
                    report_currency_id=instance.report_currency.id,
                    pricing_policy_id=instance.pricing_policy.id,
                    report_fx_rate=report_fx_rate,
                    transaction_filter_sql_string=transaction_filter_sql_string,
                    transaction_date_filter_for_initial_position_sql_string=transaction_date_filter_for_initial_position_sql_string,
                    fx_trades_and_fx_variations_filter_sql_string=fx_trades_and_fx_variations_filter_sql_string,
                    consolidation_columns=consolidation_columns,
                    balance_q_consolidated_select_columns=balance_q_consolidated_select_columns,
                    tt_consolidation_columns=tt_consolidation_columns,
                    tt_in1_consolidation_columns=tt_in1_consolidation_columns,
                    transactions_all_with_multipliers_where_expression=transactions_all_with_multipliers_where_expression,
                    filter_query_for_balance_in_multipliers_table="",
                    bday_yesterday_of_report_date=self.bday_yesterday_of_report_date,
                )
                # filter_query_for_balance_in_multipliers_table=' where multiplier = 1')
                # TODO ask for right where expression

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
                        instrument_pricing_currency_fx_rate,
                        instrument_accrued_currency_fx_rate,
                        
                        instrument_principal_price,
                        instrument_accrued_price,
                        instrument_factor,
                        instrument_ytm,
                        daily_price_change,
                        
                        currency_id,
                        
                        item_type,
                        item_type_name,
                        
                        fx_rate,
                        
                        position_size,
                        nominal_position_size,
                        
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
                        
                        principal_invested_fixed,
                        principal_invested_fixed_loc,
                        
                        amount_invested_fixed,
                        amount_invested_fixed_loc,
                        
                        position_return,
                        position_return_loc,
                        net_position_return,
                        net_position_return_loc,
                        
                        position_return_fixed,
                        position_return_fixed_loc,
                        net_position_return_fixed,
                        net_position_return_fixed_loc,
                        
                        time_invested,
                        
                        ytm,
                        modified_duration,
                        ytm_at_cost,
                        return_annually,
                        return_annually_fixed,
            
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
                            (0) as instrument_pricing_currency_fx_rate, -- WTF?
                            (0) as instrument_accrued_currency_fx_rate,
                            (1) as instrument_principal_price,
                            (0) as instrument_accrued_price,
                            (1) as instrument_factor,
                            (0) as instrument_ytm,
                            (0) as daily_price_change,
                            
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
                            
                            (0) as principal_invested_fixed,
                            (0) as principal_invested_fixed_loc,
                            
                            (0) as amount_invested_fixed,
                            (0) as amount_invested_fixed_loc,
                                
                            (0) as position_return,
                            (0) as position_return_loc,
                            (0) as net_position_return,
                            (0) as net_position_return_loc,
                            
                            (0) as position_return_fixed,
                            (0) as position_return_fixed_loc,
                            (0) as net_position_return_fixed,
                            (0) as net_position_return_fixed_loc,
                            
                            (0) as time_invested,
                            
                            (0) as ytm,
                            (0) as modified_duration,
                            (0) as ytm_at_cost,
                            (0) as return_annually,
                            (0) as return_annually_fixed,
                            
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
                        instrument_factor,
                        instrument_ytm,
                        daily_price_change,
                        
                        currency_id,
                        
                        item_type,
                        item_type_name,
                        
                        fx_rate,
                        
                        position_size,
                        nominal_position_size,
                        
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
                        
                        principal_invested_fixed,
                        principal_invested_fixed_loc,
                        
                        amount_invested_fixed,
                        amount_invested_fixed_loc,
                        
                        position_return,
                        position_return_loc,
                        net_position_return,
                        net_position_return_loc,
                        
                        position_return_fixed,
                        position_return_fixed_loc,
                        net_position_return_fixed,
                        net_position_return_fixed_loc,
                        
                        time_invested,
                        
                        ytm,
                        modified_duration,
                        ytm_at_cost,
                        return_annually,
                        return_annually_fixed,
            
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
                            instrument_factor,
                            instrument_ytm,
                            daily_price_change,
                            
                            (-1) as currency_id,
                            
                            item_type,
                            item_type_name,
                            
                            price,
                            fx_rate,
                            
                            position_size,
                            nominal_position_size,
                            
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
                            
                            principal_invested_fixed,
                            principal_invested_fixed_loc,
                            
                            amount_invested_fixed,
                            amount_invested_fixed_loc,
                            
                            position_return,
                            position_return_loc,
                            net_position_return,
                            net_position_return_loc,
                            
                            position_return_fixed,
                            position_return_fixed_loc,
                            net_position_return_fixed,
                            net_position_return_fixed_loc,
                            
                            time_invested,
                            
                            ytm,
                            modified_duration,
                            ytm_at_cost,
                            return_annually,
                            return_annually_fixed,
                
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
                            (factor) as instrument_factor,
                            (ytm) as instrument_ytm,
                            
                            case when coalesce(yesterday_principal_price,0) = 0
                                    then 0
                                    else
                                        (principal_price - yesterday_principal_price) / yesterday_principal_price
                            end as daily_price_change,
                        
                            
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
                                    
                                    principal_invested_fixed,
                                    principal_invested_fixed_loc,
                                    
                                    amount_invested_fixed,
                                    amount_invested_fixed_loc,
                                    
                                    position_return,
                                    position_return_loc,
                                    net_position_return,
                                    net_position_return_loc,
                                    
                                    position_return_fixed,
                                    position_return_fixed_loc,
                                    net_position_return_fixed,
                                    net_position_return_fixed_loc,
                                    
                                    time_invested,
                                    
                                    ytm,
                                    modified_duration,
                                    ytm_at_cost,
                                    return_annually,
                                    return_annually_fixed,
                        
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
                                    
                                  from ({pl_query}) as pl where pl.item_type != 6
                        ) as pl_q
                        on balance_q.instrument_id = pl_q.instrument_id {pl_left_join_consolidation}
                    
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
                    default_currency_id=ecosystem_defaults.currency_id,
                    report_currency_id=instance.report_currency.id,
                    pricing_policy_id=instance.pricing_policy.id,
                    consolidated_cash_columns=consolidated_cash_columns,
                    consolidated_position_columns=consolidated_position_columns,
                    consolidated_cash_as_position_columns=consolidated_cash_as_position_columns,
                    balance_q_consolidated_select_columns=balance_q_consolidated_select_columns,
                    transaction_filter_sql_string=transaction_filter_sql_string,
                    transaction_date_filter_for_initial_position_sql_string=transaction_date_filter_for_initial_position_sql_string,
                    pl_query=pl_query,
                    pl_left_join_consolidation=pl_left_join_consolidation,
                    fx_trades_and_fx_variations_filter_sql_string=fx_trades_and_fx_variations_filter_sql_string,
                    bday_yesterday_of_report_date=self.bday_yesterday_of_report_date,
                )

                if settings.DEBUG:
                    with open(
                        os.path.join(
                            settings.BASE_DIR,
                            "balance_query_result_before_execution.txt",
                        ),
                        "w",
                    ) as the_file:
                        the_file.write(query)

                cursor.execute(query)

                _l.debug(
                    "Balance report query execute done: %s",
                    "{:3.3f}".format(time.perf_counter() - st),
                )

                query_str = str(cursor.query, "utf-8")

                if settings.SERVER_TYPE == "local":
                    with open("/tmp/query_result.txt", "w") as the_file:
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
                    result_item = {}

                    # item["currency_id"] = item["settlement_currency_id"]

                    result_item["name"] = item["name"]
                    result_item["short_name"] = item["short_name"]
                    result_item["user_code"] = item["user_code"]
                    result_item["item_type"] = item["item_type"]
                    result_item["item_type_name"] = item["item_type_name"]

                    result_item["market_value"] = item["market_value"]
                    result_item["exposure"] = item["exposure"]

                    result_item["market_value_loc"] = item["market_value_loc"]
                    result_item["exposure_loc"] = item["exposure_loc"]

                    if "portfolio_id" not in item:
                        result_item["portfolio_id"] = ecosystem_defaults.portfolio_id
                    else:
                        result_item["portfolio_id"] = item["portfolio_id"]

                    if "account_cash_id" not in item:
                        result_item["account_cash_id"] = ecosystem_defaults.account_id
                    else:
                        result_item["account_cash_id"] = item["account_cash_id"]

                    if "strategy1_cash_id" not in item:
                        result_item[
                            "strategy1_cash_id"
                        ] = ecosystem_defaults.strategy1_id
                    else:
                        result_item["strategy1_cash_id"] = item["strategy1_cash_id"]

                    if "strategy2_cash_id" not in item:
                        result_item[
                            "strategy2_cash_id"
                        ] = ecosystem_defaults.strategy2_id
                    else:
                        result_item["strategy2_cash_id"] = item["strategy2_cash_id"]

                    if "strategy3_cash_id" not in item:
                        result_item[
                            "strategy3_cash_id"
                        ] = ecosystem_defaults.strategy3_id
                    else:
                        result_item["strategy3_cash_id"] = item["strategy3_cash_id"]

                    if "account_position_id" not in item:
                        result_item[
                            "account_position_id"
                        ] = ecosystem_defaults.account_id
                    else:
                        result_item["account_position_id"] = item["account_position_id"]

                    if "strategy1_position_id" not in item:
                        result_item[
                            "strategy1_position_id"
                        ] = ecosystem_defaults.strategy1_id
                    else:
                        result_item["strategy1_position_id"] = item[
                            "strategy1_position_id"
                        ]

                    if "strategy2_position_id" not in item:
                        result_item[
                            "strategy2_position_id"
                        ] = ecosystem_defaults.strategy2_id
                    else:
                        result_item["strategy2_position_id"] = item[
                            "strategy2_position_id"
                        ]

                    if "strategy3_position_id" not in item:
                        result_item[
                            "strategy3_position_id"
                        ] = ecosystem_defaults.strategy3_id
                    else:
                        result_item["strategy3_position_id"] = item[
                            "strategy3_position_id"
                        ]

                    if "allocation_pl_id" not in item:
                        result_item["allocation_pl_id"] = None
                    else:
                        result_item["allocation_pl_id"] = item["allocation_pl_id"]

                    result_item["exposure_currency_id"] = item[
                        "co_directional_exposure_currency_id"
                    ]
                    result_item["instrument_id"] = item["instrument_id"]
                    result_item["currency_id"] = item["currency_id"]
                    result_item["pricing_currency_id"] = item["pricing_currency_id"]
                    result_item["instrument_pricing_currency_fx_rate"] = item[
                        "instrument_pricing_currency_fx_rate"
                    ]
                    result_item["instrument_accrued_currency_fx_rate"] = item[
                        "instrument_accrued_currency_fx_rate"
                    ]
                    result_item["instrument_principal_price"] = item[
                        "instrument_principal_price"
                    ]
                    result_item["instrument_accrued_price"] = item[
                        "instrument_accrued_price"
                    ]
                    result_item["instrument_factor"] = item["instrument_factor"]
                    result_item["instrument_ytm"] = item["instrument_ytm"]
                    result_item["daily_price_change"] = item["daily_price_change"]

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

                    result_item["ytm"] = item["ytm"]
                    result_item["ytm_at_cost"] = item["ytm_at_cost"]
                    result_item["modified_duration"] = item["modified_duration"]
                    result_item["return_annually"] = item["return_annually"]
                    result_item["return_annually_fixed"] = item["return_annually_fixed"]

                    result_item["position_return"] = item["position_return"]
                    result_item["position_return_loc"] = item["position_return_loc"]
                    result_item["net_position_return"] = item["net_position_return"]
                    result_item["net_position_return_loc"] = item[
                        "net_position_return_loc"
                    ]

                    result_item["position_return_fixed"] = item["position_return_fixed"]
                    result_item["position_return_fixed_loc"] = item[
                        "position_return_fixed_loc"
                    ]
                    result_item["net_position_return_fixed"] = item[
                        "net_position_return_fixed"
                    ]
                    result_item["net_position_return_fixed_loc"] = item[
                        "net_position_return_fixed_loc"
                    ]

                    result_item["net_cost_price"] = item["net_cost_price"]
                    result_item["net_cost_price_loc"] = item["net_cost_price_loc"]
                    result_item["gross_cost_price"] = item["gross_cost_price"]
                    result_item["gross_cost_price_loc"] = item["gross_cost_price_loc"]

                    result_item["principal_invested"] = item["principal_invested"]
                    result_item["principal_invested_loc"] = item[
                        "principal_invested_loc"
                    ]

                    result_item["amount_invested"] = item["amount_invested"]
                    result_item["amount_invested_loc"] = item["amount_invested_loc"]

                    result_item["principal_invested_fixed"] = item[
                        "principal_invested_fixed"
                    ]
                    result_item["principal_invested_fixed_loc"] = item[
                        "principal_invested_fixed_loc"
                    ]

                    result_item["amount_invested_fixed"] = item["amount_invested_fixed"]
                    result_item["amount_invested_fixed_loc"] = item[
                        "amount_invested_fixed_loc"
                    ]

                    result_item["time_invested"] = item["time_invested"]
                    result_item["return_annually"] = item["return_annually"]
                    result_item["return_annually_fixed"] = item["return_annually_fixed"]

                    # performance

                    result_item["principal"] = item["principal_opened"]
                    result_item["carry"] = item["carry_opened"]
                    result_item["overheads"] = item["overheads_opened"]
                    result_item["total"] = item["total_opened"]

                    result_item["principal_fx"] = item["principal_fx_opened"]
                    result_item["carry_fx"] = item["carry_fx_opened"]
                    result_item["overheads_fx"] = item["overheads_fx_opened"]
                    result_item["total_fx"] = item["total_fx_opened"]

                    result_item["principal_fixed"] = item["principal_fixed_opened"]
                    result_item["carry_fixed"] = item["carry_fixed_opened"]
                    result_item["overheads_fixed"] = item["overheads_fixed_opened"]
                    result_item["total_fixed"] = item["total_fixed_opened"]

                    # loc started

                    result_item["principal_loc"] = item["principal_opened_loc"]
                    result_item["carry_loc"] = item["carry_opened_loc"]
                    result_item["overheads_loc"] = item["overheads_opened_loc"]
                    result_item["total_loc"] = item["total_opened_loc"]

                    result_item["principal_fx_loc"] = item["principal_fx_opened_loc"]
                    result_item["carry_fx_loc"] = item["carry_fx_opened_loc"]
                    result_item["overheads_fx_loc"] = item["overheads_fx_opened_loc"]
                    result_item["total_fx_loc"] = item["total_fx_opened_loc"]

                    result_item["principal_fixed_loc"] = item[
                        "principal_fixed_opened_loc"
                    ]
                    result_item["carry_fixed_loc"] = item["carry_fixed_opened_loc"]
                    result_item["overheads_fixed_loc"] = item[
                        "overheads_fixed_opened_loc"
                    ]
                    result_item["total_fixed_loc"] = item["total_fixed_opened_loc"]

                    # Position * ( Long Underlying Exposure - Short Underlying Exposure)
                    # "Underlying Long/Short Exposure - Split":
                    # Position * Long Underlying Exposure
                    # -Position * Short Underlying Exposure

                    long = 0
                    short = 0

                    if (
                        item["long_underlying_exposure_id"]
                        == LongUnderlyingExposure.ZERO
                    ):
                        long = item["exposure_long_underlying_zero"]
                    if (
                        item["long_underlying_exposure_id"]
                        == LongUnderlyingExposure.LONG_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE
                    ):
                        long = item["exposure_short_underlying_price"]
                    if (
                        item["long_underlying_exposure_id"]
                        == LongUnderlyingExposure.LONG_UNDERLYING_INSTRUMENT_PRICE_DELTA
                    ):
                        long = item["exposure_long_underlying_price_delta"]
                    if (
                        item["long_underlying_exposure_id"]
                        == LongUnderlyingExposure.LONG_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE
                    ):
                        long = item["exposure_long_underlying_fx_rate"]
                    if (
                        item["long_underlying_exposure_id"]
                        == LongUnderlyingExposure.LONG_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE
                    ):
                        long = item["exposure_long_underlying_fx_rate_delta"]

                    if (
                        item["short_underlying_exposure_id"]
                        == ShortUnderlyingExposure.ZERO
                    ):
                        short = item["exposure_short_underlying_zero"]
                    if (
                        item["short_underlying_exposure_id"]
                        == ShortUnderlyingExposure.SHORT_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE
                    ):
                        short = item["exposure_short_underlying_price"]
                    if (
                        item["short_underlying_exposure_id"]
                        == ShortUnderlyingExposure.SHORT_UNDERLYING_INSTRUMENT_PRICE_DELTA
                    ):
                        short = item["exposure_short_underlying_price_delta"]
                    if (
                        item["short_underlying_exposure_id"]
                        == ShortUnderlyingExposure.SHORT_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE
                    ):
                        short = item["exposure_short_underlying_fx_rate"]
                    if (
                        item["short_underlying_exposure_id"]
                        == ShortUnderlyingExposure.SHORT_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE
                    ):
                        short = item["exposure_short_underlying_fx_rate_delta"]

                    if (
                        item["exposure_calculation_model_id"]
                        == ExposureCalculationModel.UNDERLYING_LONG_SHORT_EXPOSURE_NET
                    ):
                        result_item["exposure"] = result_item["position_size"] * (
                            long - short
                        )

                    # (i )   Position * Long Underlying Exposure
                    # (ii)  -Position * Short Underlying Exposure

                    if long is None:
                        long = 0

                    if (
                        item["exposure_calculation_model_id"]
                        == ExposureCalculationModel.UNDERLYING_LONG_SHORT_EXPOSURE_SPLIT
                    ):
                        result_item["exposure"] = result_item["position_size"] * long

                    if round(item["position_size"], settings.ROUND_NDIGITS):
                        updated_result.append(result_item)

                        if ITEM_TYPE_INSTRUMENT == 1 and (
                            item["has_second_exposure_currency"]
                            and instance.show_balance_exposure_details
                        ):
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
                                "instrument_factor": None,
                                "instrument_ytm": None,
                                "daily_price_change": None,
                                "market_value": None,
                                "market_value_loc": None,
                                "item_type": 7,
                                "item_type_name": "Exposure",
                                "exposure": item["exposure_2"],
                                "exposure_loc": item["exposure_2_loc"],
                                "exposure_currency_id": item[
                                    "counter_directional_exposure_currency_id"
                                ],
                            }

                            if (
                                item["exposure_calculation_model_id"]
                                == ExposureCalculationModel.UNDERLYING_LONG_SHORT_EXPOSURE_SPLIT
                            ):
                                new_exposure_item["exposure"] = (
                                    -item["position_size"] * short
                                )

                            new_exposure_item["position_size"] = None
                            new_exposure_item["nominal_position_size"] = None
                            new_exposure_item["ytm"] = None
                            new_exposure_item["ytm_at_cost"] = None
                            new_exposure_item["modified_duration"] = None
                            new_exposure_item["return_annually"] = None
                            new_exposure_item["return_annually_fixed"] = None

                            new_exposure_item["position_return"] = None
                            new_exposure_item["position_return_loc"] = None
                            new_exposure_item["net_position_return"] = None
                            new_exposure_item["net_position_return_loc"] = None

                            new_exposure_item["position_return_fixed"] = None
                            new_exposure_item["position_return_fixed_loc"] = None
                            new_exposure_item["net_position_return_fixed"] = None
                            new_exposure_item["net_position_return_fixed_loc"] = None

                            new_exposure_item["net_cost_price"] = None
                            new_exposure_item["net_cost_price_loc"] = None
                            new_exposure_item["gross_cost_price"] = None
                            new_exposure_item["gross_cost_price_loc"] = None

                            new_exposure_item["principal_invested"] = None
                            new_exposure_item["principal_invested_loc"] = None

                            new_exposure_item["amount_invested"] = None
                            new_exposure_item["amount_invested_loc"] = None

                            new_exposure_item["principal_invested_fixed"] = None
                            new_exposure_item["principal_invested_fixed_loc"] = None

                            new_exposure_item["amount_invested_fixed"] = None
                            new_exposure_item["amount_invested_fixed_loc"] = None

                            new_exposure_item["time_invested"] = None
                            new_exposure_item["return_annually"] = None
                            new_exposure_item["return_annually_fixed"] = None

                            # performance

                            new_exposure_item["principal"] = None
                            new_exposure_item["carry"] = None
                            new_exposure_item["overheads"] = None
                            new_exposure_item["total"] = None

                            new_exposure_item["principal_fx"] = None
                            new_exposure_item["carry_fx"] = None
                            new_exposure_item["overheads_fx"] = None
                            new_exposure_item["total_fx"] = None

                            new_exposure_item["principal_fixed"] = None
                            new_exposure_item["carry_fixed"] = None
                            new_exposure_item["overheads_fixed"] = None
                            new_exposure_item["total_fixed"] = None

                            # loc started

                            new_exposure_item["principal_loc"] = None
                            new_exposure_item["carry_loc"] = None
                            new_exposure_item["overheads_loc"] = None
                            new_exposure_item["total_loc"] = None

                            new_exposure_item["principal_fx_loc"] = None
                            new_exposure_item["carry_fx_loc"] = None
                            new_exposure_item["overheads_fx_loc"] = None
                            new_exposure_item["total_fx_loc"] = None

                            new_exposure_item["principal_fixed_loc"] = None
                            new_exposure_item["carry_fixed_loc"] = None
                            new_exposure_item["overheads_fixed_loc"] = None
                            new_exposure_item["total_fixed_loc"] = None

                            updated_result.append(new_exposure_item)

                _l.debug("build balance result %s " % len(result))

                _l.debug("single build done: %s" % (time.perf_counter() - st))

                celery_task.status = CeleryTask.STATUS_DONE
                celery_task.save()

                return updated_result

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
                    verbose_name="Balance Report",
                    type="calculate_balance_report",
                    options_object={
                        "report_date": self.instance.report_date,
                        "portfolios_ids": [portfolio.id],
                        "accounts_ids": [
                            instance.id for instance in self.instance.accounts
                        ],
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

                tasks.append(task)

        else:
            task = CeleryTask.objects.create(
                master_user=self.instance.master_user,
                member=self.instance.member,
                verbose_name="Balance Report",
                type="calculate_balance_report",
                options_object={
                    "report_date": self.instance.report_date,
                    "portfolios_ids": [
                        instance.id for instance in self.instance.portfolios
                    ],
                    "accounts_ids": [
                        instance.id for instance in self.instance.accounts
                    ],
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

            tasks.append(task)

        _l.debug("Going to run %s tasks" % len(tasks))

        # Run the group of tasks
        job = group(build.s(task_id=task.id, context={
            "realm_code": self.instance.master_user.realm_code,
            "space_code": self.instance.master_user.space_code
        }) for task in tasks)

        group_result = job.apply_async()
        # Wait for all tasks to finish and get their results
        group_result.join()

        # Retrieve results
        all_dicts = []
        # TODO probably we can do some optimization here
        for result in group_result.results:
            # Each result is an AsyncResult instance.
            # You can get the result of the task with its .result property.
            all_dicts.extend(result.result)

        for task in tasks:
            # refresh the task instance to get the latest status from the database
            task.refresh_from_db()

            task.delete()

        # 'all_dicts' is now a list of all dicts returned by the tasks
        self.instance.items = all_dicts

        _l.debug("parallel_build done: %s", "{:3.3f}".format(time.perf_counter() - st))

    def serial_build(self):
        st = time.perf_counter()

        task = CeleryTask.objects.create(
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

        result = self.build_sync(task.id)

        # 'all_dicts' is now a list of all dicts returned by the tasks
        self.instance.items = result

        _l.debug("parallel_build done: %s", "{:3.3f}".format(time.perf_counter() - st))

    def add_data_items_instruments(self, ids):
        self.instance.item_instruments = (
            Instrument.objects.select_related(
                "instrument_type",
                "instrument_type__instrument_class",
                "pricing_currency",
                "accrued_currency",
                "country",
                "owner",
            )
            .prefetch_related(
                "attributes",
                "attributes__attribute_type",
                "attributes__classifier",
            )
            .filter(master_user=self.instance.master_user)
            .filter(id__in=ids)
        )

    def add_data_items_instrument_types(self, instruments):
        ids = []

        for instrument in instruments:
            ids.append(instrument.instrument_type_id)

        self.instance.item_instrument_types = (
            InstrumentType.objects.select_related("owner")
            .prefetch_related(
                "attributes",
                "attributes__attribute_type",
                "attributes__classifier",
            )
            .filter(master_user=self.instance.master_user)
            .filter(id__in=ids)
        )

    def add_data_items_countries(self, instruments):
        ids = []

        for instrument in instruments:
            ids.append(instrument.country_id)

        self.instance.item_countries = Country.objects.all()

    def add_data_items_portfolios(self, ids):
        self.instance.item_portfolios = (
            Portfolio.objects.select_related("owner")
            .prefetch_related("attributes")
            .defer("responsibles", "counterparties", "transaction_types", "accounts")
            .filter(master_user=self.instance.master_user)
            .filter(id__in=ids)
        )

    def add_data_items_accounts(self, ids):
        self.instance.item_accounts = (
            Account.objects.select_related("type", "owner")
            .prefetch_related(
                "attributes",
                "attributes__attribute_type",
                "attributes__classifier",
            )
            .filter(master_user=self.instance.master_user)
            .filter(id__in=ids)
        )

    def add_data_items_account_types(self, accounts):
        ids = [account.type_id for account in accounts]

        self.instance.item_account_types = (
            AccountType.objects.select_related("owner")
            .prefetch_related(
                "attributes",
                "attributes__attribute_type",
                "attributes__classifier",
            )
            .filter(master_user=self.instance.master_user)
            .filter(id__in=ids)
        )

    def add_data_items_currencies(self, ids):
        self.instance.item_currencies = (
            Currency.objects.select_related("country", "owner")
            .prefetch_related(
                "attributes",
                "attributes__attribute_type",
                "attributes__classifier",
            )
            .filter(master_user=self.instance.master_user)
            .filter(id__in=ids)
        )

    def add_data_items_strategies1(self, ids):
        self.instance.item_strategies1 = (
            Strategy1.objects.select_related("owner")
            .prefetch_related(
                "attributes",
                "attributes__attribute_type",
                "attributes__classifier",
            )
            .filter(master_user=self.instance.master_user)
            .filter(id__in=ids)
        )

    def add_data_items_strategies2(self, ids):
        self.instance.item_strategies2 = (
            Strategy2.objects.select_related("owner")
            .prefetch_related(
                "attributes",
                "attributes__attribute_type",
                "attributes__classifier",
            )
            .filter(master_user=self.instance.master_user)
            .filter(id__in=ids)
        )

    def add_data_items_strategies3(self, ids):
        self.instance.item_strategies3 = (
            Strategy3.objects.select_related("owner")
            .prefetch_related(
                "attributes",
                "attributes__attribute_type",
                "attributes__classifier",
            )
            .filter(master_user=self.instance.master_user)
            .filter(id__in=ids)
        )

    def add_data_items(self):
        instance_relations_st = time.perf_counter()

        _l.debug(
            "_refresh_with_perms_optimized instance relations done: %s",
            "{:3.3f}".format(time.perf_counter() - instance_relations_st),
        )

        permissions_st = time.perf_counter()

        _l.debug(
            "_refresh_with_perms_optimized permissions done: %s",
            "{:3.3f}".format(time.perf_counter() - permissions_st),
        )

        item_relations_st = time.perf_counter()

        instrument_ids = []
        portfolio_ids = []
        account_ids = []
        currencies_ids = []
        strategies1_ids = []
        strategies2_ids = []
        strategies3_ids = []

        for item in self.instance.items:
            if "portfolio_id" in item and item["portfolio_id"] != "-":
                portfolio_ids.append(item["portfolio_id"])

            if "instrument_id" in item:
                instrument_ids.append(item["instrument_id"])

            if "allocation_pl_id" in item:
                instrument_ids.append(item["allocation_pl_id"])

            if "account_position_id" in item and item["account_position_id"] != "-":
                account_ids.append(item["account_position_id"])
            if "account_cash_id" in item and item["account_cash_id"] != "-":
                account_ids.append(item["account_cash_id"])

            if "currency_id" in item:
                currencies_ids.append(item["currency_id"])
            if "pricing_currency_id" in item:
                currencies_ids.append(item["pricing_currency_id"])
            if "exposure_currency_id" in item:
                currencies_ids.append(item["exposure_currency_id"])

            if "strategy1_position_id" in item:
                strategies1_ids.append(item["strategy1_position_id"])

            if "strategy2_position_id" in item:
                strategies2_ids.append(item["strategy2_position_id"])

            if "strategy3_position_id" in item:
                strategies3_ids.append(item["strategy3_position_id"])

            if "strategy1_cash_id" in item:
                strategies1_ids.append(item["strategy1_cash_id"])

            if "strategy2_cash_id" in item:
                strategies2_ids.append(item["strategy2_cash_id"])

            if "strategy3_cash_id" in item:
                strategies3_ids.append(item["strategy3_cash_id"])

        instrument_ids = list(set(instrument_ids))
        portfolio_ids = list(set(portfolio_ids))
        account_ids = list(set(account_ids))
        currencies_ids = list(set(currencies_ids))
        strategies1_ids = list(set(strategies1_ids))
        strategies2_ids = list(set(strategies2_ids))
        strategies3_ids = list(set(strategies3_ids))

        _l.debug("strategies1_ids %s" % strategies1_ids)

        self.add_data_items_instruments(instrument_ids)
        self.add_data_items_portfolios(portfolio_ids)
        self.add_data_items_accounts(account_ids)
        self.add_data_items_currencies(currencies_ids)
        self.add_data_items_strategies1(strategies1_ids)
        self.add_data_items_strategies2(strategies2_ids)
        self.add_data_items_strategies3(strategies3_ids)

        _l.debug("add_data_items_strategies1 %s " % self.instance.item_strategies1)

        self.add_data_items_instrument_types(self.instance.item_instruments)
        self.add_data_items_countries(self.instance.item_instruments)
        self.add_data_items_account_types(self.instance.item_accounts)

        self.instance.custom_fields = BalanceReportCustomField.objects.filter(
            master_user=self.instance.master_user
        )

        _l.debug(
            "_refresh_with_perms_optimized item relations done: %s",
            "{:3.3f}".format(time.perf_counter() - item_relations_st),
        )

        # Execute lazy fetch?

        self.instance.item_instruments = list(self.instance.item_instruments)
        self.instance.item_portfolios = list(self.instance.item_portfolios)
        self.instance.item_accounts = list(self.instance.item_accounts)
        self.instance.item_currencies = list(self.instance.item_currencies)
        self.instance.item_strategies1 = list(self.instance.item_strategies1)
        self.instance.item_strategies2 = list(self.instance.item_strategies2)
        self.instance.item_strategies3 = list(self.instance.item_strategies3)
        self.instance.item_account_types = list(self.instance.item_account_types)
        self.instance.item_instrument_types = list(self.instance.item_instrument_types)


@finmars_task(name="reports.build_balance_report", bind=True)
def build(self, task_id, *args, **kwargs):
    celery_task = CeleryTask.objects.filter(id=task_id).first()
    if not celery_task:
        _l.error(f"build_balance_report, error: no such celery task.id={task_id}")
        return

    try:
        st = time.perf_counter()

        report_settings = celery_task.options_object

        instance = ReportInstanceModel(
            **report_settings, master_user=celery_task.master_user
        )

        # _l.debug('report_settings %s' % report_settings)

        with connection.cursor() as cursor:
            st = time.perf_counter()

            ecosystem_defaults = EcosystemDefault.objects.get(
                master_user=celery_task.master_user
            )

            pl_query = PLReportBuilderSql.get_source_query(
                cost_method=instance.cost_method.id
            )

            transaction_filter_sql_string = get_transaction_filter_sql_string(instance)
            transaction_date_filter_for_initial_position_sql_string = (
                get_transaction_date_filter_for_initial_position_sql_string(
                    instance.report_date,
                    has_where=bool(len(transaction_filter_sql_string)),
                )
            )
            report_fx_rate = get_report_fx_rate(instance, instance.report_date)
            # fx_trades_and_fx_variations_filter_sql_string = get_fx_trades_and_fx_variations_transaction_filter_sql_string(
            #     report_settings)
            transactions_all_with_multipliers_where_expression = (
                get_where_expression_for_position_consolidation(
                    instance, prefix="tt_w_m.", prefix_second="t_o."
                )
            )
            consolidation_columns = get_position_consolidation_for_select(instance)
            tt_consolidation_columns = get_position_consolidation_for_select(
                instance, prefix="tt."
            )
            tt_in1_consolidation_columns = get_position_consolidation_for_select(
                instance, prefix="tt_in1."
            )
            balance_q_consolidated_select_columns = (
                get_position_consolidation_for_select(instance, prefix="balance_q.")
            )
            pl_left_join_consolidation = get_pl_left_join_consolidation(instance)
            fx_trades_and_fx_variations_filter_sql_string = (
                get_fx_trades_and_fx_variations_transaction_filter_sql_string(instance)
            )

            self.bday_yesterday_of_report_date = get_last_business_day(
                instance.report_date - timedelta(days=1), to_string=True
            )

            pl_query = pl_query.format(
                report_date=instance.report_date,
                master_user_id=celery_task.master_user.id,
                default_currency_id=ecosystem_defaults.currency_id,
                report_currency_id=instance.report_currency.id,
                pricing_policy_id=instance.pricing_policy.id,
                report_fx_rate=report_fx_rate,
                transaction_filter_sql_string=transaction_filter_sql_string,
                transaction_date_filter_for_initial_position_sql_string=transaction_date_filter_for_initial_position_sql_string,
                fx_trades_and_fx_variations_filter_sql_string=fx_trades_and_fx_variations_filter_sql_string,
                consolidation_columns=consolidation_columns,
                balance_q_consolidated_select_columns=balance_q_consolidated_select_columns,
                tt_consolidation_columns=tt_consolidation_columns,
                tt_in1_consolidation_columns=tt_in1_consolidation_columns,
                transactions_all_with_multipliers_where_expression=transactions_all_with_multipliers_where_expression,
                filter_query_for_balance_in_multipliers_table="",
                bday_yesterday_of_report_date=self.bday_yesterday_of_report_date,
            )
            # filter_query_for_balance_in_multipliers_table=' where multiplier = 1')
            # TODO ask for right where expression

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
                        instrument_pricing_currency_fx_rate,
                        instrument_accrued_currency_fx_rate,
                        
                        instrument_principal_price,
                        instrument_accrued_price,
                        instrument_factor,
                        instrument_ytm,
                        daily_price_change,
                        
                        currency_id,
                        
                        item_type,
                        item_type_name,
                        
                        fx_rate,
                        
                        position_size,
                        nominal_position_size,
                        
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
                        
                        principal_invested_fixed,
                        principal_invested_fixed_loc,
                        
                        amount_invested_fixed,
                        amount_invested_fixed_loc,
                        
                        position_return,
                        position_return_loc,
                        net_position_return,
                        net_position_return_loc,
                        
                        position_return_fixed,
                        position_return_fixed_loc,
                        net_position_return_fixed,
                        net_position_return_fixed_loc,
                        
                        time_invested,
                        
                        ytm,
                        modified_duration,
                        ytm_at_cost,
                        return_annually,
                        return_annually_fixed,
            
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
                            (0) as instrument_pricing_currency_fx_rate, -- WTF?
                            (0) as instrument_accrued_currency_fx_rate,
                            (1) as instrument_principal_price,
                            (0) as instrument_accrued_price,
                            (1) as instrument_factor,
                            (0) as instrument_ytm,
                            (0) as daily_price_change,
                            
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
                            
                            (0) as principal_invested_fixed,
                            (0) as principal_invested_fixed_loc,
                            
                            (0) as amount_invested_fixed,
                            (0) as amount_invested_fixed_loc,
                                
                            (0) as position_return,
                            (0) as position_return_loc,
                            (0) as net_position_return,
                            (0) as net_position_return_loc,
                            
                            (0) as position_return_fixed,
                            (0) as position_return_fixed_loc,
                            (0) as net_position_return_fixed,
                            (0) as net_position_return_fixed_loc,
                            
                            (0) as time_invested,
                            
                            (0) as ytm,
                            (0) as modified_duration,
                            (0) as ytm_at_cost,
                            (0) as return_annually,
                            (0) as return_annually_fixed,
                            
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
                        instrument_factor,
                        instrument_ytm,
                        daily_price_change,
                        
                        currency_id,
                        
                        item_type,
                        item_type_name,
                        
                        fx_rate,
                        
                        position_size,
                        nominal_position_size,
                        
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
                        
                        principal_invested_fixed,
                        principal_invested_fixed_loc,
                        
                        amount_invested_fixed,
                        amount_invested_fixed_loc,
                        
                        position_return,
                        position_return_loc,
                        net_position_return,
                        net_position_return_loc,
                        
                        position_return_fixed,
                        position_return_fixed_loc,
                        net_position_return_fixed,
                        net_position_return_fixed_loc,
                        
                        time_invested,
                        
                        ytm,
                        modified_duration,
                        ytm_at_cost,
                        return_annually,
                        return_annually_fixed,
            
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
                            instrument_factor,
                            instrument_ytm,
                            daily_price_change,
                            
                            (-1) as currency_id,
                            
                            item_type,
                            item_type_name,
                            
                            price,
                            fx_rate,
                            
                            position_size,
                            nominal_position_size,
                            
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
                            
                            principal_invested_fixed,
                            principal_invested_fixed_loc,
                            
                            amount_invested_fixed,
                            amount_invested_fixed_loc,
                            
                            position_return,
                            position_return_loc,
                            net_position_return,
                            net_position_return_loc,
                            
                            position_return_fixed,
                            position_return_fixed_loc,
                            net_position_return_fixed,
                            net_position_return_fixed_loc,
                            
                            time_invested,
                            
                            ytm,
                            modified_duration,
                            ytm_at_cost,
                            return_annually,
                            return_annually_fixed,
                
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
                            (factor) as instrument_factor,
                            (ytm) as instrument_ytm,
                            
                            case when coalesce(yesterday_principal_price,0) = 0
                                    then 0
                                    else
                                        (principal_price - yesterday_principal_price) / yesterday_principal_price
                            end as daily_price_change,
                        
                            
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
                                    
                                    principal_invested_fixed,
                                    principal_invested_fixed_loc,
                                    
                                    amount_invested_fixed,
                                    amount_invested_fixed_loc,
                                    
                                    position_return,
                                    position_return_loc,
                                    net_position_return,
                                    net_position_return_loc,
                                    
                                    position_return_fixed,
                                    position_return_fixed_loc,
                                    net_position_return_fixed,
                                    net_position_return_fixed_loc,
                                    
                                    time_invested,
                                    
                                    ytm,
                                    modified_duration,
                                    ytm_at_cost,
                                    return_annually,
                                    return_annually_fixed,
                        
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
                                    
                                  from ({pl_query}) as pl where pl.item_type != 6
                        ) as pl_q
                        on balance_q.instrument_id = pl_q.instrument_id {pl_left_join_consolidation}
                    
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
            _l.debug("consolidated_position_columns %s" % consolidated_position_columns)
            _l.debug(
                "consolidated_cash_as_position_columns %s"
                % consolidated_cash_as_position_columns
            )

            query = query.format(
                report_date=instance.report_date,
                master_user_id=celery_task.master_user.id,
                default_currency_id=ecosystem_defaults.currency_id,
                report_currency_id=instance.report_currency.id,
                pricing_policy_id=instance.pricing_policy.id,
                consolidated_cash_columns=consolidated_cash_columns,
                consolidated_position_columns=consolidated_position_columns,
                consolidated_cash_as_position_columns=consolidated_cash_as_position_columns,
                balance_q_consolidated_select_columns=balance_q_consolidated_select_columns,
                transaction_filter_sql_string=transaction_filter_sql_string,
                transaction_date_filter_for_initial_position_sql_string=transaction_date_filter_for_initial_position_sql_string,
                pl_query=pl_query,
                pl_left_join_consolidation=pl_left_join_consolidation,
                fx_trades_and_fx_variations_filter_sql_string=fx_trades_and_fx_variations_filter_sql_string,
                bday_yesterday_of_report_date=self.bday_yesterday_of_report_date,
            )

            if settings.DEBUG:
                with open(
                    os.path.join(
                        settings.BASE_DIR,
                        "balance_query_result_before_execution.txt",
                    ),
                    "w",
                ) as the_file:
                    the_file.write(query)

            cursor.execute(query)

            _l.debug(
                "Balance report query execute done: %s",
                "{:3.3f}".format(time.perf_counter() - st),
            )

            query_str = str(cursor.query, "utf-8")

            if settings.SERVER_TYPE == "local":
                with open("/tmp/query_result.txt", "w") as the_file:
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
                result_item = {}

                # item["currency_id"] = item["settlement_currency_id"]

                result_item["name"] = item["name"]
                result_item["short_name"] = item["short_name"]
                result_item["user_code"] = item["user_code"]
                result_item["item_type"] = item["item_type"]
                result_item["item_type_name"] = item["item_type_name"]

                result_item["market_value"] = item["market_value"]
                result_item["exposure"] = item["exposure"]

                result_item["market_value_loc"] = item["market_value_loc"]
                result_item["exposure_loc"] = item["exposure_loc"]

                if "portfolio_id" not in item:
                    result_item["portfolio_id"] = ecosystem_defaults.portfolio_id
                else:
                    result_item["portfolio_id"] = item["portfolio_id"]

                if "account_cash_id" not in item:
                    result_item["account_cash_id"] = ecosystem_defaults.account_id
                else:
                    result_item["account_cash_id"] = item["account_cash_id"]

                if "strategy1_cash_id" not in item:
                    result_item["strategy1_cash_id"] = ecosystem_defaults.strategy1_id
                else:
                    result_item["strategy1_cash_id"] = item["strategy1_cash_id"]

                if "strategy2_cash_id" not in item:
                    result_item["strategy2_cash_id"] = ecosystem_defaults.strategy2_id
                else:
                    result_item["strategy2_cash_id"] = item["strategy2_cash_id"]

                if "strategy3_cash_id" not in item:
                    result_item["strategy3_cash_id"] = ecosystem_defaults.strategy3_id
                else:
                    result_item["strategy3_cash_id"] = item["strategy3_cash_id"]

                if "account_position_id" not in item:
                    result_item["account_position_id"] = ecosystem_defaults.account_id
                else:
                    result_item["account_position_id"] = item["account_position_id"]

                if "strategy1_position_id" not in item:
                    result_item[
                        "strategy1_position_id"
                    ] = ecosystem_defaults.strategy1_id
                else:
                    result_item["strategy1_position_id"] = item["strategy1_position_id"]

                if "strategy2_position_id" not in item:
                    result_item[
                        "strategy2_position_id"
                    ] = ecosystem_defaults.strategy2_id
                else:
                    result_item["strategy2_position_id"] = item["strategy2_position_id"]

                if "strategy3_position_id" not in item:
                    result_item[
                        "strategy3_position_id"
                    ] = ecosystem_defaults.strategy3_id
                else:
                    result_item["strategy3_position_id"] = item["strategy3_position_id"]

                if "allocation_pl_id" not in item:
                    result_item["allocation_pl_id"] = None
                else:
                    result_item["allocation_pl_id"] = item["allocation_pl_id"]

                result_item["exposure_currency_id"] = item[
                    "co_directional_exposure_currency_id"
                ]
                result_item["instrument_id"] = item["instrument_id"]
                result_item["currency_id"] = item["currency_id"]
                result_item["pricing_currency_id"] = item["pricing_currency_id"]
                result_item["instrument_pricing_currency_fx_rate"] = item[
                    "instrument_pricing_currency_fx_rate"
                ]
                result_item["instrument_accrued_currency_fx_rate"] = item[
                    "instrument_accrued_currency_fx_rate"
                ]
                result_item["instrument_principal_price"] = item[
                    "instrument_principal_price"
                ]
                result_item["instrument_accrued_price"] = item[
                    "instrument_accrued_price"
                ]
                result_item["instrument_factor"] = item["instrument_factor"]
                result_item["instrument_ytm"] = item["instrument_ytm"]
                result_item["daily_price_change"] = item["daily_price_change"]

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

                result_item["ytm"] = item["ytm"]
                result_item["ytm_at_cost"] = item["ytm_at_cost"]
                result_item["modified_duration"] = item["modified_duration"]
                result_item["return_annually"] = item["return_annually"]
                result_item["return_annually_fixed"] = item["return_annually_fixed"]

                result_item["position_return"] = item["position_return"]
                result_item["position_return_loc"] = item["position_return_loc"]
                result_item["net_position_return"] = item["net_position_return"]
                result_item["net_position_return_loc"] = item["net_position_return_loc"]

                result_item["position_return_fixed"] = item["position_return_fixed"]
                result_item["position_return_fixed_loc"] = item[
                    "position_return_fixed_loc"
                ]
                result_item["net_position_return_fixed"] = item[
                    "net_position_return_fixed"
                ]
                result_item["net_position_return_fixed_loc"] = item[
                    "net_position_return_fixed_loc"
                ]

                result_item["net_cost_price"] = item["net_cost_price"]
                result_item["net_cost_price_loc"] = item["net_cost_price_loc"]
                result_item["gross_cost_price"] = item["gross_cost_price"]
                result_item["gross_cost_price_loc"] = item["gross_cost_price_loc"]

                result_item["principal_invested"] = item["principal_invested"]
                result_item["principal_invested_loc"] = item["principal_invested_loc"]

                result_item["amount_invested"] = item["amount_invested"]
                result_item["amount_invested_loc"] = item["amount_invested_loc"]

                result_item["principal_invested_fixed"] = item[
                    "principal_invested_fixed"
                ]
                result_item["principal_invested_fixed_loc"] = item[
                    "principal_invested_fixed_loc"
                ]

                result_item["amount_invested_fixed"] = item["amount_invested_fixed"]
                result_item["amount_invested_fixed_loc"] = item[
                    "amount_invested_fixed_loc"
                ]

                result_item["time_invested"] = item["time_invested"]
                result_item["return_annually"] = item["return_annually"]
                result_item["return_annually_fixed"] = item["return_annually_fixed"]

                # performance

                result_item["principal"] = item["principal_opened"]
                result_item["carry"] = item["carry_opened"]
                result_item["overheads"] = item["overheads_opened"]
                result_item["total"] = item["total_opened"]

                result_item["principal_fx"] = item["principal_fx_opened"]
                result_item["carry_fx"] = item["carry_fx_opened"]
                result_item["overheads_fx"] = item["overheads_fx_opened"]
                result_item["total_fx"] = item["total_fx_opened"]

                result_item["principal_fixed"] = item["principal_fixed_opened"]
                result_item["carry_fixed"] = item["carry_fixed_opened"]
                result_item["overheads_fixed"] = item["overheads_fixed_opened"]
                result_item["total_fixed"] = item["total_fixed_opened"]

                # loc started

                result_item["principal_loc"] = item["principal_opened_loc"]
                result_item["carry_loc"] = item["carry_opened_loc"]
                result_item["overheads_loc"] = item["overheads_opened_loc"]
                result_item["total_loc"] = item["total_opened_loc"]

                result_item["principal_fx_loc"] = item["principal_fx_opened_loc"]
                result_item["carry_fx_loc"] = item["carry_fx_opened_loc"]
                result_item["overheads_fx_loc"] = item["overheads_fx_opened_loc"]
                result_item["total_fx_loc"] = item["total_fx_opened_loc"]

                result_item["principal_fixed_loc"] = item["principal_fixed_opened_loc"]
                result_item["carry_fixed_loc"] = item["carry_fixed_opened_loc"]
                result_item["overheads_fixed_loc"] = item["overheads_fixed_opened_loc"]
                result_item["total_fixed_loc"] = item["total_fixed_opened_loc"]

                # Position * ( Long Underlying Exposure - Short Underlying Exposure)
                # "Underlying Long/Short Exposure - Split":
                # Position * Long Underlying Exposure
                # -Position * Short Underlying Exposure

                long = 0
                short = 0

                if item["long_underlying_exposure_id"] == LongUnderlyingExposure.ZERO:
                    long = item["exposure_long_underlying_zero"]
                if (
                    item["long_underlying_exposure_id"]
                    == LongUnderlyingExposure.LONG_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE
                ):
                    long = item["exposure_short_underlying_price"]
                if (
                    item["long_underlying_exposure_id"]
                    == LongUnderlyingExposure.LONG_UNDERLYING_INSTRUMENT_PRICE_DELTA
                ):
                    long = item["exposure_long_underlying_price_delta"]
                if (
                    item["long_underlying_exposure_id"]
                    == LongUnderlyingExposure.LONG_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE
                ):
                    long = item["exposure_long_underlying_fx_rate"]
                if (
                    item["long_underlying_exposure_id"]
                    == LongUnderlyingExposure.LONG_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE
                ):
                    long = item["exposure_long_underlying_fx_rate_delta"]

                if item["short_underlying_exposure_id"] == ShortUnderlyingExposure.ZERO:
                    short = item["exposure_short_underlying_zero"]
                if (
                    item["short_underlying_exposure_id"]
                    == ShortUnderlyingExposure.SHORT_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE
                ):
                    short = item["exposure_short_underlying_price"]
                if (
                    item["short_underlying_exposure_id"]
                    == ShortUnderlyingExposure.SHORT_UNDERLYING_INSTRUMENT_PRICE_DELTA
                ):
                    short = item["exposure_short_underlying_price_delta"]
                if (
                    item["short_underlying_exposure_id"]
                    == ShortUnderlyingExposure.SHORT_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE
                ):
                    short = item["exposure_short_underlying_fx_rate"]
                if (
                    item["short_underlying_exposure_id"]
                    == ShortUnderlyingExposure.SHORT_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE
                ):
                    short = item["exposure_short_underlying_fx_rate_delta"]

                if (
                    item["exposure_calculation_model_id"]
                    == ExposureCalculationModel.UNDERLYING_LONG_SHORT_EXPOSURE_NET
                ):
                    result_item["exposure"] = result_item["position_size"] * (
                        long - short
                    )

                # (i )   Position * Long Underlying Exposure
                # (ii)  -Position * Short Underlying Exposure

                if long is None:
                    long = 0

                if (
                    item["exposure_calculation_model_id"]
                    == ExposureCalculationModel.UNDERLYING_LONG_SHORT_EXPOSURE_SPLIT
                ):
                    result_item["exposure"] = result_item["position_size"] * long

                if round(item["position_size"], settings.ROUND_NDIGITS):
                    updated_result.append(result_item)

                    if ITEM_TYPE_INSTRUMENT == 1 and (
                        item["has_second_exposure_currency"]
                        and instance.show_balance_exposure_details
                    ):
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
                            "instrument_factor": None,
                            "instrument_ytm": None,
                            "daily_price_change": None,
                            "market_value": None,
                            "market_value_loc": None,
                            "item_type": 7,
                            "item_type_name": "Exposure",
                            "exposure": item["exposure_2"],
                            "exposure_loc": item["exposure_2_loc"],
                            "exposure_currency_id": item[
                                "counter_directional_exposure_currency_id"
                            ],
                        }

                        if (
                            item["exposure_calculation_model_id"]
                            == ExposureCalculationModel.UNDERLYING_LONG_SHORT_EXPOSURE_SPLIT
                        ):
                            new_exposure_item["exposure"] = (
                                -item["position_size"] * short
                            )

                        new_exposure_item["position_size"] = None
                        new_exposure_item["nominal_position_size"] = None
                        new_exposure_item["ytm"] = None
                        new_exposure_item["ytm_at_cost"] = None
                        new_exposure_item["modified_duration"] = None
                        new_exposure_item["return_annually"] = None
                        new_exposure_item["return_annually_fixed"] = None

                        new_exposure_item["position_return"] = None
                        new_exposure_item["position_return_loc"] = None
                        new_exposure_item["net_position_return"] = None
                        new_exposure_item["net_position_return_loc"] = None

                        new_exposure_item["position_return_fixed"] = None
                        new_exposure_item["position_return_fixed_loc"] = None
                        new_exposure_item["net_position_return_fixed"] = None
                        new_exposure_item["net_position_return_fixed_loc"] = None

                        new_exposure_item["net_cost_price"] = None
                        new_exposure_item["net_cost_price_loc"] = None
                        new_exposure_item["gross_cost_price"] = None
                        new_exposure_item["gross_cost_price_loc"] = None

                        new_exposure_item["principal_invested"] = None
                        new_exposure_item["principal_invested_loc"] = None

                        new_exposure_item["amount_invested"] = None
                        new_exposure_item["amount_invested_loc"] = None

                        new_exposure_item["principal_invested_fixed"] = None
                        new_exposure_item["principal_invested_fixed_loc"] = None

                        new_exposure_item["amount_invested_fixed"] = None
                        new_exposure_item["amount_invested_fixed_loc"] = None

                        new_exposure_item["time_invested"] = None
                        new_exposure_item["return_annually"] = None
                        new_exposure_item["return_annually_fixed"] = None

                        # performance

                        new_exposure_item["principal"] = None
                        new_exposure_item["carry"] = None
                        new_exposure_item["overheads"] = None
                        new_exposure_item["total"] = None

                        new_exposure_item["principal_fx"] = None
                        new_exposure_item["carry_fx"] = None
                        new_exposure_item["overheads_fx"] = None
                        new_exposure_item["total_fx"] = None

                        new_exposure_item["principal_fixed"] = None
                        new_exposure_item["carry_fixed"] = None
                        new_exposure_item["overheads_fixed"] = None
                        new_exposure_item["total_fixed"] = None

                        # loc started

                        new_exposure_item["principal_loc"] = None
                        new_exposure_item["carry_loc"] = None
                        new_exposure_item["overheads_loc"] = None
                        new_exposure_item["total_loc"] = None

                        new_exposure_item["principal_fx_loc"] = None
                        new_exposure_item["carry_fx_loc"] = None
                        new_exposure_item["overheads_fx_loc"] = None
                        new_exposure_item["total_fx_loc"] = None

                        new_exposure_item["principal_fixed_loc"] = None
                        new_exposure_item["carry_fixed_loc"] = None
                        new_exposure_item["overheads_fixed_loc"] = None
                        new_exposure_item["total_fixed_loc"] = None

                        updated_result.append(new_exposure_item)

            _l.debug("build balance result %s " % len(result))

            _l.debug("single build done: %s" % (time.perf_counter() - st))

            celery_task.status = CeleryTask.STATUS_DONE
            celery_task.save()

            return updated_result

    except Exception as e:
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.save()
        raise e
