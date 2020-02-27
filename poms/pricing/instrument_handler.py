from datetime import timedelta

from django.db import transaction
from django.db.models import Q

from poms.common import formula
from poms.common.utils import isclose, date_now
from poms.instruments.models import Instrument, DailyPricingModel, PriceHistory
from poms.integrations.models import ProviderClass
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.pricing.brokers.broker_bloomberg import BrokerBloomberg
from poms.pricing.models import InstrumentPricingSchemeType, PricingProcedureInstance, \
    PricingProcedureBloombergInstrumentResult
from poms.pricing.utils import get_unique_pricing_schemes, get_list_of_dates_between_two_dates, group_items_by_provider, \
    get_is_yesterday
from poms.reports.builders.balance_item import Report, ReportItem
from poms.reports.builders.balance_pl import ReportBuilder


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
            pass  # do nothing

        if self.pricing_scheme.type.input_type == InstrumentPricingSchemeType.SINGLE_PARAMETER:

            if self.policy.default_value:
                self.parameters.append(self.policy.default_value)
            else:

                result = None

                if self.policy.attribute_key == 'reference_for_pricing':
                    result = self.instrument.reference_for_pricing
                else:

                    try:

                        attribute = GenericAttribute.objects.get(object_id=self.instrument.id,
                                                                 attribute_type__user_code=self.policy.attribute_key)

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
            pass  # TODO implement multiparameter case

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


class PricingInstrumentHandler(object):

    def __init__(self, procedure=None, master_user=None):

        self.master_user = master_user
        self.procedure = procedure

        self.instruments = []

        self.instrument_pricing_schemes = []

        self.instrument_items = []

        self.instrument_items_grouped = {}

        self.broker_bloomberg = BrokerBloomberg()

    def process(self):

        print("Pricing Instrument Handler: Process")

        self.instruments = self.get_instruments()

        self.instrument_pricing_schemes = get_unique_pricing_schemes(self.instruments)

        print('instrument_pricing_schemes len %s' % len(self.instrument_pricing_schemes))

        self.instrument_items = self.get_instrument_items()

        print('instrument_items len %s' % len(self.instrument_items))

        self.instrument_items_grouped = group_items_by_provider(items=self.instrument_items,
                                                                groups=self.instrument_pricing_schemes)

        print('instrument_items_grouped len %s' % len(self.instrument_items_grouped))

        self.print_grouped_instruments()

        for provider_id, items in self.instrument_items_grouped.items():

            # DEPRECATED
            # if provider_id == 2:
            #     self.process_to_manual_pricing(items)

            if provider_id == 3:
                self.process_to_single_parameter_formula(items)

            if provider_id == 4:
                self.process_to_multiple_parameter_formula(items)

            if provider_id == 5:
                self.process_to_bloomberg_provider(items)

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

            report = Report(master_user=self.procedure.master_user, member=owner_or_admin,
                            report_date=self.procedure.price_balance_date)

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

    # DEPRECATED
    def process_to_manual_pricing(self, items):

        print("Process Manual Pricing: len %s" % len(items))

        dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                    date_to=self.procedure.price_date_to)

        for item in items:

            for date in dates:

                principal_price = item.policy.default_value

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

    def process_to_single_parameter_formula(self, items):

        print("Pricing Instrument Handler - Single parameters Formula: len %s" % len(items))

        dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                    date_to=self.procedure.price_date_to)

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

                        if scheme_parameters.value_type == 40:

                            parameter = formula._parse_date(str(item.policy.default_value))

                        else:

                            parameter = item.policy.default_value

                    elif item.policy.attribute_key:

                        if 'attributes' in item.policy.attribute_key:

                            user_code = item.policy.attribute_key.split('attributes.')[1]

                            attribute = GenericAttribute.objects.get(object_id=item.instrument.id,
                                                                     attribute_type__user_code=user_code)

                            if scheme_parameters.value_type == 10:
                                parameter = attribute.value_string

                            if scheme_parameters.value_type == 20:
                                parameter = attribute.value_float

                            if scheme_parameters.value_type == 40:
                                parameter = attribute.value_date

                        else:

                            parameter = item.instrument[item.policy.attribute_key]

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

    def process_to_multiple_parameter_formula(self, items):

        print("Pricing Instrument Handler - Multiple parameters Formula: len %s" % len(items))

        dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                    date_to=self.procedure.price_date_to)

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

                        if scheme_parameters.value_type == 40:

                            parameter = formula._parse_date(str(item.policy.default_value))

                        else:

                            parameter = item.policy.default_value

                    elif item.policy.attribute_key:

                        if 'attributes' in item.policy.attribute_key:

                            user_code = item.policy.attribute_key.split('attributes.')[1]

                            attribute = GenericAttribute.objects.get(object_id=item.instrument.id,
                                                                     attribute_type__user_code=user_code)

                            if scheme_parameters.value_type == 10:
                                parameter = attribute.value_string

                            if scheme_parameters.value_type == 20:
                                parameter = attribute.value_float

                            if scheme_parameters.value_type == 40:
                                parameter = attribute.value_date

                        else:

                            parameter = item.instrument[item.policy.attribute_key]

                    values = {
                        'd': date,
                        'instrument': safe_instrument,
                        'parameter': parameter
                    }

                    if item.policy.data:

                        if 'parameters' in item.policy.data:

                            for parameter in item.policy.data['parameters']:

                                print('parameter %s ' % parameter)

                                if 'default_value' in parameter and parameter['default_value']:

                                    if float(parameter['value_type']) == 10:

                                        val = str(parameter['default_value'])

                                    elif float(parameter['value_type']) == 20:

                                        val = float(parameter['default_value'])

                                    elif float(parameter['value_type']) == 40:

                                        val = formula._parse_date(str(parameter['default_value']))

                                    else:

                                        val = parameter['default_value']

                                if 'attribute_key' in parameter and parameter['attribute_key']:

                                    if 'attributes' in parameter['attribute_key']:

                                        user_code = parameter['attribute_key'].split('attributes.')[1]

                                        attribute = GenericAttribute.objects.get(object_id=item.instrument.id,
                                                                                 attribute_type__user_code=user_code)

                                        if float(parameter['value_type']) == 10:
                                            val = attribute.value_string

                                        if float(parameter['value_type']) == 20:
                                            val = attribute.value_float

                                        if float(parameter['value_type']) == 40:
                                            val = attribute.value_date

                                    else:

                                        val = item.instrument[parameter['attribute_key']]

                                values['parameter' + str(parameter['index'])] = val

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

    def optimize_items(self, items):

        unique_references = []
        unique_codes = {}

        result_dict = {}
        result = []

        for item in items:

            reference_identifier = item['reference'] + ','.join(item['parameters'])

            if reference_identifier not in unique_references:

                result_item = {}

                result_item['reference'] = item['reference']
                result_item['parameters'] = item['parameters']
                result_item['fields'] = []

                unique_references.append(reference_identifier)

                unique_codes[reference_identifier] = []

                for field in item['fields']:

                    code_identifier = field['code'] + ','.join(field['parameters'])

                    if code_identifier not in unique_codes[reference_identifier]:
                        unique_codes[reference_identifier].append(code_identifier)

                        result_item['fields'].append(field)

                result_dict[reference_identifier] = result_item

            else:

                for field in item['fields']:

                    code_identifier = field['code'] + ','.join(field['parameters'])

                    if code_identifier not in unique_codes[reference_identifier]:
                        unique_codes[reference_identifier].append(code_identifier)

                        result_dict[reference_identifier]['fields'].append(field)

        for key, value in result_dict.items():
            result.append(value)

        return result

    def process_to_bloomberg_provider(self, items):

        print("Pricing Instrument Handler - Bloomberg Provider: len %s" % len(items))

        procedure_instance = PricingProcedureInstance(pricing_procedure=self.procedure,
                                                      master_user=self.master_user,
                                                      status=PricingProcedureInstance.STATUS_PENDING,
                                                      action='bloomberg_get_instrument_prices',
                                                      provider='bloomberg')
        procedure_instance.save()

        body = {}
        body['action'] = procedure_instance.action
        body['procedure'] = procedure_instance.id
        body['provider'] = procedure_instance.provider

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

        dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                    date_to=self.procedure.price_date_to)

        is_yesterday = get_is_yesterday(self.procedure.price_date_from, self.procedure.price_date_to)

        print('is_yesterday %s' % is_yesterday)
        print('procedure id %s' % body['procedure'])

        full_items = []

        for item in items:

            if len(item.parameters):

                item_parameters = item.parameters.copy()
                item_parameters.pop()

                if is_yesterday:

                    for date in dates:

                        with transaction.atomic():
                            try:
                                record = PricingProcedureBloombergInstrumentResult(master_user=self.master_user,
                                                                                   procedure=procedure_instance,
                                                                                   instrument=item.instrument,
                                                                                   instrument_parameters=str(
                                                                                       item_parameters),
                                                                                   pricing_policy=item.policy.pricing_policy,
                                                                                   reference=item.parameters[0],
                                                                                   date=date)

                                if 'ask_yesterday' in item.scheme_fields_map:
                                    record.ask_parameters = item.scheme_fields_map[
                                        'ask_yesterday']

                                if 'bid_yesterday' in item.scheme_fields_map:
                                    record.bid_parameters = item.scheme_fields_map[
                                        'bid_yesterday']

                                if 'last_yesterday' in item.scheme_fields_map:
                                    record.last_parameters = item.scheme_fields_map[
                                        'last_yesterday']

                                record.save()

                            except Exception as e:
                                print("Cant create Result Record %s" % e)
                                pass

                    item_obj = {
                        'reference': item.parameters[0],
                        'parameters': item_parameters,
                        'fields': []
                    }

                    if 'ask_yesterday' in item.scheme_fields_map:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['ask_yesterday'],
                            'parameters': [],
                            'values': []
                        })

                    if 'bid_yesterday' in item.scheme_fields_map:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['bid_yesterday'],
                            'parameters': [],
                            'values': []
                        })

                    if 'last_yesterday' in item.scheme_fields_map:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['last_yesterday'],
                            'parameters': [],
                            'values': []
                        })

                    full_items.append(item_obj)

                else:

                    for date in dates:

                        with transaction.atomic():
                            try:

                                record = PricingProcedureBloombergInstrumentResult(master_user=self.master_user,
                                                                                   procedure=procedure_instance,
                                                                                   instrument=item.instrument,
                                                                                   instrument_parameters=str(
                                                                                       item_parameters),
                                                                                   pricing_policy=item.policy.pricing_policy,
                                                                                   reference=item.parameters[0],
                                                                                   date=date)

                                if 'ask_historical' in item.scheme_fields_map:
                                    record.ask_parameters = item.scheme_fields_map[
                                        'ask_historical']

                                if 'bid_historical' in item.scheme_fields_map:
                                    record.bid_parameters = item.scheme_fields_map[
                                        'bid_historical']

                                if 'last_historical' in item.scheme_fields_map:
                                    record.last_parameters = item.scheme_fields_map[
                                        'last_historical']

                                record.save()

                            except Exception as e:
                                print("Cant create Result Record %s" % e)

                    item_obj = {
                        'reference': item.parameters[0],
                        'parameters': item_parameters,
                        'fields': []
                    }

                    if 'ask_historical' in item.scheme_fields_map:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['ask_historical'],
                            'parameters': [],
                            'values': []
                        })

                    if 'bid_historical' in item.scheme_fields_map:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['bid_historical'],
                            'parameters': [],
                            'values': []
                        })

                    if 'last_historical' in item.scheme_fields_map:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['last_historical'],
                            'parameters': [],
                            'values': []
                        })

                    full_items.append(item_obj)

            else:
                items_with_missing_parameters.append(item)

        print('full_items len: %s' % len(full_items))

        optimized_items = self.optimize_items(full_items)

        print('optimized_items len: %s' % len(optimized_items))

        body['data']['items'] = optimized_items

        print('items_with_missing_parameters %s' % len(items_with_missing_parameters))
        # print('data %s' % data)

        print('self.procedure %s' % self.procedure.id)
        print('send request %s' % body)

        self.broker_bloomberg.send_request(body)

    def print_grouped_instruments(self):

        names = {
            1: 'Skip',
            2: 'Manual Pricing',  # DEPRECATED
            3: 'Single Parameter Formula',
            4: 'Multiple Parameter Formula',
            5: 'Bloomberg'

        }

        for provider_id, items in self.instrument_items_grouped.items():
            print("Pricing Instrument Handler - Provider %s: len: %s" % (names[provider_id], len(items)))
