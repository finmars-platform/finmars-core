from datetime import timedelta

from django.db import transaction
from django.db.models import Q

from poms.common import formula
from poms.common.utils import isclose
from poms.currencies.models import Currency, CurrencyHistory
from poms.instruments.models import PricingCondition
from poms.integrations.models import ProviderClass
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.pricing.brokers.broker_bloomberg import BrokerBloomberg
from poms.pricing.models import PricingProcedureInstance, PricingProcedureBloombergCurrencyResult, \
    CurrencyPricingSchemeType, CurrencyHistoryError, PricingProcedureFixerCurrencyResult
from poms.pricing.transport.transport import PricingTransport
from poms.pricing.utils import get_unique_pricing_schemes, group_items_by_provider, get_list_of_dates_between_two_dates, \
    get_is_yesterday, optimize_items, roll_currency_history_for_n_day_forward

import logging

from poms.reports.builders.balance_item import Report, ReportItem
from poms.reports.builders.balance_pl import ReportBuilder

_l = logging.getLogger('poms.pricing')


class CurrencyItem(object):

    def __init__(self, currency, policy, pricing_scheme):
        self.currency = currency
        self.policy = policy
        self.pricing_scheme = pricing_scheme

        self.scheme_fields = []
        self.scheme_fields_map = {}
        self.parameters = []

        self.fill_parameters()
        self.fill_scheme_fields()

    def fill_parameters(self):

        if self.pricing_scheme.type.input_type == CurrencyPricingSchemeType.NONE:
            pass  # do nothing

        if self.pricing_scheme.type.input_type == CurrencyPricingSchemeType.SINGLE_PARAMETER:

            if self.policy.default_value:
                self.parameters.append(self.policy.default_value)
            else:

                result = None

                if self.policy.attribute_key == 'reference_for_pricing':
                    result = self.currency.reference_for_pricing   ## TODO check if needed for currency
                else:

                    try:

                        attribute = GenericAttribute.objects.get(object_id=self.currency.id,
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

        if self.pricing_scheme.type.input_type == CurrencyPricingSchemeType.MULTIPLE_PARAMETERS:
            pass  # TODO implement multiparameter case

    def fill_scheme_fields(self):

        parameters = self.pricing_scheme.get_parameters()

        if self.pricing_scheme.type.id == 5:

            # _l.info('parameters.fx_rate %s' % parameters.fx_rate)

            self.scheme_fields_map = {}

            if parameters.fx_rate:
                self.scheme_fields.append([parameters.fx_rate])
                self.scheme_fields_map['fx_rate'] = parameters.fx_rate

            # _l.info('self.scheme_fields_map %s' % self.scheme_fields_map)


class PricingCurrencyHandler(object):

    def __init__(self, procedure=None, parent_procedure=None, master_user=None, report=None):

        self.master_user = master_user
        self.procedure = procedure
        self.parent_procedure = parent_procedure

        self.currencies = []

        self.currencies_pricing_schemes = []

        self.currency_items = []

        self.currency_items_grouped = {}

        # self.broker_bloomberg = BrokerBloomberg()
        self.transport = PricingTransport()

        self.report = report

    def process(self):

        _l.info("Pricing Currency Handler: Process")

        self.currencies = self.get_currencies()

        try:
            _l.info('currencies len %s ' % len(self.currencies))
        except Exception as e:
            _l.info(e)

        self.currencies_pricing_schemes = get_unique_pricing_schemes(self.currencies)

        _l.info('currencies_pricing_schemes len %s' % len(self.currencies_pricing_schemes))

        self.currency_items = self.get_currency_items()

        _l.info('currency_items len %s' % len(self.currency_items))

        self.currency_items_grouped = group_items_by_provider(items=self.currency_items,
                                                                   groups=self.currencies_pricing_schemes)

        _l.info('currency_items_grouped len %s' % len(self.currency_items_grouped))

        self.print_grouped_currencies()

        for provider_id, items in self.currency_items_grouped.items():

            if len(items):

                # DEPRECATED
                # if provider_id == 2:
                #     self.process_to_manual_pricing(items)

                if provider_id == 3:
                    self.process_to_single_parameter_formula(items)

                if provider_id == 4:
                    self.process_to_multiple_parameter_formula(items)

                if provider_id == 5:
                    self.process_to_bloomberg_provider(items)

                if provider_id == 7:
                    self.process_to_fixer_provider(items)

    def get_currencies(self):

        currencies = []

        currencies = Currency.objects.filter(
            master_user=self.procedure.master_user,
            is_deleted=False
        ).exclude(user_code='-')

        # instruments = instruments.filter(
        #     pricing_condition__in=[PricingCondition.RUN_VALUATION_ALWAYS, PricingCondition.RUN_VALUATION_IF_NON_ZERO])

        currencies_opened = set()
        currencies_always = set()

        for i in currencies:

            if i.pricing_condition_id in [PricingCondition.RUN_VALUATION_ALWAYS, PricingCondition.RUN_VALUATION_IF_NON_ZERO]:
                currencies_always.add(i.id)

        # if self.procedure.price_balance_date:
        #
        #     owner_or_admin = self.procedure.master_user.members.filter(Q(is_owner=True) | Q(is_admin=True)).first()
        #
        #     report = Report(master_user=self.procedure.master_user, member=owner_or_admin,
        #                     report_date=self.procedure.price_balance_date)
        #
        #     builder = ReportBuilder(instance=report)
        #
        #     builder.build_position_only()
        #
        #     for i in report.items:
        #         if i.type == ReportItem.TYPE_CURRENCY and not isclose(i.pos_size, 0.0):
        #             if i.instr:
        #                 currencies_opened.add(i.instr.id)

        if self.report:

            for i in self.report.items:
                if i.type == ReportItem.TYPE_CURRENCY and not isclose(i.pos_size, 0.0):
                    if i.instr:
                        currencies_opened.add(i.instr.id)

        currencies = currencies.filter(pk__in=(currencies_always | currencies_opened))

        # _l.info("After condition filter %s" % len(currencies))

        return currencies

    def get_currency_items(self):

        result = []

        for currency in self.currencies:

            for policy in currency.pricing_policies.all():

                if policy.pricing_scheme:

                    item = CurrencyItem(currency, policy, policy.pricing_scheme)

                    result.append(item)

        return result

    def process_to_single_parameter_formula(self, items):

        _l.info("Pricing Currency Handler - Single Parameter Formula: len %s" % len(items))

        dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                    date_to=self.procedure.price_date_to)

        procedure_instance = PricingProcedureInstance(pricing_procedure=self.procedure,
                                                      parent_procedure_instance=self.parent_procedure,
                                                      master_user=self.master_user,
                                                      status=PricingProcedureInstance.STATUS_PENDING,
                                                      action='single_parameter_formula_get_currency_prices',
                                                      provider='finmars')
        procedure_instance.save()

        _l.info('process_to_single_parameter_formula dates %s' % dates)

        for item in items:

            last_price = None

            for date in dates:

                scheme_parameters = item.pricing_scheme.get_parameters()

                _l.info('process_to_single_parameter_formula scheme_parameters  %s ' % scheme_parameters)

                if scheme_parameters:

                    safe_currency = {
                        'id': item.currency.id,
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

                                attribute = GenericAttribute.objects.get(object_id=item.currency.id, attribute_type__user_code=user_code)

                                if scheme_parameters.value_type == 10:

                                    parameter = attribute.value_string

                                if scheme_parameters.value_type == 20:

                                    parameter = attribute.value_float

                                if scheme_parameters.value_type == 40:

                                    parameter = attribute.value_date

                            else:

                                parameter = getattr(item.currency, item.policy.attribute_key, None)

                    except Exception as e:

                        _l.info("Cant find parameter value. Error: %s" % e)

                        parameter = None

                    values = {
                        'd': date,
                        'currency': safe_currency,
                        'parameter': parameter
                    }

                    has_error = False
                    error = CurrencyHistoryError(
                        master_user=self.master_user,
                        procedure_instance=procedure_instance,
                        currency=item.currency,
                        pricing_scheme=item.pricing_scheme,
                        pricing_policy=item.policy.pricing_policy,
                        date=date,
                    )

                    expr = scheme_parameters.expr
                    error_text_expr = scheme_parameters.error_text_expr

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

                    can_write = True

                    try:

                        price = CurrencyHistory.objects.get(
                            currency=item.currency,
                            pricing_policy=item.policy.pricing_policy,
                            date=date
                        )

                        if not self.procedure.price_override_existed:
                            can_write = False
                            _l.info('Skip %s' % price)
                        else:
                            _l.info('Overwrite existing %s' % price)

                    except CurrencyHistory.DoesNotExist:

                        price = CurrencyHistory(
                            currency=item.currency,
                            pricing_policy=item.policy.pricing_policy,
                            date=date
                        )

                    if can_write:

                        if fx_rate:
                            price.fx_rate = fx_rate

                        price.save()

                        if has_error:
                            error.save()

                    else:

                        error.error_text = "Prices already exists. Fx rate: " + str(fx_rate) + "."

                        error.status = CurrencyHistoryError.STATUS_SKIP
                        error.save()

                    last_price = price

            if last_price:
                roll_currency_history_for_n_day_forward(item, self.procedure, last_price, self.master_user, procedure_instance)

        procedure_instance.status = PricingProcedureInstance.STATUS_DONE

        procedure_instance.save()

    def process_to_multiple_parameter_formula(self, items):

        _l.info("Pricing Currency Handler - Multiple Parameter Formula: len %s" % len(items))

        dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                    date_to=self.procedure.price_date_to)

        procedure_instance = PricingProcedureInstance(pricing_procedure=self.procedure,
                                                      parent_procedure_instance=self.parent_procedure,
                                                      master_user=self.master_user,
                                                      status=PricingProcedureInstance.STATUS_PENDING,
                                                      action='multiple_parameter_formula_get_currency_prices',
                                                      provider='finmars')
        procedure_instance.save()

        for item in items:

            last_price = None

            for date in dates:

                scheme_parameters = item.pricing_scheme.get_parameters()

                if scheme_parameters:

                    safe_currency = {
                        'id': item.currency.id,
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

                                attribute = GenericAttribute.objects.get(object_id=item.currency.id, attribute_type__user_code=user_code)

                                if scheme_parameters.value_type == 10:

                                    parameter = attribute.value_string

                                if scheme_parameters.value_type == 20:

                                    parameter = attribute.value_float

                                if scheme_parameters.value_type == 40:

                                    parameter = attribute.value_date

                            else:

                                parameter = getattr(item.currency, item.policy.attribute_key, None)

                    except Exception as e:

                        _l.info("Cant find parameter value. Error: %s" % e)

                        parameter = None

                    values = {
                        'd': date,
                        'currency': safe_currency,
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

                                        attribute = GenericAttribute.objects.get(object_id=item.currency.id, attribute_type__user_code=user_code)

                                        if float(parameter['value_type']) == 10:

                                            val = attribute.value_string

                                        if float(parameter['value_type']) == 20:

                                            val = attribute.value_float

                                        if float(parameter['value_type']) == 40:

                                            val = attribute.value_date

                                    else:

                                        val = item.currency[parameter['attribute_key']]


                                values['parameter' + str(parameter['index'])] = val

                    has_error = False
                    error = CurrencyHistoryError(
                        master_user=self.master_user,
                        procedure_instance=procedure_instance,
                        currency=item.currency,
                        pricing_scheme=item.pricing_scheme,
                        pricing_policy=item.policy.pricing_policy,
                        date=date,
                    )

                    expr = scheme_parameters.expr
                    error_text_expr = scheme_parameters.error_text_expr

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

                    can_write = True

                    try:

                        price = CurrencyHistory.objects.get(
                            currency=item.currency,
                            pricing_policy=item.policy.pricing_policy,
                            date=date
                        )

                        if not self.procedure.price_override_existed:
                            can_write = False
                            _l.info('Skip %s' % price)
                        else:
                            _l.info('Overwrite existing %s' % price)

                    except CurrencyHistory.DoesNotExist:

                        price = CurrencyHistory(
                            currency=item.currency,
                            pricing_policy=item.policy.pricing_policy,
                            date=date
                        )

                        _l.info('Create new %s' % price)

                    if can_write:

                        if fx_rate:
                            price.fx_rate = fx_rate

                        price.save()

                        if has_error:
                            error.save()
                    else:
                        error.error_text = "Prices already exists. Fx rate: " + str(fx_rate) + "."

                        error.status = CurrencyHistoryError.STATUS_SKIP
                        error.save()

                    last_price = price

            if last_price:
                roll_currency_history_for_n_day_forward(item, self.procedure, last_price, self.master_user, procedure_instance)

        procedure_instance.status = PricingProcedureInstance.STATUS_DONE

        procedure_instance.save()

    def process_to_bloomberg_provider(self, items):

        _l.info("Pricing Currency Handler - Bloomberg Provider: len %s" % len(items))

        with transaction.atomic():

            procedure_instance = PricingProcedureInstance(pricing_procedure=self.procedure,
                                                          parent_procedure_instance=self.parent_procedure,
                                                          master_user=self.master_user,
                                                          status=PricingProcedureInstance.STATUS_PENDING,
                                                          action='bloomberg_get_currency_prices',
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

                for date in dates:

                    with transaction.atomic():
                        try:

                            record = PricingProcedureBloombergCurrencyResult(master_user=self.master_user,
                                                                     procedure=procedure_instance,
                                                                     currency=item.currency,
                                                                     currency_parameters=str(item_parameters),
                                                                     pricing_policy=item.policy.pricing_policy,
                                                                     pricing_scheme=item.pricing_scheme,
                                                                     reference=item.parameters[0],
                                                                     date=date)

                            if 'fx_rate' in item.scheme_fields_map:
                                record.fx_rate_parameters = item.scheme_fields_map[
                                    'fx_rate']

                            record.save()

                        except Exception as e:
                            _l.info("Cant create Result Record %s" % e)

                item_obj = {
                    'reference': item.parameters[0],
                    'parameters': item_parameters,
                    'fields': []
                }

                if 'fx_rate' in item.scheme_fields_map:
                    item_obj['fields'].append({
                        'code': item.scheme_fields_map['fx_rate'],
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

    def process_to_fixer_provider(self, items):

        _l.info("Pricing Currency Handler - Fixer Provider: len %s" % len(items))

        with transaction.atomic():

            procedure_instance = PricingProcedureInstance(pricing_procedure=self.procedure,
                                                          parent_procedure_instance=self.parent_procedure,
                                                          master_user=self.master_user,
                                                          status=PricingProcedureInstance.STATUS_PENDING,
                                                          action='fixer_get_currency_prices',
                                                          provider='fixer')
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

                            record = PricingProcedureFixerCurrencyResult(master_user=self.master_user,
                                                                             procedure=procedure_instance,
                                                                             currency=item.currency,
                                                                             currency_parameters=str(item_parameters),
                                                                             pricing_policy=item.policy.pricing_policy,
                                                                             pricing_scheme=item.pricing_scheme,
                                                                             reference=item.parameters[0],
                                                                             date=date)

                            record.save()

                        except Exception as e:
                            _l.info("Cant create Result Record %s" % e)

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

    def print_grouped_currencies(self):

        names = {
            1: 'Skip',
            2: 'Manual Pricing',  # DEPRECATED
            3: 'Single Parameter Formula',
            4: 'Multiple Parameter Formula',
            5: 'Bloomberg',
            6: 'Wtrade', # DEPRECATED
            7: 'Fixer'

        }

        for provider_id, items in self.currency_items_grouped.items():
            _l.info("Pricing Currency Handler - Provider %s: len: %s" % (names[provider_id], len(items)))
