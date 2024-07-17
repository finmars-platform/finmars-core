from typing import Dict, List

from django.utils.timezone import now
from rest_framework import serializers
from rest_framework.fields import ReadOnlyField

from poms.common.fields import FloatEvalField
from poms.common.serializers import (
    ModelMetaSerializer,
    ModelWithTimeStampSerializer,
    ModelWithUserCodeSerializer,
)
from poms.currencies.fields import CurrencyField
from poms.currencies.models import Currency, CurrencyHistory, CurrencyPricingPolicy
from poms.instruments.fields import PricingPolicyField, CountryField
from poms.instruments.models import PricingPolicy
from poms.obj_attrs.serializers import ModelWithAttributesSerializer
from poms.pricing.models import CurrencyHistoryError
from poms.system_messages.handlers import send_system_message
from poms.users.fields import MasterUserField
from poms.users.utils import get_master_user_from_context, get_member_from_context


def set_currency_pricing_scheme_parameters(pricing_policy, parameters):
    if parameters:
        if hasattr(parameters, "data"):
            pricing_policy.data = parameters.data

        if hasattr(parameters, "default_value"):
            pricing_policy.default_value = parameters.default_value

        if hasattr(parameters, "attribute_key"):
            pricing_policy.attribute_key = parameters.attribute_key


class CurrencySerializer(
    ModelWithUserCodeSerializer,
    ModelWithAttributesSerializer,
    ModelWithTimeStampSerializer,
):
    master_user = MasterUserField()

    class Meta:
        model = Currency
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "notes",
            "reference_for_pricing",
            "pricing_condition",
            "default_fx_rate",
            "is_deleted",
            "is_enabled",
            "pricing_policies",
            "country"
        ]

    def __init__(self, *args, **kwargs):
        from poms.instruments.serializers import CurrencyPricingPolicySerializer

        super().__init__(*args, **kwargs)

        self.fields["pricing_policies"] = CurrencyPricingPolicySerializer(
            allow_null=True, many=True, required=False
        )

        from poms.instruments.serializers import CountrySerializer
        self.fields["country_object"] = CountrySerializer(source="country", read_only=True)

    def create(self, validated_data):

        pricing_policies = validated_data.pop("pricing_policies", None)

        instance = super(CurrencySerializer, self).create(validated_data)

        self.save_pricing_policies(instance, pricing_policies)

        return instance

    def update(self, instance, validated_data):
        pricing_policies = validated_data.pop("pricing_policies", None)

        instance = super(CurrencySerializer, self).update(instance, validated_data)

        self.save_pricing_policies(instance, pricing_policies)

        return instance

    def save_pricing_policies(self, instance, pricing_policies):
        ids = set()
        pricing_policies = pricing_policies or []
        for item in pricing_policies:
            obj, _ = CurrencyPricingPolicy.objects.get_or_create(
                currency=instance,
                pricing_policy_id=item["pricing_policy_id"]
            )
            self._update_and_save_pricing_policies(item, obj)
            ids.add(obj.id)

        to_delete = CurrencyPricingPolicy.objects.filter(currency=instance)
        if len(ids):
            to_delete = to_delete.exclude(id__in=ids)
        to_delete.delete()

    @staticmethod
    def _update_and_save_pricing_policies(item: dict, obj: CurrencyPricingPolicy):
        obj.target_pricing_schema_user_code = item["target_pricing_schema_user_code"]
        if "options" in item:
            obj.options = item["options"]
        obj.save()


class CurrencyLightSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = Currency
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "is_deleted",
            "is_enabled",
        ]

        read_only_fields = fields


class CurrencyViewSerializer(ModelWithUserCodeSerializer):
    class Meta:
        model = Currency
        fields = [
            "id",
            "user_code",
            "name",
            "short_name",
        ]


class CurrencyHistorySerializer(ModelMetaSerializer, ModelWithTimeStampSerializer):
    currency = CurrencyField()
    currency_object = CurrencyViewSerializer(source="currency", read_only=True)
    pricing_policy = PricingPolicyField(allow_null=False)
    pricing_policy_object = serializers.PrimaryKeyRelatedField(
        source="pricing_policy", read_only=True
    )
    fx_rate = FloatEvalField()

    procedure_modified_datetime = ReadOnlyField()

    class Meta:
        model = CurrencyHistory
        fields = [
            "id",
            "currency",
            "currency_object",
            "pricing_policy",
            "pricing_policy_object",
            "date",
            "fx_rate",
            "procedure_modified_datetime",
            "modified",
        ]

    def __init__(self, *args, **kwargs):
        from poms.instruments.serializers import PricingPolicyViewSerializer

        super().__init__(*args, **kwargs)

        self.fields["pricing_policy_object"] = PricingPolicyViewSerializer(
            source="pricing_policy", read_only=True
        )

    def get_unique_together_validators(self):
        return []

    def create(self, validated_data):
        instance = super().create(validated_data)

        instance.procedure_modified_datetime = now()
        instance.save()

        history_item = CurrencyHistoryError()
        history_item.created = now()
        history_item.master_user = instance.currency.master_user
        history_item.currency = instance.currency
        history_item.fx_rate = instance.fx_rate
        history_item.date = instance.date
        history_item.pricing_policy = instance.pricing_policy
        history_item.status = CurrencyHistoryError.STATUS_CREATED
        history_item.created = now()

        history_item.save()

        member = get_member_from_context(self.context)
        master_user = get_master_user_from_context(self.context)

        send_system_message(
            master_user=master_user,
            performed_by=member.username,
            section="prices",
            type="success",
            title="New FX rate (manual)",
            description=(
                f"{instance.currency.user_code} {str(instance.date)} "
                f"{str(instance.fx_rate)}",
            ),
        )

        return instance

    @staticmethod
    def _create_currency_history_error(instance):
        result = CurrencyHistoryError()
        result.status = CurrencyHistoryError.STATUS_CREATED
        result.master_user = instance.currency.master_user
        result.currency = instance.currency
        result.fx_rate = instance.fx_rate
        result.date = instance.date
        result.pricing_policy = instance.pricing_policy

        return result

    def update(self, instance, validated_data):
        instance = super(CurrencyHistorySerializer, self).update(
            instance, validated_data
        )

        instance.procedure_modified_datetime = now()
        instance.save()

        try:
            history_item = CurrencyHistoryError.objects.filter(
                currency=instance.currency,
                master_user=instance.currency.master_user,
                date=instance.date,
                pricing_policy=instance.pricing_policy,
            )[0]
            history_item.status = CurrencyHistoryError.STATUS_OVERWRITTEN

        except (CurrencyHistoryError.DoesNotExist, IndexError):
            history_item = self._create_currency_history_error(instance)

        history_item.save()

        member = get_member_from_context(self.context)
        master_user = get_master_user_from_context(self.context)

        send_system_message(
            master_user=master_user,
            performed_by=member.username,
            section="prices",
            type="warning",
            title="Edit FX rate (manual)",
            description=(
                instance.currency.user_code
                + " "
                + str(instance.date)
                + " "
                + str(instance.fx_rate)
            ),
        )

        return instance


class CurrencyEvalSerializer(ModelWithUserCodeSerializer, ModelWithTimeStampSerializer):
    master_user = MasterUserField()

    class Meta:
        model = Currency
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "notes",
            "reference_for_pricing",
            "pricing_condition",
            "default_fx_rate",
            "is_deleted",
            "is_enabled",
        ]

        read_only_fields = fields


class CurrencyDatabaseSearchRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    user_code = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
    numeric_code = serializers.CharField(required=False)

    @staticmethod
    def _filter_list(items: List[Dict], key: str, value: str) -> List[Dict]:
        if key and value and items:
            value_lower = value.lower()
            return list(filter(lambda x: value_lower in x[key].lower(), items))
        else:
            return []

    def filter_results(self, results: List[Dict]) -> List[Dict]:
        if not results:
            return []

        params = dict(self.validated_data)
        if "name" in params:
            value = params["name"]
            filtered_results = []
            for key in self.get_fields():
                filtered_results = self._filter_list(
                    results,
                    key=key,
                    value=value,
                )
                if filtered_results:
                    break
        elif "user_code" in params:
            filtered_results = self._filter_list(
                results,
                key="user_code",
                value=params["user_code"],
            )
        elif "code" in params:
            filtered_results = self._filter_list(
                results,
                key="code",
                value=params["code"],
            )
        elif "numeric_code" in params:
            filtered_results = self._filter_list(
                results,
                key="numeric_code",
                value=params["numeric_code"],
            )
        else:
            filtered_results = results

        return filtered_results


class CurrencyItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    user_code = serializers.CharField()
    code = serializers.CharField()
    numeric_code = serializers.CharField()


class CurrencyDatabaseSearchResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField()
    previous = serializers.CharField()
    results = CurrencyItemSerializer(many=True)
