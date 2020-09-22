from poms.common.fields import ExpressionField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.common.serializers import ModelWithTimeStampSerializer
from poms.procedures.models import RequestDataFileProcedure, PricingProcedure, PricingProcedureInstance, \
    PricingParentProcedureInstance
from poms.users.fields import MasterUserField
from rest_framework import serializers
from poms.common import formula


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
                  'provider_verbose', 'action_verbose',

                  'successful_prices_count', 'error_prices_count',

                  'error_code', 'error_message'

                  )


class PricingParentProcedureInstanceSerializer(serializers.ModelSerializer):

    pricing_procedure_object = PricingProcedureSerializer(source='pricing_procedure', read_only=True)

    procedures = PricingProcedureInstanceSerializer(many=True, read_only=True)

    class Meta:
        model = PricingParentProcedureInstance
        fields = ('master_user', 'id', 'created', 'modified', 'pricing_procedure', 'pricing_procedure_object', 'procedures')


class RunProcedureSerializer(serializers.Serializer):
    def __init__(self, **kwargs):
        kwargs['context'] = context = kwargs.get('context', {}) or {}
        super(RunProcedureSerializer, self).__init__(**kwargs)
        context['instance'] = self.instance

        self.fields['procedure'] = serializers.PrimaryKeyRelatedField(read_only=True)


class RequestDataFileProcedureSerializer(ModelWithTimeStampSerializer):

    master_user = MasterUserField()

    class Meta:
        model = RequestDataFileProcedure
        fields = [
            'id', 'master_user', 'name', 'user_code', 'notes',
            'provider', 'scheme_name'
        ]


class RunRequestDataFileProcedureSerializer(serializers.Serializer):
    def __init__(self, **kwargs):
        kwargs['context'] = context = kwargs.get('context', {}) or {}
        super(RunRequestDataFileProcedureSerializer, self).__init__(**kwargs)
        context['instance'] = self.instance

        self.fields['procedure'] = serializers.PrimaryKeyRelatedField(read_only=True)
