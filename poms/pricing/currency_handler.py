from poms.common import formula
from poms.currencies.models import Currency, CurrencyHistory
from poms.obj_attrs.models import GenericAttribute
from poms.pricing.brokers.broker_bloomberg import BrokerBloomberg
from poms.pricing.utils import get_unique_pricing_schemes, group_items_by_provider, get_list_of_dates_between_two_dates


class CurrencyItem(object):

    def __init__(self, currency, policy, pricing_scheme):
        self.currency = currency
        self.policy = policy
        self.pricing_scheme = pricing_scheme

        self.scheme_fields = []
        self.parameters = []


class PricingCurrencyHandler(object):

    def __init__(self, procedure=None, master_user=None):

        self.master_user = master_user
        self.procedure = procedure

        self.currencies = []

        self.currencies_pricing_schemes = []

        self.currency_items = []

        self.currency_items_grouped = {}

        self.broker_bloomberg = BrokerBloomberg()

    def process(self):

        print("Pricing Currency Handler: Process")

        self.currencies = self.get_currencies()

        self.currencies_pricing_schemes = get_unique_pricing_schemes(self.currencies)

        print('currencies_pricing_schemes len %s' % len(self.currencies_pricing_schemes))

        self.currency_items = self.get_currency_items()

        print('currency_items len %s' % len(self.currency_items))

        self.currency_items_grouped = group_items_by_provider(items=self.currency_items,
                                                                   groups=self.currencies_pricing_schemes)

        print('currency_items_grouped len %s' % len(self.currency_items_grouped))

        self.print_grouped_currencies()

        for provider_id, items in self.currency_items_grouped.items():

            # DEPRECATED
            # if provider_id == 2:
            #     self.process_to_manual_pricing(items)

            if provider_id == 3:
                self.process_to_single_parameter_formula(items)

            if provider_id == 4:
                self.process_to_multiple_parameter_formula(items)

            if provider_id == 5:
                self.process_to_bloomberg_provider(items)


    def get_currencies(self):

        result = []

        result = list(Currency.objects.filter(master_user=self.master_user))

        return result

    def get_currency_items(self):

        result = []

        for currency in self.currencies:

            for policy in currency.pricing_policies.all():
                item = CurrencyItem(currency, policy, policy.pricing_scheme)

                result.append(item)

        return result

    def process_to_single_parameter_formula(self, items):

        print("Pricing Currency Handler - Single Parameter Formula: len %s" % len(items))

        dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                    date_to=self.procedure.price_date_to)

        for item in items:

            for date in dates:

                scheme_parameters = item.pricing_scheme.get_parameters()

                if scheme_parameters:

                    safe_currency = {
                        'id': item.currency.id,
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

                            attribute = GenericAttribute.objects.get(object_id=item.currency.id, attribute_type__user_code=user_code)

                            if scheme_parameters.value_type == 10:

                                parameter = attribute.value_string

                            if scheme_parameters.value_type == 20:

                                parameter = attribute.value_float

                            if scheme_parameters.value_type == 40:

                                parameter = attribute.value_date

                        else:

                            parameter = item.currenc[item.policy.attribute_key]

                    values = {
                        'd': date,
                        'currency': safe_currency,
                        'parameter': parameter
                    }

                    expr = scheme_parameters.expr

                    print('values %s' % values)
                    print('expr %s' % expr)

                    try:
                        fx_rate = formula.safe_eval(expr, names=values)
                    except formula.InvalidExpression:
                        print("Error here")
                        continue

                    print('fx_rate %s' % fx_rate)

                    if fx_rate:

                        try:

                            price = CurrencyHistory.objects.get(
                                currency=item.currency,
                                pricing_policy=item.policy.pricing_policy,
                                date=date
                            )

                            price.fx_rate = fx_rate
                            price.save()

                            print('Update Currency history %s' % price.id)

                        except CurrencyHistory.DoesNotExist:

                            price = CurrencyHistory(
                                currency=item.currency,
                                pricing_policy=item.policy.pricing_policy,
                                date=date,
                                fx_rate=fx_rate
                            )

                            price.save()

    def process_to_multiple_parameter_formula(self, items):

        print("Pricing Currency Handler - Multiple Parameter Formula: len %s" % len(items))

        dates = get_list_of_dates_between_two_dates(date_from=self.procedure.price_date_from,
                                                    date_to=self.procedure.price_date_to)

        for item in items:

            for date in dates:

                scheme_parameters = item.pricing_scheme.get_parameters()

                if scheme_parameters:

                    safe_currency = {
                        'id': item.currency.id,
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

                            attribute = GenericAttribute.objects.get(object_id=item.currency.id, attribute_type__user_code=user_code)

                            if scheme_parameters.value_type == 10:

                                parameter = attribute.value_string

                            if scheme_parameters.value_type == 20:

                                parameter = attribute.value_float

                            if scheme_parameters.value_type == 40:

                                parameter = attribute.value_date

                        else:

                            parameter = item.currency[item.policy.attribute_key]

                    values = {
                        'd': date,
                        'currency': safe_currency,
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

                    expr = scheme_parameters.expr

                    print('values %s' % values)
                    print('expr %s' % expr)

                    try:
                        fx_rate = formula.safe_eval(expr, names=values)
                    except formula.InvalidExpression:
                        print("Error here")
                        continue

                    print('fx_rate %s' % fx_rate)

                    if fx_rate:

                        try:

                            price = CurrencyHistory.objects.get(
                                currency=item.currency,
                                pricing_policy=item.policy.pricing_policy,
                                date=date
                            )

                            price.fx_rate = fx_rate
                            price.save()

                            print('Update Price history %s' % price.id)

                        except CurrencyHistory.DoesNotExist:

                            price = CurrencyHistory(
                                currency=item.currency,
                                pricing_policy=item.policy.pricing_policy,
                                date=date,
                                fx_rate=fx_rate
                            )

                            price.save()

    def process_to_bloomberg_provider(self, items):

        print("Pricing Currency Handler - Bloomberg Provider: len %s" % len(items))

        pass

    def print_grouped_currencies(self):

        names = {
            1: 'Skip',
            2: 'Manual Pricing',  # DEPRECATED
            3: 'Single Parameter Formula',
            4: 'Multiple Parameter Formula',
            5: 'Bloomberg'

        }

        for provider_id, items in self.currency_items_grouped.items():
            print("Pricing Currency Handler - Provider %s: len: %s" % (names[provider_id], len(items)))
