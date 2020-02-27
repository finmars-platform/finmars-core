import time


from poms.common import formula
from poms.instruments.models import PriceHistory

from poms.pricing.currency_handler import PricingCurrencyHandler
from poms.pricing.instrument_handler import PricingInstrumentHandler
from poms.pricing.models import PricingProcedureBloombergResult


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


class FillPricesProcess(object):

    def __init__(self, instance, master_user):

        self.instance = instance
        self.master_user = master_user

    def process(self):

        print('< fill prices: total items len %s' % len(self.instance['data']['items']))

        # print('< fill prices: fields len %s' % len(self.instance['data']['items'][0]['fields']))
        #
        # print('< fill prices: values len %s' % len(self.instance['data']['items'][0]['fields'][0]['values']))

        for item in self.instance['data']['items']:

            records_st = time.perf_counter()

            records = PricingProcedureBloombergResult.objects.filter(
                master_user=self.master_user,
                procedure=self.instance['procedure'],
                reference=item['reference'],
                instrument_parameters=str(item['parameters'])
            )

            print('< fill prices: records for %s len %s' % (item['reference'], len(list(records))))

            processing_st = time.perf_counter()

            print('< get records from db done: %s', (time.perf_counter() - records_st))

            for record in records:

                for field in item['fields']:

                    for val_obj in field['values']:

                        if str(record.date) == str(val_obj['date']):

                            if field['code'] in record.ask_parameters:

                                try:
                                    record.ask_value = float(val_obj['value'])
                                except Exception as e:
                                    print('ask value e %s ' % e)

                            if field['code'] in record.bid_parameters:

                                try:
                                    record.bid_value = float(val_obj['value'])
                                except Exception as e:
                                    print('bid value e %s ' % e)

                            if field['code'] in record.last_parameters:

                                try:
                                    record.last_value = float(val_obj['value'])
                                except Exception as e:
                                    print('last value e %s ' % e)

                            record.save()

                    if not len(records):
                        print('Cant fill the value. Related records not found. Reference %s' % item['reference'])

            print('< processing item: %s', (time.perf_counter() - processing_st))

        self.create_price_history()

        print("process fill prices")

    def create_price_history(self):

        print("Creating price history")

        records = PricingProcedureBloombergResult.objects.filter(
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
                'last': record.last_value
            }

            pricing_scheme = record.pricing_policy.default_instrument_pricing_scheme

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

            if principal_price:

                try:

                    price = PriceHistory.objects.get(
                        instrument=record.instrument,
                        pricing_policy=record.pricing_policy,
                        date=record.date
                    )

                    price.principal_price = principal_price
                    price.save()

                    print('Update Price history %s' % price.id)

                except PriceHistory.DoesNotExist:

                    price = PriceHistory(
                        instrument=record.instrument,
                        pricing_policy=record.pricing_policy,
                        date=record.date,
                        principal_price=principal_price
                    )

                    price.save()

                    print('Create New Price history %s' % price.id)

        PricingProcedureBloombergResult.objects.filter(master_user=self.master_user,
                                                       procedure=self.instance['procedure'],
                                                       date__gte=self.instance['data']['date_from'],
                                                       date__lte=self.instance['data']['date_to']).delete()
