import time
import traceback

from django.db.models import Q

from poms.common import formula
from poms.currencies.models import CurrencyHistory
from poms.instruments.models import PriceHistory
from poms.integrations.providers.base import parse_date_iso

from poms.pricing.currency_handler import PricingCurrencyHandler
from poms.pricing.instrument_handler import PricingInstrumentHandler
from poms.pricing.models import PricingProcedureBloombergInstrumentResult, PricingProcedureBloombergCurrencyResult, \
    PricingProcedureWtradeInstrumentResult, PriceHistoryError, \
    CurrencyHistoryError, PricingProcedureFixerCurrencyResult, \
    PricingProcedureAlphavInstrumentResult, PricingProcedureBloombergForwardInstrumentResult, \
    PricingProcedureCbondsInstrumentResult, PricingProcedureCbondsCurrencyResult

import logging

from poms.pricing.utils import roll_price_history_for_n_day_forward, roll_currency_history_for_n_day_forward, \
    convert_results_for_calc_avg_price
from poms.procedures.models import PricingProcedureInstance, PricingParentProcedureInstance, BaseProcedureInstance
from poms.reports.builders.balance_item import Report
from poms.reports.builders.balance_pl import ReportBuilder
from poms.transactions.models import Transaction

_l = logging.getLogger('poms.pricing')


class PricingProcedureProcess(object):

    def __init__(self, procedure=None, master_user=None, date_from=None, date_to=None, member=None, schedule_instance=None):

        _l.debug('PricingProcedureProcess. Master user: %s. Procedure: %s' % (master_user, procedure))

        self.master_user = master_user
        self.procedure = procedure

        self.member = member
        self.schedule_instance = schedule_instance

        self.execute_procedure_date_expressions()

        if date_from:
            self.procedure.price_date_from = date_from
        if date_to:
            _l.debug("Date To set from user Settings")
            self.procedure.price_date_to = date_to

        _l.debug('price_date_from %s' % self.procedure.price_date_from)
        _l.debug('price_date_to %s' % self.procedure.price_date_to)

        self.parent_procedure = PricingParentProcedureInstance(procedure=procedure, master_user=master_user)
        self.parent_procedure.save()

        self.pricing_instrument_handler = PricingInstrumentHandler(procedure=procedure,
                                                                   parent_procedure=self.parent_procedure,
                                                                   master_user=master_user,
                                                                   member=self.member,
                                                                   schedule_instance=self.schedule_instance)
        self.pricing_currency_handler = PricingCurrencyHandler(procedure=procedure,
                                                               parent_procedure=self.parent_procedure,
                                                               master_user=master_user,
                                                               member=self.member,
                                                               schedule_instance=self.schedule_instance)

        _l.debug("Procedure settings - Get Principal Prices: %s" % self.procedure.price_get_principal_prices)
        _l.debug("Procedure settings - Get Accrued Prices: %s" % self.procedure.price_get_accrued_prices)
        _l.debug("Procedure settings - Get FX Rates: %s" % self.procedure.price_get_fx_rates)
        _l.debug("Procedure settings - Overwrite Principal Prices: %s" % self.procedure.price_overwrite_principal_prices)
        _l.debug("Procedure settings - Overwrite Accrued Prices: %s" % self.procedure.price_overwrite_accrued_prices)
        _l.debug("Procedure settings - Overwrite FX Rates: %s" % self.procedure.price_overwrite_fx_rates)
        _l.debug("Procedure settings - Roll Days N Forward: %s" % self.procedure.price_fill_days)

    def get_base_transactions(self):

        processing_st = time.perf_counter()

        results = Transaction.objects.filter(master_user=self.procedure.master_user)

        results = results.filter(Q(accounting_date__lte=self.procedure.price_date_to) | Q(cash_date__lte=self.procedure.price_date_to))

        # We are looking for transaction with the earliest date from account/settlement dates
        # results = results.filter(Q(accounting_date__gt=self.procedure.price_date_from) | Q(cash_date__gt=self.procedure.price_date_from))

        # Here the same pattern, we are looking for the earliest date
        # so firstly get slice by accounting date (order is not important, but we require both filters)
        # results = results.filter(accounting_date__lte=self.procedure.price_date_to)
        # Then we filter our result even more

        # Filter pattern in other words:
        # date_from < Min(accounting_date, cash_date) <= date_to

        # results = results.filter(cash_date__lte=self.procedure.price_date_to)

        if self.procedure.portfolio_filters:

            portfolio_user_codes = self.procedure.portfolio_filters.split(",")

            results = results.filter(portfolio__user_code__in=portfolio_user_codes)

        results = list(results)  # execute query

        _l.debug('< get_base_transactions len %s', len(results))
        _l.debug('< get_base_transactions done in %s', (time.perf_counter() - processing_st))

        return results

    def execute_procedure_date_expressions(self):

        if self.procedure.price_date_from_expr:
            try:
                self.procedure.price_date_from = formula.safe_eval(self.procedure.price_date_from_expr, names={})
            except formula.InvalidExpression as e:
                _l.debug("Cant execute price date from expression %s " % e)

        if self.procedure.price_date_to_expr:
            try:
                self.procedure.price_date_to = formula.safe_eval(self.procedure.price_date_to_expr, names={})
            except formula.InvalidExpression as e:
                _l.debug("Cant execute price date to expression %s " % e)

    def process(self):

        if self.procedure.price_get_principal_prices or self.procedure.price_get_accrued_prices:
            self.pricing_instrument_handler.process()

        if self.procedure.price_get_fx_rates:
            self.pricing_currency_handler.process()


class FillPricesBrokerBloombergProcess(object):

    def __init__(self, instance, master_user):

        self.instance = instance
        self.master_user = master_user

        self.procedure_instance = PricingProcedureInstance.objects.get(pk=self.instance['procedure'])
        self.procedure = self.procedure_instance.procedure



        _l.debug("Broker Bloomberg - Get Principal Prices: %s" % self.procedure.price_get_principal_prices)
        _l.debug("Broker Bloomberg - Get Accrued Prices: %s" % self.procedure.price_get_accrued_prices)
        _l.debug("Broker Bloomberg - Get FX Rates: %s" % self.procedure.price_get_fx_rates)
        _l.debug("Broker Bloomberg - Overwrite Principal Prices: %s" % self.procedure.price_overwrite_principal_prices)
        _l.debug("Broker Bloomberg - Overwrite Accrued Prices: %s" % self.procedure.price_overwrite_accrued_prices)
        _l.debug("Broker Bloomberg - Overwrite FX Rates: %s" % self.procedure.price_overwrite_fx_rates)
        _l.debug("Broker Bloomberg - Roll Days N Forward: %s" % self.procedure.price_fill_days)

    def process(self):

        _l.debug('< fill prices: total items len %s' % len(self.instance['data']['items']))
        _l.debug('< action:  %s' % self.instance['action'])

        if self.instance['action'] == 'bloomberg_get_currency_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureBloombergCurrencyResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference'],
                    currency_parameters=str(item['parameters'])
                )

                _l.debug('< fill currency prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                _l.debug('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if record.fx_rate_parameters:
                                    if field['code'] in record.fx_rate_parameters:

                                        try:
                                            record.fx_rate_value = float(val_obj['value'])
                                        except Exception as e:
                                            _l.debug('fx_rate_value e %s ' % e)

                                        try:
                                            record.fx_rate_value_error_text = val_obj['error_text']
                                        except Exception as e:
                                            _l.debug('fx_rate_value_error_text e %s ' % e)

                                record.save()

                        if not len(records):
                            _l.debug('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                _l.debug('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_currency_history()

            _l.debug("process fill currency prices")

        elif self.instance['action'] == 'bloomberg_get_instrument_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureBloombergInstrumentResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference'],
                    instrument_parameters=str(item['parameters'])
                )

                _l.debug('< fill instrument prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                _l.debug('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if record.ask_parameters:
                                    if field['code'] in record.ask_parameters:

                                        try:
                                            record.ask_value = float(val_obj['value'])
                                        except Exception as e:
                                            _l.debug('ask value e %s ' % e)

                                        try:
                                                record.ask_value_error_text = val_obj['error_text']
                                        except Exception as e:
                                            _l.debug('ask_value_error_text e %s ' % e)

                                if record.bid_parameters:
                                    if field['code'] in record.bid_parameters:

                                        try:
                                            record.bid_value = float(val_obj['value'])
                                        except Exception as e:
                                             _l.debug('bid value e %s ' % e)

                                        try:
                                            record.bid_value_error_text = val_obj['error_text']
                                        except Exception as e:
                                            _l.debug('bid_value_error_text e %s ' % e)

                                if record.last_parameters:
                                    if field['code'] in record.last_parameters:

                                        try:
                                            record.last_value = float(val_obj['value'])
                                        except Exception as e:
                                            _l.debug('last value e %s ' % e)

                                        try:
                                            record.last_value_error_text = val_obj['error_text']
                                        except Exception as e:
                                            _l.debug('last_value_error_text e %s ' % e)

                                if record.accrual_parameters:
                                    if field['code'] in record.accrual_parameters:

                                        try:
                                            record.accrual_value = float(val_obj['value'])
                                        except Exception as e:
                                            _l.debug('accrual_value value e %s ' % e)

                                        try:
                                            record.accrual_value_error_text = val_obj['error_text']
                                        except Exception as e:
                                            _l.debug('accrual_value_error_text e %s ' % e)

                                record.save()

                        if not len(records):
                            _l.debug('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                _l.debug('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_price_history()

            _l.debug("process fill instrument prices")

    def create_price_history(self):

        _l.debug("Creating price history")

        successful_prices_count = 0
        error_prices_count = 0

        records = PricingProcedureBloombergInstrumentResult.objects.filter(
            master_user=self.master_user,
            procedure=self.instance['procedure'],
            date__gte=self.instance['data']['date_from'],
            date__lte=self.instance['data']['date_to']
        )

        for record in records:

            safe_instrument = {
                'id': record.instrument.id,
            }

            safe_pp = {
                'id': record.pricing_policy.id,
            }

            values = {
                'context_date': record.date,
                'context_instrument': safe_instrument,
                'context_pricing_policy': safe_pp,

                'ask': record.ask_value,
                'bid': record.bid_value,
                'last': record.last_value,
                'accrual': record.accrual_value,

                'ask_error': record.ask_value_error_text,
                'bid_error': record.bid_value_error_text,
                'last_error': record.last_value_error_text,
                'accrual_error': record.accrual_value_error_text
            }

            pricing_scheme_parameters = record.pricing_scheme.get_parameters()

            expr = pricing_scheme_parameters.expr
            accrual_expr = pricing_scheme_parameters.accrual_expr
            pricing_error_text_expr = pricing_scheme_parameters.pricing_error_text_expr
            accrual_error_text_expr = pricing_scheme_parameters.accrual_error_text_expr

            _l.debug('values %s' % values)
            _l.debug('expr %s' % expr)

            has_error = False


            error, created = PriceHistoryError.objects.get_or_create(
                master_user=self.master_user,
                procedure_instance_id=self.instance['procedure'],
                instrument=record.instrument,
                pricing_scheme=record.pricing_scheme,
                pricing_policy=record.pricing_policy,
                date=record.date,
                created=self.procedure_instance.created
            )

            principal_price = None
            accrued_price = None

            try:
                principal_price = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:

                has_error = True

                try:
                    error.error_text = formula.safe_eval(pricing_error_text_expr, names=values)

                except formula.InvalidExpression:

                    error.error_text = 'Invalid Error Text Expression'


            _l.debug('principal_price %s' % principal_price)
            _l.debug('instrument %s' % record.instrument.user_code)
            _l.debug('pricing_policy %s' % record.pricing_policy.user_code)

            if pricing_scheme_parameters.accrual_calculation_method == 2:   # ACCRUAL_PER_SCHEDULE

                try:
                    accrued_price = record.instrument.get_accrued_price(record.date)
                except Exception as e:
                    has_error = True

                    _l.debug('record.instrument.get_accrued_price e %s' % e)
                    _l.debug(traceback.print_exc())

                    try:

                        _l.debug('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.error_text = 'Invalid Error Text Expression'

            if pricing_scheme_parameters.accrual_calculation_method == 3:   # ACCRUAL_PER_FORMULA

                try:
                    accrued_price = formula.safe_eval(accrual_expr, names=values)
                except formula.InvalidExpression:
                    has_error = True

                    try:

                        _l.debug('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.error_text = 'Invalid Error Text Expression'

            can_write = True
            exist = False

            try:

                price = PriceHistory.objects.get(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                exist = True

                if not self.procedure.price_overwrite_principal_prices and not self.procedure.price_overwrite_accrued_prices:
                    can_write = False
                    _l.debug('Skip %s' % price)
                else:
                    _l.debug('Overwrite existing %s' % price)

            except PriceHistory.DoesNotExist:

                price = PriceHistory(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date,
                    principal_price=principal_price
                )

                _l.debug('Create new %s' % price)

            price.principal_price = 0
            price.accrued_price = 0

            price.procedure_modified_datetime = self.procedure_instance.created

            if principal_price:

                if price.id:
                    if self.procedure.price_overwrite_principal_prices:
                        price.principal_price = principal_price
                else:
                    price.principal_price = principal_price

                error.principal_price = principal_price

            if accrued_price:

                if price.id:
                    if self.procedure.price_overwrite_accrued_prices:
                        price.accrued_price = accrued_price
                else:
                    price.accrued_price = accrued_price

                error.accrued_price = accrued_price

            _l.debug('Price: %s. Can write: %s. Has Error: %s.' % (price, can_write, has_error))

            if price.accrued_price == 0 and price.principal_price == 0:
                has_error = True
                error.error_text = error.error_text + ' Price is 0 or null'

            if can_write:

                # if has_error or (price.accrued_price == 0 and price.principal_price == 0):
                if has_error:

                    error_prices_count = error_prices_count + 1
                    error.status = PriceHistoryError.STATUS_ERROR
                    error.save()

                else:

                    successful_prices_count = successful_prices_count + 1

                    error.status = PriceHistoryError.STATUS_CREATED # its journal, not error log
                    error.save()

                    price.save()

            if not can_write and exist:

                error_prices_count = error_prices_count + 1

                error.error_text = "Prices already exists. Principal Price: " + str(principal_price) +"; Accrued: "+ str(accrued_price) +"."

                error.status = PriceHistoryError.STATUS_SKIP
                error.save()

            if self.instance['data']['date_to'] == str(record.date):

                _l.debug("Bloomberg Roll Prices for Price History")

                # roll_price_history_for_n_day_forward(self.procedure, price)

                instrument_pp = record.instrument.pricing_policies.filter(pricing_policy=record.pricing_policy)[0]

                roll_price_history_for_n_day_forward(record, self.procedure, price, self.master_user, self.procedure_instance, instrument_pp)

        PricingProcedureBloombergInstrumentResult.objects.filter(master_user=self.master_user,
                                                       procedure=self.instance['procedure'],
                                                       date__gte=self.instance['data']['date_from'],
                                                       date__lte=self.instance['data']['date_to']).delete()

        _l.debug('bloomberg price procedure_instance %s' % self.procedure_instance)
        _l.debug('bloomberg price successful_prices_count %s' % successful_prices_count)
        _l.debug('bloomberg price error_prices_count %s' % error_prices_count)

        self.procedure_instance.successful_prices_count = successful_prices_count
        self.procedure_instance.error_prices_count = error_prices_count

        self.procedure_instance.status = PricingProcedureInstance.STATUS_DONE

        self.procedure_instance.save()

        _l.debug('bloomberg price self.procedure_instance.successful_prices_count %s' % self.procedure_instance.successful_prices_count)
        _l.debug('bloomberg price self.procedure_instance.error_prices_count %s' % self.procedure_instance.error_prices_count)

        if self.procedure_instance.schedule_instance:
            self.procedure_instance.schedule_instance.run_next_procedure()

    def create_currency_history(self):

        _l.debug("Creating currency history")

        successful_prices_count = 0
        error_prices_count = 0

        records = PricingProcedureBloombergCurrencyResult.objects.filter(
            master_user=self.master_user,
            procedure=self.instance['procedure'],
            date__gte=self.instance['data']['date_from'],
            date__lte=self.instance['data']['date_to']
        )

        _l.debug('create_currency_history: records len %s' % len(records))

        for record in records:

            safe_currency = {
                'id': record.currency.id,
            }

            safe_pp = {
                'id': record.pricing_policy.id
            }

            values = {
                'context_date': record.date,
                'context_currency': safe_currency,
                'context_pricing_policy': safe_pp,
                'fx_rate': record.fx_rate_value,
                'fx_rate_error': record.fx_rate_value_error_text,
            }

            has_error = False
            error, created = CurrencyHistoryError.objects.get_or_create(
                master_user=self.master_user,
                procedure_instance_id=self.instance['procedure'],
                currency=record.currency,
                pricing_scheme=record.pricing_scheme,
                pricing_policy=record.pricing_policy,
                date=record.date,
                created=self.procedure_instance.created
            )

            pricing_scheme_parameters = record.pricing_scheme.get_parameters()

            expr = pricing_scheme_parameters.expr
            error_text_expr = pricing_scheme_parameters.error_text_expr

            _l.debug('values %s' % values)
            _l.debug('expr %s' % expr)

            fx_rate = None

            try:
                fx_rate = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:

                has_error = True

                try:
                    error.error_text = formula.safe_eval(error_text_expr, names=values)
                except formula.InvalidExpression:
                    error.error_text = 'Invalid Error Text Expression'

            _l.debug('fx_rate %s' % fx_rate)
            _l.debug('currency %s' % record.currency.user_code)
            _l.debug('pricing_policy %s' % record.pricing_policy.user_code)

            can_write = True
            exist = False

            try:

                price = CurrencyHistory.objects.get(
                    currency=record.currency,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                exist = True

                if not self.procedure.price_overwrite_fx_rates:
                    can_write = False
                    _l.debug('Skip %s' % price)
                else:
                    _l.debug('Overwrite existing %s' % price)


            except CurrencyHistory.DoesNotExist:

                price = CurrencyHistory(
                    currency=record.currency,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                _l.debug('Create new %s' % price)

            price.fx_rate = 0

            price.procedure_modified_datetime = self.procedure_instance.created

            if fx_rate:
                price.fx_rate = fx_rate

            if can_write:

                if has_error or price.fx_rate == 0:
                # if has_error:

                    error_prices_count = error_prices_count + 1
                    error.status = CurrencyHistoryError.STATUS_ERROR
                    error.save()
                else:

                    successful_prices_count = successful_prices_count + 1

                    error.status = CurrencyHistoryError.STATUS_CREATED # its journal, not error log
                    error.save()

                    price.save()

            if not can_write and exist:

                error_prices_count = error_prices_count + 1

                error.error_text = "Prices already exists. Fx rate: " + str(fx_rate) + "."

                error.status = CurrencyHistoryError.STATUS_SKIP
                error.save()

            if parse_date_iso(self.instance['data']['date_to']) == record.date:

                _l.debug("Bloomberg Roll Prices for Currency History")

                successes, errors = roll_currency_history_for_n_day_forward(record, self.procedure, price, self.master_user, self.procedure_instance)

                successful_prices_count = successful_prices_count + successes
                error_prices_count = error_prices_count + errors

        PricingProcedureBloombergCurrencyResult.objects.filter(master_user=self.master_user,
                                                                 procedure=self.instance['procedure'],
                                                                 date__gte=self.instance['data']['date_from'],
                                                                 date__lte=self.instance['data']['date_to']).delete()

        self.procedure_instance.successful_prices_count = successful_prices_count
        self.procedure_instance.error_prices_count = error_prices_count

        self.procedure_instance.status = PricingProcedureInstance.STATUS_DONE

        self.procedure_instance.save()

        if self.procedure_instance.schedule_instance:
            self.procedure_instance.schedule_instance.run_next_procedure()


class FillPricesBrokerBloombergForwardsProcess(object):

    def __init__(self, instance, master_user):

        self.instance = instance
        self.master_user = master_user

        self.procedure_instance = PricingProcedureInstance.objects.get(pk=self.instance['procedure'])
        self.procedure = self.procedure_instance.procedure

        _l.debug("Broker Bloomberg Forwards - Get Principal Prices: %s" % self.procedure.price_get_principal_prices)
        _l.debug("Broker Bloomberg Forwards - Get Accrued Prices: %s" % self.procedure.price_get_accrued_prices)
        _l.debug("Broker Bloomberg Forwards - Get FX Rates: %s" % self.procedure.price_get_fx_rates)
        _l.debug("Broker Bloomberg Forwards - Overwrite Principal Prices: %s" % self.procedure.price_overwrite_principal_prices)
        _l.debug("Broker Bloomberg Forwards - Overwrite Accrued Prices: %s" % self.procedure.price_overwrite_accrued_prices)
        _l.debug("Broker Bloomberg Forwards - Overwrite FX Rates: %s" % self.procedure.price_overwrite_fx_rates)
        _l.debug("Broker Bloomberg Forwards - Roll Days N Forward: %s" % self.procedure.price_fill_days)

    def process(self):

        _l.debug('< fill prices: total items len %s' % len(self.instance['data']['items']))
        _l.debug('< action:  %s' % self.instance['action'])

        if self.instance['action'] == 'bloomberg_forwards_get_instrument_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureBloombergForwardInstrumentResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference']
                )

                _l.debug('< fill instrument prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                # _l.debug('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if record.price_code_parameters:
                                    if field['code'] in record.price_code_parameters:

                                        try:
                                            record.price_code_value = float(val_obj['value'])
                                        except Exception as e:
                                            _l.debug('price_code_value %s ' % e)
                                            _l.debug('price_code_value original value %s ' % val_obj['value'])

                                        try:
                                            record.price_code_value_error_text = val_obj['error_text']
                                        except Exception as e:
                                            _l.debug('price_code_value_error_text e %s ' % e)

                                record.save()

                        if not len(records):
                            _l.debug('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                _l.debug('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_price_history()

            _l.debug("process fill instrument prices")

    def create_price_history(self):

        _l.debug("Creating price history")

        successful_prices_count = 0
        error_prices_count = 0

        broker_results = PricingProcedureBloombergForwardInstrumentResult.objects.filter(
            master_user=self.master_user,
            procedure=self.instance['procedure'],
            date__gte=self.instance['data']['date_from'],
            date__lte=self.instance['data']['date_to']
        )

        records = convert_results_for_calc_avg_price(broker_results)

        for record in records:

            safe_instrument = {
                'id': record.instrument.id,
            }

            safe_pp = {
                'id': record.pricing_policy.id
            }

            values = {
                'context_date': record.date,
                'context_instrument': safe_instrument,
                'context_pricing_policy': safe_pp,
                'price': record.average_weighted_price,
                'price_error': record.price_code_value_error_text,
            }

            pricing_scheme_parameters = record.pricing_scheme.get_parameters()

            expr = pricing_scheme_parameters.expr
            accrual_expr = pricing_scheme_parameters.accrual_expr
            pricing_error_text_expr = pricing_scheme_parameters.pricing_error_text_expr
            accrual_error_text_expr = pricing_scheme_parameters.accrual_error_text_expr

            _l.debug('values %s' % values)
            _l.debug('expr %s' % expr)

            has_error = False
            error = PriceHistoryError(
                master_user=self.master_user,
                procedure_instance_id=self.instance['procedure'],
                instrument=record.instrument,
                pricing_scheme=record.pricing_scheme,
                pricing_policy=record.pricing_policy,
                date=record.date,
                created=self.procedure_instance.created
            )

            principal_price = None
            accrued_price = None

            try:
                principal_price = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:

                has_error = True

                try:
                    error.error_text = formula.safe_eval(pricing_error_text_expr, names=values)

                except formula.InvalidExpression:

                    error.error_text = 'Invalid Error Text Expression'


            _l.debug('principal_price %s' % principal_price)
            _l.debug('instrument %s' % record.instrument.user_code)
            _l.debug('pricing_policy %s' % record.pricing_policy.user_code)

            if pricing_scheme_parameters.accrual_calculation_method == 2:   # ACCRUAL_PER_SCHEDULE

                try:
                    accrued_price = record.instrument.get_accrued_price(record.date)
                except Exception:
                    has_error = True

                    try:

                        _l.debug('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.error_text = 'Invalid Error Text Expression'

            if pricing_scheme_parameters.accrual_calculation_method == 3:   # ACCRUAL_PER_FORMULA

                try:
                    accrued_price = formula.safe_eval(accrual_expr, names=values)
                except formula.InvalidExpression:
                    has_error = True

                    try:

                        _l.debug('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.error_text = 'Invalid Error Text Expression'

            can_write = True
            exist = False

            try:

                price = PriceHistory.objects.get(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                exist = True

                if not self.procedure.price_overwrite_principal_prices and not self.procedure.price_overwrite_accrued_prices:
                    can_write = False
                    _l.debug('Skip %s' % price)
                else:
                    _l.debug('Overwrite existing %s' % price)

            except PriceHistory.DoesNotExist:

                price = PriceHistory(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date,
                    principal_price=principal_price
                )

                _l.debug('Create new %s' % price)

            price.principal_price = 0
            price.accrued_price = 0
            price.procedure_modified_datetime = self.procedure_instance.created

            if principal_price:

                if price.id:
                    if self.procedure.price_overwrite_principal_prices:
                        price.principal_price = principal_price
                else:
                    price.principal_price = principal_price

                error.principal_price = principal_price

            if accrued_price:

                if price.id:
                    if self.procedure.price_overwrite_accrued_prices:
                        price.accrued_price = accrued_price
                else:
                    price.accrued_price = accrued_price

                error.accrued_price = accrued_price

            _l.debug('Price: %s. Can write: %s. Has Error: %s.' % (price, can_write, has_error))

            if price.accrued_price == 0 and price.principal_price == 0:
                has_error = True
                error.error_text = error.error_text + ' Price is 0 or null'

            if can_write:

                # if has_error or (price.accrued_price == 0 and price.principal_price == 0):
                if has_error:

                    error_prices_count = error_prices_count + 1
                    error.status = PriceHistoryError.STATUS_ERROR
                    error.save()

                else:

                    successful_prices_count = successful_prices_count + 1

                    error.status = PriceHistoryError.STATUS_CREATED # its journal, not error log
                    error.save()

                    price.save()

            if not can_write and exist:

                error_prices_count = error_prices_count + 1

                error.error_text = "Prices already exists. Principal Price: " + str(principal_price) +"; Accrued: "+ str(accrued_price) +"."

                error.status = PriceHistoryError.STATUS_SKIP
                error.save()

            if self.instance['data']['date_to'] == str(record.date):

                _l.debug("Bloomberg Forwards Roll Prices for Price History")

                # roll_price_history_for_n_day_forward(self.procedure, price)
                instrument_pp = record.instrument.pricing_policies.filter(pricing_policy=record.pricing_policy)[0]
                roll_price_history_for_n_day_forward(record, self.procedure, price, self.master_user, self.procedure_instance, instrument_pp)

        PricingProcedureBloombergInstrumentResult.objects.filter(master_user=self.master_user,
                                                                 procedure=self.instance['procedure'],
                                                                 date__gte=self.instance['data']['date_from'],
                                                                 date__lte=self.instance['data']['date_to']).delete()

        _l.debug('bloomberg forwards price procedure_instance %s' % self.procedure_instance)
        _l.debug('bloomberg forwards price successful_prices_count %s' % successful_prices_count)
        _l.debug('bloomberg forwards price error_prices_count %s' % error_prices_count)

        self.procedure_instance.successful_prices_count = successful_prices_count
        self.procedure_instance.error_prices_count = error_prices_count

        self.procedure_instance.status = PricingProcedureInstance.STATUS_DONE

        self.procedure_instance.save()

        if self.procedure_instance.schedule_instance:
            self.procedure_instance.schedule_instance.run_next_procedure()

        _l.debug('bloomberg forwards price self.procedure_instance.successful_prices_count %s' % self.procedure_instance.successful_prices_count)
        _l.debug('bloomberg forwards price self.procedure_instance.error_prices_count %s' % self.procedure_instance.error_prices_count)


class FillPricesBrokerWtradeProcess(object):

    def __init__(self, instance, master_user):

        self.instance = instance
        self.master_user = master_user

        self.procedure_instance = PricingProcedureInstance.objects.get(pk=self.instance['procedure'])
        self.procedure = self.procedure_instance.procedure

        _l.debug('Broker Wtrade - Roll Days N Forward: %s' % self.procedure.price_fill_days)

    def process(self):

        _l.debug('< fill prices: total items len %s' % len(self.instance['data']['items']))
        _l.debug('< action:  %s' % self.instance['action'])

        if self.instance['action'] == 'wtrade_get_instrument_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureWtradeInstrumentResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference'],
                    instrument_parameters=str(item['parameters'])
                )

                _l.debug('< fill instrument prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                _l.debug('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if field['code'] == 'open':

                                    try:
                                        record.open_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.debug('fx_rate_value e %s ' % e)

                                    try:
                                        record.open_value_error_text = val_obj['error_text']
                                    except Exception as e:
                                        _l.debug('open_value_error_text e %s ' % e)

                                if field['code'] == 'close':

                                    try:
                                        record.close_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.debug('close_value e %s ' % e)

                                    try:
                                        record.close_value_error_text = val_obj['error_text']
                                    except Exception as e:
                                        _l.debug('close_value_error_text e %s ' % e)

                                if field['code'] == 'high':

                                    try:
                                        record.high_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.debug('high_value e %s ' % e)

                                    try:
                                        record.high_value_error_text = val_obj['error_text']
                                    except Exception as e:
                                        _l.debug('high_value_error_text e %s ' % e)

                                if field['code'] == 'low':

                                    try:
                                        record.low_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.debug('low_value e %s ' % e)

                                    try:
                                        record.low_value_error_text = val_obj['error_text']
                                    except Exception as e:
                                        _l.debug('low_value_error_text e %s ' % e)

                                if field['code'] == 'volume':

                                    try:
                                        record.volume_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.debug('volume_value e %s ' % e)

                                    try:
                                        record.volume_value_error_text = val_obj['error_text']
                                    except Exception as e:
                                        _l.debug('volume_value_error_text e %s ' % e)

                                _l.info('record %s' % record)
                                _l.info('record %s' % record.low_value)

                                record.save()

                        if not len(records):
                            _l.debug('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                _l.debug('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_price_history()

            _l.debug("process fill instrument prices")

    def create_price_history(self):

        _l.debug("Creating price history")

        successful_prices_count = 0
        error_prices_count = 0

        records = PricingProcedureWtradeInstrumentResult.objects.filter(
            master_user=self.master_user,
            procedure=self.instance['procedure'],
            date__gte=self.instance['data']['date_from'],
            date__lte=self.instance['data']['date_to']
        )

        for record in records:

            safe_instrument = {
                'id': record.instrument.id,
            }

            safe_pp = {
                'id': record.pricing_policy.id,
            }

            values = {
                'context_date': record.date,
                'context_instrument': safe_instrument,
                'context_pricing_policy': safe_pp,
                'open': record.open_value,
                'close': record.close_value,
                'high': record.high_value,
                'low': record.low_value,
                'volume': record.volume_value,

                'open_error': record.open_value_error_text,
                'close_error': record.close_value_error_text,
                'high_error': record.high_value_error_text,
                'low_error': record.low_value_error_text,
                'volume_error': record.volume_value_error_text
            }

            pricing_scheme_parameters = record.pricing_scheme.get_parameters()

            expr = pricing_scheme_parameters.expr
            accrual_expr = pricing_scheme_parameters.accrual_expr
            pricing_error_text_expr = pricing_scheme_parameters.pricing_error_text_expr
            accrual_error_text_expr = pricing_scheme_parameters.accrual_error_text_expr

            _l.debug('values %s' % values)
            _l.debug('expr %s' % expr)

            has_error = False
            error = PriceHistoryError(
                master_user=self.master_user,
                procedure_instance_id=self.instance['procedure'],
                instrument=record.instrument,
                pricing_scheme=record.pricing_scheme,
                pricing_policy=record.pricing_policy,
                date=record.date,
                created=self.procedure_instance.created
            )

            principal_price = None
            accrued_price = None

            try:
                principal_price = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:

                has_error = True

                try:
                    error.error_text = formula.safe_eval(pricing_error_text_expr, names=values)

                except formula.InvalidExpression:

                    error.error_text = 'Invalid Error Text Expression'


            _l.debug('principal_price %s' % principal_price)
            _l.debug('instrument %s' % record.instrument.user_code)
            _l.debug('pricing_policy %s' % record.pricing_policy.user_code)

            if pricing_scheme_parameters.accrual_calculation_method == 2:   # ACCRUAL_PER_SCHEDULE

                try:
                    accrued_price = record.instrument.get_accrued_price(record.date)
                except Exception:
                    has_error = True

                    try:

                        _l.debug('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.error_text = 'Invalid Error Text Expression'

            if pricing_scheme_parameters.accrual_calculation_method == 3:   # ACCRUAL_PER_FORMULA

                try:
                    accrued_price = formula.safe_eval(accrual_expr, names=values)
                except formula.InvalidExpression:
                    has_error = True

                    try:

                        _l.debug('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.error_text = 'Invalid Error Text Expression'

            can_write = True
            exist = False

            try:

                price = PriceHistory.objects.get(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                exist = True

                if not self.procedure.price_overwrite_principal_prices and not self.procedure.price_overwrite_accrued_prices:
                    can_write = False
                    _l.debug('Skips %s' % price)
                else:
                    _l.debug('Overwrite existing %s' % price)

            except PriceHistory.DoesNotExist:

                price = PriceHistory(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date,
                    principal_price=principal_price
                )

                _l.debug('Create new %s' % price)

            price.principal_price = 0
            price.accrued_price = 0
            price.procedure_modified_datetime = self.procedure_instance.created

            if principal_price:

                if price.id:
                    if self.procedure.price_overwrite_principal_prices:
                        price.principal_price = principal_price
                else:
                    price.principal_price = principal_price

                error.principal_price = principal_price

            if accrued_price:

                if price.id:
                    if self.procedure.price_overwrite_accrued_prices:
                        price.accrued_price = accrued_price
                else:
                    price.accrued_price = accrued_price

                error.accrued_price = accrued_price

            _l.debug('Price: %s. Can write: %s. Has Error: %s.' % (price, can_write, has_error))

            if price.accrued_price == 0 and price.principal_price == 0:
                has_error = True
                error.error_text = error.error_text + ' Price is 0 or null'

            if can_write:

                # if has_error or (price.accrued_price == 0 and price.principal_price == 0):
                if has_error:

                    error_prices_count = error_prices_count + 1
                    error.status = PriceHistoryError.STATUS_ERROR
                    error.save()

                else:

                    successful_prices_count = successful_prices_count + 1

                    error.status = PriceHistoryError.STATUS_CREATED # its journal, not error log
                    error.save()

                    price.save()

            if not can_write and exist:

                error_prices_count = error_prices_count + 1

                error.error_text =  "Prices already exists. Principal Price: " + str(principal_price) +"; Accrued: "+ str(accrued_price) +"."

                error.status = PriceHistoryError.STATUS_SKIP
                error.save()

            if self.instance['data']['date_to'] == str(record.date):

                _l.debug("Wtrade Roll Prices for Price History")

                instrument_pp = record.instrument.pricing_policies.filter(pricing_policy=record.pricing_policy)[0]
                successes, errors = roll_price_history_for_n_day_forward(record, self.procedure, price, self.master_user, self.procedure_instance, instrument_pp)

                successful_prices_count = successful_prices_count + successes
                error_prices_count = error_prices_count + errors

        PricingProcedureWtradeInstrumentResult.objects.filter(master_user=self.master_user,
                                                                 procedure=self.instance['procedure'],
                                                                 date__gte=self.instance['data']['date_from'],
                                                                 date__lte=self.instance['data']['date_to']).delete()

        self.procedure_instance.successful_prices_count = successful_prices_count
        self.procedure_instance.error_prices_count = error_prices_count

        self.procedure_instance.status = PricingProcedureInstance.STATUS_DONE

        self.procedure_instance.save()

        if self.procedure_instance.schedule_instance:
            self.procedure_instance.schedule_instance.run_next_procedure()


class FillPricesBrokerCbondsProcess(object):

    def __init__(self, instance, master_user):

        self.instance = instance
        self.master_user = master_user

        self.procedure_instance = PricingProcedureInstance.objects.get(pk=self.instance['procedure'])
        self.procedure = self.procedure_instance.procedure

        _l.debug('Broker Cbonds - Roll Days N Forward: %s' % self.procedure.price_fill_days)

    def process(self):

        _l.debug('< fill prices: total items len %s' % len(self.instance['data']['items']))
        _l.debug('< action:  %s' % self.instance['action'])

        if self.instance['action'] == 'cbonds_get_instrument_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureCbondsInstrumentResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference']
                )

                _l.debug('< fill instrument prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                _l.debug('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            _l.info('str(record.date) %s' % str(record.date))
                            _l.info('str(val_obj[value]) %s' % str(val_obj['value']))


                            if str(record.date) == str(val_obj['date']):

                                if field['code'] == 'open':

                                    try:
                                        record.open_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.debug('fx_rate_value e %s ' % e)

                                    try:
                                        record.open_value_error_text = val_obj['error_text']
                                    except Exception as e:
                                        _l.debug('open_value_error_text e %s ' % e)

                                if field['code'] == 'close':

                                    try:
                                        record.close_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.debug('close_value e %s ' % e)

                                    try:
                                        record.close_value_error_text = val_obj['error_text']
                                    except Exception as e:
                                        _l.debug('close_value_error_text e %s ' % e)

                                if field['code'] == 'high':

                                    try:
                                        record.high_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.debug('high_value e %s ' % e)

                                    try:
                                        record.high_value_error_text = val_obj['error_text']
                                    except Exception as e:
                                        _l.debug('high_value_error_text e %s ' % e)

                                if field['code'] == 'low':

                                    try:
                                        record.low_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.debug('low_value e %s ' % e)

                                    try:
                                        record.low_value_error_text = val_obj['error_text']
                                    except Exception as e:
                                        _l.debug('low_value_error_text e %s ' % e)

                                if field['code'] == 'volume':

                                    try:
                                        record.volume_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.debug('volume_value e %s ' % e)

                                    try:
                                        record.volume_value_error_text = val_obj['error_text']
                                    except Exception as e:
                                        _l.debug('volume_value_error_text e %s ' % e)

                    record.save()

                if not len(records):
                    _l.debug('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                    _l.debug('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_price_history()

            _l.debug("process fill instrument prices")

    def create_price_history(self):

        _l.debug("Creating price history")

        successful_prices_count = 0
        error_prices_count = 0

        records = PricingProcedureCbondsInstrumentResult.objects.filter(
            master_user=self.master_user,
            procedure=self.instance['procedure'],
            date__gte=self.instance['data']['date_from'],
            date__lte=self.instance['data']['date_to']
        )

        for record in records:

            safe_instrument = {
                'id': record.instrument.id,
            }

            safe_pp = {
                'id': record.pricing_policy.id,
            }

            values = {
                'context_date': record.date,
                'context_instrument': safe_instrument,
                'context_pricing_policy': safe_pp,
                'open': record.open_value,
                'close': record.close_value,
                'high': record.high_value,
                'low': record.low_value,
                'volume': record.volume_value,

                'open_error': record.open_value_error_text,
                'close_error': record.close_value_error_text,
                'high_error': record.high_value_error_text,
                'low_error': record.low_value_error_text,
                'volume_error': record.volume_value_error_text,

            }

            pricing_scheme_parameters = record.pricing_scheme.get_parameters()

            expr = pricing_scheme_parameters.expr
            accrual_expr = pricing_scheme_parameters.accrual_expr
            pricing_error_text_expr = pricing_scheme_parameters.pricing_error_text_expr
            accrual_error_text_expr = pricing_scheme_parameters.accrual_error_text_expr

            _l.debug('values %s' % values)
            _l.debug('expr %s' % expr)

            has_error = False
            error = PriceHistoryError(
                master_user=self.master_user,
                procedure_instance_id=self.instance['procedure'],
                instrument=record.instrument,
                pricing_scheme=record.pricing_scheme,
                pricing_policy=record.pricing_policy,
                date=record.date,
                created=self.procedure_instance.created
            )

            principal_price = None
            accrued_price = None

            try:
                principal_price = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:

                has_error = True

                try:
                    error.error_text = formula.safe_eval(pricing_error_text_expr, names=values)

                except formula.InvalidExpression:

                    error.error_text = 'Invalid Error Text Expression'


            _l.debug('principal_price %s' % principal_price)
            _l.debug('instrument %s' % record.instrument.user_code)
            _l.debug('pricing_policy %s' % record.pricing_policy.user_code)

            if pricing_scheme_parameters.accrual_calculation_method == 2:   # ACCRUAL_PER_SCHEDULE

                try:
                    accrued_price = record.instrument.get_accrued_price(record.date)
                except Exception:
                    has_error = True

                    try:

                        _l.debug('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.error_text = 'Invalid Error Text Expression'

            if pricing_scheme_parameters.accrual_calculation_method == 3:   # ACCRUAL_PER_FORMULA

                try:
                    accrued_price = formula.safe_eval(accrual_expr, names=values)
                except formula.InvalidExpression:
                    has_error = True

                    try:

                        _l.debug('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.error_text = 'Invalid Error Text Expression'

            can_write = True
            exist = False

            try:

                price = PriceHistory.objects.get(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                exist = True

                if not self.procedure.price_overwrite_principal_prices and not self.procedure.price_overwrite_accrued_prices:
                    can_write = False
                    _l.debug('Skips %s' % price)
                else:
                    _l.debug('Overwrite existing %s' % price)

            except PriceHistory.DoesNotExist:

                price = PriceHistory(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date,
                    principal_price=principal_price
                )

                _l.debug('Create new %s' % price)

            price.principal_price = 0
            price.accrued_price = 0
            price.procedure_modified_datetime = self.procedure_instance.created

            if principal_price:

                if price.id:
                    if self.procedure.price_overwrite_principal_prices:
                        price.principal_price = principal_price
                else:
                    price.principal_price = principal_price

                error.principal_price = principal_price

            if accrued_price:

                if price.id:
                    if self.procedure.price_overwrite_accrued_prices:
                        price.accrued_price = accrued_price
                else:
                    price.accrued_price = accrued_price

                error.accrued_price = accrued_price

            _l.debug('Price: %s. Can write: %s. Has Error: %s.' % (price, can_write, has_error))

            if price.accrued_price == 0 and price.principal_price == 0:
                has_error = True
                error.error_text = error.error_text + ' Price is 0 or null'

            if can_write:

                # if has_error or (price.accrued_price == 0 and price.principal_price == 0):
                # if has_error:
                #
                #     error_prices_count = error_prices_count + 1
                #     error.status = PriceHistoryError.STATUS_ERROR
                #     error.save()
                #
                # else:

                successful_prices_count = successful_prices_count + 1

                error.status = PriceHistoryError.STATUS_CREATED # its journal, not error log
                error.save()

                price.save()

            if not can_write and exist:

                error_prices_count = error_prices_count + 1

                error.error_text =  "Prices already exists. Principal Price: " + str(principal_price) +"; Accrued: "+ str(accrued_price) +"."

                error.status = PriceHistoryError.STATUS_SKIP
                error.save()

            if self.instance['data']['date_to'] == str(record.date):

                _l.debug("Cbonds Roll Prices for Price History")

                instrument_pp = record.instrument.pricing_policies.filter(pricing_policy=record.pricing_policy)[0]
                successes, errors = roll_price_history_for_n_day_forward(record, self.procedure, price, self.master_user, self.procedure_instance, instrument_pp)

                successful_prices_count = successful_prices_count + successes
                error_prices_count = error_prices_count + errors

        PricingProcedureCbondsInstrumentResult.objects.filter(master_user=self.master_user,
                                                              procedure=self.instance['procedure'],
                                                              date__gte=self.instance['data']['date_from'],
                                                              date__lte=self.instance['data']['date_to']).delete()

        self.procedure_instance.successful_prices_count = successful_prices_count
        self.procedure_instance.error_prices_count = error_prices_count

        self.procedure_instance.status = PricingProcedureInstance.STATUS_DONE

        self.procedure_instance.save()

        if self.procedure_instance.schedule_instance:
            self.procedure_instance.schedule_instance.run_next_procedure()



class FillPricesBrokerFixerProcess(object):

    def __init__(self, instance, master_user):

        self.instance = instance
        self.master_user = master_user

        self.procedure_instance = PricingProcedureInstance.objects.get(pk=self.instance['procedure'])
        self.procedure = self.procedure_instance.procedure

        _l.debug("Broker Fixer - Get FX Rates: %s" % self.procedure.price_get_fx_rates)
        _l.debug("Broker Fixer - Overwrite FX Rates: %s" % self.procedure.price_overwrite_fx_rates)
        _l.debug('Broker Fixer - Roll Days N Forward: %s' % self.procedure.price_fill_days)

    def process(self):

        _l.debug('< fill prices: total items len %s' % len(self.instance['data']['items']))
        _l.debug('< action:  %s' % self.instance['action'])

        if self.instance['action'] == 'fixer_get_currency_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureFixerCurrencyResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference'],
                    currency_parameters=str(item['parameters'])
                )

                _l.debug('< fill currency prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                _l.debug('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if field['code'] == 'close':

                                    try:
                                        record.close_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.debug('close_value e %s ' % e)

                                    try:
                                        record.close_value_error_text = val_obj['error_text']
                                    except Exception as e:
                                        _l.debug('close_value_error_text e %s ' % e)

                                record.save()

                        if not len(records):
                            _l.debug('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                _l.debug('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_currency_history()

            _l.debug("process fill currency prices")

    def create_currency_history(self):

        _l.debug("Creating currency history")

        successful_prices_count = 0
        error_prices_count = 0

        records = PricingProcedureFixerCurrencyResult.objects.filter(
            master_user=self.master_user,
            procedure=self.instance['procedure'],
            date__gte=self.instance['data']['date_from'],
            date__lte=self.instance['data']['date_to']
        )

        _l.debug('create_currency_history: records len %s' % len(records))

        for record in records:

            safe_currency = {
                'id': record.currency.id,
            }

            safe_pp = {
                'id': record.pricing_policy.id,
            }


            values = {
                'context_date': record.date,
                'context_currency': safe_currency,
                'context_pricing_policy': safe_pp,
                'close': record.close_value,
                'close_error': record.close_value_error_text
            }

            has_error = False
            error = CurrencyHistoryError(
                master_user=self.master_user,
                procedure_instance_id=self.instance['procedure'],
                currency=record.currency,
                pricing_scheme=record.pricing_scheme,
                pricing_policy=record.pricing_policy,
                date=record.date,
                created=self.procedure_instance.created
            )

            pricing_scheme_parameters = record.pricing_scheme.get_parameters()

            expr = pricing_scheme_parameters.expr
            error_text_expr = pricing_scheme_parameters.error_text_expr

            _l.debug('values %s' % values)
            _l.debug('expr %s' % expr)

            fx_rate = None

            try:
                fx_rate = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:

                has_error = True

                try:
                    error.error_text = formula.safe_eval(error_text_expr, names=values)
                except formula.InvalidExpression:
                    error.error_text = 'Invalid Error Text Expression'

            _l.debug('fx_rate %s' % fx_rate)
            _l.debug('currency %s' % record.currency.user_code)
            _l.debug('pricing_policy %s' % record.pricing_policy.user_code)

            can_write = True
            exist = False

            try:

                price = CurrencyHistory.objects.get(
                    currency=record.currency,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                exist = True

                if not self.procedure.price_overwrite_fx_rates:
                    can_write = False
                    _l.debug('Skip %s' % price)
                else:
                    _l.debug('Overwrite existing %s' % price)

            except CurrencyHistory.DoesNotExist:

                price = CurrencyHistory(
                    currency=record.currency,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                _l.debug('Create new %s' % price)

            price.fx_rate = 0
            price.procedure_modified_datetime = self.procedure_instance.created

            if fx_rate:
                price.fx_rate = fx_rate

            if can_write:

                if has_error or price.fx_rate == 0:
                # if has_error:

                    error_prices_count = error_prices_count + 1
                    error.status = CurrencyHistoryError.STATUS_ERROR
                    error.save()

                else:

                    successful_prices_count = successful_prices_count + 1

                    error.status = CurrencyHistoryError.STATUS_CREATED # its journal, not error log
                    error.save()

                    price.save()

            if not can_write and exist:

                error_prices_count = error_prices_count + 1

                error.error_text = "Prices already exists. Fx rate: " + str(fx_rate) + "."

                error.status = CurrencyHistoryError.STATUS_SKIP
                error.save()

            if parse_date_iso(self.instance['data']['date_to']) == record.date:

                _l.debug("Fixer Roll Prices for Currency History")

                successes, errors = roll_currency_history_for_n_day_forward(record, self.procedure, price, self.master_user, self.procedure_instance)

                successful_prices_count = successful_prices_count + successes
                error_prices_count = error_prices_count + errors

        PricingProcedureFixerCurrencyResult.objects.filter(master_user=self.master_user,
                                                               procedure=self.instance['procedure'],
                                                               date__gte=self.instance['data']['date_from'],
                                                               date__lte=self.instance['data']['date_to']).delete()

        _l.debug('fixer self.procedure_instance %s' % self.procedure_instance)
        _l.debug('fixer fx successful_prices_count %s' % successful_prices_count)
        _l.debug('fixer fx error_prices_count %s' % error_prices_count)

        self.procedure_instance.successful_prices_count = int(successful_prices_count)
        self.procedure_instance.error_prices_count = int(error_prices_count)

        self.procedure_instance.status = PricingProcedureInstance.STATUS_DONE

        self.procedure_instance.save()

        _l.debug('fixer self.procedure_instance.successful_prices_count %s' % self.procedure_instance.successful_prices_count)
        _l.debug('fixer self.procedure_instance.error_prices_count %s' % self.procedure_instance.error_prices_count)

        if self.procedure_instance.schedule_instance:
            self.procedure_instance.schedule_instance.run_next_procedure()


class FillPricesBrokerFxCbondsProcess(object):

    def __init__(self, instance, master_user):

        self.instance = instance
        self.master_user = master_user

        self.procedure_instance = PricingProcedureInstance.objects.get(pk=self.instance['procedure'])
        self.procedure = self.procedure_instance.procedure

        _l.debug("Broker Fixer - Get FX Rates: %s" % self.procedure.price_get_fx_rates)
        _l.debug("Broker Fixer - Overwrite FX Rates: %s" % self.procedure.price_overwrite_fx_rates)
        _l.debug('Broker Fixer - Roll Days N Forward: %s' % self.procedure.price_fill_days)

    def process(self):

        _l.debug('< fill prices: total items len %s' % len(self.instance['data']['items']))
        _l.debug('< action:  %s' % self.instance['action'])

        if self.instance['action'] == 'cbonds_get_currency_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureCbondsCurrencyResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference']
                )

                _l.debug('< fill currency prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                _l.debug('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if field['code'] == 'close':

                                    try:
                                        record.close_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.debug('close_value e %s ' % e)

                                    try:
                                        record.close_value_error_text = val_obj['error_text']
                                    except Exception as e:
                                        _l.debug('close_value_error_text e %s ' % e)

                                record.save()

                        if not len(records):
                            _l.debug('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                _l.debug('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_currency_history()

            _l.debug("process fill currency prices")

    def create_currency_history(self):

        _l.debug("Creating currency history")

        successful_prices_count = 0
        error_prices_count = 0

        records = PricingProcedureCbondsCurrencyResult.objects.filter(
            master_user=self.master_user,
            procedure=self.instance['procedure'],
            date__gte=self.instance['data']['date_from'],
            date__lte=self.instance['data']['date_to']
        )

        _l.debug('create_currency_history: records len %s' % len(records))

        for record in records:

            safe_currency = {
                'id': record.currency.id,
            }

            safe_pp = {
                'id': record.pricing_policy.id,
            }


            values = {
                'context_date': record.date,
                'context_currency': safe_currency,
                'context_pricing_policy': safe_pp,
                'close': record.close_value,
                'close_error': record.close_value_error_text
            }

            has_error = False
            error = CurrencyHistoryError(
                master_user=self.master_user,
                procedure_instance_id=self.instance['procedure'],
                currency=record.currency,
                pricing_scheme=record.pricing_scheme,
                pricing_policy=record.pricing_policy,
                date=record.date,
                created=self.procedure_instance.created
            )

            pricing_scheme_parameters = record.pricing_scheme.get_parameters()

            expr = pricing_scheme_parameters.expr
            error_text_expr = pricing_scheme_parameters.error_text_expr

            _l.debug('values %s' % values)
            _l.debug('expr %s' % expr)

            fx_rate = None

            try:
                fx_rate = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:

                has_error = True

                try:
                    error.error_text = formula.safe_eval(error_text_expr, names=values)
                except formula.InvalidExpression:
                    error.error_text = 'Invalid Error Text Expression'

            _l.debug('fx_rate %s' % fx_rate)
            _l.debug('currency %s' % record.currency.user_code)
            _l.debug('pricing_policy %s' % record.pricing_policy.user_code)

            can_write = True
            exist = False

            try:

                price = CurrencyHistory.objects.get(
                    currency=record.currency,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                exist = True

                if not self.procedure.price_overwrite_fx_rates:
                    can_write = False
                    _l.debug('Skip %s' % price)
                else:
                    _l.debug('Overwrite existing %s' % price)

            except CurrencyHistory.DoesNotExist:

                price = CurrencyHistory(
                    currency=record.currency,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                _l.debug('Create new %s' % price)

            price.fx_rate = 0
            price.procedure_modified_datetime = self.procedure_instance.created

            if fx_rate:
                price.fx_rate = fx_rate

            if can_write:

                if has_error or price.fx_rate == 0:
                    # if has_error:

                    error_prices_count = error_prices_count + 1
                    error.status = CurrencyHistoryError.STATUS_ERROR
                    error.save()

                else:

                    successful_prices_count = successful_prices_count + 1

                    error.status = CurrencyHistoryError.STATUS_CREATED # its journal, not error log
                    error.save()

                    price.save()

            if not can_write and exist:

                error_prices_count = error_prices_count + 1

                error.error_text = "Prices already exists. Fx rate: " + str(fx_rate) + "."

                error.status = CurrencyHistoryError.STATUS_SKIP
                error.save()

            if parse_date_iso(self.instance['data']['date_to']) == record.date:

                _l.debug("Fixer Roll Prices for Currency History")

                successes, errors = roll_currency_history_for_n_day_forward(record, self.procedure, price, self.master_user, self.procedure_instance)

                successful_prices_count = successful_prices_count + successes
                error_prices_count = error_prices_count + errors

        PricingProcedureCbondsCurrencyResult.objects.filter(master_user=self.master_user,
                                                           procedure=self.instance['procedure'],
                                                           date__gte=self.instance['data']['date_from'],
                                                           date__lte=self.instance['data']['date_to']).delete()

        _l.debug('cbonds self.procedure_instance %s' % self.procedure_instance)
        _l.debug('cbonds fx successful_prices_count %s' % successful_prices_count)
        _l.debug('cbonds fx error_prices_count %s' % error_prices_count)

        self.procedure_instance.successful_prices_count = int(successful_prices_count)
        self.procedure_instance.error_prices_count = int(error_prices_count)

        self.procedure_instance.status = PricingProcedureInstance.STATUS_DONE

        self.procedure_instance.save()

        _l.debug('cbonds self.procedure_instance.successful_prices_count %s' % self.procedure_instance.successful_prices_count)
        _l.debug('cbonds self.procedure_instance.error_prices_count %s' % self.procedure_instance.error_prices_count)

        if self.procedure_instance.schedule_instance:
            self.procedure_instance.schedule_instance.run_next_procedure()



class FillPricesBrokerAlphavProcess(object):

    def __init__(self, instance, master_user):

        self.instance = instance
        self.master_user = master_user

        self.procedure_instance = PricingProcedureInstance.objects.get(pk=self.instance['procedure'])
        self.procedure = self.procedure_instance.procedure

        _l.debug('Broker Alphav - Roll Days N Forward: %s' % self.procedure.price_fill_days)

    def process(self):

        _l.debug('< fill prices: total items len %s' % len(self.instance['data']['items']))
        _l.debug('< action:  %s' % self.instance['action'])

        if self.instance['action'] == 'alphav_get_instrument_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureAlphavInstrumentResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference'],
                    instrument_parameters=str(item['parameters'])
                )

                _l.debug('< fill instrument prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                _l.debug('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if field['code'] == 'close':

                                    try:
                                        record.close_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.debug('close_value e %s ' % e)

                                    try:
                                        record.close_value_error_text = val_obj['error_text']
                                    except Exception as e:
                                        _l.debug('close_value_error_text e %s ' % e)

                                record.save()

                        if not len(records):
                            _l.debug('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                _l.debug('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_price_history()

            _l.debug("process fill instrument prices")

    def create_price_history(self):

        _l.debug("Creating price history")

        successful_prices_count = 0
        error_prices_count = 0

        records = PricingProcedureAlphavInstrumentResult.objects.filter(
            master_user=self.master_user,
            procedure=self.instance['procedure'],
            date__gte=self.instance['data']['date_from'],
            date__lte=self.instance['data']['date_to']
        )

        for record in records:

            safe_instrument = {
                'id': record.instrument.id,
            }

            safe_pp = {
                'id': record.pricing_policy.id,
            }

            values = {
                'context_date': record.date,
                'context_instrument': safe_instrument,
                'context_pricing_policy': safe_pp,
                'close': record.close_value,
                'close_error': record.close_value_error_text,
            }

            pricing_scheme_parameters = record.pricing_scheme.get_parameters()

            expr = pricing_scheme_parameters.expr
            accrual_expr = pricing_scheme_parameters.accrual_expr
            pricing_error_text_expr = pricing_scheme_parameters.pricing_error_text_expr
            accrual_error_text_expr = pricing_scheme_parameters.accrual_error_text_expr

            _l.debug('values %s' % values)
            _l.debug('expr %s' % expr)

            has_error = False
            error = PriceHistoryError(
                master_user=self.master_user,
                procedure_instance_id=self.instance['procedure'],
                instrument=record.instrument,
                pricing_scheme=record.pricing_scheme,
                pricing_policy=record.pricing_policy,
                date=record.date,
                created=self.procedure_instance.created
            )

            principal_price = None
            accrued_price = None

            try:
                principal_price = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:

                has_error = True

                try:
                    error.error_text = formula.safe_eval(pricing_error_text_expr, names=values)

                except formula.InvalidExpression:

                    error.error_text = 'Invalid Error Text Expression'


            _l.debug('principal_price %s' % principal_price)
            _l.debug('instrument %s' % record.instrument.user_code)
            _l.debug('pricing_policy %s' % record.pricing_policy.user_code)

            if pricing_scheme_parameters.accrual_calculation_method == 2:   # ACCRUAL_PER_SCHEDULE

                try:
                    accrued_price = record.instrument.get_accrued_price(record.date)
                except Exception:
                    has_error = True

                    try:

                        _l.debug('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.error_text = 'Invalid Error Text Expression'

            if pricing_scheme_parameters.accrual_calculation_method == 3:   # ACCRUAL_PER_FORMULA

                try:
                    accrued_price = formula.safe_eval(accrual_expr, names=values)
                except formula.InvalidExpression:
                    has_error = True

                    try:

                        _l.debug('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.error_text = 'Invalid Error Text Expression'

            can_write = True
            exist = False

            try:

                price = PriceHistory.objects.get(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                exist = True

                if not self.procedure.price_overwrite_principal_prices and not self.procedure.price_overwrite_accrued_prices:
                    can_write = False
                    _l.debug('Skips %s' % price)
                else:
                    _l.debug('Overwrite existing %s' % price)

            except PriceHistory.DoesNotExist:

                price = PriceHistory(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date,
                    principal_price=principal_price
                )

                _l.debug('Create new %s' % price)

            price.principal_price = 0
            price.accrued_price = 0
            price.procedure_modified_datetime = self.procedure_instance.created

            if principal_price:

                if price.id:
                    if self.procedure.price_overwrite_principal_prices:
                        price.principal_price = principal_price
                else:
                    price.principal_price = principal_price

                error.principal_price = principal_price

            if accrued_price:

                if price.id:
                    if self.procedure.price_overwrite_accrued_prices:
                        price.accrued_price = accrued_price
                else:
                    price.accrued_price = accrued_price

                error.accrued_price = accrued_price

            _l.debug('Price: %s. Can write: %s. Has Error: %s.' % (price, can_write, has_error))

            if price.accrued_price == 0 and price.principal_price == 0:
                has_error = True
                error.error_text = error.error_text + ' Price is 0 or null'

            if can_write:

                # if has_error or (price.accrued_price == 0 and price.principal_price == 0):
                if has_error:

                    error_prices_count = error_prices_count + 1
                    error.status = PriceHistoryError.STATUS_ERROR
                    error.save()

                else:

                    successful_prices_count = successful_prices_count + 1

                    error.status = PriceHistoryError.STATUS_CREATED # its journal, not error log
                    error.save()

                    price.save()

            if not can_write and exist:

                error_prices_count = error_prices_count + 1

                error.error_text =  "Prices already exists. Principal Price: " + str(principal_price) +"; Accrued: "+ str(accrued_price) +"."

                error.status = PriceHistoryError.STATUS_SKIP
                error.save()

            if self.instance['data']['date_to'] == str(record.date):

                _l.debug("Wtrade Roll Prices for Price History")

                instrument_pp = record.instrument.pricing_policies.filter(pricing_policy=record.pricing_policy)[0]
                successes, errors = roll_price_history_for_n_day_forward(record, self.procedure, price, self.master_user, self.procedure_instance, instrument_pp)

                successful_prices_count = successful_prices_count + successes
                error_prices_count = error_prices_count + errors

        PricingProcedureAlphavInstrumentResult.objects.filter(master_user=self.master_user,
                                                              procedure=self.instance['procedure'],
                                                              date__gte=self.instance['data']['date_from'],
                                                              date__lte=self.instance['data']['date_to']).delete()

        self.procedure_instance.successful_prices_count = successful_prices_count
        self.procedure_instance.error_prices_count = error_prices_count

        self.procedure_instance.status = PricingProcedureInstance.STATUS_DONE

        self.procedure_instance.save()

        if self.procedure_instance.schedule_instance:
            self.procedure_instance.schedule_instance.run_next_procedure()

