from django.db.models import Q

from poms.common.utils import isclose
from poms.instruments.models import Instrument, DailyPricingModel
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.pricing.brokers.broker_bloomberg import BrokerBloomberg
from poms.pricing.models import InstrumentPricingSchemeType
from poms.reports.builders.balance_item import ReportItem, Report
from poms.reports.builders.balance_pl import ReportBuilder


class InstrumentItem(object):

    def __init__(self, instrument, policy, pricing_scheme):
        self.instrument = instrument
        self.policy = policy
        self.pricing_scheme = pricing_scheme

        self.scheme_fields = []
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

            if parameters.bid0:
                self.scheme_fields.append([parameters.bid0])
            if parameters.bid1:
                self.scheme_fields.append([parameters.bid1])

            if parameters.ask0:
                self.scheme_fields.append([parameters.ask0])
            if parameters.ask1:
                self.scheme_fields.append([parameters.ask1])

            if parameters.last0:
                self.scheme_fields.append([parameters.last0])
            if parameters.last1:
                self.scheme_fields.append([parameters.last1])


class CurrencyItem(object):

    def __init__(self, currency, policy, pricing_scheme):
        self.currency = currency
        self.policy = policy
        self.pricing_scheme = pricing_scheme

        self.scheme_fields = []
        self.parameters = []


class PricingProcedureProcess(object):

    def __init__(self, procedure=None):

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

        self.process()

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

        for provider_id, items in self.instrument_items_grouped.items():

            if provider_id == 5:

                self.process_to_bloomberg_provider(items)

    def get_instruments(self):

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

        return instruments

    def get_instrument_items(self):

        result = []

        for instrument in self.instruments:

            for policy in instrument.pricing_policies.all():

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

    def process_to_bloomberg_provider(self, items):

        data = {}

        data['date_from'] = str(self.procedure.price_date_from)
        data['date_to'] = str(self.procedure.price_date_to)
        data['items'] = []

        items_with_missing_parameters = []

        for item in items:

            if len(item.parameters):

                item_parameters = item.parameters.copy()
                item_parameters.pop()

                item_obj = {
                    'reference': item.parameters[0],
                    'parameters': item_parameters,
                    'fields': []
                }

                for field in item.scheme_fields:
                    item_obj['fields'].append({
                        'code': field[0],
                        'parameters': [],
                        'values': []
                    })

                data['items'].append(item_obj)

            else:
                items_with_missing_parameters.append(item)

        print('items_with_missing_parameters %s' % len(items_with_missing_parameters))
        # print('data %s' % data)

        self.broker_bloomberg.send_request(self.procedure, data)

