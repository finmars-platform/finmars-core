

from poms.currencies.models import Currency
from poms.instruments.models import Instrument, PaymentSizeDetail, AccrualCalculationModel, Periodicity, Country
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier


import traceback

from logging import getLogger
_l = getLogger('poms.csv_import')

## Probably DEPRECATED, Use InstrumentTypeProcess.fill_instrument_with_instrument_type_defaults
def set_defaults_from_instrument_type(instrument_object, instrument_type, ecosystem_default):
    try:
        # Set system attributes

        if instrument_type.payment_size_detail_id:
            instrument_object['payment_size_detail'] = instrument_type.payment_size_detail_id
        else:
            instrument_object['payment_size_detail'] = None

        if instrument_type.accrued_currency_id:
            instrument_object['accrued_currency'] = instrument_type.accrued_currency_id
        else:
            instrument_object['accrued_currency'] = None

        instrument_object['price_multiplier'] = instrument_type.price_multiplier
        instrument_object['default_price'] = instrument_type.default_price
        instrument_object['maturity_date'] = instrument_type.maturity_date
        instrument_object['maturity_price'] = instrument_type.maturity_price

        instrument_object['accrued_multiplier'] = instrument_type.accrued_multiplier
        instrument_object['default_accrued'] = instrument_type.default_accrued

        if instrument_type.exposure_calculation_model_id:
            instrument_object['exposure_calculation_model'] = instrument_type.exposure_calculation_model_id
        else:
            instrument_object['exposure_calculation_model'] = None

        if instrument_type.pricing_condition_id:
            instrument_object['pricing_condition'] = instrument_type.pricing_condition_id
        else:
            instrument_object['pricing_condition'] = None

        try:
            instrument_object['long_underlying_instrument'] = Instrument.objects.get(master_user=instrument_type.master_user,
                                                                                     user_code=instrument_type.long_underlying_instrument).pk
        except Exception as e:
            _l.info("Could not set long_underlying_instrument, fallback to default")
            instrument_object['long_underlying_instrument'] = ecosystem_default.instrument.pk

        instrument_object['underlying_long_multiplier'] = instrument_type.underlying_long_multiplier

        try:
            instrument_object['short_underlying_instrument'] = Instrument.objects.get(master_user=instrument_type.master_user,
                                                                                      user_code=instrument_type.short_underlying_instrument).pk
        except Exception as e:
            _l.info("Could not set short_underlying_instrument, fallback to default")
            instrument_object['short_underlying_instrument'] = ecosystem_default.instrument.pk

        instrument_object['underlying_short_multiplier'] = instrument_type.underlying_short_multiplier

        instrument_object['long_underlying_exposure'] = instrument_type.long_underlying_exposure_id
        instrument_object['short_underlying_exposure'] = instrument_type.short_underlying_exposure_id

        try:
            instrument_object['co_directional_exposure_currency'] = Currency.objects.get(master_user=instrument_type.master_user,
                                                                                         user_code=instrument_type.co_directional_exposure_currency).pk
        except Exception as e:
            _l.info("Could not set co_directional_exposure_currency, fallback to default")
            instrument_object['co_directional_exposure_currency'] = ecosystem_default.currency.pk

        try:
            instrument_object[
                'counter_directional_exposure_currency'] = Currency.objects.get(master_user=instrument_type.master_user,
                                                                                user_code=instrument_type.counter_directional_exposure_currency).pk
        except Exception as e:
            _l.info("Could not set counter_directional_exposure_currency, fallback to default")
            instrument_object['counter_directional_exposure_currency'] = ecosystem_default.currency.pk

        # Set attributes
        instrument_object['attributes'] = []

        for attribute in instrument_type.instrument_attributes.all():

            attribute_type = GenericAttributeType.objects.get(master_user=instrument_type.master_user,
                                                              user_code=attribute.attribute_type_user_code)

            attr = {
                'attribute_type': attribute_type.id
            }

            if attribute.value_type == 10:
                attr['value_string'] = attribute.value_string

            if attribute.value_type == 20:
                attr['value_float'] = attribute.value_float

            if attribute.value_type == 30:
                try:

                    item = GenericClassifier.objects.get(attribute_type__user_code=attribute.attribute_type_user_code,
                                                         name=attribute.value_classifier)

                    attr['classifier'] = item.id
                    attr['classifier_object'] = {
                        "id": item.id,
                        "name": item.name
                    }
                except Exception as e:

                    _l.info("Exception %s e " % e)

                    attr['classifier'] = None

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

        # Set Pricing Policy

        try:

            instrument_object['pricing_policies'] = []

            for it_pricing_policy in instrument_type.pricing_policies.all():
                pricing_policy = {}

                pricing_policy['pricing_policy'] = it_pricing_policy.pricing_policy.id
                pricing_policy['pricing_scheme'] = it_pricing_policy.pricing_scheme.id
                pricing_policy['notes'] = it_pricing_policy.notes
                pricing_policy['default_value'] = it_pricing_policy.default_value
                pricing_policy['attribute_key'] = it_pricing_policy.attribute_key
                pricing_policy['json_data'] = it_pricing_policy.json_data

                instrument_object['pricing_policies'].append(pricing_policy)

        except Exception as e:
            _l.info("Can't set default pricing policy %s" % e)

        _l.info('instrument_object %s' % instrument_object)

        return instrument_object

    except Exception as e:
        _l.info('set_defaults_from_instrument_type e %s' % e)
        _l.info(traceback.format_exc())

        raise Exception("Instrument Type is not configured correctly %s" % e)


def set_events_for_instrument(instrument_object, data_object, instrument_type_obj):
    instrument_type = instrument_type_obj.user_code.lower()

    maturity = None

    if 'maturity' in data_object:
        maturity = data_object['maturity']

    if 'maturity_date' in data_object:
        maturity = data_object['maturity_date']

    if maturity:

        if instrument_type in ['bonds', 'convertible_bonds', 'index_linked_bonds', 'short_term_notes']:

            if len(instrument_object['event_schedules']):
                # C
                coupon_event = instrument_object['event_schedules'][0]

                # coupon_event['periodicity'] = data_object['periodicity']

                if 'first_coupon_date' in data_object:
                    coupon_event['effective_date'] = data_object['first_coupon_date']

                coupon_event['final_date'] = maturity

                if len(instrument_object['event_schedules']) == 2:
                    # M
                    expiration_event = instrument_object['event_schedules'][1]

                    expiration_event['effective_date'] = maturity
                    expiration_event['final_date'] = maturity

        if instrument_type in ['bond_futures', 'fx_forwards', 'forwards', 'futures', 'commodity_futures',
                               'call_options', 'etfs', 'funds',
                               'index_futures', 'index_options', 'put_options', 'tbills', 'warrants']:
            # M
            expiration_event = instrument_object['event_schedules'][0]

            expiration_event['effective_date'] = maturity
            expiration_event['final_date'] = maturity


def set_accruals_for_instrument(instrument_object, data_object, instrument_type_obj):
    # instrument_type = data_object['instrument_type']

    instrument_type = instrument_type_obj.user_code.lower()

    if instrument_type in ['bonds']:

        if len(instrument_object['accrual_calculation_schedules']):
            accrual = instrument_object['accrual_calculation_schedules'][0]

            accrual['effective_date'] = data_object['first_coupon_date']
            accrual['accrual_end_date'] = data_object['maturity']
            # accrual['accrual_size'] = data_object['accrual_size']
            # accrual['periodicity'] = data_object['periodicity']
            # accrual['periodicity_n'] = data_object['periodicity_n']



# Global method for create instrument object from Instrument Type Defaults
def handler_instrument_object(source_data, instrument_type, master_user, ecosystem_default, attribute_types):
    object_data = {}
    # object_data = source_data.copy()

    object_data['instrument_type'] = instrument_type.id

    set_defaults_from_instrument_type(object_data, instrument_type, ecosystem_default)

    _l.info("Settings defaults for instrument done")

    try:

        # TODO remove, when finmars.database.com will be deployed
        if isinstance(source_data['pricing_currency'], str):

            object_data['pricing_currency'] = Currency.objects.get(master_user=master_user,
                                                                   user_code=source_data['pricing_currency']).id
        else:

            object_data['pricing_currency'] = Currency.objects.get(master_user=master_user,
                                                                   user_code=source_data['pricing_currency']['code']).id

    except Exception as e:

        object_data['pricing_currency'] = ecosystem_default.currency.id

    # try:
    #     object_data['accrued_currency'] = Currency.objects.get(master_user=master_user,
    #                                                            user_code=source_data['accrued_currency']).id
    # except Exception as e:
    #
    #     object_data['accrued_currency'] = ecosystem_default.currency.id

    object_data['public_name'] = source_data['name']
    object_data['user_code'] = source_data['user_code']
    object_data['name'] = source_data['name']
    object_data['short_name'] = source_data['short_name']

    object_data['accrued_currency'] = object_data['pricing_currency']
    object_data['co_directional_exposure_currency'] = object_data['pricing_currency']
    object_data['counter_directional_exposure_currency'] = object_data['pricing_currency']

    try:
        object_data['payment_size_detail'] = PaymentSizeDetail.objects.get(
            user_code=source_data['payment_size_detail']).id
    except Exception as e:

        object_data['payment_size_detail'] = ecosystem_default.payment_size_detail.id

    # try:
    #     object_data['pricing_condition'] = PricingCondition.objects.get(
    #         user_code=source_data['pricing_condition']).id
    # except Exception as e:
    #
    #     object_data['pricing_condition'] = ecosystem_default.pricing_condition.id

    if 'maturity_price' in source_data:
        try:
            object_data['maturity_price'] = float(source_data['maturity_price'])
        except Exception as e:
            _l.warn("Could not set maturity price")

    if 'maturity' in source_data and source_data['maturity'] != '':
        object_data['maturity_date'] = source_data['maturity']

    elif 'maturity_date' in source_data and source_data['maturity_date'] != '':

        if source_data['maturity_date'] == 'null' or source_data['maturity_date'] == '9999-00-00':
            object_data['maturity_date'] = '2999-01-01'
        else:
            object_data['maturity_date'] = source_data['maturity_date']
    else:
        object_data['maturity_date'] = '2999-01-01'

    try:
        if 'country' in source_data:

            country = Country.objects.get(alpha_2=source_data['country']['code'])

            object_data['country'] = country.id

    except Exception as e:
        _l.error("Could not set country")

    try:
        if 'sector' in source_data:

            sector_attribute = GenericAttributeType.objects.get(user_code='sector')

            attribute = {}
            exist = False

            for attribute in object_data['attributes']:
                if attribute['attribute_type'] == sector_attribute.id:
                    exist = True
                    attribute['value_string'] = source_data['sector']

            if not exist:

                attribute['attribute_type'] = sector_attribute.id
                attribute['value_string'] = source_data['sector']

                object_data['attributes'].append(attribute)


    except Exception as e:
        _l.error("Could not set sector")

    # object_data['attributes'] = []

    _l.info("Settings attributes for instrument done attribute_types %s " % attribute_types)

    _tmp_attributes_dict = {}

    for item in object_data['attributes']:
        _tmp_attributes_dict[item['attribute_type']] = item

    try:
        if 'attributes' in source_data:

            for attribute_type in attribute_types:

                lower_user_code = attribute_type.user_code.lower()

                for key, value in source_data['attributes'].items():

                    _l_key = key.lower()

                    if _l_key == lower_user_code:

                        attribute = {
                            'attribute_type': attribute_type.id,
                        }

                        if attribute_type.value_type == 10:
                            attribute['value_string'] = value

                        if attribute_type.value_type == 20:
                            attribute['value_float'] = value

                        if attribute_type.value_type == 30:

                            try:

                                classifier = GenericClassifier.objects.get(attribute_type=attribute_type,
                                                                           name=value)

                                attribute['classifier'] = classifier.id

                            except Exception as e:
                                attribute['classifier'] = None

                        if attribute_type.value_type == 40:
                            attribute['value_date'] = value

                        _tmp_attributes_dict[attribute['attribute_type']] = attribute
    except Exception as e:
        _l.error("Could not set attributes from finmars database. Error %s"  % e )
        _l.error("Could not set attributes from finmars database. Traceback %s"  % traceback.format_exc())


    object_data['attributes'] = []

    _l.info('_tmp_attributes_dict %s' % _tmp_attributes_dict)

    for key, value in _tmp_attributes_dict.items():
        object_data['attributes'].append(value)

    _l.info("Settings attributes for instrument done object_data %s " % object_data)

    object_data['master_user'] = master_user.id
    object_data['manual_pricing_formulas'] = []
    # object_data['accrual_calculation_schedules'] = []
    # object_data['event_schedules'] = []
    object_data['factor_schedules'] = []

    set_events_for_instrument(object_data, source_data, instrument_type)
    _l.info("Settings events for instrument done")

    # _l.info('source_data %s' % source_data)

    if 'accrual_calculation_schedules' in source_data:
        if source_data['accrual_calculation_schedules']:
            if len(source_data['accrual_calculation_schedules']):

                if len(object_data['event_schedules']):
                    # C
                    coupon_event = object_data['event_schedules'][0]

                    if 'first_payment_date' in source_data['accrual_calculation_schedules'][0]:
                        coupon_event['effective_date'] = source_data['accrual_calculation_schedules'][0][
                            'first_payment_date']

    accrual_map = {
        'Actual/Actual (ICMA)': AccrualCalculationModel.ACT_ACT,
        'Actual/Actual (ISDA)': AccrualCalculationModel.ACT_ACT_ISDA,
        'Actual/360': AccrualCalculationModel.ACT_360,
        'Actual/364': AccrualCalculationModel.ACT_365,
        'Actual/365 (Actual/365F)': AccrualCalculationModel.ACT_365,
        'Actual/366': AccrualCalculationModel.ACT_365_366,
        'Actual/365L': AccrualCalculationModel.ACT_365_366,
        'Actual/365A': AccrualCalculationModel.ACT_1_365,
        '30/360 US': AccrualCalculationModel.C_30_360,
        '30E+/360': AccrualCalculationModel.C_30E_P_360,
        'NL/365': AccrualCalculationModel.NL_365,
        'BD/252': AccrualCalculationModel.BUS_DAYS_252,
        '30E/360': AccrualCalculationModel.GERMAN_30_360_EOM,
        '30/360 (30/360 ISDA)': AccrualCalculationModel.GERMAN_30_360_EOM,
        '30/360 German': AccrualCalculationModel.GERMAN_30_360_NO_EOM,
    }

    if 'accrual_calculation_schedules' in source_data:

        if source_data['accrual_calculation_schedules']:

            if len(source_data['accrual_calculation_schedules']):

                _l.info("Setting up accrual schedules. Init")

                if len(object_data['accrual_calculation_schedules']):

                    _l.info("Setting up accrual schedules. Overwrite Existing")

                    accrual = object_data['accrual_calculation_schedules'][0]

                    if 'day_count_convention' in source_data:

                        if source_data['day_count_convention'] in accrual_map:

                            accrual['accrual_calculation_model'] = accrual_map[source_data['day_count_convention']]

                        else:
                            accrual['accrual_calculation_model'] = AccrualCalculationModel.DEFAULT

                    if 'accrual_start_date' in source_data['accrual_calculation_schedules'][0]:
                        accrual['accrual_start_date'] = source_data['accrual_calculation_schedules'][0][
                            'accrual_start_date']

                    if 'first_payment_date' in source_data['accrual_calculation_schedules'][0]:
                        accrual['first_payment_date'] = source_data['accrual_calculation_schedules'][0][
                            'first_payment_date']

                    try:
                        accrual['accrual_size'] = float(source_data['accrual_calculation_schedules'][0]['accrual_size'])
                    except Exception as e:
                        accrual['accrual_size'] = 0

                    try:
                        accrual['periodicity_n'] = int(source_data['accrual_calculation_schedules'][0]['periodicity_n'])

                        if accrual['periodicity_n'] == 1:
                            accrual['periodicity'] = Periodicity.ANNUALLY

                        if accrual['periodicity_n'] == 2:
                            accrual['periodicity'] = Periodicity.SEMI_ANNUALLY

                        if accrual['periodicity_n'] == 4:
                            accrual['periodicity'] = Periodicity.QUARTERLY

                        if accrual['periodicity_n'] == 6:
                            accrual['periodicity'] = Periodicity.BIMONTHLY

                        if accrual['periodicity_n'] == 12:
                            accrual['periodicity'] = Periodicity.MONTHLY

                        _l.info('periodicity %s' % accrual['periodicity'])

                        accrual['periodicity_n'] = 0

                    except Exception as e:
                        accrual['periodicity_n'] = 0

                else:

                    _l.info("Setting up accrual schedules. Creating new")

                    accrual = {}

                    accrual['accrual_calculation_model'] = AccrualCalculationModel.ACT_365
                    accrual['periodicity'] = Periodicity.ANNUALLY

                    if 'accrual_start_date' in source_data['accrual_calculation_schedules'][0]:
                        accrual['accrual_start_date'] = source_data['accrual_calculation_schedules'][0][
                            'accrual_start_date']

                    if 'first_payment_date' in source_data['accrual_calculation_schedules'][0]:
                        accrual['first_payment_date'] = source_data['accrual_calculation_schedules'][0][
                            'first_payment_date']

                    try:
                        accrual['accrual_size'] = float(source_data['accrual_calculation_schedules'][0]['accrual_size'])
                    except Exception as e:
                        accrual['accrual_size'] = 0

                    try:
                        accrual['periodicity_n'] = int(source_data['accrual_calculation_schedules'][0]['periodicity_n'])

                        if accrual['periodicity_n'] == 1:
                            accrual['periodicity'] = Periodicity.ANNUALLY

                        if accrual['periodicity_n'] == 2:
                            accrual['periodicity'] = Periodicity.SEMI_ANNUALLY

                        if accrual['periodicity_n'] == 4:
                            accrual['periodicity'] = Periodicity.QUARTERLY

                        if accrual['periodicity_n'] == 6:
                            accrual['periodicity'] = Periodicity.BIMONTHLY

                        if accrual['periodicity_n'] == 12:
                            accrual['periodicity'] = Periodicity.MONTHLY

                        _l.info('periodicity %s' % accrual['periodicity'])

                    except Exception as e:
                        accrual['periodicity_n'] = 0

                    object_data['accrual_calculation_schedules'].append(accrual)
    else:
        set_accruals_for_instrument(object_data, source_data, instrument_type)

    if 'name' not in object_data and 'user_code' in object_data:
        object_data['name'] = object_data['user_code']

    if 'short_name' not in object_data and 'user_code' in object_data:
        object_data['short_name'] = object_data['user_code']

    return object_data
