import time


from poms.common import formula
from poms.currencies.models import CurrencyHistory
from poms.instruments.models import PriceHistory

from poms.pricing.currency_handler import PricingCurrencyHandler
from poms.pricing.instrument_handler import PricingInstrumentHandler
from poms.pricing.models import PricingProcedureBloombergInstrumentResult, PricingProcedureBloombergCurrencyResult, \
    PricingProcedureWtradeInstrumentResult, PricingProcedureWtradeCurrencyResult, PriceHistoryError, \
    CurrencyHistoryError


class PricingProcedureProcess(object):

    def __init__(self, procedure=None, master_user=None):

        self.master_user = master_user
        self.procedure = procedure

        self.execute_procedure_date_expressions()

        self.pricing_instrument_handler = PricingInstrumentHandler(procedure=procedure, master_user=master_user)
        self.pricing_currency_handler = PricingCurrencyHandler(procedure=procedure, master_user=master_user)

    def execute_procedure_date_expressions(self):

        if self.procedure.price_date_from_expr:
            try:
                self.procedure.price_date_from = formula.safe_eval(self.procedure.price_date_from_expr, names={})
            except formula.InvalidExpression as e:
                print("Cant execute price date from expression %s " % e)

        if self.procedure.price_date_to_expr:
            try:
                self.procedure.price_date_to = formula.safe_eval(self.procedure.price_date_to_expr, names={})
            except formula.InvalidExpression as e:
                print("Cant execute price date to expression %s " % e)

        if self.procedure.price_balance_date_expr:
            try:
                self.procedure.price_balance_date = formula.safe_eval(self.procedure.price_balance_date_expr, names={})
            except formula.InvalidExpression as e:
                print("Cant execute balance date expression %s " % e)

        # DEPRECATED
        # if self.procedure.accrual_date_from_expr:
        #     try:
        #         self.procedure.accrual_date_from = formula.safe_eval(self.procedure.accrual_date_from_expr, names={})
        #     except formula.InvalidExpression as e:
        #         print("Cant execute accrual date from expression %s " % e)
        #
        # if self.procedure.accrual_date_to_expr:
        #     try:
        #         self.procedure.accrual_date_to = formula.safe_eval(self.procedure.accrual_date_to_expr, names={})
        #     except formula.InvalidExpression as e:
        #         print("Cant execute accrual date to expression %s " % e)

        print('price_date_from %s' % self.procedure.price_date_from)
        print('price_date_to %s' % self.procedure.price_date_to)
        print('price_balance_date %s' % self.procedure.price_balance_date)
        # print('accrual_date_from %s' % self.procedure.accrual_date_from)
        # print('accrual_date_to %s' % self.procedure.accrual_date_to)

    def process(self):

        self.pricing_instrument_handler.process()
        self.pricing_currency_handler.process()


class FillPricesBrokerBloombergProcess(object):

    def __init__(self, instance, master_user):

        self.instance = instance
        self.master_user = master_user

    def process(self):

        print('< fill prices: total items len %s' % len(self.instance['data']['items']))
        print('< action:  %s' % self.instance['action'])

        if self.instance['action'] == 'bloomberg_get_currency_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureBloombergCurrencyResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference'],
                    currency_parameters=str(item['parameters'])
                )

                print('< fill currency prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                print('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if record.fx_rate_parameters:
                                    if field['code'] in record.fx_rate_parameters:

                                        try:
                                            record.fx_rate_value = float(val_obj['value'])
                                        except Exception as e:
                                            print('fx_rate_value e %s ' % e)

                                record.save()

                        if not len(records):
                            print('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                print('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_currency_history()

            print("process fill currency prices")

        elif self.instance['action'] == 'bloomberg_get_instrument_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureBloombergInstrumentResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference'],
                    instrument_parameters=str(item['parameters'])
                )

                print('< fill instrument prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                print('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if record.ask_parameters:
                                    if field['code'] in record.ask_parameters:

                                        try:
                                            record.ask_value = float(val_obj['value'])
                                        except Exception as e:
                                            print('ask value e %s ' % e)

                                if record.bid_parameters:
                                    if field['code'] in record.bid_parameters:

                                        try:
                                            record.bid_value = float(val_obj['value'])
                                        except Exception as e:
                                             print('bid value e %s ' % e)

                                if record.last_parameters:
                                    if field['code'] in record.last_parameters:

                                        try:
                                            record.last_value = float(val_obj['value'])
                                        except Exception as e:
                                            print('last value e %s ' % e)

                                if record.accrual_parameters:
                                    if field['code'] in record.accrual_parameters:

                                        try:
                                            record.accrual_value = float(val_obj['value'])
                                        except Exception as e:
                                            print('accrual_value value e %s ' % e)

                                record.save()

                        if not len(records):
                            print('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                print('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_price_history()

            print("process fill instrument prices")

    def create_price_history(self):

        print("Creating price history")

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

            print('values %s' % values)
            print('expr %s' % expr)

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


            print('principal_price %s' % principal_price)
            print('instrument %s' % record.instrument.user_code)
            print('pricing_policy %s' % record.pricing_policy.user_code)

            if record.pricing_scheme.accrual_calculation_method == 2:   # ACCRUAL_PER_SCHEDULE

                try:
                    accrued_price = record.instrument.get_accrued_price(date)
                except Exception:
                    has_error = True

                    try:

                        print('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.accrual_error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.accrual_error_text = 'Invalid Error Text Expression'

            if record.pricing_scheme.accrual_calculation_method == 3:   # ACCRUAL_PER_FORMULA

                try:
                    accrued_price = formula.safe_eval(accrual_expr, names=values)
                except formula.InvalidExpression:
                    has_error = True

                    try:

                        print('accrual_error_text_expr %s' % accrual_error_text_expr)

                        error.accrual_error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                    except formula.InvalidExpression:
                        error.accrual_error_text = 'Invalid Error Text Expression'

            try:

                price = PriceHistory.objects.get(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

            except PriceHistory.DoesNotExist:

                price = PriceHistory(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date,
                    principal_price=principal_price
                )

            if principal_price:
                price.principal_price = principal_price
                error.principal_price = principal_price

            if accrued_price:
                price.accrued_price = accrued_price
                error.accrued_price = accrued_price

            price.save()

            if has_error:
                error.save()

        PricingProcedureBloombergInstrumentResult.objects.filter(master_user=self.master_user,
                                                       procedure=self.instance['procedure'],
                                                       date__gte=self.instance['data']['date_from'],
                                                       date__lte=self.instance['data']['date_to']).delete()

    def create_currency_history(self):

        print("Creating currency history")

        records = PricingProcedureBloombergCurrencyResult.objects.filter(
            master_user=self.master_user,
            procedure=self.instance['procedure'],
            date__gte=self.instance['data']['date_from'],
            date__lte=self.instance['data']['date_to']
        )

        print('create_currency_history: records len %s' % len(records))

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

            print('values %s' % values)
            print('expr %s' % expr)

            fx_rate = None

            try:
                fx_rate = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:

                has_error = True

                try:
                    error.error_text = formula.safe_eval(error_text_expr, names=values)
                except formula.InvalidExpression:
                    error.error_text = 'Invalid Error Text Expression'

            print('fx_rate %s' % fx_rate)
            print('currency %s' % record.currency.user_code)
            print('pricing_policy %s' % record.pricing_policy.user_code)

            try:

                price = CurrencyHistory.objects.get(
                    currency=record.currency,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

            except CurrencyHistory.DoesNotExist:

                price = CurrencyHistory(
                    currency=record.currency,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

            if fx_rate:
                price.fx_rate = fx_rate

            price.save()

            if has_error:
                error.save()

        PricingProcedureBloombergCurrencyResult.objects.filter(master_user=self.master_user,
                                                                 procedure=self.instance['procedure'],
                                                                 date__gte=self.instance['data']['date_from'],
                                                                 date__lte=self.instance['data']['date_to']).delete()


class FillPricesBrokerWtradeProcess(object):

    def __init__(self, instance, master_user):

        self.instance = instance
        self.master_user = master_user

    def process(self):

        print('< fill prices: total items len %s' % len(self.instance['data']['items']))
        print('< action:  %s' % self.instance['action'])

        if self.instance['action'] == 'wtrade_get_currency_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureWtradeCurrencyResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference'],
                    currency_parameters=str(item['parameters'])
                )

                print('< fill currency prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                print('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if field['code'] == 'open':

                                    try:
                                        record.open_value = float(val_obj['value'])
                                    except Exception as e:
                                        print('fx_rate_value e %s ' % e)

                                if field['code'] == 'close':

                                    try:
                                        record.close_value = float(val_obj['value'])
                                    except Exception as e:
                                        print('close_value e %s ' % e)

                                if field['code'] == 'high':

                                    try:
                                        record.high_value = float(val_obj['value'])
                                    except Exception as e:
                                        print('high_value e %s ' % e)

                                if field['code'] == 'low':

                                    try:
                                        record.low_value = float(val_obj['value'])
                                    except Exception as e:
                                        print('low_value e %s ' % e)

                                if field['code'] == 'volume':

                                    try:
                                        record.volume_value = float(val_obj['value'])
                                    except Exception as e:
                                        print('volume_value e %s ' % e)

                                record.save()

                        if not len(records):
                            print('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                print('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_currency_history()

            print("process fill currency prices")

        elif self.instance['action'] == 'wtrade_get_instrument_prices':

            for item in self.instance['data']['items']:

                records_st = time.perf_counter()

                records = PricingProcedureWtradeInstrumentResult.objects.filter(
                    master_user=self.master_user,
                    procedure=self.instance['procedure'],
                    reference=item['reference'],
                    instrument_parameters=str(item['parameters'])
                )

                print('< fill instrument prices: records for %s len %s' % (item['reference'], len(list(records))))

                processing_st = time.perf_counter()

                print('< get records from db done: %s', (time.perf_counter() - records_st))

                for record in records:

                    for field in item['fields']:

                        for val_obj in field['values']:

                            if str(record.date) == str(val_obj['date']):

                                if field['code'] == 'open':

                                    try:
                                        record.open_value = float(val_obj['value'])
                                    except Exception as e:
                                        print('fx_rate_value e %s ' % e)

                                if field['code'] == 'close':

                                    try:
                                        record.close_value = float(val_obj['value'])
                                    except Exception as e:
                                        print('close_value e %s ' % e)

                                if field['code'] == 'high':

                                    try:
                                        record.high_value = float(val_obj['value'])
                                    except Exception as e:
                                        print('high_value e %s ' % e)

                                if field['code'] == 'low':

                                    try:
                                        record.low_value = float(val_obj['value'])
                                    except Exception as e:
                                        print('low_value e %s ' % e)

                                if field['code'] == 'volume':

                                    try:
                                        record.volume_value = float(val_obj['value'])
                                    except Exception as e:
                                        print('volume_value e %s ' % e)

                                record.save()

                        if not len(records):
                            print('Cant fill the value. Related records not found. Reference %s' % item['reference'])

                print('< processing item: %s', (time.perf_counter() - processing_st))

            self.create_price_history()

            print("process fill instrument prices")

    def create_price_history(self):

        print("Creating price history")

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

            pricing_scheme = record.pricing_policy.default_instrument_pricing_scheme # TODO why we took default scheme?

            expr = pricing_scheme.get_parameters().expr

            print('values %s' % values)
            print('expr %s' % expr)

            try:
                principal_price = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:
                print("Error here")
                continue

            print('principal_price %s' % principal_price)
            print('instrument %s' % record.instrument.user_code)
            print('pricing_policy %s' % record.pricing_policy.user_code)

            accrued_price = record.instrument.get_accrued_price(record.date)

            try:

                price = PriceHistory.objects.get(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date
                )

            except PriceHistory.DoesNotExist:

                price = PriceHistory(
                    instrument=record.instrument,
                    pricing_policy=record.pricing_policy,
                    date=record.date,
                    principal_price=principal_price
                )

            if principal_price:
                price.principal_price = principal_price

            if accrued_price:
                price.accrued_price = accrued_price

            price.save()

        PricingProcedureWtradeInstrumentResult.objects.filter(master_user=self.master_user,
                                                                 procedure=self.instance['procedure'],
                                                                 date__gte=self.instance['data']['date_from'],
                                                                 date__lte=self.instance['data']['date_to']).delete()

    def create_currency_history(self):

        print("Creating currency history")

        records = PricingProcedureWtradeCurrencyResult.objects.filter(
            master_user=self.master_user,
            procedure=self.instance['procedure'],
            date__gte=self.instance['data']['date_from'],
            date__lte=self.instance['data']['date_to']
        )

        print('create_currency_history: records len %s' % len(records))

        for record in records:

            safe_currency = {
                'id': record.currency.id,
            }

            values = {
                'd': record.date,
                'currency': safe_currency,
                'open': record.open_value,
                'close': record.close_value,
                'high': record.high_value,
                'low': record.low_value,
                'volume': record.volume_value
            }

            pricing_scheme = record.pricing_policy.default_currency_pricing_scheme  # TODO why we took default scheme?

            expr = pricing_scheme.get_parameters().expr

            print('values %s' % values)
            print('expr %s' % expr)

            try:
                fx_rate = formula.safe_eval(expr, names=values)
            except formula.InvalidExpression:
                print("Error here")
                continue

            print('fx_rate %s' % fx_rate)
            print('currency %s' % record.currency.user_code)
            print('pricing_policy %s' % record.pricing_policy.user_code)

            if fx_rate:

                try:

                    price = CurrencyHistory.objects.get(
                        currency=record.currency,
                        pricing_policy=record.pricing_policy,
                        date=record.date
                    )

                    price.fx_rate = fx_rate
                    price.save()

                    print('Update Currency history %s' % price.id)

                except CurrencyHistory.DoesNotExist:

                    price = CurrencyHistory(
                        currency=record.currency,
                        pricing_policy=record.pricing_policy,
                        date=record.date,
                        fx_rate=fx_rate
                    )

                    price.save()

                    print('Create New Currency history %s' % price.id)

        PricingProcedureWtradeCurrencyResult.objects.filter(master_user=self.master_user,
                                                               procedure=self.instance['procedure'],
                                                               date__gte=self.instance['data']['date_from'],
                                                               date__lte=self.instance['data']['date_to']).delete()
