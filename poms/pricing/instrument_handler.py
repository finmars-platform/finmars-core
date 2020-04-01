import json
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
    PricingProcedureBloombergInstrumentResult, PricingProcedureWtradeInstrumentResult, PriceHistoryError
from poms.pricing.transport.transport import PricingTransport
from poms.pricing.utils import get_unique_pricing_schemes, get_list_of_dates_between_two_dates, group_items_by_provider, \
    get_is_yesterday, optimize_items, roll_price_history_for_n_day_forward
from poms.reports.builders.balance_item import Report, ReportItem
from poms.reports.builders.balance_pl import ReportBuilder


import logging

_l = logging.getLogger('poms.pricing')


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

            if parameters.accrual_historical:
                self.scheme_fields.append([parameters.accrual_historical])
                self.scheme_fields_map['accrual_historical'] = parameters.accrual_historical

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

            if parameters.accrual_yesterday:
                self.scheme_fields.append([parameters.accrual_yesterday])
                self.scheme_fields_map['accrual_yesterday'] = parameters.accrual_yesterday


class PricingInstrumentHandler(object):

    def __init__(self, procedure=None, parent_procedure=None, master_user=None):

        self.master_user = master_user
        self.procedure = procedure
        self.parent_procedure = parent_procedure

        self.instruments = []

        self.instrument_pricing_schemes = []

        self.instrument_items = []

        self.instrument_items_grouped = {}

        # self.broker_bloomberg = BrokerBloomberg()
        self.transport = PricingTransport()

    def process(self):

        _l.info("Pricing Instrument Handler: Process")

        self.instruments = self.get_instruments()

        self.instrument_pricing_schemes = get_unique_pricing_schemes(self.instruments)

        _l.info('instrument_pricing_schemes len %s' % len(self.instrument_pricing_schemes))

        self.instrument_items = self.get_instrument_items()

        _l.info('instrument_items len %s' % len(self.instrument_items))

        self.instrument_items_grouped = group_items_by_provider(items=self.instrument_items,
                                                                groups=self.instrument_pricing_schemes)

        _l.info('instrument_items_grouped len %s' % len(self.instrument_items_grouped))

        self.print_grouped_instruments()

        for provider_id, items in self.instrument_items_grouped.items():

            if provider_id == 3:
                self.process_to_single_parameter_formula(items)

            if provider_id == 4:
                self.process_to_multiple_parameter_formula(items)

            if provider_id == 5:
                self.process_to_bloomberg_provider(items)

            if provider_id == 6:
                self.process_to_wtrade_provider(items)

    def get_instruments(self):

        result = []

        instruments = Instrument.objects.filter(
            master_user=self.procedure.master_user,
            is_deleted=False
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

        # if self.procedure.instrument_filters:
        #     for instrument in instruments:
        #
        #         if instrument.user_code in self.procedure.instrument_filters:
        #             result.append(instrument)
        # else:
        #     result = instruments

        if self.procedure.instrument_type_filters:

            user_codes = self.procedure.instrument_type_filters.split(",")

            print("Filter by Instrument Types %s " % user_codes)

            print("instruments before filter %s " % len(instruments))
            instruments = instruments.filter(instrument_type__user_code__in=user_codes)
            print("instruments after filter %s " % len(instruments))

        result = instruments

        return result

    def get_instrument_items(self):

        result = []

        for instrument in self.instruments:

            for policy in instrument.pricing_policies.all():

                # Filter By Procedure Filter Settings
                # TODO refactor soon

                if policy.pricing_scheme:

                    if self.procedure.pricing_policy_filters:

                        if policy.pricing_policy.user_code in self.procedure.pricing_policy_filters:
                            item = InstrumentItem(instrument, policy, policy.pricing_scheme)

                            result.append(item)

                    else:

                        item = InstrumentItem(instrument, policy, policy.pricing_scheme)

                        result.append(item)

        return result

    def process_to_single_parameter_formula(self, items):

        _l.info("Pricing Instrument Handler - Single parameters Formula: len %s" % len(items))

        dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                    date_to=self.procedure.price_date_to)

        procedure_instance = PricingProcedureInstance(pricing_procedure=self.procedure,
                                                      parent_procedure_instance=self.parent_procedure,
                                                      master_user=self.master_user,
                                                      status=PricingProcedureInstance.STATUS_PENDING,
                                                      action='single_parameter_formula_get_instrument_prices',
                                                      provider='finmars')
        procedure_instance.save()

        for item in items:

            last_price = None

            for date in dates:

                scheme_parameters = item.pricing_scheme.get_parameters()

                if scheme_parameters:

                    safe_instrument = {
                        'id': item.instrument.id,
                    }

                    parameter = None

                    try:

                        if item.policy.default_value:

                            if scheme_parameters.value_type == 10:

                                parameter = str(item.policy.default_value)

                            elif scheme_parameters.value_type == 20:

                                parameter = float(item.policy.default_value)

                            elif scheme_parameters.value_type == 40:

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

                    except Exception as e:

                        _l.info("Cant find parameter value. Error: %s" % e)

                        parameter = None

                    values = {
                        'd': date,
                        'instrument': safe_instrument,
                        'parameter': parameter
                    }

                    expr = scheme_parameters.expr
                    accrual_expr = scheme_parameters.accrual_expr
                    pricing_error_text_expr = scheme_parameters.pricing_error_text_expr
                    accrual_error_text_expr = scheme_parameters.accrual_error_text_expr

                    _l.info('values %s' % values)
                    _l.info('expr %s' % expr)

                    has_error = False
                    error = PriceHistoryError(
                        master_user=self.master_user,
                        procedure_instance=procedure_instance,
                        instrument=item.instrument,
                        pricing_scheme=item.pricing_scheme,
                        pricing_policy=item.policy.pricing_policy,
                        date=date,
                    )

                    principal_price = None
                    accrued_price = None

                    try:
                        principal_price = formula.safe_eval(expr, names=values)
                    except formula.InvalidExpression:

                        has_error = True

                        try:

                            _l.info('pricing_error_text_expr %s' % pricing_error_text_expr)

                            error.price_error_text = formula.safe_eval(pricing_error_text_expr, names=values)

                        except formula.InvalidExpression:
                            error.price_error_text = 'Invalid Error Text Expression'

                    _l.info("Error here? %s" % has_error)

                    _l.info('principal_price %s' % principal_price)

                    if scheme_parameters.accrual_calculation_method == 2:   # ACCRUAL_PER_SCHEDULE

                        try:
                            accrued_price = item.instrument.get_accrued_price(date)
                        except Exception:
                            has_error = True

                            try:

                                _l.info('accrual_error_text_expr %s' % accrual_error_text_expr)

                                error.accrual_error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                            except formula.InvalidExpression:
                                error.accrual_error_text = 'Invalid Error Text Expression'

                    if scheme_parameters.accrual_calculation_method == 3:   # ACCRUAL_PER_FORMULA

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
                            instrument=item.instrument,
                            pricing_policy=item.policy.pricing_policy,
                            date=date
                        )

                        if not self.procedure.price_override_existed:
                            can_write = False
                            _l.info('Skip %s' % price)
                        else:
                            _l.info('Overwrite existing %s' % price)

                    except PriceHistory.DoesNotExist:

                        price = PriceHistory(
                            instrument=item.instrument,
                            pricing_policy=item.policy.pricing_policy,
                            date=date
                        )

                        _l.info('Create new %s' % price)

                    if can_write:

                        price.principal_price = 0
                        price.accrued_price = 0

                        if principal_price:
                            price.principal_price = principal_price
                            error.principal_price = principal_price

                        if accrued_price:
                            price.accrued_price = accrued_price
                            error.accrued_price = accrued_price

                        price.save()

                        if has_error:
                            error.save()
                    else:

                        error.error_text =  "Prices already exists. Principal Price: " + principal_price +"; Accrued: "+ accrued_price +"."

                        error.status = PriceHistoryError.STATUS_SKIP
                        error.save()

                    last_price = price

            roll_price_history_for_n_day_forward(self.procedure, last_price)

        procedure_instance.status = PricingProcedureInstance.STATUS_DONE

        procedure_instance.save()

    def process_to_multiple_parameter_formula(self, items):

        _l.info("Pricing Instrument Handler - Multiple parameters Formula: len %s" % len(items))

        dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                    date_to=self.procedure.price_date_to)

        procedure_instance = PricingProcedureInstance(pricing_procedure=self.procedure,
                                                      parent_procedure_instance=self.parent_procedure,
                                                      master_user=self.master_user,
                                                      status=PricingProcedureInstance.STATUS_PENDING,
                                                      action='multiple_parameter_formula_get_instrument_prices',
                                                      provider='finmars')
        procedure_instance.save()

        for item in items:

            last_price = None

            for date in dates:

                scheme_parameters = item.pricing_scheme.get_parameters()

                if scheme_parameters:

                    safe_instrument = {
                        'id': item.instrument.id,
                    }

                    parameter = None

                    try:

                        if item.policy.default_value:

                            if scheme_parameters.value_type == 10:

                                parameter = str(item.policy.default_value)

                            elif scheme_parameters.value_type == 20:

                                parameter = float(item.policy.default_value)

                            elif scheme_parameters.value_type == 40:

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

                    except Exception as e:

                        _l.info("Cant find parameter value. Error: %s" % e)

                        parameter = None

                    values = {
                        'd': date,
                        'instrument': safe_instrument,
                        'parameter': parameter
                    }

                    if item.policy.data:

                        if 'parameters' in item.policy.data:

                            for parameter in item.policy.data['parameters']:

                                _l.info('parameter %s ' % parameter)

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

                                        val = getattr(item.instrument, parameter['attribute_key'])

                                values['parameter' + str(parameter['index'])] = val

                    expr = scheme_parameters.expr
                    accrual_expr = scheme_parameters.accrual_expr
                    pricing_error_text_expr = scheme_parameters.pricing_error_text_expr
                    accrual_error_text_expr = scheme_parameters.accrual_error_text_expr

                    _l.info('values %s' % values)
                    _l.info('expr %s' % expr)

                    has_error = False
                    error = PriceHistoryError(
                        master_user=self.master_user,
                        procedure_instance=procedure_instance,
                        instrument=item.instrument,
                        pricing_scheme=item.pricing_scheme,
                        pricing_policy=item.policy.pricing_policy,
                        date=date,
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

                    if scheme_parameters.accrual_calculation_method == 2:   # ACCRUAL_PER_SCHEDULE

                        try:
                            accrued_price = item.instrument.get_accrued_price(date)
                        except Exception:
                            has_error = True

                            try:

                                _l.info('accrual_error_text_expr %s' % accrual_error_text_expr)

                                error.accrual_error_text = formula.safe_eval(accrual_error_text_expr, names=values)

                            except formula.InvalidExpression:
                                error.accrual_error_text = 'Invalid Error Text Expression'

                    if scheme_parameters.accrual_calculation_method == 3:   # ACCRUAL_PER_FORMULA

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
                            instrument=item.instrument,
                            pricing_policy=item.policy.pricing_policy,
                            date=date
                        )

                        if not self.procedure.price_override_existed:
                            can_write = False
                            _l.info('Skip %s' % price)
                        else:
                            _l.info('Overwrite existing %s' % price)

                    except PriceHistory.DoesNotExist:

                        price = PriceHistory(
                            instrument=item.instrument,
                            pricing_policy=item.policy.pricing_policy,
                            date=date
                        )

                        _l.info('Create new %s' % price)

                    if can_write:

                        price.principal_price = 0
                        price.accrued_price = 0

                        if principal_price:
                            price.principal_price = principal_price
                            error.principal_price = principal_price

                        if accrued_price:
                            price.accrued_price = accrued_price
                            error.accrued_price = accrued_price

                        price.save()

                        if has_error:
                            error.save()

                    else:

                        error.error_text =  "Prices already exists. Principal Price: " + principal_price +"; Accrued: "+ accrued_price +"."

                        error.status = PriceHistoryError.STATUS_SKIP
                        error.save()

                    last_price = price

            roll_price_history_for_n_day_forward(self.procedure, last_price)

        procedure_instance.status = PricingProcedureInstance.STATUS_DONE

        procedure_instance.save()

    def process_to_bloomberg_provider(self, items):

        _l.info("Pricing Instrument Handler - Bloomberg Provider: len %s" % len(items))

        with transaction.atomic():

            procedure_instance = PricingProcedureInstance(pricing_procedure=self.procedure,
                                                          parent_procedure_instance=self.parent_procedure,
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

        _l.info('is_yesterday %s' % is_yesterday)
        _l.info('procedure id %s' % body['procedure'])

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
                                                                                   pricing_scheme=item.pricing_scheme,
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

                                if 'accrual_yesterday' in item.scheme_fields_map:
                                    record.accrual_parameters = item.scheme_fields_map[
                                        'accrual_yesterday']

                                record.save()

                            except Exception as e:
                                _l.info("Cant create Result Record %s" % e)
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

                    if 'accrual_yesterday' in item.scheme_fields_map:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['accrual_yesterday'],
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
                                                                                   pricing_scheme=item.pricing_scheme,
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

                                if 'accrual_historical' in item.scheme_fields_map:
                                    record.accrual_parameters = item.scheme_fields_map[
                                        'accrual_historical']

                                record.save()

                            except Exception as e:
                                _l.info("Cant create Result Record %s" % e)

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

                    if 'accrual_historical' in item.scheme_fields_map:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['accrual_historical'],
                            'parameters': [],
                            'values': []
                        })

                    full_items.append(item_obj)

            else:
                items_with_missing_parameters.append(item)

        _l.info('full_items len: %s' % len(full_items))

        optimized_items = optimize_items(full_items)

        _l.info('optimized_items len: %s' % len(optimized_items))

        body['data']['items'] = optimized_items

        _l.info('items_with_missing_parameters %s' % len(items_with_missing_parameters))
        # _l.info('data %s' % data)

        _l.info('self.procedure %s' % self.procedure.id)
        _l.info('send request %s' % body)

        self.transport.send_request(body)

    def process_to_wtrade_provider(self, items):

        _l.info("Pricing Instrument Handler - Wtrade Provider: len %s" % len(items))

        procedure_instance = PricingProcedureInstance(pricing_procedure=self.procedure,
                                                      parent_procedure_instance=self.parent_procedure,
                                                      master_user=self.master_user,
                                                      status=PricingProcedureInstance.STATUS_PENDING,
                                                      action='wtrade_get_instrument_prices',
                                                      provider='wtrade')
        procedure_instance.save()

        body = {}
        body['action'] = procedure_instance.action
        body['procedure'] = procedure_instance.id
        body['provider'] = procedure_instance.provider

        body['user'] = {
            'token': self.master_user.id
        }

        body['data'] = {}

        body['data']['date_from'] = str(self.procedure.price_date_from)
        body['data']['date_to'] = str(self.procedure.price_date_to)
        body['data']['items'] = []

        items_with_missing_parameters = []

        dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                    date_to=self.procedure.price_date_to)

        _l.info('procedure id %s' % body['procedure'])

        full_items = []

        for item in items:

            if len(item.parameters):

                item_parameters = item.parameters.copy()
                item_parameters.pop()

                for date in dates:

                    with transaction.atomic():
                        try:
                            record = PricingProcedureWtradeInstrumentResult(master_user=self.master_user,
                                                                            procedure=procedure_instance,
                                                                            instrument=item.instrument,
                                                                            instrument_parameters=str(
                                                                                item_parameters),
                                                                            pricing_policy=item.policy.pricing_policy,
                                                                            pricing_scheme=item.pricing_scheme,
                                                                            reference=item.parameters[0],
                                                                            date=date)

                            record.save()

                        except Exception as e:
                            _l.info("Cant create Result Record %s" % e)
                            pass

                item_obj = {
                    'reference': item.parameters[0],
                    'parameters': item_parameters,
                    'fields': []
                }

                item_obj['fields'].append({
                    'code': 'close',
                    'parameters': [],
                    'values': []
                })

                item_obj['fields'].append({
                    'code': 'open',
                    'parameters': [],
                    'values': []
                })

                item_obj['fields'].append({
                    'code': 'high',
                    'parameters': [],
                    'values': []
                })

                item_obj['fields'].append({
                    'code': 'low',
                    'parameters': [],
                    'values': []
                })

                item_obj['fields'].append({
                    'code': 'volume',
                    'parameters': [],
                    'values': []
                })

                full_items.append(item_obj)

            else:
                items_with_missing_parameters.append(item)

        _l.info('full_items len: %s' % len(full_items))

        optimized_items = optimize_items(full_items)

        _l.info('optimized_items len: %s' % len(optimized_items))

        body['data']['items'] = optimized_items

        _l.info('items_with_missing_parameters %s' % len(items_with_missing_parameters))
        # _l.info('data %s' % data)

        _l.info('self.procedure %s' % self.procedure.id)
        _l.info('send request %s' % body)

        self.transport.send_request(body)

    def print_grouped_instruments(self):

            names = {
                1: 'Skip',
                2: 'Manual Pricing',  # DEPRECATED
                3: 'Single Parameter Formula',
                4: 'Multiple Parameter Formula',
                5: 'Bloomberg',
                6: 'Wtrade'

            }

            for provider_id, items in self.instrument_items_grouped.items():
                _l.info("Pricing Instrument Handler - Provider %s: len: %s" % (names[provider_id], len(items)))
