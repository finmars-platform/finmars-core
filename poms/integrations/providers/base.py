from datetime import date, datetime
from logging import getLogger

from dateutil import parser
from dateutil.rrule import rrule, DAILY
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy

from poms.common import formula
from poms.currencies.models import CurrencyHistory
from poms.instruments.models import Instrument, PriceHistory
from poms.integrations.models import InstrumentDownloadScheme, ProviderClass, CurrencyMapping, InstrumentTypeMapping, \
    InstrumentAttributeValueMapping, AccrualCalculationModelMapping, PeriodicityMapping
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType

_l = getLogger('poms.integrations')


class ProviderException(Exception):
    pass


class ProviderNotConfiguredException(ProviderException):
    pass


class AbstractProvider(object):
    def __init__(self):
        self.empty_value = ()

    def get_max_retries(self):
        return 3

    def get_retry_delay(self):
        return 5

    def is_empty_value(self, value):
        return value is None or value == '' or value in self.empty_value

    def parse_date(self, v):
        if v is not None:
            if isinstance(v, date):
                return v
            elif isinstance(v, datetime):
                return v.date()
            else:
                try:
                    v = parser.parse(v)
                    return v.date()
                except ValueError:
                    return None
        return None

    def parse_float(self, v):
        if v is None:
            return None
        try:
            return float(v)
        except ValueError:
            return 0.0

    def get_factor_schedule_method_fields(self, factor_schedule_method=None):
        return []

    def get_accrual_calculation_schedule_method_fields(self, accrual_calculation_schedule_method=None):
        return []

    def is_valid_reference(self, value):
        return True

    def download_instrument(self, options):
        return None, True

    def download_instrument_pricing(self, options):
        return None, True

    def download_currency_pricing(self, options):
        return None, True

    def get_currency(self, master_user, provider, value):
        # if not value:
        #     return None
        if value is None:
            value = ''
        try:
            obj = CurrencyMapping.objects.select_related('content_object').get(
                master_user=master_user, provider=provider, value=value)
        except CurrencyMapping.DoesNotExist:
            return None
        return obj.content_object

    def get_instrument_type(self, master_user, provider, value):
        # if not value:
        #     return None
        if value is None:
            value = ''
        try:
            obj = InstrumentTypeMapping.objects.select_related('content_object').get(
                master_user=master_user, provider=provider, value=value)
        except InstrumentTypeMapping.DoesNotExist:
            return None
        return obj.content_object

    def get_instrument_attribute_value(self, master_user, provider, attribute_type, value):
        # if not value:
        #     return None
        if value is None:
            value = ''
        try:
            obj = InstrumentAttributeValueMapping.objects.select_related('content_object', 'classifier').get(
                master_user=master_user, provider=provider, content_object=attribute_type, value=value)
        except InstrumentAttributeValueMapping.DoesNotExist:
            return None
        return obj.value_string, obj.value_float, obj.value_date, obj.classifier

    def get_accrual_calculation_model(self, master_user, provider, value):
        # if not value:
        #     return None
        if value is None:
            value = ''
        try:
            obj = AccrualCalculationModelMapping.objects.select_related('content_object').get(
                master_user=master_user, provider=provider, value=value)
        except AccrualCalculationModelMapping.DoesNotExist:
            return None
        return obj.content_object

    def get_periodicity(self, master_user, provider, value):
        # if not value:
        #     return None
        if value is None:
            value = ''
        try:
            obj = PeriodicityMapping.objects.select_related('content_object').get(
                master_user=master_user, provider=provider, value=value)
        except PeriodicityMapping.DoesNotExist:
            return None
        return obj.content_object

    def create_instrument(self, instrument_download_scheme, values):
        errors = {}
        master_user = instrument_download_scheme.master_user
        provider = instrument_download_scheme.provider

        instr = Instrument(master_user=master_user)

        # instr.instrument_type = master_user.instrument_type
        # instr.pricing_currency = master_user.currency
        # instr.accrued_currency = master_user.currency

        instr.payment_size_detail = instrument_download_scheme.payment_size_detail
        instr.daily_pricing_model = instrument_download_scheme.daily_pricing_model
        instr.price_download_scheme = instrument_download_scheme.price_download_scheme
        instr.default_price = instrument_download_scheme.default_price
        instr.default_accrued = instrument_download_scheme.default_accrued

        values_converted = {}

        for input in instrument_download_scheme.inputs.all():
            for key, value in values.items():
                if input.name == key:

                    try:
                        values_converted[key] = formula.safe_eval(input.name_expr, names=values)
                    except formula.InvalidExpression:
                        _l.debug('Invalid instrument attribute expression conversion: id=%s, input=%s, expr=%s, values=%s',
                                 instrument_download_scheme.id, input, input.name_expr, values)
                        errors[input] = [ugettext_lazy('Invalid expression.')]
                        continue


        for attr in InstrumentDownloadScheme.BASIC_FIELDS:
            expr = getattr(instrument_download_scheme, attr)
            if not expr:
                continue
            try:
                v = formula.safe_eval(expr, names=values_converted)
            except formula.InvalidExpression:
                _l.debug('Invalid instrument attribute expression: id=%s, attr=%s, expr=%s, values=%s',
                         instrument_download_scheme.id, attr, expr, values)
                errors[attr] = [ugettext_lazy('Invalid expression.')]
                continue
            if attr in ('pricing_currency', 'accrued_currency',):
                # if self.is_empty_value(v):
                #     pass
                # else:
                v = self.get_currency(master_user, provider, v)
                if v:
                    setattr(instr, attr, v)
                else:
                    errors[attr] = [ugettext_lazy('This field is required.')]
            elif attr in ('instrument_type',):
                # if self.is_empty_value(v):
                #     pass
                # else:
                v = self.get_instrument_type(master_user, provider, v)
                if v:
                    setattr(instr, attr, v)
                else:
                    errors[attr] = [ugettext_lazy('This field is required.')]
            elif attr in ('price_multiplier', 'accrued_multiplier', 'default_price', 'default_accrued',
                          'maturity_price'):
                if self.is_empty_value(v):
                    pass
                else:
                    try:
                        setattr(instr, attr, float(v))
                    except (ValueError, TypeError):
                        errors[attr] = [ugettext_lazy('A valid number is required.')]
            elif attr in ('maturity_date',):
                if self.is_empty_value(v):
                    pass
                else:
                    if isinstance(v, datetime):
                        v = v.date()
                    if isinstance(v, date):
                        setattr(instr, attr, v)
                    else:
                        errors[attr] = [ugettext_lazy('A valid date is required.')]
            else:
                if self.is_empty_value(v):
                    pass
                else:
                    v = str(v)
                    setattr(instr, attr, v)

        instr._attributes = self.create_instrument_attributes(
            instrument_download_scheme=instrument_download_scheme, instrument=instr, values=values, errors=errors)

        instr._accrual_calculation_schedules = self.create_accrual_calculation_schedules(
            instrument_download_scheme=instrument_download_scheme, instrument=instr, values=values)

        instr._factor_schedules = self.create_factor_schedules(
            instrument_download_scheme=instrument_download_scheme, instrument=instr, values=values)

        return instr, errors

    def create_instrument_attributes(self, instrument_download_scheme, instrument, values, errors):
        iattrs = []
        master_user = instrument_download_scheme.master_user
        provider = instrument_download_scheme.provider
        for attr in instrument_download_scheme.attributes.select_related('attribute_type').all():
            tattr = attr.attribute_type

            iattr = GenericAttribute(content_object=instrument, attribute_type=tattr)
            iattrs.append(iattr)

            err_name = 'attribute_type_%s' % attr.attribute_type.id

            if attr.value:
                try:
                    v = formula.safe_eval(attr.value, names=values)
                except formula.InvalidExpression:
                    _l.debug('Invalid instrument dynamic attribute expression: id=%s, attr=%s, expr="%s", values=%s',
                             instrument_download_scheme.id, attr.id, attr.value, values)
                    errors[err_name] = [ugettext_lazy('Invalid expression.')]
                    continue
                # if not self.is_empty_value(v):
                #     attr_mapped_values = self.get_instrument_attribute_value(master_user, provider, tattr, v)
                # else:
                #     attr_mapped_values = None
                attr_mapped_values = self.get_instrument_attribute_value(master_user, provider, tattr, v)
                if attr_mapped_values is not None:
                    iattr.value_string, iattr.value_float, iattr.value_date, iattr.classifier = attr_mapped_values
                else:
                    if tattr.value_type == GenericAttributeType.STRING:
                        if self.is_empty_value(v):
                            pass
                        else:
                            iattr.value_string = str(v)
                    elif tattr.value_type == GenericAttributeType.NUMBER:
                        if self.is_empty_value(v):
                            pass
                        else:
                            try:
                                iattr.value_float = float(v)
                            except (ValueError, TypeError):
                                errors[err_name] = [ugettext_lazy('A valid number is required.')]
                    elif tattr.value_type == GenericAttributeType.DATE:
                        if self.is_empty_value(v):
                            pass
                        else:
                            if isinstance(v, datetime):
                                v = v.date()
                            if isinstance(v, date):
                                iattr.value_date = v
                            else:
                                errors[err_name] = [ugettext_lazy('A valid date is required.')]
                    elif tattr.value_type == GenericAttributeType.CLASSIFIER:
                        if self.is_empty_value(v):
                            pass
                        else:
                            v = str(v)
                            v = tattr.classifiers.filter(name=v).first()
                            if v:
                                iattr.classifier = v
                            else:
                                errors[err_name] = [ugettext_lazy('This field is required.')]
            else:
                errors[err_name] = [ugettext_lazy('Expression required')]
        return iattrs

    def create_accrual_calculation_schedules(self, instrument_download_scheme, instrument, values):
        return []

    def create_factor_schedules(self, instrument_download_scheme, instrument, values):
        return []

    def create_instrument_pricing(self, price_download_scheme, options, values, instruments, pricing_policies):
        return [], {}

    def create_currency_pricing(self, price_download_scheme, options, values, currencies, pricing_policies):
        return [], {}

    def price_adapt_value(self, value, multiplier):
        if self.is_empty_value(value):
            return 0.0
        return value * multiplier

    def get_price_scheme_value(self, price_scheme, values, *args):
        for attr_name in args:
            field_name = getattr(price_scheme, attr_name)
            if field_name and field_name in values:
                value = values[field_name]
                if value is None or self.is_empty_value(value):
                    return 0.0
                try:
                    return float(value)
                except ValueError:
                    _l.debug('Invalid float value: price_scheme=%s, attr_name=%s, value=%s',
                             price_scheme.id, attr_name, value)
                    # Try next value
                    pass
        return 0.0

    def get_instrument_yesterday_values(self, price_scheme, values):
        bid = self.get_price_scheme_value(price_scheme, values, 'bid0', 'bid1', 'bid2')
        ask = self.get_price_scheme_value(price_scheme, values, 'ask0', 'ask1', 'ask2')
        mid = self.get_price_scheme_value(price_scheme, values, 'mid')
        last = self.get_price_scheme_value(price_scheme, values, 'last')
        return {
            'bid': self.price_adapt_value(bid, price_scheme.bid_multiplier),
            'ask': self.price_adapt_value(ask, price_scheme.ask_multiplier),
            'mid': self.price_adapt_value(mid, price_scheme.last_multiplier),
            'last': self.price_adapt_value(last, price_scheme.mid_multiplier),
        }

    def get_instrument_history_values(self, price_scheme, values):
        bid = self.get_price_scheme_value(price_scheme, values, 'bid_history')
        ask = self.get_price_scheme_value(price_scheme, values, 'ask_history')
        mid = self.get_price_scheme_value(price_scheme, values, 'last_history')
        last = self.get_price_scheme_value(price_scheme, values, 'mid_history')
        return {
            'bid': self.price_adapt_value(bid, price_scheme.bid_history_multiplier),
            'ask': self.price_adapt_value(ask, price_scheme.ask_history_multiplier),
            'mid': self.price_adapt_value(mid, price_scheme.last_history_multiplier),
            'last': self.price_adapt_value(last, price_scheme.mid_history_multiplier),
        }

    def get_currency_history_values(self, price_scheme, values):
        value = self.get_price_scheme_value(price_scheme, values, 'currency_fxrate')
        return {
            'bid': self.price_adapt_value(value, price_scheme.currency_fxrate_multiplier),
            'ask': self.price_adapt_value(value, price_scheme.currency_fxrate_multiplier),
            'mid': self.price_adapt_value(value, price_scheme.currency_fxrate_multiplier),
            'last': self.price_adapt_value(value, price_scheme.currency_fxrate_multiplier),
        }

    @staticmethod
    def fail_pricing_policy(errors, pricing_policy, names):
        msg = ugettext_lazy('Invalid pricing policy expression in "%(pricing_policy)s".') % {
            'pricing_policy': pricing_policy.name
        }
        msgs = errors.get('pricing_policy', None) or []
        if msg not in msgs:
            _l.debug('Invalid pricing policy expression: pricing_policy=%s, expr="%s", names=%s',
                     pricing_policy.id, pricing_policy.expr, names)
            errors['pricing_policy'] = msgs + [msg]

    @staticmethod
    def fail_manual_pricing_formula(errors, manual_pricing_formula, names):
        msg = ugettext_lazy('Invalid manual pricing formula expression in instrument "%(instrument)s".') % {
            'instrument': manual_pricing_formula.instrument.user_code
        }
        msgs = errors.get('manual_pricing_formula', None) or []
        if msg not in msgs:
            _l.debug(
                'Invalid manual formula expression: instrument=%s, manual_pricing_formula=%s, expr="%s", values=%s',
                manual_pricing_formula.instrument_id, manual_pricing_formula.id, manual_pricing_formula.expr, names)
            errors['manual_pricing_formula'] = msgs + [msg]


def get_provider(master_user=None, provider=None, task=None):
    if master_user is None:
        master_user = task.master_user
    if provider is None:
        provider = task.provider_id
    if isinstance(provider, ProviderClass):
        provider = provider.id

    if provider == ProviderClass.BLOOMBERG:
        if settings.BLOOMBERG_SANDBOX:

            from poms.integrations.providers.bloomberg import FakeBloombergDataProvider
            return FakeBloombergDataProvider()
        else:
            from poms.integrations.providers.bloomberg import BloombergDataProvider
            try:
                config = master_user.import_configs.get(provider=ProviderClass.BLOOMBERG)
                cert, key = config.pair
                return BloombergDataProvider(cert=cert, key=key)
            except (ObjectDoesNotExist, FileNotFoundError, ValueError):
                raise ProviderNotConfiguredException()
    return None


def parse_date_iso(v):
    if v is not None:
        return datetime.strptime(v, "%Y-%m-%d").date()
    return None


def fill_instrument_price(date_from, days, original):
    ret = []
    for d in rrule(freq=DAILY, count=days, dtstart=date_from):
        ret.append(PriceHistory(
            instrument=original.instrument,
            pricing_policy=original.pricing_policy,
            date=d.date(),
            principal_price=original.principal_price
        ))
    return ret


def fill_currency_price(date_from, days, original):
    ret = []
    for d in rrule(freq=DAILY, count=days, dtstart=date_from):
        ret.append(CurrencyHistory(
            currency=original.currency,
            pricing_policy=original.pricing_policy,
            date=d.date(),
            fx_rate=original.fx_rate
        ))
    return ret
