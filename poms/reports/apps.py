from __future__ import unicode_literals

import logging

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db import connection
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy

from poms_app import settings

_l = logging.getLogger('provision')


class ReportsConfig(AppConfig):
    name = 'poms.reports'
    # label = 'poms_reports'
    verbose_name = gettext_lazy('Reports')

    def ready(self):
        post_migrate.connect(self.create_views_for_sql_reports, sender=self)

    def create_views_for_sql_reports(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):

        _l.debug("Creating views for SQL reports")

        if settings.DROP_VIEWS:
            self.create_view_for_positions()
            self.create_view_for_cash_fx_trades()
            self.create_view_for_cash_fx_variations()
            self.create_view_for_cash_transaction_pl()

    def create_view_for_positions(self):

        try:

            _l.debug("create_view_for_positions")

            with connection.cursor() as cursor:

                query = "DROP VIEW IF EXISTS pl_transactions_with_ttype"

                cursor.execute(query)

                query = """
                    CREATE or REPLACE VIEW pl_transactions_with_ttype AS
                        SELECT
                        
                           id,
                           master_user_id,
                           transaction_class_id,
                           transaction_code,
                           
                           transaction_date,
                           accounting_date,
                           cash_date,
                           
                           cash_consideration,
                           position_size_with_sign,
                           principal_with_sign,
                           carry_with_sign,
                           overheads_with_sign,
                           instrument_id,
                           linked_instrument_id,
                           portfolio_id,
                           account_position_id,
                           account_cash_id,
                           account_interim_id,
                           
                           strategy1_position_id,
                           strategy1_cash_id,
                           strategy2_position_id,
                           strategy2_cash_id,
                           strategy3_position_id,
                           strategy3_cash_id,
                           
                           transaction_currency_id,
                           settlement_currency_id,
                           
                           reference_fx_rate,
                           ytm_at_cost,
                           
                           allocation_balance_id,
                           allocation_pl_id,
                           
                           case 
                                when cash_date < accounting_date
                                then cash_date
                                else accounting_date
                           end
                           as min_date,
                           
                           case
                             
                             when transaction_class_id = 4
                                then 4
                             when position_size_with_sign < 0
                               then 0
                             else 1
                             end as ttype
                        FROM transactions_transaction
                        WHERE transaction_class_id in (1,2,4,14) and NOT is_canceled AND NOT is_deleted
                        
                        UNION ALL
                        
                        select
                        
                          id,
                          master_user_id,
                          (1) as transaction_class_id,
                          transaction_code,
                          
                          transaction_date,
                          accounting_date,
                          cash_date,
                          
                          cash_consideration,
                          position_size_with_sign,
                          (-principal_with_sign) as principal_with_sign,
                          (-carry_with_sign) as carry_with_sign,
                          (-overheads_with_sign) as overheads_with_sign,
                          instrument_id,
                          linked_instrument_id,
                          portfolio_id,
                          account_cash_id as account_position_id,
                          account_cash_id,
                          account_interim_id,
                          strategy1_cash_id as strategy1_position_id,
                          strategy1_cash_id,
                          strategy2_cash_id as strategy2_position_id,
                          strategy2_cash_id,
                          strategy3_cash_id as strategy3_position_id,
                          strategy3_cash_id,
                          
                          transaction_currency_id,
                          settlement_currency_id,
                          
                          reference_fx_rate,
                          ytm_at_cost,
                          
                          allocation_balance_id,
                          allocation_pl_id,
                          
                          case 
                                when cash_date < accounting_date
                                then cash_date
                                else accounting_date
                           end
                           as min_date,
                          
                          case
                            when position_size_with_sign < 0
                              then 0
                            else 1
                            end as ttype
                        from transactions_transaction
                        WHERE transaction_class_id in (6) and NOT is_canceled AND NOT is_deleted
                        
                        UNION ALL
                        
                        select

                          id,
                          master_user_id,
                          (2) as transaction_class_id,
                          transaction_code,
                          
                          transaction_date,
                          accounting_date,
                          cash_date,
                          
                          cash_consideration,
                          (-position_size_with_sign) as position_size_with_sign,
                          principal_with_sign,
                          carry_with_sign,
                          overheads_with_sign,
                          instrument_id,
                          linked_instrument_id,
                          portfolio_id,
                          account_position_id,
                          account_position_id as account_cash_id,
                          account_interim_id,
                          strategy1_position_id,
                          strategy1_position_id as strategy1_cash_id,
                          strategy2_position_id,
                          strategy2_position_id as strategy2_cash_id,
                          strategy3_position_id,
                          strategy3_position_id as strategy3_cash_id,
                          
                          transaction_currency_id,
                          settlement_currency_id,
                          
                          reference_fx_rate,
                          ytm_at_cost,
                          
                          allocation_balance_id,
                          allocation_pl_id,
                          
                          case 
                                when cash_date < accounting_date
                                then cash_date
                                else accounting_date
                           end
                           as min_date,
                          
                          case
                            when (-position_size_with_sign) < 0 
                              then 0
                            else 1
                            end as ttype
                        from transactions_transaction 
                        WHERE transaction_class_id in (6) and NOT is_canceled AND NOT is_deleted;            
                """

                cursor.execute(query)

        except Exception as e:
            _l.debug("create_view_for_positions %s" % e)

    def create_view_for_cash_fx_trades(self):

        _l.debug("create_view_for_cash_fx_trades")

        with connection.cursor() as cursor:
            query = "DROP VIEW IF EXISTS pl_cash_fx_trades_transactions_with_ttype"

            cursor.execute(query)

            query = """
                CREATE or REPLACE VIEW pl_cash_fx_trades_transactions_with_ttype AS
                    (
                    select 

                        tt.id,
                         tt.master_user_id,
                       
                       transaction_date,
                       accounting_date, 
                       cash_date,
                       
                       (1001) as transaction_class_id,
                       
                       transaction_code,
                       notes,
                       
                       position_size_with_sign as cash_consideration,
                       
                       position_size_with_sign as principal_with_sign,
                       0                       as carry_with_sign,
                       0                       as overheads_with_sign,
                       
                       portfolio_id,
                       instrument_id,
                       
                       transaction_currency_id as settlement_currency_id,
                       transaction_currency_id,
                       
                       reference_fx_rate,
                       ytm_at_cost,
                       
                       account_interim_id,
                     
                         
                         -- order matters
                         account_position_id,
                         account_position_id        as account_cash_id,
                        
                          strategy1_position_id,
                         strategy1_position_id      as strategy1_cash_id,
                        
                         strategy2_position_id,
                         strategy2_position_id      as strategy2_cash_id,
                         
                         strategy3_position_id,
                         strategy3_position_id      as strategy3_cash_id,
                         
                         allocation_balance_id,
                         allocation_pl_id
                         

                from transactions_transaction tt
                where transaction_class_id in (3) and NOT tt.is_canceled AND NOT tt.is_deleted
                
                union
                
                select 
                
                     tt.id,
                     tt.master_user_id,
                       
                       transaction_date,
                       accounting_date,
                       cash_date,
                       
                       (1002) as transaction_class_id,
                       
                       transaction_code,
                       notes,
                       
                       cash_consideration,
                       
                       principal_with_sign,
                       carry_with_sign,
                       overheads_with_sign,
                       
                       portfolio_id,
                       instrument_id,
                       
                       settlement_currency_id,
                       transaction_currency_id,
                       
                       
                       reference_fx_rate,
                       ytm_at_cost,
                       
                        account_interim_id,
                     
                         -- order matters
                         account_position_id,
                         account_cash_id,
                         
                         strategy1_position_id,
                         strategy1_cash_id,
                         
                         strategy2_position_id,
                         strategy2_cash_id,
                        
                         strategy3_position_id,
                         strategy3_cash_id,
                         allocation_balance_id,
                         allocation_pl_id
                     
              /*перечислить все поля*/

          from transactions_transaction tt
          where transaction_class_id in (3) and NOT tt.is_canceled AND NOT tt.is_deleted

         )         
            """

            cursor.execute(query)

    def create_view_for_cash_fx_variations(self):

        _l.debug("create_view_for_cash_fx_variations")

        with connection.cursor() as cursor:
            query = "DROP VIEW IF EXISTS pl_cash_fx_variations_transactions_with_ttype"

            cursor.execute(query)

            query = """
                CREATE or REPLACE VIEW pl_cash_fx_variations_transactions_with_ttype AS
                    select
                            
                           tt.id,
                           tt.master_user_id,
                           
                           transaction_date,
                           accounting_date,
                           cash_date,
                           
                           transaction_class_id,
                           
                           transaction_code,
                           notes,
                           
                           position_size_with_sign,
                           cash_consideration,
                           
                           principal_with_sign,
                           carry_with_sign,
                           overheads_with_sign,
                           
                           portfolio_id,
                           instrument_id,
                           
                           transaction_currency_id,
                           settlement_currency_id,
                           
                           reference_fx_rate,
                           ytm_at_cost,
                           
                           account_interim_id,
                           
                           account_position_id,
                           account_cash_id,
                           
                           strategy1_position_id,
                           strategy1_cash_id,
                           
                           strategy2_position_id,
                           strategy2_cash_id,
                           
                           strategy3_position_id,
                           strategy3_cash_id,
                           allocation_balance_id,
                           allocation_pl_id
                           

                    from transactions_transaction as tt
                    where transaction_class_id in (8,9,12,13,15) and NOT tt.is_canceled AND NOT tt.is_deleted
                    
                    union all

                    select 

                         tt.id,
                         tt.master_user_id,
                         
                         transaction_date,
                         accounting_date,
                         cash_date,
                    
                         8 as transaction_class_id,
                         
                         transaction_code,
                         notes,
                         
                         position_size_with_sign,
                         cash_consideration,
                         
                         principal_with_sign,
                         carry_with_sign,
                         overheads_with_sign,

                         portfolio_id,
                         instrument_id,
                         
                         settlement_currency_id,
                         transaction_currency_id,
                         
                         reference_fx_rate,
                         ytm_at_cost,
                         
                          account_interim_id,
                         
                         -- order matters
                         (account_cash_id) as account_position_id,
                         account_cash_id,
                         
                         (strategy1_cash_id) as strategy1_position_id,
                          strategy1_cash_id,
                          
                          (strategy2_cash_id) as strategy2_position_id,
                          strategy2_cash_id,
                          
                          (strategy3_cash_id) as strategy3_position_id,
                          strategy3_cash_id,
                          
                          allocation_balance_id,
                          allocation_pl_id
                         
                      from transactions_transaction tt
                      where transaction_class_id in (7) and NOT tt.is_canceled AND NOT tt.is_deleted
                          
                    union all

                    select 
                    
                         tt.id,
                         tt.master_user_id,
                         
                         transaction_date,
                         accounting_date,
                         cash_date,
                    
                         9 as transaction_class_id,
                         
                         transaction_code,
                         notes,
                         
                         position_size_with_sign,
                         -cash_consideration as cash_consideration,
                         
                         principal_with_sign,
                         carry_with_sign,
                         overheads_with_sign,

                         portfolio_id,
                         instrument_id,
                         
                         settlement_currency_id,
                         transaction_currency_id,
                         
                         reference_fx_rate,
                         ytm_at_cost,
                         
                          account_interim_id,
                         
                         -- order matters
                          account_position_id,
                         (account_position_id) as account_cash_id,
                        
                         (strategy1_cash_id) as strategy1_position_id,
                         strategy1_cash_id,
                         
                         (strategy2_cash_id) as strategy2_position_id,
                         strategy2_cash_id,
                         
                         (strategy1_cash_id) as strategy1_position_id,
                         strategy2_cash_id,
                         
                         allocation_balance_id,
                         allocation_pl_id
                         
                    from transactions_transaction tt
                    where transaction_class_id in (7) and NOT tt.is_canceled AND NOT tt.is_deleted
                           
            """

            cursor.execute(query)

    def create_view_for_cash_transaction_pl(self):

        _l.debug("create_view_for_cash_transaction_pl")

        with connection.cursor() as cursor:
            query = "DROP VIEW IF EXISTS pl_cash_transaction_pl_transactions_with_ttype"

            cursor.execute(query)

            query = """
                CREATE or REPLACE VIEW pl_cash_transaction_pl_transactions_with_ttype AS
                    (
                    select 
                    
                        tt.id,
                         tt.master_user_id,
                       
                       transaction_date,
                       accounting_date,
                       cash_date,
                       
                       transaction_class_id,
                       
                       transaction_code,
                       notes,
                       
                       position_size_with_sign,
                       cash_consideration,
                       
                       principal_with_sign,
                       carry_with_sign,
                       overheads_with_sign,
                       
                       portfolio_id,
                       instrument_id,
                       
                       settlement_currency_id,
                       transaction_currency_id,
                       
                       reference_fx_rate,
                       ytm_at_cost,
                       
                       account_interim_id,
                     
                         
                         -- order matters
                         account_position_id,
                         account_cash_id,
                        
                          strategy1_position_id,
                         strategy1_cash_id,
                        
                         strategy2_position_id,
                         strategy2_cash_id,
                         
                         strategy3_position_id,
                         strategy3_cash_id,
                         
                         allocation_balance_id,
                         allocation_pl_id
                         

                from transactions_transaction tt
                where transaction_class_id in (5) and NOT tt.is_canceled AND NOT tt.is_deleted
                )         
            """

            cursor.execute(query)
