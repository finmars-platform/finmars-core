from __future__ import unicode_literals

from django.utils.timezone import now
from rest_framework import serializers
from rest_framework.fields import ReadOnlyField

from poms.common.fields import FloatEvalField
from poms.common.serializers import ModelWithUserCodeSerializer, ModelWithTimeStampSerializer
from poms.currencies.fields import CurrencyField
from poms.currencies.models import Currency, CurrencyHistory
from poms.instruments.fields import PricingPolicyField
from poms.instruments.models import PricingPolicy
from poms.obj_attrs.serializers import ModelWithAttributesSerializer, ModelWithAttributesOnlySerializer
from poms.obj_perms.serializers import ModelWithObjectPermissionSerializer
from poms.pricing.models import CurrencyPricingPolicy, CurrencyHistoryError
from poms.pricing.serializers import CurrencyPricingPolicySerializer
from poms.system_messages.handlers import send_system_message
from poms.users.fields import MasterUserField
from poms.users.utils import get_member_from_context, get_master_user_from_context


def set_currency_pricing_scheme_parameters(pricing_policy, parameters):
    # print('pricing_policy %s ' % pricing_policy)
    # print('parameters %s ' % parameters)

    if parameters:

        if hasattr(parameters, 'data'):
            pricing_policy.data = parameters.data

        if hasattr(parameters, 'default_value'):
            pricing_policy.default_value = parameters.default_value

        if hasattr(parameters, 'attribute_key'):
            pricing_policy.attribute_key = parameters.attribute_key


class CurrencySerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer,
                         ModelWithAttributesSerializer, ModelWithTimeStampSerializer):
    master_user = MasterUserField()

    pricing_policies = CurrencyPricingPolicySerializer(allow_null=True, many=True, required=False)

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Currency
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'notes',
            'reference_for_pricing',
            'pricing_condition',
            'default_fx_rate',
            'is_default', 'is_deleted', 'is_enabled',
            'pricing_policies'
        ]

    def __init__(self, *args, **kwargs):
        super(CurrencySerializer, self).__init__(*args, **kwargs)

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

        policies = PricingPolicy.objects.filter(master_user=instance.master_user)

        ids = set()

        # print("creating default policies")

        for policy in policies:

            try:

                o = CurrencyPricingPolicy.objects.get(currency=instance, pricing_policy=policy)

            except CurrencyPricingPolicy.DoesNotExist:

                o = CurrencyPricingPolicy(currency=instance, pricing_policy=policy)

                # print('policy.default_instrument_pricing_scheme %s' % policy.default_currency_pricing_scheme)

                if policy.default_currency_pricing_scheme:
                    o.pricing_scheme = policy.default_currency_pricing_scheme

                    parameters = policy.default_currency_pricing_scheme.get_parameters()
                    set_currency_pricing_scheme_parameters(o, parameters)

                # print('o.pricing_scheme %s' % o.pricing_scheme)

                o.save()

                ids.add(o.id)

        # print("update existing policies %s " % len(pricing_policies))

        if pricing_policies:

            for item in pricing_policies:

                print('item %s' % item)

                try:

                    oid = item.get('id', None)

                    ids.add(oid)

                    o = CurrencyPricingPolicy.objects.get(currency_id=instance.id, id=oid)

                    o.pricing_scheme = item['pricing_scheme']
                    o.default_value = item['default_value']
                    o.attribute_key = item['attribute_key']

                    if 'data' in item:
                        o.data = item['data']
                    else:
                        o.data = None

                    o.notes = item['notes']

                    o.save()

                except CurrencyPricingPolicy.DoesNotExist as e:

                    try:

                        # print("Id is not Provided. Trying to lookup.")
                        #
                        # print('instance id %s' % instance)
                        # print('pricing scheme %s' % item['pricing_scheme'])

                        o = CurrencyPricingPolicy.objects.get(currency_id=instance.id,
                                                              pricing_policy=item['pricing_policy']
                                                              )

                        o.pricing_scheme = item['pricing_scheme']
                        o.default_value = item['default_value']
                        o.attribute_key = item['attribute_key']

                        if 'data' in item:
                            o.data = item['data']
                        else:
                            o.data = None

                        o.notes = item['notes']

                        o.save()

                        ids.add(o.id)

                    except Exception as e:

                        print("Can't Find  Pricing Policy %s" % e)

        # print('ids %s' % ids)

        if len(ids):
            CurrencyPricingPolicy.objects.filter(currency=instance).exclude(id__in=ids).delete()


class CurrencyEvSerializer(ModelWithObjectPermissionSerializer, ModelWithAttributesOnlySerializer,
                           ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Currency
        fields = [
            'id', 'master_user',
            'user_code', 'name', 'short_name', 'notes',
            'is_default', 'is_deleted', 'is_enabled',

            'reference_for_pricing', 'default_fx_rate',
            'pricing_condition'
        ]


class CurrencyLightSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Currency
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name',
            'is_default', 'is_deleted', 'is_enabled',
        ]


class CurrencyViewSerializer(ModelWithUserCodeSerializer):
    # url = serializers.HyperlinkedIdentityField(view_name='currency-detail')

    class Meta:
        model = Currency
        fields = [
            'id', 'user_code', 'name', 'short_name',
        ]


class CurrencyHistorySerializer(ModelWithTimeStampSerializer):
    # url = serializers.HyperlinkedIdentityField(view_name='currencyhistory-detail')
    currency = CurrencyField()
    currency_object = CurrencyViewSerializer(source='currency', read_only=True)
    pricing_policy = PricingPolicyField(allow_null=False)
    pricing_policy_object = serializers.PrimaryKeyRelatedField(source='pricing_policy', read_only=True)
    fx_rate = FloatEvalField()

    procedure_modified_datetime = ReadOnlyField()

    class Meta:
        model = CurrencyHistory
        fields = [
            'id', 'currency', 'currency_object', 'pricing_policy', 'pricing_policy_object', 'date', 'fx_rate',
            'procedure_modified_datetime'
        ]

    def __init__(self, *args, **kwargs):
        super(CurrencyHistorySerializer, self).__init__(*args, **kwargs)
        # if 'request' not in self.context:
        #     self.fields.pop('url')

        from poms.instruments.serializers import PricingPolicyViewSerializer
        self.fields['pricing_policy_object'] = PricingPolicyViewSerializer(source='pricing_policy', read_only=True)

    def create(self, validated_data):

        instance = super(CurrencyHistorySerializer, self).create(validated_data)

        instance.procedure_modified_datetime = now()
        instance.save()

        # try:
        #
        #     history_item = CurrencyHistoryError.objects.get(currency=instance.currency,
        #                                                     master_user=instance.currency.master_user, date=instance.date,
        #                                                     pricing_policy=instance.pricing_policy)
        #
        #     history_item.status = CurrencyHistoryError.STATUS_OVERWRITTEN
        #
        # except CurrencyHistoryError.DoesNotExist:

        history_item = CurrencyHistoryError()

        history_item.created = now()

        history_item.status = CurrencyHistoryError.STATUS_CREATED

        history_item.master_user = instance.currency.master_user
        history_item.currency = instance.currency
        history_item.fx_rate = instance.fx_rate
        history_item.date = instance.date
        history_item.pricing_policy = instance.pricing_policy
        history_item.created = now()

        history_item.save()

        member = get_member_from_context(self.context)
        master_user = get_master_user_from_context(self.context)

        send_system_message(master_user=master_user,
                            performed_by=member.username,
                            section='prices',
                            type='success',
                            title='New FX rate (manual)',
                            description=instance.currency.user_code + ' ' + str(instance.date) + ' ' + str(
                                instance.fx_rate)
                            )

        return instance

    def update(self, instance, validated_data):

        instance = super(CurrencyHistorySerializer, self).update(instance, validated_data)

        instance.procedure_modified_datetime = now()
        instance.save()

        try:

            history_item = CurrencyHistoryError.objects.get(currency=instance.currency,
                                                            master_user=instance.currency.master_user,
                                                            date=instance.date,
                                                            pricing_policy=instance.pricing_policy)

            history_item.status = CurrencyHistoryError.STATUS_OVERWRITTEN

        except CurrencyHistoryError.DoesNotExist:

            history_item = CurrencyHistoryError()

            history_item.status = CurrencyHistoryError.STATUS_CREATED

            history_item.master_user = instance.currency.master_user
            history_item.currency = instance.currency
            history_item.fx_rate = instance.fx_rate
            history_item.date = instance.date
            history_item.pricing_policy = instance.pricing_policy

        history_item.save()

        member = get_member_from_context(self.context)
        master_user = get_master_user_from_context(self.context)

        send_system_message(master_user=master_user,
                            performed_by=member.username,
                            section='prices',
                            type='warning',
                            title='Edit FX rate (manual)',
                            description=instance.currency.user_code + ' ' + str(instance.date) + ' ' + str(
                                instance.fx_rate)
                            )

        return instance
