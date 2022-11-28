import logging
import time

from django.db import transaction
from django.db.models import Q

from poms.common import formula
from poms.common.utils import date_now
from poms.currencies.models import Currency, CurrencyHistory
from poms.instruments.models import PricingCondition
from poms.integrations.models import ProviderClass, BloombergDataProviderCredential
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.pricing.models import PricingProcedureInstance, PricingProcedureBloombergCurrencyResult, \
    CurrencyPricingSchemeType, CurrencyHistoryError, PricingProcedureFixerCurrencyResult, \
    PricingProcedureCbondsCurrencyResult
from poms.pricing.transport.transport import PricingTransport
from poms.pricing.utils import get_unique_pricing_schemes, get_list_of_dates_between_two_dates, \
    get_is_yesterday, optimize_items, roll_currency_history_for_n_day_forward, get_empty_values_for_dates, \
    group_currency_items_by_provider
from poms.procedures.models import PricingProcedure, BaseProcedureInstance
from poms.system_messages.handlers import send_system_message
from poms.transactions.models import Transaction
from poms.users.models import Member
from poms_app import settings

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
                    result = self.currency.reference_for_pricing  ## TODO check if needed for currency
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

            # _l.debug('parameters.fx_rate %s' % parameters.fx_rate)

            self.scheme_fields_map = {}

            if parameters.fx_rate:
                self.scheme_fields.append([parameters.fx_rate])
                self.scheme_fields_map['fx_rate'] = parameters.fx_rate

            # _l.debug('self.scheme_fields_map %s' % self.scheme_fields_map)


class PricingCurrencyHandler(object):

    def __init__(self, procedure=None, parent_procedure=None, master_user=None, member=None, schedule_instance=None):

        self.master_user = master_user
        self.procedure = procedure
        self.parent_procedure = parent_procedure

        self.member = member

        if not self.member:
            self.member = Member.objects.get(master_user=self.master_user, is_owner=True)

        self.schedule_instance = schedule_instance

        self.currencies = []

        self.currencies_pricing_schemes = []

        self.currency_items = []

        self.currency_items_grouped = {}

        # self.broker_bloomberg = BrokerBloomberg()
        self.transport = PricingTransport()

    def process(self):

        _l.debug("Pricing Currency Handler: Process")

        self.currencies = self.get_currencies()

        try:
            _l.debug('currencies len %s ' % len(self.currencies))
        except Exception as e:
            _l.debug(e)

        self.currencies_pricing_schemes = get_unique_pricing_schemes(self.currencies)

        _l.debug('currencies_pricing_schemes len %s' % len(self.currencies_pricing_schemes))

        self.currency_items = self.get_currency_items()

        _l.debug('currency_items len %s' % len(self.currency_items))

        self.currency_items_grouped = group_currency_items_by_provider(items=self.currency_items,
                                                                       groups=self.currencies_pricing_schemes)

        _l.debug('currency_items_grouped len %s' % len(self.currency_items_grouped))

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

                if provider_id == 9:
                    self.process_to_fx_cbonds_provider(items)

    def get_currencies(self):

        currencies = []

        currencies = Currency.objects.filter(
            master_user=self.procedure.master_user,
            is_deleted=False
        ).exclude(user_code='-')

        currencies_opened = set()
        currencies_always = set()

        if self.procedure.type == PricingProcedure.CREATED_BY_USER:

            active_pricing_conditions = []

            if self.procedure.currency_pricing_condition_filters:
                active_pricing_conditions = list(map(int, self.procedure.currency_pricing_condition_filters.split(",")))

            _l.debug('active_pricing_conditions %s' % active_pricing_conditions)

            # Add RUN_VALUATION_ALWAYS currencies only if pricing condition is enabled
            if PricingCondition.RUN_VALUATION_ALWAYS in active_pricing_conditions:

                for i in currencies:

                    if i.pricing_condition_id in [PricingCondition.RUN_VALUATION_ALWAYS]:
                        currencies_always.add(i.id)

            # Add RUN_VALUATION_IF_NON_ZERO currencies only if pricing condition is enabled
            if PricingCondition.RUN_VALUATION_IF_NON_ZERO in active_pricing_conditions:

                processing_st = time.perf_counter()

                base_transactions = Transaction.objects.filter(master_user=self.procedure.master_user)

                base_transactions = base_transactions.filter(Q(accounting_date__lte=self.procedure.price_date_to) | Q(
                    cash_date__lte=self.procedure.price_date_to))

                if self.procedure.portfolio_filters:
                    portfolio_user_codes = self.procedure.portfolio_filters.split(",")

                    base_transactions = base_transactions.filter(portfolio__user_code__in=portfolio_user_codes)

                _l.debug('< get_currencies base transactions len %s', len(base_transactions))
                _l.debug('< get_currencies base transactions done in %s', (time.perf_counter() - processing_st))

                if len(list(base_transactions)):

                    for base_transaction in base_transactions:

                        if base_transaction.transaction_currency_id:

                            if base_transaction.transaction_currency.pricing_condition_id in [
                                PricingCondition.RUN_VALUATION_IF_NON_ZERO]:
                                currencies_opened.add(base_transaction.transaction_currency_id)

                        if base_transaction.settlement_currency_id:

                            if base_transaction.settlement_currency.pricing_condition_id in [
                                PricingCondition.RUN_VALUATION_IF_NON_ZERO]:
                                currencies_opened.add(base_transaction.settlement_currency_id)

            currencies = currencies.filter(pk__in=(currencies_always | currencies_opened))

        if self.procedure.type == PricingProcedure.CREATED_BY_CURRENCY:

            if self.procedure.currency_filters:
                user_codes = self.procedure.currency_filters.split(",")

                _l.debug("Filter by Currencies %s " % user_codes)

                _l.debug("currencies before filter %s " % len(currencies))
                currencies = currencies.filter(user_code__in=user_codes)
                _l.debug("currencies after filter %s " % len(currencies))

        return currencies

    def get_currency_items(self):

        result = []

        for currency in self.currencies:

            for policy in currency.pricing_policies.all():

                if policy.pricing_scheme:

                    allowed_policy = True  # Policy that will pass all filters

                    if self.procedure.currency_pricing_scheme_filters:
                        if policy.pricing_scheme.user_code not in self.procedure.currency_pricing_scheme_filters:
                            allowed_policy = False

                    if self.procedure.pricing_policy_filters:
                        if policy.pricing_policy.user_code not in self.procedure.pricing_policy_filters:
                            allowed_policy = False

                    if allowed_policy:
                        item = CurrencyItem(currency, policy, policy.pricing_scheme)

                        result.append(item)

        return result

    def process_to_single_parameter_formula(self, items):

        _l.debug("Pricing Currency Handler - Single Parameter Formula: len %s" % len(items))

        procedure_instance = PricingProcedureInstance.objects.create(procedure=self.procedure,
                                                                     parent_procedure_instance=self.parent_procedure,
                                                                     master_user=self.master_user,
                                                                     member=self.member,
                                                                     status=PricingProcedureInstance.STATUS_PENDING,
                                                                     action='single_parameter_formula_get_currency_prices',
                                                                     provider='finmars',

                                                                     action_verbose='Get FX Rates from Single Parameter Formula',
                                                                     provider_verbose='Finmars'

                                                                     )

        try:

            dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                        date_to=self.procedure.price_date_to)

            successful_prices_count = 0
            error_prices_count = 0

            if self.member:
                procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_MEMBER
                procedure_instance.member = self.member

            if self.schedule_instance:
                procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_SCHEDULE
                procedure_instance.schedule_instance = self.schedule_instance

            procedure_instance.save()

            _l.debug('process_to_single_parameter_formula dates %s' % dates)

            for item in items:

                last_price = None

                for date in dates:

                    scheme_parameters = item.pricing_scheme.get_parameters()

                    _l.debug('process_to_single_parameter_formula scheme_parameters  %s ' % scheme_parameters)

                    if scheme_parameters:

                        safe_currency = {
                            'id': item.currency.id,
                        }

                        safe_pp = {
                            'id': item.policy.id,
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

                                    attribute = GenericAttribute.objects.get(object_id=item.currency.id,
                                                                             attribute_type__user_code=user_code)

                                    if scheme_parameters.value_type == 10:
                                        parameter = attribute.value_string

                                    if scheme_parameters.value_type == 20:
                                        parameter = attribute.value_float

                                    if scheme_parameters.value_type == 40:
                                        parameter = attribute.value_date

                                else:

                                    parameter = getattr(item.currency, item.policy.attribute_key, None)

                        except Exception as e:

                            _l.debug("Cant find parameter value. Error: %s" % e)

                            parameter = None

                        values = {
                            'context_date': date,
                            'context_currency': safe_currency,
                            'context_pricing_policy': safe_pp,
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
                            created=procedure_instance.created
                        )

                        expr = scheme_parameters.expr
                        error_text_expr = scheme_parameters.error_text_expr

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

                        can_write = True

                        try:

                            price = CurrencyHistory.objects.get(
                                currency=item.currency,
                                pricing_policy=item.policy.pricing_policy,
                                date=date
                            )

                            if not self.procedure.price_overwrite_fx_rates:
                                can_write = False
                                _l.debug('Skip %s' % price)
                            else:
                                _l.debug('Overwrite existing %s' % price)

                        except CurrencyHistory.DoesNotExist:

                            price = CurrencyHistory(
                                currency=item.currency,
                                pricing_policy=item.policy.pricing_policy,
                                date=date
                            )

                        price.procedure_modified_datetime = date_now()

                        price.fx_rate = 0

                        if fx_rate is not None:
                            price.fx_rate = fx_rate

                        if can_write:

                            if has_error or price.fx_rate == 0:
                                # if has_error:

                                error_prices_count = error_prices_count + 1
                                error.status = CurrencyHistoryError.STATUS_ERROR
                                error.save()
                            else:

                                successful_prices_count = successful_prices_count + 1

                                price.save()

                                if price.id:
                                    error.status = CurrencyHistoryError.STATUS_OVERWRITTEN
                                else:
                                    error.status = CurrencyHistoryError.STATUS_SKIP
                                error.save()

                        else:

                            error_prices_count = error_prices_count + 1

                            error.error_text = "Prices already exists. Fx rate: " + str(fx_rate) + "."

                            error.status = CurrencyHistoryError.STATUS_SKIP
                            error.save()

                        last_price = price

                if last_price:
                    successes, errors = roll_currency_history_for_n_day_forward(item, self.procedure, last_price,
                                                                                self.master_user, procedure_instance)
                    successful_prices_count = successful_prices_count + successes
                    error_prices_count = error_prices_count + errors

            procedure_instance.successful_prices_count = successful_prices_count
            procedure_instance.error_prices_count = error_prices_count

            procedure_instance.status = PricingProcedureInstance.STATUS_DONE

            procedure_instance.save()

            if procedure_instance.schedule_instance:
                procedure_instance.schedule_instance.run_next_procedure()

        except Exception as e:
            procedure_instance.error_message = 'Error %s' % e
            procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
            procedure_instance.save()

    def process_to_multiple_parameter_formula(self, items):

        _l.debug("Pricing Currency Handler - Multiple Parameter Formula: len %s" % len(items))

        procedure_instance = PricingProcedureInstance.objects.create(procedure=self.procedure,
                                                                     parent_procedure_instance=self.parent_procedure,
                                                                     master_user=self.master_user,
                                                                     member=self.member,
                                                                     status=PricingProcedureInstance.STATUS_PENDING,
                                                                     action='multiple_parameter_formula_get_currency_prices',
                                                                     provider='finmars',

                                                                     action_verbose='Get FX Rates from Multiple Parameter Formula',
                                                                     provider_verbose='Finmars'
                                                                     )

        try:

            dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                        date_to=self.procedure.price_date_to)

            successful_prices_count = 0
            error_prices_count = 0

            if self.member:
                procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_MEMBER
                procedure_instance.member = self.member

            if self.schedule_instance:
                procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_SCHEDULE
                procedure_instance.schedule_instance = self.schedule_instance

            procedure_instance.save()

            for item in items:

                last_price = None

                for date in dates:

                    scheme_parameters = item.pricing_scheme.get_parameters()

                    if scheme_parameters:

                        safe_currency = {
                            'id': item.currency.id,
                        }

                        safe_pp = {
                            'id': item.policy.id,
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

                                    attribute = GenericAttribute.objects.get(object_id=item.currency.id,
                                                                             attribute_type__user_code=user_code)

                                    if scheme_parameters.value_type == 10:
                                        parameter = attribute.value_string

                                    if scheme_parameters.value_type == 20:
                                        parameter = attribute.value_float

                                    if scheme_parameters.value_type == 40:
                                        parameter = attribute.value_date

                                else:

                                    parameter = getattr(item.currency, item.policy.attribute_key, None)

                        except Exception as e:

                            _l.debug("Cant find parameter value. Error: %s" % e)

                            parameter = None

                        values = {
                            'context_date': date,
                            'context_currency': safe_currency,
                            'context_pricing_policy': safe_pp,
                            'parameter': parameter
                        }

                        if item.policy.data:

                            if 'parameters' in item.policy.data:

                                for parameter in item.policy.data['parameters']:

                                    _l.debug('parameter %s ' % parameter)

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

                                            attribute = GenericAttribute.objects.get(object_id=item.currency.id,
                                                                                     attribute_type__user_code=user_code)

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
                            created=procedure_instance.created
                        )

                        expr = scheme_parameters.expr
                        error_text_expr = scheme_parameters.error_text_expr

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

                        can_write = True

                        try:

                            price = CurrencyHistory.objects.get(
                                currency=item.currency,
                                pricing_policy=item.policy.pricing_policy,
                                date=date
                            )

                            if not self.procedure.price_overwrite_fx_rates:
                                can_write = False
                                _l.debug('Skip %s' % price)
                            else:
                                _l.debug('Overwrite existing %s' % price)

                        except CurrencyHistory.DoesNotExist:

                            price = CurrencyHistory(
                                currency=item.currency,
                                pricing_policy=item.policy.pricing_policy,
                                date=date
                            )

                            _l.debug('Create new %s' % price)

                        price.procedure_modified_datetime = date_now()

                        price.fx_rate = 0

                        if fx_rate is not None:
                            price.fx_rate = fx_rate

                        if can_write:

                            if has_error or price.fx_rate == 0:
                                # if has_error:

                                error_prices_count = error_prices_count + 1
                                error.status = CurrencyHistoryError.STATUS_ERROR
                                error.save()
                            else:

                                successful_prices_count = successful_prices_count + 1

                                price.save()

                                if price.id:
                                    error.status = CurrencyHistoryError.STATUS_OVERWRITTEN
                                else:
                                    error.status = CurrencyHistoryError.STATUS_SKIP
                                error.save()

                        else:

                            error_prices_count = error_prices_count + 1

                            error.error_text = "Prices already exists. Fx rate: " + str(fx_rate) + "."

                            error.status = CurrencyHistoryError.STATUS_SKIP
                            error.save()

                        last_price = price

                if last_price:
                    successes, errors = roll_currency_history_for_n_day_forward(item, self.procedure, last_price,
                                                                                self.master_user, procedure_instance)

                    successful_prices_count = successful_prices_count + successes
                    error_prices_count = error_prices_count + errors

            procedure_instance.successful_prices_count = successful_prices_count
            procedure_instance.error_prices_count = error_prices_count

            procedure_instance.status = PricingProcedureInstance.STATUS_DONE

            procedure_instance.save()

            if procedure_instance.schedule_instance:
                procedure_instance.schedule_instance.run_next_procedure()

        except Exception as e:
            procedure_instance.error_message = 'Error %s' % e
            procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
            procedure_instance.save()

    def process_to_bloomberg_provider(self, items):

        _l.debug("Pricing Currency Handler - Bloomberg Provider: len %s" % len(items))

        procedure_instance = PricingProcedureInstance.objects.create(procedure=self.procedure,
                                                                     parent_procedure_instance=self.parent_procedure,
                                                                     master_user=self.master_user,
                                                                     member=self.member,
                                                                     status=PricingProcedureInstance.STATUS_PENDING,
                                                                     action='bloomberg_get_currency_prices',
                                                                     provider='bloomberg',
                                                                     action_verbose='Get FX Rates from Bloomberg',
                                                                     provider_verbose='Bloomberg'

                                                                     )

        if self.member:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_MEMBER
            procedure_instance.member = self.member

        if self.schedule_instance:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_SCHEDULE
            procedure_instance.schedule_instance = self.schedule_instance

        procedure_instance.save()

        try:

            body = {}
            body['action'] = procedure_instance.action
            body['procedure'] = procedure_instance.id
            body['provider'] = procedure_instance.provider

            config = None

            try:

                config = BloombergDataProviderCredential.objects.get(master_user=self.master_user)

            except Exception as e:

                config = self.master_user.import_configs.get(provider=ProviderClass.BLOOMBERG)

            body['user'] = {
                'token': self.master_user.token,
                'base_api_url': settings.BASE_API_URL,
                'credentials': {
                    'p12cert': str(config.p12cert),
                    'password': config.password
                }
            }

            body['error_code'] = None
            body['error_message'] = None

            body['data'] = {}

            body['data']['date_from'] = str(self.procedure.price_date_from)
            body['data']['date_to'] = str(self.procedure.price_date_to)
            body['data']['items'] = []

            items_with_missing_parameters = []

            dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                        date_to=self.procedure.price_date_to)

            is_yesterday = get_is_yesterday(self.procedure.price_date_from, self.procedure.price_date_to)

            empty_values = get_empty_values_for_dates(dates)

            _l.debug('is_yesterday %s' % is_yesterday)
            _l.debug('procedure id %s' % body['procedure'])

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
                                                                                 currency_parameters=str(
                                                                                     item_parameters),
                                                                                 pricing_policy=item.policy.pricing_policy,
                                                                                 pricing_scheme=item.pricing_scheme,
                                                                                 reference=item.parameters[0],
                                                                                 date=date)

                                if 'fx_rate' in item.scheme_fields_map:
                                    record.fx_rate_parameters = item.scheme_fields_map[
                                        'fx_rate']

                                CurrencyHistoryError.objects.create(
                                    master_user=self.master_user,
                                    procedure_instance_id=procedure_instance.id,
                                    currency=record.currency,
                                    pricing_scheme=record.pricing_scheme,
                                    pricing_policy=record.pricing_policy,
                                    date=record.date,
                                    status=CurrencyHistoryError.STATUS_REQUESTED,
                                    created=procedure_instance.created
                                )

                                record.save()

                            except Exception as e:
                                _l.debug("Cant create Result Record %s" % e)

                    item_obj = {
                        'reference': item.parameters[0],
                        'parameters': item_parameters,
                        'fields': []
                    }

                    if 'fx_rate' in item.scheme_fields_map:
                        item_obj['fields'].append({
                            'code': item.scheme_fields_map['fx_rate'],
                            'parameters': [],
                            'values': empty_values
                        })

                    full_items.append(item_obj)

                else:
                    items_with_missing_parameters.append(item)

            _l.debug('full_items len: %s' % len(full_items))

            optimized_items = optimize_items(full_items)

            _l.debug('optimized_items len: %s' % len(optimized_items))

            body['data']['items'] = optimized_items

            _l.debug('items_with_missing_parameters %s' % len(items_with_missing_parameters))
            # _l.debug('data %s' % data)

            _l.debug('self.procedure %s' % self.procedure.id)
            _l.debug('send request %s' % body)

            procedure_instance.request_data = body
            procedure_instance.save()

            try:

                self.transport.send_request(body)

            except Exception as e:

                _l.info("Bloomberg fx rates request failed %s" % e)

                procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
                procedure_instance.error_code = 500
                procedure_instance.error_message = "Mediator is unavailable. Please try later."

                procedure_instance.save()

                send_system_message(master_user=self.master_user,
                                    performed_by='System',
                                    type='error',
                                    description="Pricing Procedure %s. Error, Mediator is unavailable." % procedure_instance.procedure.name)
        except Exception as e:
            procedure_instance.error_message = 'Error %s' % e
            procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
            procedure_instance.save()

    def process_to_fixer_provider(self, items):

        _l.debug("Pricing Currency Handler - Fixer Provider: len %s" % len(items))

        with transaction.atomic():

            procedure_instance = PricingProcedureInstance(procedure=self.procedure,
                                                          parent_procedure_instance=self.parent_procedure,
                                                          master_user=self.master_user,
                                                          status=PricingProcedureInstance.STATUS_PENDING,
                                                          action='fixer_get_currency_prices',
                                                          provider='fixer',

                                                          action_verbose='Get FX Rates from Fixer',
                                                          provider_verbose='Fixer'

                                                          )

            if self.member:
                procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_MEMBER
                procedure_instance.member = self.member

            if self.schedule_instance:
                procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_SCHEDULE
                procedure_instance.schedule_instance = self.schedule_instance

            procedure_instance.save()

        body = {}
        body['action'] = procedure_instance.action
        body['procedure'] = procedure_instance.id
        body['provider'] = procedure_instance.provider

        body['user'] = {
            'token': self.master_user.id,
            'base_api_url': settings.BASE_API_URL
        }

        body['error_code'] = None
        body['error_message'] = None

        body['data'] = {}

        body['data']['date_from'] = str(self.procedure.price_date_from)
        body['data']['date_to'] = str(self.procedure.price_date_to)
        body['data']['items'] = []

        items_with_missing_parameters = []

        dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                    date_to=self.procedure.price_date_to)

        _l.debug('procedure id %s' % body['procedure'])

        empty_values = get_empty_values_for_dates(dates)

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
                            _l.debug("Cant create Result Record %s" % e)

                item_obj = {
                    'reference': item.parameters[0],
                    'parameters': item_parameters,
                    'fields': []
                }

                item_obj['fields'].append({
                    'code': 'close',
                    'parameters': [],
                    'values': empty_values
                })

                full_items.append(item_obj)

            else:
                items_with_missing_parameters.append(item)

        _l.debug('full_items len: %s' % len(full_items))

        optimized_items = optimize_items(full_items)

        _l.debug('optimized_items len: %s' % len(optimized_items))

        body['data']['items'] = optimized_items

        _l.debug('items_with_missing_parameters %s' % len(items_with_missing_parameters))
        # _l.debug('data %s' % data)

        _l.debug('self.procedure %s' % self.procedure.id)
        _l.debug('send request %s' % body)

        procedure_instance.request_data = body
        procedure_instance.save()

        try:

            self.transport.send_request(body)

        except Exception as e:

            procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
            procedure_instance.error_code = 500
            procedure_instance.error_message = "Mediator is unavailable. Please try later."

            procedure_instance.save()

            send_system_message(master_user=self.master_user,
                                performed_by='System',
                                type='error',
                                description="Pricing Procedure %s. Error, Mediator is unavailable." % procedure_instance.procedure.name)

    def process_to_fx_cbonds_provider(self, items):

        _l.debug("Pricing Currency Handler - Fixer Provider: len %s" % len(items))

        with transaction.atomic():

            procedure_instance = PricingProcedureInstance(procedure=self.procedure,
                                                          parent_procedure_instance=self.parent_procedure,
                                                          master_user=self.master_user,
                                                          member=self.member,
                                                          status=PricingProcedureInstance.STATUS_PENDING,
                                                          action='cbonds_get_currency_prices',
                                                          provider='cbonds',

                                                          action_verbose='Get FX Rates from Cbonds',
                                                          provider_verbose='Cbonds'

                                                          )

            if self.member:
                procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_MEMBER
                procedure_instance.member = self.member

            if self.schedule_instance:
                procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_SCHEDULE
                procedure_instance.schedule_instance = self.schedule_instance

            procedure_instance.save()

        try:

            body = {}
            body['action'] = procedure_instance.action
            body['procedure'] = procedure_instance.id
            body['provider'] = procedure_instance.provider

            body['user'] = {
                'token': self.master_user.id,
                'base_api_url': settings.BASE_API_URL
            }

            body['error_code'] = None
            body['error_message'] = None

            body['data'] = {}

            body['data']['date_from'] = str(self.procedure.price_date_from)
            body['data']['date_to'] = str(self.procedure.price_date_to)
            body['data']['items'] = []

            items_with_missing_parameters = []

            dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                        date_to=self.procedure.price_date_to)

            _l.debug('procedure id %s' % body['procedure'])

            empty_values = get_empty_values_for_dates(dates)

            full_items = []

            for item in items:

                if len(item.parameters):

                    item_parameters = item.parameters.copy()
                    item_parameters.pop()

                    for date in dates:

                        with transaction.atomic():
                            try:

                                record = PricingProcedureCbondsCurrencyResult(master_user=self.master_user,
                                                                              procedure=procedure_instance,
                                                                              currency=item.currency,
                                                                              currency_parameters=str(item_parameters),
                                                                              pricing_policy=item.policy.pricing_policy,
                                                                              pricing_scheme=item.pricing_scheme,
                                                                              reference=item.parameters[0],
                                                                              date=date)

                                record.save()

                            except Exception as e:
                                _l.debug("Cant create Result Record %s" % e)

                    item_obj = {
                        'reference': item.parameters[0],
                        'parameters': item_parameters,
                        'fields': []
                    }

                    item_obj['fields'].append({
                        'code': 'close',
                        'parameters': [],
                        'values': empty_values
                    })

                    full_items.append(item_obj)

                else:
                    items_with_missing_parameters.append(item)

            _l.debug('full_items len: %s' % len(full_items))

            optimized_items = optimize_items(full_items)

            _l.debug('optimized_items len: %s' % len(optimized_items))

            body['data']['items'] = optimized_items

            _l.debug('items_with_missing_parameters %s' % len(items_with_missing_parameters))
            # _l.debug('data %s' % data)

            _l.debug('self.procedure %s' % self.procedure.id)
            _l.debug('send request %s' % body)

            procedure_instance.request_data = body
            procedure_instance.save()

            try:

                self.transport.send_request(body)

            except Exception as e:

                procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
                procedure_instance.error_code = 500
                procedure_instance.error_message = "Mediator is unavailable. Please try later."

                procedure_instance.save()

                send_system_message(master_user=self.master_user,
                                    performed_by='System',
                                    type='error',
                                    description="Pricing Procedure %s. Error, Mediator is unavailable." % procedure_instance.procedure.name)
        except Exception as e:
            procedure_instance.error_message = 'Error %s' % e
            procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
            procedure_instance.save()

    def print_grouped_currencies(self):

        names = {
            1: 'Skip',
            2: 'Manual Pricing',  # DEPRECATED
            3: 'Single Parameter Formula',
            4: 'Multiple Parameter Formula',
            5: 'Bloomberg',
            6: 'Wtrade',  # DEPRECATED
            7: 'Fixer',
            9: 'Cbonds'

        }

        for provider_id, items in self.currency_items_grouped.items():
            _l.debug("Pricing Currency Handler - Provider %s: len: %s" % (names[provider_id], len(items)))
