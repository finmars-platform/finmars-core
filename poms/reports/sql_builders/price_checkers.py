import logging
import time

from django.conf import settings
from django.db import connection

from poms.currencies.models import Currency
from poms.instruments.models import Instrument
from poms.reports.sql_builders.helpers import get_transaction_filter_sql_string, \
    get_position_consolidation_for_select, dictfetchall, \
    get_cash_consolidation_for_select, get_cash_as_position_consolidation_for_select
from poms.users.models import EcosystemDefault

_l = logging.getLogger('poms.reports')


def execute_nav_sql(date, instance, cursor, ecosystem_defaults):
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
            
        
        ),
        
        unioned_interim_account_transactions as (
            
            select 
                   id,
                   master_user_id,
                   
                   instrument_id,
                   portfolio_id,
                   --account_cash_id,
                   -- TODO add consolidation columns
                   --strategy1_cash_id,
                   --strategy2_cash_id,
                   --strategy2_cash_id,
                   
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
                   
                   strategy1_cash_id,
                   strategy2_cash_id,
                   strategy3_cash_id,
                   
                   strategy1_position_id,
                   strategy2_position_id,
                   strategy3_position_id,
                   -- account_cash_id,
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
                   
                   strategy1_cash_id,
                   strategy2_cash_id,
                   strategy3_cash_id,
                   
                   strategy1_position_id,
                   strategy2_position_id,
                   strategy3_position_id,
                   -- account_cash_id,
                   -- TODO add consolidation columns
            
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
            where not (accounting_date <= '{report_date}' /* REPORTING DATE */
              and '{report_date}' < cash_date)
                
        ),
        
        filtered_transactions as (
            
            select * from unioned_interim_account_transactions
            {transaction_filter_sql_string}
        
        ),
        
        nav_positions as (
            
            select 
            * 
 
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
                accrued_currency_id,
                
                (pch_fx_rate) as instrument_pricing_currency_fx_rate,
                (ach_fx_rate) as instrument_accrued_currency_fx_rate,
                
                (rep_cur_fx/pch_fx_rate) cross_loc_prc_fx,
                
                (principal_price) as instrument_principal_price,
                (accrued_price) as instrument_accrued_price,
                
                (position_size * principal_price * price_multiplier * pch_fx_rate + (position_size * accrued_price * ach_fx_rate * 1 * accrued_multiplier)) as market_value,
                (position_size * principal_price * price_multiplier * pch_fx_rate + (position_size * accrued_price * ach_fx_rate * 1 * accrued_multiplier)) as exposure
                
            from (
                select
                    instrument_id,
                    {consolidated_position_columns}
                    
                    position_size,
                    
                    i.name,
                    i.short_name,
                    i.user_code,
                    i.pricing_currency_id,
                    i.accrued_currency_id,
                    i.price_multiplier,
                    i.accrued_multiplier,
                    
    
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
                    as accrued_price
                    
                from
                    (select
                      {consolidated_position_columns}
                      instrument_id,
                      SUM(position_size_with_sign) as position_size
                    from filtered_transactions
                    where min_date <= '{report_date}' and master_user_id = {master_user_id}
                    group by
                      {consolidated_position_columns}
                      instrument_id) as t
                left join instruments_instrument as i
                ON instrument_id = i.id
                where not i.is_deleted and i.is_active = true and i.is_enabled = true
                ) as grouped
            where position_size != 0
            ) as balance_q
        
        )
        
        select 
            (instrument_id) as id,
            name,
            user_code,
            position_size,
            ('missing_principal_pricing_history') as type
        from nav_positions WHERE instrument_principal_price ISNULL and instrument_accrued_price ISNULL 
        
        UNION ALL
        
        select 
            DISTINCT pricing_currency_id,
            (pricing_currency_id::VARCHAR(255)) as name,
            (pricing_currency_id::VARCHAR(255)) as user_code,
            (0) as position_size,
            ('missing_instrument_currency_fx_rate') as type
        from nav_positions WHERE instrument_pricing_currency_fx_rate ISNULL 
        
        UNION 
        
        select 
            DISTINCT accrued_currency_id,
            (accrued_currency_id::VARCHAR(255)) as name,
            (accrued_currency_id::VARCHAR(255)) as user_code,
            (0) as position_size,
            ('missing_instrument_currency_fx_rate') as type
        from nav_positions WHERE instrument_accrued_currency_fx_rate ISNULL
        
        UNION
        
        select 
            DISTINCT id,
            name,
            user_code,
            (0) as position_size,
            ('missing_report_currency_fx_rate') as type
        from currencies_currency ch1
        where 
            (
                select 
                    currency_id 
                from currencies_currencyhistory ch2
                where 
                    ch2.date = '{report_date}' and 
                    ch2.pricing_policy_id = {pricing_policy_id} and 
                    ch2.currency_id = ch1.id
            ) ISNULL
            and
              ch1.master_user_id = {master_user_id}
            and
              ch1.id = {report_currency_id}
            and {report_currency_id} != {default_currency_id}
    """

    consolidated_cash_columns = get_cash_consolidation_for_select(instance)
    consolidated_position_columns = get_position_consolidation_for_select(instance)
    consolidated_cash_as_position_columns = get_cash_as_position_consolidation_for_select(instance)

    transaction_filter_sql_string = get_transaction_filter_sql_string(instance)

    query = query.format(report_date=date,
                         master_user_id=instance.master_user.id,
                         default_currency_id=ecosystem_defaults.currency_id,
                         report_currency_id=instance.report_currency.id,
                         pricing_policy_id=instance.pricing_policy.id,

                         consolidated_cash_columns=consolidated_cash_columns,
                         consolidated_position_columns=consolidated_position_columns,
                         consolidated_cash_as_position_columns=consolidated_cash_as_position_columns,

                         transaction_filter_sql_string=transaction_filter_sql_string
                         )

    cursor.execute(query)

    query_str = str(cursor.query, 'utf-8')

    if settings.SERVER_TYPE == 'local':
        with open('/tmp/query_result.txt', 'w') as the_file:
            the_file.write(query_str)

    result = dictfetchall(cursor)

    return result


def execute_transaction_prices_sql(date, instance, cursor, ecosystem_defaults):
    # language=PostgreSQL
    query = """
            with 
            pl_transactions_with_ttype_filtered as (
                select * from pl_transactions_with_ttype
                {transaction_filter_sql_string}
            ),
            
            transactions_hist as (
            
                select 
                
                   accounting_date,
                   transaction_class_id,

                   instrument_id,
                   position_size_with_sign,
                   
                   transaction_currency_id,
                   settlement_currency_id,
                   
                   (ct.name) as transaction_currency_name,
                   (ct.user_code) as transaction_currency_user_code,
                   
                   (cs.name) as settlement_currency_name,
                   (cs.user_code) as settlement_currency_user_code,
                   
                   reference_fx_rate,
                   
                   case 
                        when cash_date < accounting_date
                        then cash_date
                        else accounting_date
                   end
                   as min_date,
                   
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
                       when {report_currency_id} = {default_currency_id}
                           then 1
                       else
                           (select fx_rate
                            from currencies_currencyhistory c_ch
                            where c_ch.date = accounting_date and 
                                c_ch.currency_id = {report_currency_id} and
                                c_ch.pricing_policy_id = {pricing_policy_id}
                            limit 1)
                  end as rep_hist_fx,
                  
                  case
                       when
                           settlement_currency_id = {default_currency_id} -- system currency
                           then 1
                       else
                           (select fx_rate
                            from currencies_currencyhistory c_ch
                            where date = '{report_date}'
                              and c_ch.currency_id = settlement_currency_id
                              and c_ch.pricing_policy_id = {pricing_policy_id}
                            limit 1)
                  end as stl_cur_fx
                
                from pl_transactions_with_ttype_filtered t
                left join currencies_currency ct on transaction_currency_id = ct.id
                left join currencies_currency cs on settlement_currency_id = cs.id
                where t.master_user_id = {master_user_id}
               
                
            )
            
            -- optional start
            select DISTINCT
                ('fixed_calc') as type,
                accounting_date,
                transaction_currency_id,
                
                transaction_currency_name,
                transaction_currency_user_code
                
            from transactions_hist
            where trn_hist_fx ISNULL and not transaction_class_id in (8,9,12,13)
            and  min_date <= '{report_date}'
            
            UNION 
            
            select DISTINCT
                ('rep_fixed_calc') as type,
                accounting_date,
                ({report_currency_id}) as report_currency_id,
                
                transaction_currency_name,
                transaction_currency_user_code
            from transactions_hist
            where rep_hist_fx ISNULL and not transaction_class_id in (8,9,12,13)
            and  min_date <= '{report_date}'
            
            -- optional end
            
            -- required start
            
            UNION 
            
            select DISTINCT
                ('stl_cur_fx') as type,
                ('{report_date}'::DATE) as report_date,
                settlement_currency_id,
                
                transaction_currency_name,
                transaction_currency_user_code
            from transactions_hist
            where stl_cur_fx ISNULL 
            and  min_date <= '{report_date}'
            
            UNION 
            
            
            select DISTINCT
                ('fx_var') as type,
                accounting_date,
                transaction_currency_id,
                transaction_currency_name,
                transaction_currency_user_code
            from transactions_hist
            where trn_hist_fx ISNULL and transaction_class_id in (8,9,12,13)
            and  min_date <= '{report_date}'
            
            UNION 
            
            select DISTINCT
                ('rep_fx_var') as type,
                accounting_date,
                ({report_currency_id}) as report_currency_id,
                transaction_currency_name,
                transaction_currency_user_code
            from transactions_hist
            where rep_hist_fx ISNULL and transaction_class_id in (8,9,12,13)
            and  min_date <= '{report_date}'
            
            -- required end
            
            
    """

    consolidated_cash_columns = get_cash_consolidation_for_select(instance)
    consolidated_position_columns = get_position_consolidation_for_select(instance)
    consolidated_cash_as_position_columns = get_cash_as_position_consolidation_for_select(instance)

    transaction_filter_sql_string = get_transaction_filter_sql_string(instance)

    query = query.format(report_date=date,
                         master_user_id=instance.master_user.id,
                         default_currency_id=ecosystem_defaults.currency_id,
                         report_currency_id=instance.report_currency.id,
                         pricing_policy_id=instance.pricing_policy.id,

                         consolidated_cash_columns=consolidated_cash_columns,
                         consolidated_position_columns=consolidated_position_columns,
                         consolidated_cash_as_position_columns=consolidated_cash_as_position_columns,

                         transaction_filter_sql_string=transaction_filter_sql_string
                         )

    if settings.SERVER_TYPE == 'local':
        with open('/tmp/price_check_query_raw.txt', 'w') as the_file:
            the_file.write(query)

    cursor.execute(query)

    query_str = str(cursor.query, 'utf-8')

    if settings.SERVER_TYPE == 'local':
        with open('/tmp/price_check_query_result.txt', 'w') as the_file:
            the_file.write(query_str)

    result = dictfetchall(cursor)

    return result


class PriceHistoryCheckerSql:

    def __init__(self, instance=None):

        _l.debug('PriceHistoryCheckerSql init')

        self.instance = instance

        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self.instance.master_user)

    def process(self):

        st = time.perf_counter()

        with connection.cursor() as cursor:

            self.instance.items = []

            # pl first date

            if self.instance.pl_first_date:
                positions = execute_nav_sql(self.instance.pl_first_date, self.instance, cursor, self.ecosystem_defaults)

                for item in positions:
                    if item['user_code'] != '-' and item['name'] != '-':

                        item['position_size'] = round(item['position_size'], settings.ROUND_NDIGITS)

                        if item['type'] == 'missing_principal_pricing_history':
                            if item['position_size']:
                                self.instance.items.append(item)
                        else:
                            self.instance.items.append(item)

                # self.instance.items = self.instance.items + positions

                transactions = execute_transaction_prices_sql(self.instance.pl_first_date, self.instance, cursor,
                                                              self.ecosystem_defaults)

                _l.debug('transactions %s ' % len(transactions))

                self.instance.items = self.instance.items + transactions

            # report date

            positions = execute_nav_sql(self.instance.report_date, self.instance, cursor, self.ecosystem_defaults)

            for item in positions:
                if item['user_code'] != '-' and item['name'] != '-':

                    item['position_size'] = round(item['position_size'], settings.ROUND_NDIGITS)

                    if item['type'] == 'missing_principal_pricing_history':
                        if item['position_size']:
                            self.instance.items.append(item)
                    else:
                        self.instance.items.append(item)

            # self.instance.items = self.instance.items + positions

            transactions = execute_transaction_prices_sql(self.instance.report_date, self.instance, cursor,
                                                          self.ecosystem_defaults)

            _l.debug('transactions %s ' % len(transactions))

            self.instance.items = self.instance.items + transactions

            unique_items_dict = {}
            unique_items = []

            for item in self.instance.items:

                try:
                    if 'user_code' in item:
                        unique_items_dict[item['type'] + '_' + item['user_code']] = item
                    elif 'name' in item:
                        unique_items_dict[item['type'] + '_' + item['name']] = item
                    elif 'transaction_currency_user_code' in item:
                        unique_items_dict[item['type'] + '_' + item['transaction_currency_user_code']] = item
                    elif 'settlement_currency_user_code' in item:
                        unique_items_dict[item['type'] + '_' + item['settlement_currency_user_code']] = item
                except Exception as e:
                    _l.info('error %s' % e)
                    _l.info(item)

            for key, value in unique_items_dict.items():
                unique_items.append(unique_items_dict[key])

            self.instance.items = unique_items

        self.add_data_items()

        _l.debug('Price History check query execute done: %s', "{:3.3f}".format(time.perf_counter() - st))

        return self.instance

    def add_data_items_instruments(self, ids):

        self.instance.item_instruments = Instrument.objects.select_related(
            'instrument_type',
            'instrument_type__instrument_class',
            'pricing_currency',
            'accrued_currency',
            'payment_size_detail',
            'daily_pricing_model',
            # 'price_download_scheme',
            # 'price_download_scheme__provider',
        ).prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
            'pricing_policies',
            'pricing_policies__pricing_scheme'
        ).filter(master_user=self.instance.master_user) \
            .filter(id__in=ids)

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

        item_relations_st = time.perf_counter()

        instrument_ids = []
        currencies_ids = []

        dash_currency = Currency.objects.get(user_code='-', master_user=self.instance.master_user)

        items_without_dash_currency = []

        print('dash_currency %s' % dash_currency.id)

        for item in self.instance.items:

            is_not_dash = True

            if item['type'] == 'missing_principal_pricing_history':
                instrument_ids.append(item['id'])

            if item['type'] == 'missing_instrument_currency_fx_rate':
                currencies_ids.append(item['id'])

                if item['id'] == dash_currency.id:
                    is_not_dash = False

            if item['type'] == 'fixed_calc':
                currencies_ids.append(item['transaction_currency_id'])

                if item['transaction_currency_id'] == dash_currency.id:
                    is_not_dash = False

            if item['type'] == 'stl_cur_fx':
                currencies_ids.append(item['transaction_currency_id'])

                if item['transaction_currency_id'] == dash_currency.id:
                    is_not_dash = False

            if item['type'] == 'rep_fx_var':
                currencies_ids.append(item['transaction_currency_id'])

                if item['transaction_currency_id'] == dash_currency.id:
                    is_not_dash = False

            if is_not_dash:
                items_without_dash_currency.append(item)

        self.instance.items = items_without_dash_currency

        _l.debug('len instrument_ids %s' % len(instrument_ids))

        self.add_data_items_instruments(instrument_ids)

        self.add_data_items_currencies(currencies_ids)

        _l.debug('_refresh_with_perms_optimized item relations done: %s',
                 "{:3.3f}".format(time.perf_counter() - item_relations_st))
