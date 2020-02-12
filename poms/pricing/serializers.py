from rest_framework import serializers

from poms.common.serializers import ModelWithUserCodeSerializer
from poms.instruments.models import PricingPolicy
from poms.pricing.models import InstrumentPricingScheme, InstrumentPricingSchemeType, CurrencyPricingSchemeType, \
    InstrumentPricingSchemeManualPricingParameters, CurrencyPricingSchemeManualPricingParameters, \
    InstrumentPricingSchemeSingleParameterFormulaParameters, CurrencyPricingSchemeSingleParameterFormulaParameters, \
    CurrencyPricingScheme, PricingProcedure, InstrumentPricingSchemeMultipleParametersFormulaParameters, \
    CurrencyPricingSchemeMultipleParametersFormulaParameters, InstrumentPricingSchemeBloombergParameters, \
    CurrencyPricingSchemeBloombergParameters, CurrencyPricingPolicy, InstrumentTypePricingPolicy, \
    InstrumentPricingPolicy
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
        fields = ('id', 'instrument_pricing_scheme', 'expr', 'default_value', 'attribute_key', 'value_type')


class CurrencyPricingSchemeSingleParameterFormulaParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyPricingSchemeSingleParameterFormulaParameters
        fields = ('id', 'currency_pricing_scheme', 'expr', 'default_value', 'attribute_key', 'value_type')


class InstrumentPricingSchemeMultipleParametersFormulaParametersSerializer(serializers.ModelSerializer):

    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = InstrumentPricingSchemeMultipleParametersFormulaParameters
        fields = ('id', 'instrument_pricing_scheme', 'expr', 'data')


class CurrencyPricingSchemeMultipleParametersFormulaParametersSerializer(serializers.ModelSerializer):

    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = CurrencyPricingSchemeMultipleParametersFormulaParameters
        fields = ('id', 'currency_pricing_scheme', 'expr', 'data')


class InstrumentPricingSchemeBloombergParametersSerializer(serializers.ModelSerializer):

    class Meta:
        model = InstrumentPricingSchemeBloombergParameters
        fields = ('id', 'instrument_pricing_scheme', 'expr', 'default_value', 'attribute_key', 'value_type',
                  'bid0', 'bid1', 'bid0_multiplier', 'bid1_multiplier',
                  'ask0', 'ask1', 'ask0_multiplier', 'ask1_multiplier',
                  'last0', 'last1', 'last0_multiplier', 'last1_multiplier')


class CurrencyPricingSchemeBloombergParametersSerializer(serializers.ModelSerializer):

    class Meta:
        model = CurrencyPricingSchemeBloombergParameters
        fields = ('id', 'currency_pricing_scheme', 'expr', 'default_value', 'attribute_key', 'value_type', 'fxrate', 'fxrate_multiplier')



class InstrumentPricingSchemeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstrumentPricingSchemeType
        fields = ('id', 'name', 'notes', 'input_type')


class InstrumentPricingSchemeSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    type_settings = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super(InstrumentPricingSchemeSerializer, self).__init__(*args, **kwargs)

        self.fields['type_object'] = InstrumentPricingSchemeTypeSerializer(source='type', read_only=True)

    class Meta:
        model = InstrumentPricingScheme
        fields = ('id', 'name', 'master_user', 'notes', 'notes_for_users', 'notes_for_parameter', 'error_handler', 'type', 'type_settings')

    def get_type_settings(self, instance):

        result = {}

        if instance.type_id:

            if instance.type_id == 2:  # manual pricing scheme

                try:

                    manual_formula = InstrumentPricingSchemeManualPricingParameters.objects.get(instrument_pricing_scheme=instance.id)

                    result = InstrumentPricingSchemeManualPricingParametersSerializer(instance=manual_formula).data

                except InstrumentPricingSchemeManualPricingParameters.DoesNotExist:
                    pass

            if instance.type_id == 3:  # single parameter formula

                try:

                    single_parameter_formula = InstrumentPricingSchemeSingleParameterFormulaParameters.objects.get(instrument_pricing_scheme=instance.id)

                    result = InstrumentPricingSchemeSingleParameterFormulaParametersSerializer(instance=single_parameter_formula).data

                except InstrumentPricingSchemeSingleParameterFormulaParameters.DoesNotExist:
                    pass

            if instance.type_id == 4:  # multiple parameters formula

                try:

                    multiple_parameters_formula = InstrumentPricingSchemeMultipleParametersFormulaParameters.objects.get(instrument_pricing_scheme=instance.id)

                    result = InstrumentPricingSchemeMultipleParametersFormulaParametersSerializer(instance=multiple_parameters_formula).data

                except InstrumentPricingSchemeMultipleParametersFormulaParameters.DoesNotExist:
                    pass

            if instance.type_id == 5:  # bloomberg

                try:

                    multiple_parameters_formula = InstrumentPricingSchemeBloombergParameters.objects.get(instrument_pricing_scheme=instance.id)

                    result = InstrumentPricingSchemeBloombergParametersSerializer(instance=multiple_parameters_formula).data

                except InstrumentPricingSchemeBloombergParameters.DoesNotExist:
                    pass

        return result


    def to_internal_value(self, data):

        type_settings = data.pop('type_settings', None)

        ret = super(InstrumentPricingSchemeSerializer, self).to_internal_value(data)

        # Special thing to ignore type_settings type check
        ret['type_settings'] = type_settings

        return ret


    def set_type_settings(self, instance, type_settings):

        if instance.type_id and type_settings:

            if instance.type_id == 2:  # manual pricing scheme

                try:
                    manual_formula = InstrumentPricingSchemeManualPricingParameters.objects.get(instrument_pricing_scheme_id=instance.id)

                except InstrumentPricingSchemeManualPricingParameters.DoesNotExist:

                    manual_formula = InstrumentPricingSchemeManualPricingParameters(instrument_pricing_scheme_id=instance.id)

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
                    single_parameter_formula = InstrumentPricingSchemeSingleParameterFormulaParameters.objects.get(instrument_pricing_scheme_id=instance.id)

                except InstrumentPricingSchemeSingleParameterFormulaParameters.DoesNotExist:

                    single_parameter_formula = InstrumentPricingSchemeSingleParameterFormulaParameters(instrument_pricing_scheme_id=instance.id)

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
                    multiple_parameters_formula = InstrumentPricingSchemeMultipleParametersFormulaParameters.objects.get(instrument_pricing_scheme_id=instance.id)

                except InstrumentPricingSchemeMultipleParametersFormulaParameters.DoesNotExist:

                    multiple_parameters_formula = InstrumentPricingSchemeMultipleParametersFormulaParameters(instrument_pricing_scheme_id=instance.id)

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
                    bloomberg = InstrumentPricingSchemeBloombergParameters.objects.get(instrument_pricing_scheme_id=instance.id)

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

                if 'bid0' in type_settings:
                    bloomberg.bid0 = type_settings['bid0']
                else:
                    bloomberg.bid0 = None

                if 'bid1' in type_settings:
                    bloomberg.bid1 = type_settings['bid1']
                else:
                    bloomberg.bid1 = None

                if 'bid0_multiplier' in type_settings:
                    bloomberg.bid0_multiplier = type_settings['bid0_multiplier']
                else:
                    bloomberg.bid0_multiplier = None

                if 'bid1_multiplier' in type_settings:
                    bloomberg.bid1_multiplier = type_settings['bid1_multiplier']
                else:
                    bloomberg.bid1_multiplier = None

                if 'ask0' in type_settings:
                    bloomberg.ask0 = type_settings['ask0']
                else:
                    bloomberg.ask0 = None

                if 'ask1' in type_settings:
                    bloomberg.ask1 = type_settings['ask1']
                else:
                    bloomberg.ask1 = None

                if 'ask0_multiplier' in type_settings:
                    bloomberg.ask0_multiplier = type_settings['ask0_multiplier']
                else:
                    bloomberg.ask0_multiplier = None

                if 'ask1_multiplier' in type_settings:
                    bloomberg.ask1_multiplier = type_settings['ask1_multiplier']
                else:
                    bloomberg.ask1_multiplier = None

                if 'last0' in type_settings:
                    bloomberg.last0 = type_settings['last0']
                else:
                    bloomberg.last0 = None

                if 'last1' in type_settings:
                    bloomberg.last1 = type_settings['last1']
                else:
                    bloomberg.last1 = None

                if 'last0_multiplier' in type_settings:
                    bloomberg.last0_multiplier = type_settings['last0_multiplier']
                else:
                    bloomberg.last0_multiplier = None

                if 'last1_multiplier' in type_settings:
                    bloomberg.last1_multiplier = type_settings['last1_multiplier']
                else:
                    bloomberg.last1_multiplier = None

                bloomberg.save()

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


class CurrencyPricingSchemeSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    type_settings =  serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super(CurrencyPricingSchemeSerializer, self).__init__(*args, **kwargs)

        self.fields['type_object'] = CurrencyPricingSchemeTypeSerializer(source='type', read_only=True)

    class Meta:
        model = CurrencyPricingScheme
        fields = ('id', 'name', 'master_user', 'notes', 'notes_for_users', 'notes_for_parameter', 'error_handler', 'type', 'type_settings')

    def get_type_settings(self, instance):

        result = {}

        if instance.type_id:

            if instance.type_id == 2:  # manual pricing scheme

                try:

                    manual_formula = CurrencyPricingSchemeManualPricingParameters.objects.get(currency_pricing_scheme=instance.id)

                    result = CurrencyPricingSchemeManualPricingParametersSerializer(instance=manual_formula).data

                except CurrencyPricingSchemeManualPricingParameters.DoesNotExist:
                    pass

            if instance.type_id == 3:  # single parameter formula

                try:

                    single_parameter_formula = CurrencyPricingSchemeSingleParameterFormulaParameters.objects.get(currency_pricing_scheme=instance.id)

                    result = CurrencyPricingSchemeSingleParameterFormulaParametersSerializer(instance=single_parameter_formula).data

                except CurrencyPricingSchemeManualPricingParameters.DoesNotExist:
                    pass

            if instance.type_id == 4:  # multiple parameters formula

                try:

                    multiple_parameters_formula = CurrencyPricingSchemeMultipleParametersFormulaParameters.objects.get(currency_pricing_scheme=instance.id)

                    result = CurrencyPricingSchemeMultipleParametersFormulaParametersSerializer(instance=multiple_parameters_formula).data

                except CurrencyPricingSchemeMultipleParametersFormulaParameters.DoesNotExist:
                    pass

            if instance.type_id == 5:  # bloomberg

                try:

                    multiple_parameters_formula = CurrencyPricingSchemeBloombergParameters.objects.get(currency_pricing_scheme=instance.id)

                    result = CurrencyPricingSchemeBloombergParametersSerializer(instance=multiple_parameters_formula).data

                except CurrencyPricingSchemeBloombergParameters.DoesNotExist:
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

            if instance.type_id == 2:  # manual pricing scheme

                try:
                    manual_formula = CurrencyPricingSchemeManualPricingParameters.objects.get(currency_pricing_scheme_id=instance.id)

                except CurrencyPricingSchemeManualPricingParameters.DoesNotExist:

                    manual_formula = CurrencyPricingSchemeManualPricingParameters(currency_pricing_scheme_id=instance.id)

                if 'default_value' in type_settings:
                    manual_formula.default_value = type_settings['default_value']
                else:
                    manual_formula.default_value = None

                if 'attribute_key' in type_settings:
                    manual_formula.attribute_key = type_settings['attribute_key']
                else:
                    manual_formula.attribute_key = None

                print('manual_formula %s' % manual_formula)

                manual_formula.save()

            if instance.type_id == 3:  # single parameter formula

                try:
                    single_parameter_formula = CurrencyPricingSchemeSingleParameterFormulaParameters.objects.get(currency_pricing_scheme_id=instance.id)

                except CurrencyPricingSchemeSingleParameterFormulaParameters.DoesNotExist:

                    single_parameter_formula = CurrencyPricingSchemeSingleParameterFormulaParameters(currency_pricing_scheme_id=instance.id)

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
                    multiple_parameters_formula = CurrencyPricingSchemeMultipleParametersFormulaParameters.objects.get(currency_pricing_scheme_id=instance.id)

                except CurrencyPricingSchemeMultipleParametersFormulaParameters.DoesNotExist:

                    multiple_parameters_formula = CurrencyPricingSchemeMultipleParametersFormulaParameters(currency_pricing_scheme_id=instance.id)

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
                    bloomberg = CurrencyPricingSchemeBloombergParameters.objects.get(currency_pricing_scheme_id=instance.id)

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

                if 'fxrate' in type_settings:
                    bloomberg.fxrate = type_settings['fxrate']
                else:
                    bloomberg.fxrate = None

                if 'fxrate_multiplier' in type_settings:
                    bloomberg.fxrate_multiplier = type_settings['fxrate_multiplier']
                else:
                    bloomberg.fxrate_multiplier = None

                if 'expr' in type_settings:
                    bloomberg.expr = type_settings['expr']
                else:
                    bloomberg.expr = None

                bloomberg.save()

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

    class Meta:
        model = PricingProcedure
        fields = ('master_user', 'id', 'name', 'notes', 'notes_for_users',
                  'price_date_from', 'price_date_to', 'price_balance_date', 'price_fill_days', 'price_override_existed',
                  'accrual_date_from', 'accrual_date_to')


class PricingPolicyViewSerializer(ModelWithUserCodeSerializer):
    class Meta:
        model = PricingPolicy
        fields = ['id', 'user_code', 'name', 'short_name', 'notes', 'expr']


class CurrencyPricingPolicySerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=False)
    data = serializers.JSONField(allow_null=True)

    def __init__(self, *args, **kwargs):
        super(CurrencyPricingPolicySerializer, self).__init__(*args, **kwargs)

        self.fields['pricing_policy_object'] = PricingPolicyViewSerializer(source='pricing_policy', read_only=True)
        self.fields['pricing_scheme_object'] = CurrencyPricingSchemeSerializer(source='pricing_scheme', read_only=True)

    class Meta:
        model = CurrencyPricingPolicy
        fields = ('id', 'currency', 'pricing_policy', 'pricing_scheme', 'notes', 'default_value', 'attribute_key', 'data')


class InstrumentTypePricingPolicySerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=False)
    data = serializers.JSONField(allow_null=True)

    def __init__(self, *args, **kwargs):
        super(InstrumentTypePricingPolicySerializer, self).__init__(*args, **kwargs)


        self.fields['pricing_policy_object'] = PricingPolicyViewSerializer(source='pricing_policy', read_only=True)
        self.fields['pricing_scheme_object'] = InstrumentPricingSchemeSerializer(source='pricing_scheme', read_only=True)

    class Meta:
        model = InstrumentTypePricingPolicy
        fields = ('id', 'instrument_type', 'pricing_policy', 'pricing_scheme', 'notes', 'default_value', 'attribute_key', 'data')


class InstrumentPricingPolicySerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=False)
    data = serializers.JSONField(allow_null=True)

    def __init__(self, *args, **kwargs):
        super(InstrumentPricingPolicySerializer, self).__init__(*args, **kwargs)


        self.fields['pricing_policy_object'] = PricingPolicyViewSerializer(source='pricing_policy', read_only=True)

        self.fields['pricing_scheme_object'] = InstrumentPricingSchemeSerializer(source='pricing_scheme', read_only=True)

    class Meta:
        model = InstrumentPricingPolicy
        fields = ('id', 'instrument', 'pricing_policy', 'pricing_scheme', 'notes', 'default_value', 'attribute_key', 'data')


class RunProcedureSerializer(serializers.Serializer):
    def __init__(self, **kwargs):

        kwargs['context'] = context = kwargs.get('context', {}) or {}
        super(RunProcedureSerializer, self).__init__(**kwargs)
        context['instance'] = self.instance

        self.fields['procedure'] = serializers.PrimaryKeyRelatedField(read_only=True)


class BrokerBloombergSerializer(serializers.Serializer):

    def __init__(self, **kwargs):

        pass
