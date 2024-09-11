from rest_framework import serializers

from poms.common.serializers import ModelWithUserCodeSerializer, ModelWithTimeStampSerializer, ModelMetaSerializer
from poms.currencies.models import CurrencyHistory
from poms.instruments.models import PricingPolicy, PriceHistory
from poms.pricing.models import PriceHistoryError, CurrencyHistoryError


class RunPricingSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    pricing_policies = serializers.ListField(child=serializers.CharField(), required=False)
    instrument_types = serializers.ListField(child=serializers.CharField(), required=False)
    instruments = serializers.ListField(child=serializers.CharField(), required=False)
    currencies = serializers.ListField(child=serializers.CharField(), required=False)

    def validate(self, data):
        if not data.get('instrument_types') and not data.get('instruments') and not data.get('currencies'):
            raise serializers.ValidationError('Either "instrument_types", "instruments" or "currencies" must be provided.')
        return data


class PriceHistoryErrorSerializer(serializers.ModelSerializer):

    modified_at = serializers.DateTimeField(read_only=True, allow_null=False)
    created_at = serializers.DateTimeField(read_only=True, allow_null=False)

    def __init__(self, *args, **kwargs):
        super(PriceHistoryErrorSerializer, self).__init__(*args, **kwargs)

        from poms.instruments.serializers import InstrumentLightSerializer
        from poms.instruments.serializers import PricingPolicyLightSerializer

        self.fields['instrument_object'] = InstrumentLightSerializer(source='instrument', read_only=True)
        self.fields['pricing_policy_object'] = PricingPolicyLightSerializer(source='pricing_policy', read_only=True)

    class Meta:
        model = PriceHistoryError
        fields = ('id', 'master_user', 'instrument', 'pricing_policy', 'date', 'principal_price',
                  'accrued_price', 'error_text', 'price_error_text', 'accrual_error_text',

                  'status',

                  'modified_at', 'created_at',

                  )

    def update(self, instance, validated_data):

        instance = super(PriceHistoryErrorSerializer, self).update(instance, validated_data)

        try:
            price_history = PriceHistory.objects.get(instrument=instance.instrument,
                                                     pricing_policy=instance.pricing_policy, date=instance.date)
        except PriceHistory.DoesNotExist:
            price_history = PriceHistory(instrument=instance.instrument, pricing_policy=instance.pricing_policy,
                                         date=instance.date)

        price_history.principal_price = instance.principal_price
        price_history.accrued_price = instance.accrued_price

        price_history.save()

        instance.delete()

        return instance


class CurrencyHistoryErrorSerializer(serializers.ModelSerializer):

    modified_at = serializers.DateTimeField(read_only=True, allow_null=False)
    created_at = serializers.DateTimeField(read_only=True, allow_null=False)

    def __init__(self, *args, **kwargs):
        super(CurrencyHistoryErrorSerializer, self).__init__(*args, **kwargs)

        from poms.instruments.serializers import PricingPolicyLightSerializer
        from poms.currencies.serializers import CurrencyViewSerializer

        self.fields['currency_object'] = CurrencyViewSerializer(source='currency', read_only=True)
        self.fields['pricing_policy_object'] = PricingPolicyLightSerializer(source='pricing_policy', read_only=True)

    class Meta:
        model = CurrencyHistoryError
        fields = ('id', 'master_user', 'currency', 'pricing_policy',  'date', 'fx_rate', 'error_text',

                  'status',

                  'modified_at',
                  'created_at',

                  )

    def update(self, instance, validated_data):

        instance = super(CurrencyHistoryErrorSerializer, self).update(instance, validated_data)

        try:
            currency_history = CurrencyHistory.objects.get(currency=instance.currency,
                                                           pricing_policy=instance.pricing_policy, date=instance.date)
        except CurrencyHistory.DoesNotExist:
            currency_history = CurrencyHistory(currency=instance.currency, pricing_policy=instance.pricing_policy,
                                               date=instance.date)

        currency_history.fx_rate = instance.fx_rate

        currency_history.save()

        instance.delete()

        return instance
