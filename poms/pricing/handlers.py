import time

from django.db.models import Q

from poms.common import formula
from poms.common.utils import isclose, date_now
from poms.instruments.models import Instrument, DailyPricingModel, PriceHistory, PricingPolicy
from poms.integrations.models import ProviderClass
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.pricing.brokers.broker_bloomberg import BrokerBloomberg
from poms.pricing.models import InstrumentPricingSchemeType, PricingProcedureBloombergResult
from poms.reports.builders.balance_item import ReportItem, Report
from poms.reports.builders.balance_pl import ReportBuilder
from datetime import timedelta, date, datetime


def get_list_of_dates_between_two_dates(date_from, date_to):

    result = []

    diff = date_to - date_from

    for i in range(diff.days + 1):
        day = date_from + timedelta(days=i)
        result.append(day)

    return result


class InstrumentItem(object):

    def __init__(self, instrument, policy, pricing_scheme):
        self.instrument = instrument
        self.policy = policy
        self.pricing_scheme = pricing_scheme

        self.scheme_fields = []
        self.scheme_fields_map = {}
        self.parameters = []

        self.fill_parameters()
        self.fill_scheme_fields()

    def fill_parameters(self):

        if self.pricing_scheme.type.input_type == InstrumentPricingSchemeType.NONE:
            pass # do nothing

        if self.pricing_scheme.type.input_type == InstrumentPricingSchemeType.SINGLE_PARAMETER:

            if self.policy.default_value:
                self.parameters.append(self.policy.default_value)
            else:

                result = None

                if self.policy.attribute_key == 'reference_for_pricing':
                    result = self.instrument.reference_for_pricing
                else:

                    try:

                        attribute = GenericAttribute.objects.get(object_id=self.instrument.id, attribute_type__user_code=self.policy.attribute_key)

                        if attribute.attribute_type.value_type == GenericAttributeType.STRING:
                            result = attribute.value_string

                        if attribute.attribute_type.value_type == GenericAttributeType.NUMBER:
                            result = attribute.value_float

                        if attribute.attribute_type.value_type == GenericAttributeType.DATE:
                            result = attribute.value_date

                        if attribute.attribute_type.value_type == GenericAttributeType.CLASSIFIER:

                            if attribute.classifier:
                                result = attribute.classifier.name

                    except GenericAttribute.DoesNotExist:
                        pass

                if result:
                    self.parameters.append(result)

        if self.pricing_scheme.type.input_type == InstrumentPricingSchemeType.MULTIPLE_PARAMETERS:
            pass # TODO implement multiparameter case

    def fill_scheme_fields(self):

        parameters = self.pricing_scheme.get_parameters()

        if self.pricing_scheme.type.id == 5:

            self.scheme_fields_map = {}

            if parameters.bid_historical:
                self.scheme_fields.append([parameters.bid_historical])
                self.scheme_fields_map['bid_historical'] = parameters.bid_historical

            if parameters.ask_historical:
                self.scheme_fields.append([parameters.ask_historical])
                self.scheme_fields_map['ask_historical'] = parameters.ask_historical

            if parameters.last_historical:
                self.scheme_fields.append([parameters.last_historical])
                self.scheme_fields_map['last_historical'] = parameters.last_historical

            if parameters.bid_yesterday:
                self.scheme_fields.append([parameters.bid_yesterday])
                self.scheme_fields_map['bid_yesterday'] = parameters.bid_yesterday

            if parameters.ask_yesterday:
                self.scheme_fields.append([parameters.ask_yesterday])
                self.scheme_fields_map['ask_yesterday'] = parameters.ask_yesterday

            if parameters.last_yesterday:
                self.scheme_fields.append([parameters.last_yesterday])
                self.scheme_fields_map['last_yesterday'] = parameters.last_yesterday



class CurrencyItem(object):

    def __init__(self, currency, policy, pricing_scheme):
        self.currency = currency
        self.policy = policy
        self.pricing_scheme = pricing_scheme

        self.scheme_fields = []
        self.parameters = []


class PricingProcedureProcess(object):

    def __init__(self, procedure=None, master_user=None):

        self.master_user = master_user
        self.procedure = procedure

        self.instruments = []
        self.currencies = []

        self.instrument_pricing_schemes = []
        self.currencies_pricing_schemes = []

        self.instrument_items = []
        self.currency_items = []

        self.instrument_items_grouped = {}
        self.currency_items_grouped = {}

        self.broker_bloomberg = BrokerBloomberg()

        self.execute_procedure_date_expressions()

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

        if self.procedure.accrual_date_from_expr:
            try:
                self.procedure.accrual_date_from = formula.safe_eval(self.procedure.accrual_date_from_expr, names={})
            except formula.InvalidExpression as e:
                print("Cant execute accrual date from expression %s " % e)

        if self.procedure.accrual_date_to_expr:
            try:
                self.procedure.accrual_date_to = formula.safe_eval(self.procedure.accrual_date_to_expr, names={})
            except formula.InvalidExpression as e:
                print("Cant execute accrual date to expression %s " % e)

        print('price_date_from %s' % self.procedure.price_date_from)
        print('price_date_to %s' % self.procedure.price_date_to)
        print('price_balance_date %s' % self.procedure.price_balance_date)
        print('accrual_date_from %s' % self.procedure.accrual_date_from)
        print('accrual_date_to %s' % self.procedure.accrual_date_to)

    def print_grouped_instruments(self):

        names = {
            1: 'Skip',
            2: 'Manual Pricing',
            3: 'Single Parameter Formula',
            4: 'Multiple Parameter Formula',
            5: 'Bloomberg'

        }

        for provider_id, items in self.instrument_items_grouped.items():

            print("Provider %s: len: %s" % (names[provider_id], len(items)))


    def process(self):

        print("Pricing Procedure Process")

        self.instruments = self.get_instruments()

        self.instrument_pricing_schemes = self.get_unique_pricing_schemes(self.instruments)
        self.currencies_pricing_schemes = self.get_unique_pricing_schemes(self.currencies)

        print('instrument_pricing_schemes len %s' % len(self.instrument_pricing_schemes))
        print('currencies_pricing_schemes len %s' % len(self.currencies_pricing_schemes))

        self.instrument_items = self.get_instrument_items()
        self.currency_items = self.get_currency_items()

        print('instrument_items len %s' % len(self.instrument_items))
        print('currency_items len %s' % len(self.currency_items))

        self.instrument_items_grouped = self.group_items_by_provider(items=self.instrument_items, groups=self.instrument_pricing_schemes)
        self.currency_items_grouped = self.group_items_by_provider(items=self.currency_items, groups=self.currencies_pricing_schemes)

        print('instrument_items_grouped len %s' % len(self.instrument_items_grouped))
        print('currency_items_grouped len %s' % len(self.currency_items_grouped))

        self.print_grouped_instruments()

        for provider_id, items in self.instrument_items_grouped.items():

                if provider_id == 5:

                    self.process_to_bloomberg_provider(items)

                if provider_id == 3:

                    self.process_to_single_parameter_formula(items)

    def get_instruments(self):

        result = []

        instruments = Instrument.objects.filter(
            master_user=self.procedure.master_user
        ).exclude(
            daily_pricing_model=DailyPricingModel.SKIP
        )

        instruments_opened = set()
        instruments_always = set()

        for i in instruments:

            if i.daily_pricing_model_id in [DailyPricingModel.FORMULA_ALWAYS, DailyPricingModel.PROVIDER_ALWAYS]:
                instruments_always.add(i.id)

        if self.procedure.price_balance_date:

            owner_or_admin = self.procedure.master_user.members.filter(Q(is_owner=True) | Q(is_admin=True)).first()

            report = Report(master_user=self.procedure.master_user, member=owner_or_admin, report_date=self.procedure.price_balance_date)

            builder = ReportBuilder(instance=report)

            builder.build_position_only()

            for i in report.items:
                if i.type == ReportItem.TYPE_INSTRUMENT and not isclose(i.pos_size, 0.0):
                    if i.instr:
                        instruments_opened.add(i.instr.id)

        instruments = instruments.filter(pk__in=(instruments_always | instruments_opened))

        # Filter by Procedure Filter Settings

        if self.procedure.instrument_filters:
            for instrument in instruments:

                if instrument.user_code in self.procedure.instrument_filters:
                    result.append(instrument)
        else:
            result = instruments

        return result

    def get_instrument_items(self):

        result = []

        for instrument in self.instruments:

            for policy in instrument.pricing_policies.all():

                # Filter By Procedure Filter Settings
                # TODO refactor soon

                if self.procedure.pricing_policy_filters:

                    if policy.pricing_policy.user_code in self.procedure.pricing_policy_filters:

                        item = InstrumentItem(instrument, policy, policy.pricing_scheme)

                        result.append(item)

                else:

                    item = InstrumentItem(instrument, policy, policy.pricing_scheme)

                    result.append(item)

        return result

    def get_currency_items(self):

        result = []

        for currency in self.currencies:

            for policy in currency.pricing_policies.all():

                item = CurrencyItem(currency, policy, policy.pricing_scheme)

                result.append(item)

        return result

    def get_unique_pricing_schemes(self, items):

        unique_ids = []
        result = []

        for item in items:

            for policy in item.pricing_policies.all():

                if policy.pricing_scheme:

                    if policy.pricing_scheme.id not in unique_ids:

                        unique_ids.append(policy.pricing_scheme.id)
                        result.append(policy.pricing_scheme)

        return result

    def group_items_by_provider(self, items, groups):

        result = {}

        for item in groups:
            result[item.type.id] = []

        for item in items:

            result[item.policy.pricing_scheme.type.id].append(item)

        return result

    def is_yesterday(self, date_from, date_to):

        if date_from == date_to:

            yesterday = date_now() - timedelta(days=1)

            if yesterday == date_from:

                return True

        return False

    def process_to_bloomberg_provider(self, items):

        body = {}
        body['procedure'] = self.procedure.id

        config = self.master_user.import_configs.get(provider=ProviderClass.BLOOMBERG)
        body['user'] = {
            'token': self.master_user.id,
            'credentials': {
                'p12cert': str(config.p12cert),
                'password': config.password
            }
        }

        body['data'] = {}

        body['data']['date_from'] = str(self.procedure.price_date_from)
        body['data']['date_to'] = str(self.procedure.price_date_to)
        body['data']['items'] = []

        items_with_missing_parameters = []

        dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from, date_to=self.procedure.price_date_to)

        is_yesterday = self.is_yesterday(self.procedure.price_date_from, self.procedure.price_date_to)

        print('is_yesterday %s' % is_yesterday)

        for item in items:

            if len(item.parameters):

                item_parameters = item.parameters.copy()
                item_parameters.pop()

                if is_yesterday:

                    for date in dates:

                        try:

                            record = PricingProcedureBloombergResult(master_user=self.master_user,
                                                                     procedure=self.procedure,
                                                                     instrument=item.instrument,
                                                                     instrument_parameters=str(item_parameters),
                                                                     pricing_policy=item.policy.pricing_policy,
                                                                     reference=item.parameters[0],
                                                                     date=date,
                                                                     ask_parameters=item.scheme_fields_map['ask_yesterday'],
                                                                     bid_parameters=item.scheme_fields_map['bid_yesterday'],
                                                                     last_parameters=item.scheme_fields_map['last_yesterday'])
                            record.save()

                        except Exception as e:
                            print("Cant create Result Record %s" % e)

                    item_obj = {
                        'reference': item.parameters[0],
                        'parameters': item_parameters,
                        'fields': []
                    }

                    if item.scheme_fields_map['ask_yesterday']:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['ask_yesterday'],
                            'parameters': [],
                            'values': []
                        })

                    if item.scheme_fields_map['bid_yesterday']:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['bid_yesterday'],
                            'parameters': [],
                            'values': []
                        })

                    if item.scheme_fields_map['last_yesterday']:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['last_yesterday'],
                            'parameters': [],
                            'values': []
                        })


                    body['data']['items'].append(item_obj)

                else:

                    for date in dates:

                        try:

                            record = PricingProcedureBloombergResult(master_user=self.master_user,
                                                                     procedure=self.procedure,
                                                                     instrument=item.instrument,
                                                                     instrument_parameters=str(item_parameters),
                                                                     pricing_policy=item.policy.pricing_policy,
                                                                     reference=item.parameters[0],
                                                                     date=date,
                                                                     ask_parameters=item.scheme_fields_map['ask_historical'],
                                                                     bid_parameters=item.scheme_fields_map['bid_historical'],
                                                                     last_parameters=item.scheme_fields_map['last_historical'])
                            record.save()

                        except Exception as e:
                            print("Cant create Result Record %s" % e)

                    item_obj = {
                        'reference': item.parameters[0],
                        'parameters': item_parameters,
                        'fields': []
                    }

                    if item.scheme_fields_map['ask_historical']:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['ask_historical'],
                            'parameters': [],
                            'values': []
                        })

                    if item.scheme_fields_map['bid_historical']:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['bid_historical'],
                            'parameters': [],
                            'values': []
                        })

                    if item.scheme_fields_map['last_historical']:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['last_historical'],
                            'parameters': [],
                            'values': []
                        })

                    body['data']['items'].append(item_obj)

            else:
                items_with_missing_parameters.append(item)

        print('items_with_missing_parameters %s' % len(items_with_missing_parameters))
        # print('data %s' % data)

        print('self.procedure %s' % self.procedure.id)
        print('send request %s' % body)

        self.broker_bloomberg.send_request(body)

    def process_to_single_parameter_formula(self, items):

        print("Single parameters formula len %s" % len(items))

        dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from, date_to=self.procedure.price_date_to)

        for item in items:

            for date in dates:

                scheme_parameters = item.pricing_scheme.get_parameters()

                if scheme_parameters:

                    safe_instrument = {
                        'id': item.instrument.id,
                    }

                    parameter = None

                    if item.policy.default_value:

                        if scheme_parameters.value_type == 10:

                            parameter = str(item.policy.default_value)

                        elif scheme_parameters.value_type == 20:

                            parameter = float(item.policy.default_value)

                        else:

                            parameter = item.policy.default_value

                        # if scheme_parameters.type == 40:
                        #
                        #     parameter = float(item.policy.default_value)


                    values = {
                        'd': date,
                        'instrument': safe_instrument,
                        'parameter': parameter
                    }

                    expr = scheme_parameters.expr

                    print('values %s' % values)
                    print('expr %s' % expr)

                    try:
                        principal_price = formula.safe_eval(expr, names=values)
                    except formula.InvalidExpression:
                        print("Error here")
                        continue

                    print('principal_price %s' % principal_price)

                    if principal_price:

                        try:

                            price = PriceHistory.objects.get(
                                instrument=item.instrument,
                                pricing_policy=item.policy.pricing_policy,
                                date=date
                            )

                            price.principal_price = principal_price
                            price.save()

                            print('Update Price history %s' % price.id)

                        except PriceHistory.DoesNotExist:

                            price = PriceHistory(
                                instrument=item.instrument,
                                pricing_policy=item.policy.pricing_policy,
                                date=date,
                                principal_price=principal_price
                            )

                            price.save()


class FillPricesProcess(object):

    def __init__(self, instance, master_user):

        self.instance = instance
        self.master_user = master_user

    def process(self):

        print('< fill prices: total items len %s' % len(self.instance['data']['items']))

        print('< fill prices: fields len %s' % len(self.instance['data']['items'][0]['fields']))

        print('< fill prices: values len %s' % len(self.instance['data']['items'][0]['fields'][0]['values']))

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
