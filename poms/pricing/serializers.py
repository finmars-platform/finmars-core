from rest_framework import serializers

from poms.common import formula
from poms.common.fields import ExpressionField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.common.serializers import ModelWithUserCodeSerializer, ModelWithTimeStampSerializer
from poms.currencies.models import CurrencyHistory
from poms.instruments.fields import InstrumentField, PricingPolicyField
from poms.instruments.models import PricingPolicy, PriceHistory
from poms.pricing.models import InstrumentPricingScheme, InstrumentPricingSchemeType, CurrencyPricingSchemeType, \
    InstrumentPricingSchemeManualPricingParameters, CurrencyPricingSchemeManualPricingParameters, \
    InstrumentPricingSchemeSingleParameterFormulaParameters, CurrencyPricingSchemeSingleParameterFormulaParameters, \
    CurrencyPricingScheme, PricingProcedure, InstrumentPricingSchemeMultipleParametersFormulaParameters, \
    CurrencyPricingSchemeMultipleParametersFormulaParameters, InstrumentPricingSchemeBloombergParameters, \
    CurrencyPricingSchemeBloombergParameters, CurrencyPricingPolicy, InstrumentTypePricingPolicy, \
    InstrumentPricingPolicy, InstrumentPricingSchemeWtradeParameters, \
    PriceHistoryError, CurrencyHistoryError, PricingProcedureInstance, CurrencyPricingSchemeFixerParameters, \
    PricingParentProcedureInstance, InstrumentPricingSchemeAlphavParameters
from poms.users.fields import MasterUserField


class InstrumentPricingSchemeManualPricingParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstrumentPricingSchemeManualPricingParameters
        fields = ('id', 'instrument_pricing_scheme', 'default_value', 'attribute_key')


class CurrencyPricingSchemeManualPricingParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyPricingSchemeManualPricingParameters
        fields = ('id', 'currency_pricing_scheme', 'default_value', 'attribute_key')


class InstrumentPricingSchemeSingleParameterFormulaParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstrumentPricingSchemeSingleParameterFormulaParameters
        fields = ('id', 'instrument_pricing_scheme', 'expr', 'default_value', 'attribute_key', 'value_type',
                  'pricing_error_text_expr',
                  'accrual_calculation_method', 'accrual_expr', 'accrual_error_text_expr')


class CurrencyPricingSchemeSingleParameterFormulaParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyPricingSchemeSingleParameterFormulaParameters
        fields = (
            'id', 'currency_pricing_scheme', 'expr', 'default_value', 'attribute_key', 'value_type', 'error_text_expr')


class InstrumentPricingSchemeMultipleParametersFormulaParametersSerializer(serializers.ModelSerializer):
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = InstrumentPricingSchemeMultipleParametersFormulaParameters
        fields = ('id', 'instrument_pricing_scheme', 'expr', 'data', 'default_value', 'attribute_key', 'value_type',
                  'pricing_error_text_expr',
                  'accrual_calculation_method', 'accrual_expr', 'accrual_error_text_expr')


class CurrencyPricingSchemeMultipleParametersFormulaParametersSerializer(serializers.ModelSerializer):
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = CurrencyPricingSchemeMultipleParametersFormulaParameters
        fields = ('id', 'currency_pricing_scheme', 'expr', 'data', 'default_value', 'attribute_key', 'value_type',
                  'error_text_expr')


class InstrumentPricingSchemeBloombergParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstrumentPricingSchemeBloombergParameters
        fields = ('id', 'instrument_pricing_scheme', 'expr', 'default_value', 'attribute_key', 'value_type',
                  'pricing_error_text_expr',
                  'accrual_calculation_method', 'accrual_expr', 'accrual_error_text_expr',
                  'bid_historical', 'bid_yesterday',
                  'ask_historical', 'ask_yesterday',
                  'last_historical', 'last_yesterday',
                  'accrual_historical', 'accrual_yesterday',
                  )


class CurrencyPricingSchemeBloombergParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyPricingSchemeBloombergParameters
        fields = ('id', 'currency_pricing_scheme', 'expr', 'default_value', 'attribute_key', 'value_type', 'fx_rate',
                  'error_text_expr')


class InstrumentPricingSchemeWtradeParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstrumentPricingSchemeWtradeParameters
        fields = ('id', 'instrument_pricing_scheme', 'expr', 'default_value', 'attribute_key', 'value_type',
                  'accrual_calculation_method', 'accrual_expr', 'accrual_error_text_expr',
                  'pricing_error_text_expr')


class CurrencyPricingSchemeFixerParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyPricingSchemeFixerParameters
        fields = ('id', 'currency_pricing_scheme', 'expr', 'default_value', 'attribute_key', 'value_type', 'error_text_expr')


class InstrumentPricingSchemeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstrumentPricingSchemeType
        fields = ('id', 'name', 'notes', 'input_type')


class InstrumentPricingSchemeSerializer(ModelWithTimeStampSerializer):
    master_user = MasterUserField()

    type_settings = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super(InstrumentPricingSchemeSerializer, self).__init__(*args, **kwargs)

        self.fields['type_object'] = InstrumentPricingSchemeTypeSerializer(source='type', read_only=True)

    class Meta:
        model = InstrumentPricingScheme
        fields = (
            'id', 'name', 'user_code', 'master_user', 'notes', 'notes_for_users', 'notes_for_parameter', 'error_handler', 'type',
            'type_settings')

    def get_type_settings(self, instance):

        result = {}

        if instance.type_id:

            if instance.type_id == 2:  # manual pricing scheme

                try:

                    parameters = InstrumentPricingSchemeManualPricingParameters.objects.get(
                        instrument_pricing_scheme=instance.id)

                    result = InstrumentPricingSchemeManualPricingParametersSerializer(instance=parameters).data

                except InstrumentPricingSchemeManualPricingParameters.DoesNotExist:
                    pass

            if instance.type_id == 3:  # single parameter formula

                try:

                    parameters = InstrumentPricingSchemeSingleParameterFormulaParameters.objects.get(
                        instrument_pricing_scheme=instance.id)

                    result = InstrumentPricingSchemeSingleParameterFormulaParametersSerializer(
                        instance=parameters).data

                except InstrumentPricingSchemeSingleParameterFormulaParameters.DoesNotExist:
                    pass

            if instance.type_id == 4:  # multiple parameters formula

                try:

                    parameters = InstrumentPricingSchemeMultipleParametersFormulaParameters.objects.get(
                        instrument_pricing_scheme=instance.id)

                    result = InstrumentPricingSchemeMultipleParametersFormulaParametersSerializer(
                        instance=parameters).data

                except InstrumentPricingSchemeMultipleParametersFormulaParameters.DoesNotExist:
                    pass

            if instance.type_id == 5:  # bloomberg

                try:

                    parameters = InstrumentPricingSchemeBloombergParameters.objects.get(
                        instrument_pricing_scheme=instance.id)

                    result = InstrumentPricingSchemeBloombergParametersSerializer(
                        instance=parameters).data

                except InstrumentPricingSchemeBloombergParameters.DoesNotExist:
                    pass

            if instance.type_id == 6:  # wtrade

                try:

                    parameters = InstrumentPricingSchemeWtradeParameters.objects.get(
                        instrument_pricing_scheme=instance.id)

                    result = InstrumentPricingSchemeWtradeParametersSerializer(
                        instance=parameters).data

                except InstrumentPricingSchemeWtradeParameters.DoesNotExist:
                    pass

            if instance.type_id == 7:  # alphav

                try:

                    parameters = InstrumentPricingSchemeAlphavParameters.objects.get(
                        instrument_pricing_scheme=instance.id)

                    result = InstrumentPricingSchemeWtradeParametersSerializer(
                        instance=parameters).data

                except InstrumentPricingSchemeWtradeParameters.DoesNotExist:
                    pass



        return result

    def set_type_settings(self, instance, type_settings):

        if instance.type_id and type_settings:

            if instance.type_id == 2:  # manual pricing scheme

                try:
                    manual_formula = InstrumentPricingSchemeManualPricingParameters.objects.get(
                        instrument_pricing_scheme_id=instance.id)

                except InstrumentPricingSchemeManualPricingParameters.DoesNotExist:

                    manual_formula = InstrumentPricingSchemeManualPricingParameters(
                        instrument_pricing_scheme_id=instance.id)

                if 'default_value' in type_settings:
                    manual_formula.default_value = type_settings['default_value']
                else:
                    manual_formula.default_value = None

                if 'attribute_key' in type_settings:
                    manual_formula.attribute_key = type_settings['attribute_key']
                else:
                    manual_formula.attribute_key = None

                manual_formula.save()

            if instance.type_id == 3:  # single parameter formula

                try:
                    single_parameter_formula = InstrumentPricingSchemeSingleParameterFormulaParameters.objects.get(
                        instrument_pricing_scheme_id=instance.id)

                except InstrumentPricingSchemeSingleParameterFormulaParameters.DoesNotExist:

                    single_parameter_formula = InstrumentPricingSchemeSingleParameterFormulaParameters(
                        instrument_pricing_scheme_id=instance.id)

                if 'default_value' in type_settings:
                    single_parameter_formula.default_value = type_settings['default_value']
                else:
                    single_parameter_formula.default_value = None

                if 'attribute_key' in type_settings:
                    single_parameter_formula.attribute_key = type_settings['attribute_key']
                else:
                    single_parameter_formula.attribute_key = None

                if 'value_type' in type_settings:
                    single_parameter_formula.value_type = type_settings['value_type']
                else:
                    single_parameter_formula.value_type = None

                if 'expr' in type_settings:
                    single_parameter_formula.expr = type_settings['expr']
                else:
                    single_parameter_formula.expr = None

                if 'pricing_error_text_expr' in type_settings:
                    single_parameter_formula.pricing_error_text_expr = type_settings['pricing_error_text_expr']
                else:
                    single_parameter_formula.pricing_error_text_expr = None

                if 'accrual_calculation_method' in type_settings:
                    single_parameter_formula.accrual_calculation_method = type_settings['accrual_calculation_method']
                else:
                    single_parameter_formula.accrual_calculation_method = None

                if 'accrual_expr' in type_settings:
                    single_parameter_formula.accrual_expr = type_settings['accrual_expr']
                else:
                    single_parameter_formula.accrual_expr = None

                if 'accrual_error_text_expr' in type_settings:
                    single_parameter_formula.accrual_error_text_expr = type_settings['accrual_error_text_expr']
                else:
                    single_parameter_formula.accrual_error_text_expr = None

                single_parameter_formula.save()

            if instance.type_id == 4:  # multiple parameters formula

                try:
                    multiple_parameters_formula = InstrumentPricingSchemeMultipleParametersFormulaParameters.objects.get(
                        instrument_pricing_scheme_id=instance.id)

                except InstrumentPricingSchemeMultipleParametersFormulaParameters.DoesNotExist:

                    multiple_parameters_formula = InstrumentPricingSchemeMultipleParametersFormulaParameters(
                        instrument_pricing_scheme_id=instance.id)

                if 'default_value' in type_settings:
                    multiple_parameters_formula.default_value = type_settings['default_value']
                else:
                    multiple_parameters_formula.default_value = None

                if 'attribute_key' in type_settings:
                    multiple_parameters_formula.attribute_key = type_settings['attribute_key']
                else:
                    multiple_parameters_formula.attribute_key = None

                if 'value_type' in type_settings:
                    multiple_parameters_formula.value_type = type_settings['value_type']
                else:
                    multiple_parameters_formula.value_type = None

                if 'expr' in type_settings:
                    multiple_parameters_formula.expr = type_settings['expr']
                else:
                    multiple_parameters_formula.expr = None

                if 'pricing_error_text_expr' in type_settings:
                    multiple_parameters_formula.pricing_error_text_expr = type_settings['pricing_error_text_expr']
                else:
                    multiple_parameters_formula.pricing_error_text_expr = None

                if 'accrual_calculation_method' in type_settings:
                    multiple_parameters_formula.accrual_calculation_method = type_settings['accrual_calculation_method']
                else:
                    multiple_parameters_formula.accrual_calculation_method = None

                if 'accrual_expr' in type_settings:
                    multiple_parameters_formula.accrual_expr = type_settings['accrual_expr']
                else:
                    multiple_parameters_formula.accrual_expr = None

                if 'accrual_error_text_expr' in type_settings:
                    multiple_parameters_formula.accrual_error_text_expr = type_settings['accrual_error_text_expr']
                else:
                    multiple_parameters_formula.accrual_error_text_expr = None

                if 'data' in type_settings:
                    multiple_parameters_formula.data = type_settings['data']
                else:
                    multiple_parameters_formula.data = None

                multiple_parameters_formula.save()

            if instance.type_id == 5:  # multiple parameters formula

                try:
                    bloomberg = InstrumentPricingSchemeBloombergParameters.objects.get(
                        instrument_pricing_scheme_id=instance.id)

                except InstrumentPricingSchemeBloombergParameters.DoesNotExist:

                    bloomberg = InstrumentPricingSchemeBloombergParameters(instrument_pricing_scheme_id=instance.id)

                if 'default_value' in type_settings:
                    bloomberg.default_value = type_settings['default_value']
                else:
                    bloomberg.default_value = None

                if 'attribute_key' in type_settings:
                    bloomberg.attribute_key = type_settings['attribute_key']
                else:
                    bloomberg.attribute_key = None

                if 'value_type' in type_settings:
                    bloomberg.value_type = type_settings['value_type']
                else:
                    bloomberg.value_type = None

                if 'expr' in type_settings:
                    bloomberg.expr = type_settings['expr']
                else:
                    bloomberg.expr = None

                if 'pricing_error_text_expr' in type_settings:
                    bloomberg.pricing_error_text_expr = type_settings['pricing_error_text_expr']
                else:
                    bloomberg.pricing_error_text_expr = None

                if 'accrual_calculation_method' in type_settings:
                    bloomberg.accrual_calculation_method = type_settings['accrual_calculation_method']
                else:
                    bloomberg.accrual_calculation_method = None

                if 'accrual_expr' in type_settings:
                    bloomberg.accrual_expr = type_settings['accrual_expr']
                else:
                    bloomberg.accrual_expr = None

                if 'accrual_error_text_expr' in type_settings:
                    bloomberg.accrual_error_text_expr = type_settings['accrual_error_text_expr']
                else:
                    bloomberg.accrual_error_text_expr = None

                if 'bid_historical' in type_settings:
                    bloomberg.bid_historical = type_settings['bid_historical']
                else:
                    bloomberg.bid_historical = None

                if 'bid_yesterday' in type_settings:
                    bloomberg.bid_yesterday = type_settings['bid_yesterday']
                else:
                    bloomberg.bid_yesterday = None

                if 'ask_historical' in type_settings:
                    bloomberg.ask_historical = type_settings['ask_historical']
                else:
                    bloomberg.ask_historical = None

                if 'ask_yesterday' in type_settings:
                    bloomberg.ask_yesterday = type_settings['ask_yesterday']
                else:
                    bloomberg.ask_yesterday = None

                if 'last_historical' in type_settings:
                    bloomberg.last_historical = type_settings['last_historical']
                else:
                    bloomberg.last_historical = None

                if 'last_yesterday' in type_settings:
                    bloomberg.last_yesterday = type_settings['last_yesterday']
                else:
                    bloomberg.last_yesterday = None

                if 'accrual_historical' in type_settings:
                    bloomberg.accrual_historical = type_settings['accrual_historical']
                else:
                    bloomberg.accrual_historical = None

                if 'accrual_yesterday' in type_settings:
                    bloomberg.accrual_yesterday = type_settings['accrual_yesterday']
                else:
                    bloomberg.accrual_yesterday = None

                bloomberg.save()

            if instance.type_id == 6:  # wtrade

                try:
                    wtrade = InstrumentPricingSchemeWtradeParameters.objects.get(
                        instrument_pricing_scheme_id=instance.id)

                except InstrumentPricingSchemeWtradeParameters.DoesNotExist:

                    wtrade = InstrumentPricingSchemeWtradeParameters(instrument_pricing_scheme_id=instance.id)

                if 'default_value' in type_settings:
                    wtrade.default_value = type_settings['default_value']
                else:
                    wtrade.default_value = None

                if 'attribute_key' in type_settings:
                    wtrade.attribute_key = type_settings['attribute_key']
                else:
                    wtrade.attribute_key = None

                if 'value_type' in type_settings:
                    wtrade.value_type = type_settings['value_type']
                else:
                    wtrade.value_type = None

                if 'expr' in type_settings:
                    wtrade.expr = type_settings['expr']
                else:
                    wtrade.expr = None

                if 'pricing_error_text_expr' in type_settings:
                    wtrade.pricing_error_text_expr = type_settings['pricing_error_text_expr']
                else:
                    wtrade.pricing_error_text_expr = None

                if 'accrual_calculation_method' in type_settings:
                    wtrade.accrual_calculation_method = type_settings['accrual_calculation_method']
                else:
                    wtrade.accrual_calculation_method = None

                if 'accrual_expr' in type_settings:
                    wtrade.accrual_expr = type_settings['accrual_expr']
                else:
                    wtrade.accrual_expr = None

                if 'accrual_error_text_expr' in type_settings:
                    wtrade.accrual_error_text_expr = type_settings['accrual_error_text_expr']
                else:
                    wtrade.accrual_error_text_expr = None


                wtrade.save()

            if instance.type_id == 7:  # alphav

                try:
                    parameters = InstrumentPricingSchemeAlphavParameters.objects.get(
                        instrument_pricing_scheme_id=instance.id)

                except InstrumentPricingSchemeAlphavParameters.DoesNotExist:

                    parameters = InstrumentPricingSchemeAlphavParameters(instrument_pricing_scheme_id=instance.id)

                if 'default_value' in type_settings:
                    parameters.default_value = type_settings['default_value']
                else:
                    parameters.default_value = None

                if 'attribute_key' in type_settings:
                    parameters.attribute_key = type_settings['attribute_key']
                else:
                    parameters.attribute_key = None

                if 'value_type' in type_settings:
                    parameters.value_type = type_settings['value_type']
                else:
                    parameters.value_type = None

                if 'expr' in type_settings:
                    parameters.expr = type_settings['expr']
                else:
                    parameters.expr = None

                if 'pricing_error_text_expr' in type_settings:
                    parameters.pricing_error_text_expr = type_settings['pricing_error_text_expr']
                else:
                    parameters.pricing_error_text_expr = None

                if 'accrual_calculation_method' in type_settings:
                    parameters.accrual_calculation_method = type_settings['accrual_calculation_method']
                else:
                    parameters.accrual_calculation_method = None

                if 'accrual_expr' in type_settings:
                    parameters.accrual_expr = type_settings['accrual_expr']
                else:
                    parameters.accrual_expr = None

                if 'accrual_error_text_expr' in type_settings:
                    parameters.accrual_error_text_expr = type_settings['accrual_error_text_expr']
                else:
                    parameters.accrual_error_text_expr = None

                parameters.save()

    def to_internal_value(self, data):

        type_settings = data.pop('type_settings', None)

        ret = super(InstrumentPricingSchemeSerializer, self).to_internal_value(data)

        # Special thing to ignore type_settings type check
        ret['type_settings'] = type_settings

        return ret

    def create(self, validated_data):

        type_settings = validated_data.pop('type_settings', None)

        instance = super(InstrumentPricingSchemeSerializer, self).create(validated_data)

        self.set_type_settings(instance, type_settings)

        return instance

    def update(self, instance, validated_data):

        type_settings = validated_data.pop('type_settings', None)

        print('update type_settings %s' % type_settings)

        instance = super(InstrumentPricingSchemeSerializer, self).update(instance, validated_data)

        self.set_type_settings(instance, type_settings)

        return instance


class CurrencyPricingSchemeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyPricingSchemeType
        fields = ('id', 'name', 'notes', 'input_type')


class CurrencyPricingSchemeSerializer(ModelWithTimeStampSerializer):
    master_user = MasterUserField()

    type_settings = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super(CurrencyPricingSchemeSerializer, self).__init__(*args, **kwargs)

        self.fields['type_object'] = CurrencyPricingSchemeTypeSerializer(source='type', read_only=True)

    class Meta:
        model = CurrencyPricingScheme
        fields = (
            'id', 'name', 'user_code', 'master_user', 'notes', 'notes_for_users', 'notes_for_parameter', 'error_handler', 'type',
            'type_settings')

    def get_type_settings(self, instance):

        result = {}

        if instance.type_id:

            if instance.type_id == 2:  # manual pricing scheme

                try:

                    manual_formula = CurrencyPricingSchemeManualPricingParameters.objects.get(
                        currency_pricing_scheme=instance.id)

                    result = CurrencyPricingSchemeManualPricingParametersSerializer(instance=manual_formula).data

                except CurrencyPricingSchemeManualPricingParameters.DoesNotExist:
                    pass

            if instance.type_id == 3:  # single parameter formula

                try:

                    single_parameter_formula = CurrencyPricingSchemeSingleParameterFormulaParameters.objects.get(
                        currency_pricing_scheme=instance.id)

                    result = CurrencyPricingSchemeSingleParameterFormulaParametersSerializer(
                        instance=single_parameter_formula).data

                except CurrencyPricingSchemeManualPricingParameters.DoesNotExist:
                    pass

            if instance.type_id == 4:  # multiple parameters formula

                try:

                    multiple_parameters_formula = CurrencyPricingSchemeMultipleParametersFormulaParameters.objects.get(
                        currency_pricing_scheme=instance.id)

                    result = CurrencyPricingSchemeMultipleParametersFormulaParametersSerializer(
                        instance=multiple_parameters_formula).data

                except CurrencyPricingSchemeMultipleParametersFormulaParameters.DoesNotExist:
                    pass

            if instance.type_id == 5:  # bloomberg

                try:

                    multiple_parameters_formula = CurrencyPricingSchemeBloombergParameters.objects.get(
                        currency_pricing_scheme=instance.id)

                    result = CurrencyPricingSchemeBloombergParametersSerializer(
                        instance=multiple_parameters_formula).data

                except CurrencyPricingSchemeBloombergParameters.DoesNotExist:
                    pass

            # if instance.type_id == 6:  # wtrade
            #
            #     try:
            #
            #         multiple_parameters_formula = CurrencyPricingSchemeWtradeParameters.objects.get(
            #             currency_pricing_scheme=instance.id)
            #
            #         result = CurrencyPricingSchemeWtradeParametersSerializer(
            #             instance=multiple_parameters_formula).data
            #
            #     except CurrencyPricingSchemeWtradeParameters.DoesNotExist:
            #         pass

            if instance.type_id == 7:  # fixer

                try:

                    multiple_parameters_formula = CurrencyPricingSchemeFixerParameters.objects.get(
                        currency_pricing_scheme=instance.id)

                    result = CurrencyPricingSchemeFixerParametersSerializer(
                        instance=multiple_parameters_formula).data

                except CurrencyPricingSchemeFixerParameters.DoesNotExist:
                    pass

        return result

    def to_internal_value(self, data):

        type_settings = data.pop('type_settings', None)

        ret = super(CurrencyPricingSchemeSerializer, self).to_internal_value(data)

        # Special thing to ignore type_settings type check
        ret['type_settings'] = type_settings

        return ret

    def set_type_settings(self, instance, type_settings):

        if instance.type_id and type_settings:

            # if instance.type_id == 2:  # manual pricing scheme
            #
            #     try:
            #         manual_formula = CurrencyPricingSchemeManualPricingParameters.objects.get(
            #             currency_pricing_scheme_id=instance.id)
            #
            #     except CurrencyPricingSchemeManualPricingParameters.DoesNotExist:
            #
            #         manual_formula = CurrencyPricingSchemeManualPricingParameters(
            #             currency_pricing_scheme_id=instance.id)
            #
            #     if 'default_value' in type_settings:
            #         manual_formula.default_value = type_settings['default_value']
            #     else:
            #         manual_formula.default_value = None
            #
            #     if 'attribute_key' in type_settings:
            #         manual_formula.attribute_key = type_settings['attribute_key']
            #     else:
            #         manual_formula.attribute_key = None
            #
            #     print('manual_formula %s' % manual_formula)
            #
            #     manual_formula.save()

            if instance.type_id == 3:  # single parameter formula

                try:
                    single_parameter_formula = CurrencyPricingSchemeSingleParameterFormulaParameters.objects.get(
                        currency_pricing_scheme_id=instance.id)

                except CurrencyPricingSchemeSingleParameterFormulaParameters.DoesNotExist:

                    single_parameter_formula = CurrencyPricingSchemeSingleParameterFormulaParameters(
                        currency_pricing_scheme_id=instance.id)

                if 'default_value' in type_settings:
                    single_parameter_formula.default_value = type_settings['default_value']
                else:
                    single_parameter_formula.default_value = None

                if 'attribute_key' in type_settings:
                    single_parameter_formula.attribute_key = type_settings['attribute_key']
                else:
                    single_parameter_formula.attribute_key = None

                if 'value_type' in type_settings:
                    single_parameter_formula.value_type = type_settings['value_type']
                else:
                    single_parameter_formula.value_type = None

                if 'expr' in type_settings:
                    single_parameter_formula.expr = type_settings['expr']
                else:
                    single_parameter_formula.expr = None

                single_parameter_formula.save()

            if instance.type_id == 4:  # multiple parameters formula

                try:
                    multiple_parameters_formula = CurrencyPricingSchemeMultipleParametersFormulaParameters.objects.get(
                        currency_pricing_scheme_id=instance.id)

                except CurrencyPricingSchemeMultipleParametersFormulaParameters.DoesNotExist:

                    multiple_parameters_formula = CurrencyPricingSchemeMultipleParametersFormulaParameters(
                        currency_pricing_scheme_id=instance.id)

                if 'default_value' in type_settings:
                    multiple_parameters_formula.default_value = type_settings['default_value']
                else:
                    multiple_parameters_formula.default_value = None

                if 'attribute_key' in type_settings:
                    multiple_parameters_formula.attribute_key = type_settings['attribute_key']
                else:
                    multiple_parameters_formula.attribute_key = None

                if 'value_type' in type_settings:
                    multiple_parameters_formula.value_type = type_settings['value_type']
                else:
                    multiple_parameters_formula.value_type = None

                if 'expr' in type_settings:
                    multiple_parameters_formula.expr = type_settings['expr']
                else:
                    multiple_parameters_formula.expr = None

                if 'data' in type_settings:
                    multiple_parameters_formula.data = type_settings['data']
                else:
                    multiple_parameters_formula.data = None

                multiple_parameters_formula.save()

            if instance.type_id == 5:  # multiple parameters formula

                try:
                    bloomberg = CurrencyPricingSchemeBloombergParameters.objects.get(
                        currency_pricing_scheme_id=instance.id)

                except CurrencyPricingSchemeBloombergParameters.DoesNotExist:

                    bloomberg = CurrencyPricingSchemeBloombergParameters(currency_pricing_scheme_id=instance.id)

                if 'default_value' in type_settings:
                    bloomberg.default_value = type_settings['default_value']
                else:
                    bloomberg.default_value = None

                if 'attribute_key' in type_settings:
                    bloomberg.attribute_key = type_settings['attribute_key']
                else:
                    bloomberg.attribute_key = None

                if 'value_type' in type_settings:
                    bloomberg.value_type = type_settings['value_type']
                else:
                    bloomberg.value_type = None

                if 'fx_rate' in type_settings:
                    bloomberg.fx_rate = type_settings['fx_rate']
                else:
                    bloomberg.fx_rate = None

                if 'expr' in type_settings:
                    bloomberg.expr = type_settings['expr']
                else:
                    bloomberg.expr = None

                bloomberg.save()

            # if instance.type_id == 6:  # wtrade
            #
            #     try:
            #         wtrade = CurrencyPricingSchemeWtradeParameters.objects.get(
            #             currency_pricing_scheme_id=instance.id)
            #
            #     except CurrencyPricingSchemeWtradeParameters.DoesNotExist:
            #
            #         wtrade = CurrencyPricingSchemeWtradeParameters(currency_pricing_scheme_id=instance.id)
            #
            #     if 'default_value' in type_settings:
            #         wtrade.default_value = type_settings['default_value']
            #     else:
            #         wtrade.default_value = None
            #
            #     if 'attribute_key' in type_settings:
            #         wtrade.attribute_key = type_settings['attribute_key']
            #     else:
            #         wtrade.attribute_key = None
            #
            #     if 'value_type' in type_settings:
            #         wtrade.value_type = type_settings['value_type']
            #     else:
            #         wtrade.value_type = None
            #
            #     if 'expr' in type_settings:
            #         wtrade.expr = type_settings['expr']
            #     else:
            #         wtrade.expr = None
            #
            #     wtrade.save()

            if instance.type_id == 7:  # fixer

                try:
                    fixer = CurrencyPricingSchemeFixerParameters.objects.get(
                        currency_pricing_scheme_id=instance.id)

                except CurrencyPricingSchemeFixerParameters.DoesNotExist:

                    fixer = CurrencyPricingSchemeFixerParameters(currency_pricing_scheme_id=instance.id)

                if 'default_value' in type_settings:
                    fixer.default_value = type_settings['default_value']
                else:
                    fixer.default_value = None

                if 'attribute_key' in type_settings:
                    fixer.attribute_key = type_settings['attribute_key']
                else:
                    fixer.attribute_key = None

                if 'value_type' in type_settings:
                    fixer.value_type = type_settings['value_type']
                else:
                    fixer.value_type = None

                if 'expr' in type_settings:
                    fixer.expr = type_settings['expr']
                else:
                    fixer.expr = None

                if 'error_text_expr' in type_settings:
                    fixer.error_text_expr = type_settings['error_text_expr']
                else:
                    fixer.error_text_expr = None

                fixer.save()

    def create(self, validated_data):

        type_settings = validated_data.pop('type_settings', None)

        instance = super(CurrencyPricingSchemeSerializer, self).create(validated_data)

        self.set_type_settings(instance, type_settings)

        return instance

    def update(self, instance, validated_data):

        type_settings = validated_data.pop('type_settings', None)

        instance = super(CurrencyPricingSchemeSerializer, self).update(instance, validated_data)

        self.set_type_settings(instance, type_settings)

        return instance


class PricingProcedureSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    price_date_from_expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_null=True,
                                           allow_blank=True, default='')
    price_date_to_expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_null=True,
                                         allow_blank=True, default='')

    class Meta:
        model = PricingProcedure
        fields = ('master_user', 'id', 'name', 'notes', 'notes_for_users',
                  'user_code', 'type',

                  'price_date_from', 'price_date_to',
                  'price_date_from_expr', 'price_date_to_expr',

                  'price_fill_days',

                  'price_get_principal_prices', 'price_get_accrued_prices', 'price_get_fx_rates',
                  'price_overwrite_principal_prices', 'price_overwrite_accrued_prices', 'price_overwrite_fx_rates',

                  'instrument_filters',
                  'currency_filters',

                  'pricing_policy_filters',
                  'portfolio_filters',
                  'instrument_type_filters',
                  'instrument_pricing_scheme_filters',
                  'instrument_pricing_condition_filters',
                  'currency_pricing_scheme_filters',
                  'currency_pricing_condition_filters',

                  )

    def to_representation(self, instance):
        data = super(PricingProcedureSerializer, self).to_representation(instance)

        if data['price_date_from_expr']:

            try:
                data['price_date_from_calculated'] = formula.safe_eval(data['price_date_from_expr'], names={})
            except formula.InvalidExpression as e:
                data['price_date_from_calculated'] = 'Invalid Expression'
        else:
            data['price_date_from_calculated'] = data['price_date_from']

        if data['price_date_to_expr']:

            try:
                data['price_date_to_calculated'] = formula.safe_eval(data['price_date_to_expr'], names={})
            except formula.InvalidExpression as e:
                data['price_date_to_calculated'] = 'Invalid Expression'
        else:
            data['price_date_to_calculated'] = data['price_date_to']

        return data


class PricingProcedureInstanceSerializer(serializers.ModelSerializer):

    pricing_procedure_object = PricingProcedureSerializer(source='pricing_procedure', read_only=True)

    class Meta:
        model = PricingProcedureInstance
        fields = ('master_user', 'id', 'parent_procedure_instance',
                  'created', 'modified',
                  'status',
                  'pricing_procedure', 'pricing_procedure_object',
                  'provider_verbose', 'action_verbose')


class PricingParentProcedureInstanceSerializer(serializers.ModelSerializer):

    pricing_procedure_object = PricingProcedureSerializer(source='pricing_procedure', read_only=True)

    procedures = PricingProcedureInstanceSerializer(many=True, read_only=True)

    class Meta:
        model = PricingParentProcedureInstance
        fields = ('master_user', 'id', 'created', 'modified', 'pricing_procedure', 'pricing_procedure_object', 'procedures')


class PricingPolicyViewSerializer(ModelWithUserCodeSerializer):
    class Meta:
        model = PricingPolicy
        fields = ['id', 'user_code', 'name', 'short_name', 'notes', 'expr']


class CurrencyPricingPolicySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, allow_null=True, required=False)
    data = serializers.JSONField(allow_null=True, required=False)

    def __init__(self, *args, **kwargs):
        super(CurrencyPricingPolicySerializer, self).__init__(*args, **kwargs)

        self.fields['pricing_policy_object'] = PricingPolicyViewSerializer(source='pricing_policy', read_only=True)
        self.fields['pricing_scheme_object'] = CurrencyPricingSchemeSerializer(source='pricing_scheme', read_only=True)

    class Meta:
        model = CurrencyPricingPolicy
        fields = (
            'id', 'pricing_policy', 'pricing_scheme', 'notes', 'default_value', 'attribute_key', 'data')


class InstrumentTypePricingPolicySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, allow_null=True, required=False)
    data = serializers.JSONField(allow_null=True, required=False)

    def __init__(self, *args, **kwargs):
        super(InstrumentTypePricingPolicySerializer, self).__init__(*args, **kwargs)

        self.fields['pricing_policy_object'] = PricingPolicyViewSerializer(source='pricing_policy', read_only=True)
        self.fields['pricing_scheme_object'] = InstrumentPricingSchemeSerializer(source='pricing_scheme',
                                                                                 read_only=True)

    class Meta:
        model = InstrumentTypePricingPolicy
        fields = (
            'id', 'pricing_policy', 'pricing_scheme', 'notes', 'default_value', 'attribute_key', 'data', 'overwrite_default_parameters')


class InstrumentPricingPolicySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, allow_null=True, required=False)
    data = serializers.JSONField(allow_null=True, required=False)

    def __init__(self, *args, **kwargs):
        super(InstrumentPricingPolicySerializer, self).__init__(*args, **kwargs)

        self.fields['pricing_policy_object'] = PricingPolicyViewSerializer(source='pricing_policy', read_only=True)

        self.fields['pricing_scheme_object'] = InstrumentPricingSchemeSerializer(source='pricing_scheme',
                                                                                 read_only=True)

    class Meta:
        model = InstrumentPricingPolicy
        fields = ('id', 'pricing_policy', 'pricing_scheme', 'notes', 'default_value', 'attribute_key', 'data')


class RunProcedureSerializer(serializers.Serializer):
    def __init__(self, **kwargs):
        kwargs['context'] = context = kwargs.get('context', {}) or {}
        super(RunProcedureSerializer, self).__init__(**kwargs)
        context['instance'] = self.instance

        self.fields['procedure'] = serializers.PrimaryKeyRelatedField(read_only=True)


class BrokerBloombergSerializer(serializers.Serializer):

    def __init__(self, **kwargs):
        pass


class PriceHistoryErrorSerializer(serializers.ModelSerializer):

    pricing_scheme_object = InstrumentPricingSchemeSerializer(source='pricing_scheme', read_only=True)
    procedure_instance_object = PricingProcedureInstanceSerializer(source='procedure_instance', read_only=True)

    def __init__(self, *args, **kwargs):
        super(PriceHistoryErrorSerializer, self).__init__(*args, **kwargs)

        from poms.instruments.serializers import InstrumentViewSerializer
        from poms.instruments.serializers import PricingPolicySerializer

        self.fields['instrument_object'] = InstrumentViewSerializer(source='instrument', read_only=True)
        self.fields['pricing_policy_object'] = PricingPolicySerializer(source='pricing_policy', read_only=True)

    class Meta:
        model = PriceHistoryError
        fields = ('id', 'master_user', 'instrument', 'pricing_policy', 'pricing_scheme', 'date', 'principal_price',
                  'accrued_price', 'price_error_text', 'accrual_error_text', 'procedure_instance',

                  'status',

                  'pricing_scheme_object',
                  'procedure_instance_object'

                  )

    def update(self, instance, validated_data):

        instance = super(PriceHistoryErrorSerializer, self).update(instance, validated_data)

        try:
            price_history = PriceHistory.objects.get(instrument=instance.instrument, pricing_policy=instance.pricing_policy, date=instance.date)
        except PriceHistory.DoesNotExist:
            price_history = PriceHistory(instrument=instance.instrument, pricing_policy=instance.pricing_policy, date=instance.date)

        price_history.principal_price = instance.principal_price
        price_history.accrued_price = instance.accrued_price

        price_history.save()

        instance.delete()

        return instance


class CurrencyHistoryErrorSerializer(serializers.ModelSerializer):

    pricing_scheme_object = CurrencyPricingSchemeSerializer(source='pricing_scheme', read_only=True)
    procedure_instance_object = PricingProcedureInstanceSerializer(source='procedure_instance', read_only=True)

    def __init__(self, *args, **kwargs):
        super(CurrencyHistoryErrorSerializer, self).__init__(*args, **kwargs)

        from poms.instruments.serializers import PricingPolicySerializer
        from poms.currencies.serializers import CurrencyViewSerializer

        self.fields['currency_object'] = CurrencyViewSerializer(source='currency', read_only=True)
        self.fields['pricing_policy_object'] = PricingPolicySerializer(source='pricing_policy', read_only=True)



    class Meta:
        model = CurrencyHistoryError
        fields = ('id', 'master_user', 'currency', 'pricing_policy', 'pricing_scheme', 'date', 'fx_rate', 'error_text',
                  'procedure_instance',

                  'status',

                  'pricing_scheme_object',
                  'procedure_instance_object',

                  )

    def update(self, instance, validated_data):

        instance = super(CurrencyHistoryErrorSerializer, self).update(instance, validated_data)

        try:
            currency_history = CurrencyHistory.objects.get(currency=instance.currency, pricing_policy=instance.pricing_policy, date=instance.date)
        except CurrencyHistory.DoesNotExist:
            currency_history = CurrencyHistory(currency=instance.currency, pricing_policy=instance.pricing_policy, date=instance.date)

        currency_history.fx_rate = instance.fx_rate

        currency_history.save()

        instance.delete()

        return instance
