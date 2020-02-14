from __future__ import unicode_literals

from rest_framework import serializers

from poms.common.fields import FloatEvalField
from poms.common.serializers import ModelWithUserCodeSerializer
from poms.currencies.fields import CurrencyField
from poms.currencies.models import Currency, CurrencyHistory
from poms.instruments.fields import PricingPolicyField
from poms.integrations.fields import PriceDownloadSchemeField
from poms.obj_attrs.serializers import ModelWithAttributesSerializer
from poms.obj_perms.serializers import ModelWithObjectPermissionSerializer
from poms.pricing.models import CurrencyPricingPolicy
from poms.pricing.serializers import CurrencyPricingPolicySerializer
from poms.tags.serializers import ModelWithTagSerializer
from poms.users.fields import MasterUserField


class CurrencySerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer,
                         ModelWithAttributesSerializer, ModelWithTagSerializer):
    # url = serializers.HyperlinkedIdentityField(view_name='currency-detail')
    master_user = MasterUserField()
    price_download_scheme = PriceDownloadSchemeField(allow_null=True, required=False)

    # daily_pricing_model_object = serializers.PrimaryKeyRelatedField(source='daily_pricing_model', read_only=True)
    # price_download_scheme_object = serializers.PrimaryKeyRelatedField(source='price_download_scheme', read_only=True)

    # tags = TagField(many=True, required=False, allow_null=True)
    # tags_object = TagViewSerializer(source='tags', many=True, read_only=True)

    pricing_policies = CurrencyPricingPolicySerializer(allow_null=True, many=True, required=False)

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Currency
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'notes',
            'reference_for_pricing', 'daily_pricing_model',
            'price_download_scheme', 'default_fx_rate',
            'is_default', 'is_deleted', 'is_enabled',
            'pricing_policies'
            # 'tags', 'tags_object',
            # 'daily_pricing_model_object', 'price_download_scheme_object',
        ]

    def __init__(self, *args, **kwargs):
        super(CurrencySerializer, self).__init__(*args, **kwargs)

        from poms.instruments.serializers import DailyPricingModelSerializer
        from poms.integrations.serializers import PriceDownloadSchemeViewSerializer

        self.fields['daily_pricing_model_object'] = DailyPricingModelSerializer(source='daily_pricing_model',
                                                                                read_only=True)
        self.fields['price_download_scheme_object'] = PriceDownloadSchemeViewSerializer(source='price_download_scheme',
                                                                                        read_only=True)

    def create(self, validated_data):

        pricing_policies = validated_data.pop('pricing_policies', None)

        instance = super(CurrencySerializer, self).create(validated_data)

        self.save_pricing_policies(instance, pricing_policies)

        return instance

    def update(self, instance, validated_data):

        pricing_policies = validated_data.pop('pricing_policies', None)

        instance = super(CurrencySerializer, self).update(instance, validated_data)

        self.save_pricing_policies(instance, pricing_policies)

        return instance

    def save_pricing_policies(self, instance, pricing_policies):

        if pricing_policies:
            for item in pricing_policies:

                try:

                    oid = item.get('id', None)

                    o = CurrencyPricingPolicy.objects.get(currency=instance, id=oid)

                    o.default_value = item['default_value']
                    o.attribute_key = item['attribute_key']
                    o.data = item['data']
                    o.notes = item['notes']

                    o.save()

                except Exception as e:
                    print("Can't Find  Pricing Policy %s" % e)


class CurrencyViewSerializer(ModelWithUserCodeSerializer):
    # url = serializers.HyperlinkedIdentityField(view_name='currency-detail')

    class Meta:
        model = Currency
        fields = [
            'id', 'user_code', 'name', 'short_name', 'notes',
        ]


class CurrencyHistorySerializer(serializers.ModelSerializer):
    # url = serializers.HyperlinkedIdentityField(view_name='currencyhistory-detail')
    currency = CurrencyField()
    currency_object = CurrencyViewSerializer(source='currency', read_only=True)
    pricing_policy = PricingPolicyField(allow_null=False)
    pricing_policy_object = serializers.PrimaryKeyRelatedField(source='pricing_policy', read_only=True)
    fx_rate = FloatEvalField()

    class Meta:
        model = CurrencyHistory
        fields = [
            'id', 'currency', 'currency_object', 'pricing_policy', 'pricing_policy_object', 'date', 'fx_rate'
        ]

    def __init__(self, *args, **kwargs):
        super(CurrencyHistorySerializer, self).__init__(*args, **kwargs)
        # if 'request' not in self.context:
        #     self.fields.pop('url')

        from poms.instruments.serializers import PricingPolicyViewSerializer
        self.fields['pricing_policy_object'] = PricingPolicyViewSerializer(source='pricing_policy', read_only=True)
