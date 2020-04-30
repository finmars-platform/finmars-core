import time

from django.db.models import Q

from poms.common import formula
from poms.currencies.models import CurrencyHistory
from poms.instruments.models import PriceHistory
from poms.integrations.providers.base import parse_date_iso

from poms.pricing.currency_handler import PricingCurrencyHandler
from poms.pricing.instrument_handler import PricingInstrumentHandler
from poms.pricing.models import PricingProcedureBloombergInstrumentResult, PricingProcedureBloombergCurrencyResult, \
    PricingProcedureWtradeInstrumentResult, PriceHistoryError, \
    CurrencyHistoryError, PricingProcedureFixerCurrencyResult, PricingParentProcedureInstance, PricingProcedureInstance

import logging

from poms.pricing.utils import roll_price_history_for_n_day_forward, roll_currency_history_for_n_day_forward
from poms.reports.builders.balance_item import Report
from poms.reports.builders.balance_pl import ReportBuilder
from poms.transactions.models import Transaction

_l = logging.getLogger('poms.pricing')


class PricingProcedureProcess(object):

    def __init__(self, procedure=None, master_user=None, date_from=None, date_to=None):

        _l.info('PricingProcedureProcess. Master user: %s. Procedure: %s' % (master_user, procedure))

        self.master_user = master_user
        self.procedure = procedure

        self.execute_procedure_date_expressions()

        if date_from:
            self.procedure.price_date_from = date_from
        if date_to:
            _l.info("Date To set from user Settings")
            self.procedure.price_date_to = date_to

        _l.info('price_date_from %s' % self.procedure.price_date_from)
        _l.info('price_date_to %s' % self.procedure.price_date_to)

        self.parent_procedure = PricingParentProcedureInstance(pricing_procedure=procedure, master_user=master_user)
        self.parent_procedure.save()

        self.pricing_instrument_handler = PricingInstrumentHandler(procedure=procedure, parent_procedure=self.parent_procedure, master_user=master_user)
        self.pricing_currency_handler = PricingCurrencyHandler(procedure=procedure, parent_procedure=self.parent_procedure, master_user=master_user)

        _l.info("Procedure settings - Get Principal Prices: %s" % self.procedure.price_get_principal_prices)
        _l.info("Procedure settings - Get Accrued Prices: %s" % self.procedure.price_get_accrued_prices)
        _l.info("Procedure settings - Get FX Rates: %s" % self.procedure.price_get_fx_rates)
        _l.info("Procedure settings - Overwrite Principal Prices: %s" % self.procedure.price_overwrite_principal_prices)
        _l.info("Procedure settings - Overwrite Accrued Prices: %s" % self.procedure.price_overwrite_accrued_prices)
        _l.info("Procedure settings - Overwrite FX Rates: %s" % self.procedure.price_overwrite_fx_rates)
        _l.info("Procedure settings - Roll Days N Forward: %s" % self.procedure.price_fill_days)

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

        _l.info('< get_base_transactions len %s', len(results))
        _l.info('< get_base_transactions done in %s', (time.perf_counter() - processing_st))

        return results

    def execute_procedure_date_expressions(self):

        if self.procedure.price_date_from_expr:
            try:
                self.procedure.price_date_from = formula.safe_eval(self.procedure.price_date_from_expr, names={})
            except formula.InvalidExpression as e:
                _l.info("Cant execute price date from expression %s " % e)

        if self.procedure.price_date_to_expr:
            try:
                self.procedure.price_date_to = formula.safe_eval(self.procedure.price_date_to_expr, names={})
            except formula.InvalidExpression as e:
                _l.info("Cant execute price date to expression %s " % e)

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
        self.procedure = self.procedure_instance.pricing_procedure

        _l.info("Broker Bloomberg - Get Principal Prices: %s" % self.procedure.price_get_principal_prices)
        _l.info("Broker Bloomberg - Get Accrued Prices: %s" % self.procedure.price_get_accrued_prices)
        _l.info("Broker Bloomberg - Get FX Rates: %s" % self.procedure.price_get_fx_rates)
        _l.info("Broker Bloomberg - Overwrite Principal Prices: %s" % self.procedure.price_overwrite_principal_prices)
        _l.info("Broker Bloomberg - Overwrite Accrued Prices: %s" % self.procedure.price_overwrite_accrued_prices)
        _l.info("Broker Bloomberg - Overwrite FX Rates: %s" % self.procedure.price_overwrite_fx_rates)
        _l.info("Broker Bloomberg - Roll Days N Forward: %s" % self.procedure.price_fill_days)

    def process(self):

        _l.info('< fill prices: total items len %s' % len(self.instance['data']['items']))
        _l.info('< action:  %s' % self.instance['action'])

        if self.instance['action'] == 'bloomberg_get_currency_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureBloombergCurrencyResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference'],
                    currency_parameters=str(item['parameters'])
                )

                _l.info('< fill currency prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                _l.info('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if record.fx_rate_parameters:
                                    if field['code'] in record.fx_rate_parameters:

                                        try:
                                            record.fx_rate_value = float(val_obj['value'])
                                        except Exception as e:
                                            _l.info('fx_rate_value e %s ' % e)

                                record.save()

                        if not len(records):
                            _l.info('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                _l.info('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_currency_history()

            _l.info("process fill currency prices")

        elif self.instance['action'] == 'bloomberg_get_instrument_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureBloombergInstrumentResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference'],
                    instrument_parameters=str(item['parameters'])
                )

                _l.info('< fill instrument prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                _l.info('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if record.ask_parameters:
                                    if field['code'] in record.ask_parameters:

                                        try:
                                            record.ask_value = float(val_obj['value'])
                                        except Exception as e:
                                            _l.info('ask value e %s ' % e)

                                if record.bid_parameters:
                                    if field['code'] in record.bid_parameters:

                                        try:
                                            record.bid_value = float(val_obj['value'])
                                        except Exception as e:
                                             _l.info('bid value e %s ' % e)

                                if record.last_parameters:
                                    if field['code'] in record.last_parameters:

                                        try:
                                            record.last_value = float(val_obj['value'])
                                        except Exception as e:
                                            _l.info('last value e %s ' % e)

                                if record.accrual_parameters:
                                    if field['code'] in record.accrual_parameters:

                                        try:
                                            record.accrual_value = float(val_obj['value'])
                                        except Exception as e:
                                            _l.info('accrual_value value e %s ' % e)

                                record.save()

                        if not len(records):
                            _l.info('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                _l.info('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_price_history()

            _l.info("process fill instrument prices")

    def create_price_history(self):

        _l.info("Creating price history")

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

            values = {
                'd': record.date,
                'instrument': safe_instrument,
                'ask': record.ask_value,
                'bid': record.bid_value,
                'last': record.last_value,
                'accrual': record.accrual_value
            }

            pricing_scheme_parameters = record.pricing_scheme.get_parameters()

            expr = pricing_scheme_parameters.expr
            accrual_expr = pricing_scheme_parameters.accrual_expr
            pricing_error_text_expr = pricing_scheme_parameters.pricing_error_text_expr
            accrual_error_text_expr = pricing_scheme_parameters.accrual_error_text_expr

            _l.info('values %s' % values)
            _l.info('expr %s' % expr)

            has_error = False
            error = PriceHistoryError(
                master_user=self.master_user,
                procedure_instance_id=self.instance['procedure'],
                instrument=record.instrument,
                pricing_scheme=record.pricing_scheme,
                pricing_policy=record.pricing_policy,
                date=record.date,
            )

            principal_price = None
            accrued_price = None

            try:
                principal_price = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:

                has_error = True

                try:
                    error.price_error_text = formula.safe_eval(pricing_error_text_expr, names=values)

                except formula.InvalidExpression:

                    error.price_error_text = 'Invalid Error Text Expression'


            _l.info('principal_price %s' % principal_price)
            _l.info('instrument %s' % record.instrument.user_code)
            _l.info('pricing_policy %s' % record.pricing_policy.user_code)

            if pricing_scheme_parameters.accrual_calculation_method == 2:   # ACCRUAL_PER_SCHEDULE

                try:
                    accrued_price = record.instrument.get_accrued_price(record.date)
                except Exception:
                    has_error = True

                    try:

                        _l.info('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.accrual_error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.accrual_error_text = 'Invalid Error Text Expression'

            if pricing_scheme_parameters.accrual_calculation_method == 3:   # ACCRUAL_PER_FORMULA

                try:
                    accrued_price = formula.safe_eval(accrual_expr, names=values)
                except formula.InvalidExpression:
                    has_error = True

                    try:

                        _l.info('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.accrual_error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.accrual_error_text = 'Invalid Error Text Expression'

            can_write = True

            try:

                price = PriceHistory.objects.get(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                if not self.procedure.price_overwrite_principal_prices and not self.procedure.price_overwrite_accrued_prices:
                    can_write = False
                    _l.info('Skip %s' % price)
                else:
                    _l.info('Overwrite existing %s' % price)

            except PriceHistory.DoesNotExist:

                price = PriceHistory(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date,
                    principal_price=principal_price
                )

                _l.info('Create new %s' % price)

            price.principal_price = 0
            price.accrued_price = 0

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

            _l.info('Price: %s. Can write: %s. Has Error: %s.' % (price, can_write, has_error))

            if can_write:

                if has_error or (price.accrued_price == 0 and price.principal_price == 0):
                    error.save()
                else:
                    price.save()

            else:

                error.error_text = "Prices already exists. Principal Price: " + str(principal_price) +"; Accrued: "+ str(accrued_price) +"."

                error.status = PriceHistoryError.STATUS_SKIP
                error.save()

            if self.instance['data']['date_to'] == str(record.date):

                _l.info("Bloomberg Roll Prices for Price History")

                # roll_price_history_for_n_day_forward(self.procedure, price)
                roll_price_history_for_n_day_forward(record, self.procedure, price, self.master_user, self.procedure_instance)

        PricingProcedureBloombergInstrumentResult.objects.filter(master_user=self.master_user,
                                                       procedure=self.instance['procedure'],
                                                       date__gte=self.instance['data']['date_from'],
                                                       date__lte=self.instance['data']['date_to']).delete()

    def create_currency_history(self):

        _l.info("Creating currency history")

        records = PricingProcedureBloombergCurrencyResult.objects.filter(
            master_user=self.master_user,
            procedure=self.instance['procedure'],
            date__gte=self.instance['data']['date_from'],
            date__lte=self.instance['data']['date_to']
        )

        _l.info('create_currency_history: records len %s' % len(records))

        for record in records:

            safe_currency = {
                'id': record.currency.id,
            }

            values = {
                'd': record.date,
                'currency': safe_currency,
                'fx_rate': record.fx_rate_value,
            }

            has_error = False
            error = CurrencyHistoryError(
                master_user=self.master_user,
                procedure_instance_id=self.instance['procedure'],
                currency=record.currency,
                pricing_scheme=record.pricing_scheme,
                pricing_policy=record.pricing_policy,
                date=record.date,
            )

            pricing_scheme_parameters = record.pricing_scheme.get_parameters()

            expr = pricing_scheme_parameters.expr
            error_text_expr = pricing_scheme_parameters.error_text_expr

            _l.info('values %s' % values)
            _l.info('expr %s' % expr)

            fx_rate = None

            try:
                fx_rate = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:

                has_error = True

                try:
                    error.error_text = formula.safe_eval(error_text_expr, names=values)
                except formula.InvalidExpression:
                    error.error_text = 'Invalid Error Text Expression'

            _l.info('fx_rate %s' % fx_rate)
            _l.info('currency %s' % record.currency.user_code)
            _l.info('pricing_policy %s' % record.pricing_policy.user_code)

            can_write = True

            try:

                price = CurrencyHistory.objects.get(
                    currency=record.currency,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                if not self.procedure.price_overwrite_fx_rates:
                    can_write = False
                    _l.info('Skip %s' % price)
                else:
                    _l.info('Overwrite existing %s' % price)


            except CurrencyHistory.DoesNotExist:

                price = CurrencyHistory(
                    currency=record.currency,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                _l.info('Create new %s' % price)

            price.fx_rate = 0

            if fx_rate:
                price.fx_rate = fx_rate

            if can_write:

                if has_error or fx_rate == 0:
                    error.save()
                else:
                    price.save()

            else:
                error.error_text = "Prices already exists. Fx rate: " + str(fx_rate) + "."

                error.status = CurrencyHistoryError.STATUS_SKIP
                error.save()

            if parse_date_iso(self.instance['data']['date_to']) == record.date:

                _l.info("Bloomberg Roll Prices for Currency History")

                roll_currency_history_for_n_day_forward(record, self.procedure, price, self.master_user, self.procedure_instance)

        PricingProcedureBloombergCurrencyResult.objects.filter(master_user=self.master_user,
                                                                 procedure=self.instance['procedure'],
                                                                 date__gte=self.instance['data']['date_from'],
                                                                 date__lte=self.instance['data']['date_to']).delete()


class FillPricesBrokerWtradeProcess(object):

    def __init__(self, instance, master_user):

        self.instance = instance
        self.master_user = master_user

        self.procedure_instance = PricingProcedureInstance.objects.get(pk=self.instance['procedure'])
        self.procedure = self.procedure_instance.pricing_procedure

        _l.info('Broker Wtrade - Roll Days N Forward: %s' % self.procedure.price_fill_days)

    def process(self):

        _l.info('< fill prices: total items len %s' % len(self.instance['data']['items']))
        _l.info('< action:  %s' % self.instance['action'])

        if self.instance['action'] == 'wtrade_get_instrument_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureWtradeInstrumentResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference'],
                    instrument_parameters=str(item['parameters'])
                )

                _l.info('< fill instrument prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                _l.info('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if field['code'] == 'open':

                                    try:
                                        record.open_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.info('fx_rate_value e %s ' % e)

                                if field['code'] == 'close':

                                    try:
                                        record.close_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.info('close_value e %s ' % e)

                                if field['code'] == 'high':

                                    try:
                                        record.high_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.info('high_value e %s ' % e)

                                if field['code'] == 'low':

                                    try:
                                        record.low_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.info('low_value e %s ' % e)

                                if field['code'] == 'volume':

                                    try:
                                        record.volume_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.info('volume_value e %s ' % e)

                                record.save()

                        if not len(records):
                            _l.info('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                _l.info('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_price_history()

            _l.info("process fill instrument prices")

    def create_price_history(self):

        _l.info("Creating price history")

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

            values = {
                'd': record.date,
                'instrument': safe_instrument,
                'open': record.open_value,
                'close': record.close_value,
                'high': record.high_value,
                'low': record.low_value,
                'volume': record.volume_value
            }

            pricing_scheme_parameters = record.pricing_scheme.get_parameters()

            expr = pricing_scheme_parameters.expr
            accrual_expr = pricing_scheme_parameters.accrual_expr
            pricing_error_text_expr = pricing_scheme_parameters.pricing_error_text_expr
            accrual_error_text_expr = pricing_scheme_parameters.accrual_error_text_expr

            _l.info('values %s' % values)
            _l.info('expr %s' % expr)

            has_error = False
            error = PriceHistoryError(
                master_user=self.master_user,
                procedure_instance_id=self.instance['procedure'],
                instrument=record.instrument,
                pricing_scheme=record.pricing_scheme,
                pricing_policy=record.pricing_policy,
                date=record.date,
            )

            principal_price = None
            accrued_price = None

            try:
                principal_price = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:

                has_error = True

                try:
                    error.price_error_text = formula.safe_eval(pricing_error_text_expr, names=values)

                except formula.InvalidExpression:

                    error.price_error_text = 'Invalid Error Text Expression'


            _l.info('principal_price %s' % principal_price)
            _l.info('instrument %s' % record.instrument.user_code)
            _l.info('pricing_policy %s' % record.pricing_policy.user_code)

            if pricing_scheme_parameters.accrual_calculation_method == 2:   # ACCRUAL_PER_SCHEDULE

                try:
                    accrued_price = record.instrument.get_accrued_price(record.date)
                except Exception:
                    has_error = True

                    try:

                        _l.info('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.accrual_error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.accrual_error_text = 'Invalid Error Text Expression'

            if pricing_scheme_parameters.accrual_calculation_method == 3:   # ACCRUAL_PER_FORMULA

                try:
                    accrued_price = formula.safe_eval(accrual_expr, names=values)
                except formula.InvalidExpression:
                    has_error = True

                    try:

                        _l.info('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.accrual_error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.accrual_error_text = 'Invalid Error Text Expression'

            can_write = True

            try:

                price = PriceHistory.objects.get(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                if not self.procedure.price_overwrite_principal_prices and not self.procedure.price_overwrite_accrued_prices:
                    can_write = False
                    _l.info('Skips %s' % price)
                else:
                    _l.info('Overwrite existing %s' % price)

            except PriceHistory.DoesNotExist:

                price = PriceHistory(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date,
                    principal_price=principal_price
                )

                _l.info('Create new %s' % price)

            price.principal_price = 0
            price.accrued_price = 0

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

            _l.info('Price: %s. Can write: %s. Has Error: %s.' % (price, can_write, has_error))

            if can_write:

                if has_error or (price.accrued_price == 0 and price.principal_price == 0):
                    error.save()
                else:
                    price.save()

            else:

                error.error_text =  "Prices already exists. Principal Price: " + str(principal_price) +"; Accrued: "+ str(accrued_price) +"."

                error.status = PriceHistoryError.STATUS_SKIP
                error.save()

            if self.instance['data']['date_to'] == str(record.date):

                _l.info("Wtrade Roll Prices for Price History")

                roll_price_history_for_n_day_forward(record, self.procedure, price, self.master_user, self.procedure_instance)

        PricingProcedureWtradeInstrumentResult.objects.filter(master_user=self.master_user,
                                                                 procedure=self.instance['procedure'],
                                                                 date__gte=self.instance['data']['date_from'],
                                                                 date__lte=self.instance['data']['date_to']).delete()


class FillPricesBrokerFixerProcess(object):

    def __init__(self, instance, master_user):

        self.instance = instance
        self.master_user = master_user

        self.procedure_instance = PricingProcedureInstance.objects.get(pk=self.instance['procedure'])
        self.procedure = self.procedure_instance.pricing_procedure

        _l.info("Broker Fixer - Get FX Rates: %s" % self.procedure.price_get_fx_rates)
        _l.info("Broker Fixer - Overwrite FX Rates: %s" % self.procedure.price_overwrite_fx_rates)
        _l.info('Broker Fixer - Roll Days N Forward: %s' % self.procedure.price_fill_days)

    def process(self):

        _l.info('< fill prices: total items len %s' % len(self.instance['data']['items']))
        _l.info('< action:  %s' % self.instance['action'])

        if self.instance['action'] == 'fixer_get_currency_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureFixerCurrencyResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference'],
                    currency_parameters=str(item['parameters'])
                )

                _l.info('< fill currency prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                _l.info('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if field['code'] == 'close':

                                    try:
                                        record.close_value = float(val_obj['value'])
                                    except Exception as e:
                                        _l.info('close_value e %s ' % e)

                                record.save()

                        if not len(records):
                            _l.info('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                _l.info('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_currency_history()

            _l.info("process fill currency prices")

    def create_currency_history(self):

        _l.info("Creating currency history")

        records = PricingProcedureFixerCurrencyResult.objects.filter(
            master_user=self.master_user,
            procedure=self.instance['procedure'],
            date__gte=self.instance['data']['date_from'],
            date__lte=self.instance['data']['date_to']
        )

        _l.info('create_currency_history: records len %s' % len(records))

        for record in records:

            safe_currency = {
                'id': record.currency.id,
            }

            values = {
                'd': record.date,
                'currency': safe_currency,
                'close': record.close_value,
            }

            has_error = False
            error = CurrencyHistoryError(
                master_user=self.master_user,
                procedure_instance_id=self.instance['procedure'],
                currency=record.currency,
                pricing_scheme=record.pricing_scheme,
                pricing_policy=record.pricing_policy,
                date=record.date,
            )

            pricing_scheme_parameters = record.pricing_scheme.get_parameters()

            expr = pricing_scheme_parameters.expr
            error_text_expr = pricing_scheme_parameters.error_text_expr

            _l.info('values %s' % values)
            _l.info('expr %s' % expr)

            fx_rate = None

            try:
                fx_rate = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:

                has_error = True

                try:
                    error.error_text = formula.safe_eval(error_text_expr, names=values)
                except formula.InvalidExpression:
                    error.error_text = 'Invalid Error Text Expression'

            _l.info('fx_rate %s' % fx_rate)
            _l.info('currency %s' % record.currency.user_code)
            _l.info('pricing_policy %s' % record.pricing_policy.user_code)

            can_write = True

            try:

                price = CurrencyHistory.objects.get(
                    currency=record.currency,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                if not self.procedure.price_overwrite_fx_rates:
                    can_write = False
                    _l.info('Skip %s' % price)
                else:
                    _l.info('Overwrite existing %s' % price)

            except CurrencyHistory.DoesNotExist:

                price = CurrencyHistory(
                    currency=record.currency,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

                _l.info('Create new %s' % price)

            price.fx_rate = 0

            if fx_rate:
                price.fx_rate = fx_rate

            if can_write:

                if has_error or fx_rate == 0:
                    error.save()
                else:
                    price.save()

            else:
                error.error_text = "Prices already exists. Fx rate: " + str(fx_rate) + "."

                error.status = CurrencyHistoryError.STATUS_SKIP
                error.save()

            if parse_date_iso(self.instance['data']['date_to']) == record.date:

                _l.info("Fixer Roll Prices for Currency History")

                roll_currency_history_for_n_day_forward(record, self.procedure, price, self.master_user, self.procedure_instance)

        PricingProcedureFixerCurrencyResult.objects.filter(master_user=self.master_user,
                                                               procedure=self.instance['procedure'],
                                                               date__gte=self.instance['data']['date_from'],
                                                               date__lte=self.instance['data']['date_to']).delete()
