import time
import traceback

from django.contrib.contenttypes.models import ContentType

from poms.instruments.models import GeneratedEvent
from poms.obj_attrs.models import GenericClassifier, GenericAttributeType
from poms.transactions.handlers import TransactionTypeProcess
from poms.transactions.models import ComplexTransaction, TransactionType

import logging

_l = logging.getLogger('poms.instruments')


# Context variables here

class GeneratedEventProcess(TransactionTypeProcess):
    def __init__(self, generated_event=None, action=None, **kwargs):
        self.generated_event = generated_event
        self.action = action
        # kwargs['transaction_type'] = action.transaction_type

        kwargs['transaction_type'] = TransactionType.objects.get(master_user=generated_event.master_user,
                                                                 user_code=action.transaction_type)

        # Some Inputs can choose from which context variable it will take value

        context_values = kwargs.get('context_values', None) or {}
        context_values.update({
            'context_instrument': generated_event.instrument,
            'context_pricing_currency': generated_event.instrument.pricing_currency,
            'context_accrued_currency': generated_event.instrument.accrued_currency,
            'context_portfolio': generated_event.portfolio,
            'context_account': generated_event.account,
            'context_strategy1': generated_event.strategy1,
            'context_strategy2': generated_event.strategy2,
            'context_strategy3': generated_event.strategy3,
            'context_position': generated_event.position,
            'context_effective_date': generated_event.effective_date,
            'context_notification_date': generated_event.notification_date,  # not in context variables
            # 'final_date': generated_event.event_schedule.final_date,
            # 'maturity_date': generated_event.instrument.maturity_date
        })

        _l.info('generated_event data %s' % generated_event.data)

        if generated_event.data:
            if generated_event.data['actions_parameters']:

                if action.button_position in generated_event.data['actions_parameters']:

                    for key, value in generated_event.data['actions_parameters'][action.button_position].items():
                        context_values[key] = value

        kwargs['context_values'] = context_values

        # But by default Context Variables overwrites default value

        # default_values = kwargs.get('default_values', None) or {}
        # default_values.update({
        #     'instrument': generated_event.instrument,
        #     'pricing_currency': generated_event.instrument.pricing_currency,
        #     'accrued_currency': generated_event.instrument.accrued_currency,
        #     'portfolio': generated_event.portfolio,
        #     'account': generated_event.account,
        #     'strategy1': generated_event.strategy1,
        #     'strategy2': generated_event.strategy2,
        #     'strategy3': generated_event.strategy3,
        #     'position': generated_event.position,
        #     'effective_date': generated_event.effective_date,
        #     'notification_date': generated_event.notification_date, # not in context variables
        #     # 'final_date': generated_event.event_schedule.final_date,
        #     # 'maturity_date': generated_event.instrument.maturity_date
        # })
        # kwargs['default_values'] = default_values

        if generated_event.status == GeneratedEvent.ERROR:
            kwargs['complex_transaction_status'] = ComplexTransaction.PENDING
        else:
            if action.is_sent_to_pending:
                kwargs['complex_transaction_status'] = ComplexTransaction.PENDING
            else:
                kwargs['complex_transaction_status'] = ComplexTransaction.PRODUCTION

        # context = kwargs.get('context', None) or {}
        # if 'master_user' not in context:
        #     context['master_user'] = generated_event.master_user

        super(GeneratedEventProcess, self).__init__(**kwargs)


class InstrumentTypeProcess(object):

    def __init__(self, instrument_type=None, context=None):
        self.instrument_type = instrument_type
        self.context = context

        instrument_object = {
            "instrument_type": instrument_type.id
        }
        self.instrument = self.fill_instrument_with_instrument_type_defaults(instrument_object, self.instrument_type)

    def fill_instrument_with_instrument_type_defaults(self, instrument_object, instrument_type):

        try:

            _l.info(
                'InstrumentTypeProcess.fill_instrument_with_instrument_type_defaults instrument_type %s' % self.instrument_type.user_code)
            _l.info(
                'InstrumentTypeProcess.fill_instrument_with_instrument_type_defaults instrument_type %s' % self.instrument_type.maturity_date)

            start_time = time.time()

            # Set system attributes

            if instrument_type.payment_size_detail:
                instrument_object['payment_size_detail'] = instrument_type.payment_size_detail_id
            else:
                instrument_object['payment_size_detail'] = None

            if instrument_type.accrued_currency:
                instrument_object['accrued_currency'] = instrument_type.accrued_currency_id
            else:
                instrument_object['accrued_currency'] = None

            if instrument_type.pricing_currency:
                instrument_object['pricing_currency'] = instrument_type.pricing_currency_id
            else:
                instrument_object['pricing_currency'] = None

            instrument_object['default_price'] = instrument_type.default_price
            instrument_object['maturity_date'] = instrument_type.maturity_date
            instrument_object['maturity_price'] = instrument_type.maturity_price

            instrument_object['accrued_multiplier'] = instrument_type.accrued_multiplier
            instrument_object['price_multiplier'] = instrument_type.price_multiplier

            instrument_object['default_accrued'] = instrument_type.default_accrued
            instrument_object['reference_for_pricing'] = instrument_type.reference_for_pricing
            instrument_object['pricing_condition'] = instrument_type.pricing_condition_id
            instrument_object['position_reporting'] = instrument_type.position_reporting

            if instrument_type.exposure_calculation_model:
                instrument_object['exposure_calculation_model'] = instrument_type.exposure_calculation_model_id
            else:
                instrument_object['exposure_calculation_model'] = None

            instrument_object['long_underlying_instrument'] = instrument_type.long_underlying_instrument
            instrument_object['underlying_long_multiplier'] = instrument_type.underlying_long_multiplier

            instrument_object['short_underlying_instrument'] = instrument_type.short_underlying_instrument
            instrument_object['underlying_short_multiplier'] = instrument_type.underlying_short_multiplier

            instrument_object['long_underlying_exposure'] = instrument_type.long_underlying_exposure_id
            instrument_object['short_underlying_exposure'] = instrument_type.short_underlying_exposure_id

            instrument_object['co_directional_exposure_currency'] = instrument_type.co_directional_exposure_currency
            instrument_object[
                'counter_directional_exposure_currency'] = instrument_type.counter_directional_exposure_currency

            # Set attributes
            instrument_object['attributes'] = []

            content_type = ContentType.objects.get(model="instrument", app_label="instruments")

            for attribute in instrument_type.instrument_attributes.all():

                attribute_type = GenericAttributeType.objects.get(master_user=self.instrument_type.master_user,
                                                                  content_type=content_type,
                                                                  user_code=attribute.attribute_type_user_code)

                attr = {
                    'attribute_type': attribute_type.id,
                    'attribute_type_object': {
                        'id': attribute_type.id,
                        'name': attribute_type.name,
                        'user_code': attribute_type.user_code,
                        'value_type': attribute_type.value_type
                    }
                }

                attr['value_string'] = None
                attr['value_float'] = None
                attr['value_date'] = None
                attr['classifier'] = None
                attr['classifier_object'] = None

                if attribute.value_type == 10:
                    attr['value_string'] = attribute.value_string

                if attribute.value_type == 20:
                    attr['value_float'] = attribute.value_float

                if attribute.value_type == 30:
                    try:

                        classifier = GenericClassifier.objects.filter(name=attribute.value_classifier,
                                                                      attribute_type=attribute_type)[0]

                        attr['classifier'] = classifier.id
                        attr['classifier_object'] = {
                            "id": classifier.id,
                            "level": classifier.level,
                            "parent": classifier.parent,
                            "name": classifier.name
                        }
                    except Exception as e:
                        attr['classifier'] = None
                        attr['classifier_object'] = None

                if attribute.value_type == 40:
                    attr['value_date'] = attribute.value_date

                instrument_object['attributes'].append(attr)

            # Set Event Schedules

            instrument_object['event_schedules'] = []

            for instrument_type_event in instrument_type.events.all():

                event_schedule = {
                    # 'name': instrument_type_event.name,
                    'event_class': instrument_type_event.data['event_class']
                }

                for item in instrument_type_event.data['items']:

                    # TODO add check for value type
                    if 'default_value' in item:
                        event_schedule[item['key']] = item['default_value']

                if 'items2' in instrument_type_event.data:

                    for item in instrument_type_event.data['items2']:
                        if 'default_value' in item:
                            event_schedule[item['key']] = item['default_value']

                #
                event_schedule['is_auto_generated'] = True
                event_schedule['actions'] = []

                for instrument_type_action in instrument_type_event.data['actions']:
                    action = {}
                    action['transaction_type'] = instrument_type_action[
                        'transaction_type']  # TODO check if here user code instead of id
                    action['text'] = instrument_type_action['text']
                    action['is_sent_to_pending'] = instrument_type_action['is_sent_to_pending']
                    action['is_book_automatic'] = instrument_type_action['is_book_automatic']

                    event_schedule['actions'].append(action)

                instrument_object['event_schedules'].append(event_schedule)

            # Set Accruals

            instrument_object['accrual_calculation_schedules'] = []

            for instrument_type_accrual in instrument_type.accruals.all():

                accrual = {

                }

                for item in instrument_type_accrual.data['items']:

                    # TODO add check for value type
                    if 'default_value' in item:
                        accrual[item['key']] = item['default_value']

                instrument_object['accrual_calculation_schedules'].append(accrual)

            _l.info(
                'InstrumentTypeProcess.fill_instrument_with_instrument_type_defaults instrument_object %s' % instrument_object)

            _l.info(
                "InstrumentTypeProcess.fill_instrument_with_instrument_type_defaults %s seconds " % "{:3.3f}".format(
                    time.time() - start_time))

            return instrument_object

        except Exception as e:
            _l.info('set_defaults_from_instrument_type e %s' % e)
            _l.info(traceback.format_exc())

            raise Exception("Instrument Type is not configured correctly %s" % e)
