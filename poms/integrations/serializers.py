from __future__ import unicode_literals, print_function

import json

from datetime import timedelta
from logging import getLogger

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.translation import ugettext, ugettext_lazy
from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.validators import UniqueTogetherValidator

import uuid

from poms.accounts.fields import AccountField, AccountTypeField
from poms.common.fields import ExpressionField, DateTimeTzAwareField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.common.serializers import PomsClassSerializer, ModelWithUserCodeSerializer
from poms.counterparties.fields import CounterpartyField, ResponsibleField
from poms.currencies.fields import CurrencyField, CurrencyDefault
from poms.currencies.models import CurrencyHistory
from poms.instruments.fields import InstrumentTypeField, InstrumentTypeDefault, InstrumentField, PricingPolicyField
from poms.instruments.models import PriceHistory, Instrument, AccrualCalculationModel, Periodicity, DailyPricingModel, \
    PaymentSizeDetail
from poms.integrations.fields import InstrumentDownloadSchemeField, PriceDownloadSchemeField, \
    ComplexTransactionImportSchemeRestField
from poms.integrations.models import InstrumentDownloadSchemeInput, InstrumentDownloadSchemeAttribute, \
    InstrumentDownloadScheme, ImportConfig, Task, ProviderClass, FactorScheduleDownloadMethod, \
    AccrualScheduleDownloadMethod, PriceDownloadScheme, CurrencyMapping, InstrumentTypeMapping, \
    InstrumentAttributeValueMapping, AccrualCalculationModelMapping, PeriodicityMapping, PricingAutomatedSchedule, \
    AbstractMapping, AccountMapping, InstrumentMapping, CounterpartyMapping, ResponsibleMapping, PortfolioMapping, \
    Strategy1Mapping, Strategy2Mapping, Strategy3Mapping, DailyPricingModelMapping, PaymentSizeDetailMapping, \
    PriceDownloadSchemeMapping, ComplexTransactionImportScheme, ComplexTransactionImportSchemeInput, \
    ComplexTransactionImportSchemeRule, ComplexTransactionImportSchemeField, PortfolioClassifierMapping, \
    AccountClassifierMapping, CounterpartyClassifierMapping, ResponsibleClassifierMapping, PricingPolicyMapping, \
    InstrumentClassifierMapping, AccountTypeMapping
from poms.integrations.providers.base import get_provider, ProviderException
from poms.integrations.storage import import_file_storage
from poms.integrations.tasks import download_pricing, download_instrument, test_certificate
from poms.obj_attrs.fields import GenericAttributeTypeField, GenericClassifierField
from poms.obj_attrs.serializers import ModelWithAttributesSerializer, GenericAttributeTypeSerializer, \
    GenericClassifierSerializer
from poms.obj_perms.serializers import ModelWithObjectPermissionSerializer
from poms.portfolios.fields import PortfolioField
from poms.portfolios.models import Portfolio
from poms.strategies.fields import Strategy1Field, Strategy2Field, Strategy3Field
from poms.tags.serializers import ModelWithTagSerializer
from poms.transactions.fields import TransactionTypeField, TransactionTypeInputField
from poms.users.fields import MasterUserField, MemberField, HiddenMemberField

_l = getLogger('poms.integrations')


class ProviderClassSerializer(PomsClassSerializer):
    class Meta(PomsClassSerializer.Meta):
        model = ProviderClass


class FactorScheduleDownloadMethodSerializer(PomsClassSerializer):
    class Meta(PomsClassSerializer.Meta):
        model = FactorScheduleDownloadMethod


class AccrualScheduleDownloadMethodSerializer(PomsClassSerializer):
    class Meta(PomsClassSerializer.Meta):
        model = AccrualScheduleDownloadMethod


class ImportConfigSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    provider_object = ProviderClassSerializer(source='provider', read_only=True)
    p12cert = serializers.FileField(allow_null=True, allow_empty_file=False, write_only=True)
    password = serializers.CharField(allow_null=True, allow_blank=True, write_only=True)

    class Meta:
        model = ImportConfig
        fields = [
            'id', 'master_user', 'provider', 'provider_object', 'p12cert', 'password', 'has_p12cert',
            'has_password', 'is_valid'
        ]


class InstrumentDownloadSchemeInputSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)

    class Meta:
        model = InstrumentDownloadSchemeInput
        fields = ['id', 'name', 'name_expr', 'field']


class InstrumentDownloadSchemeAttributeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    attribute_type = GenericAttributeTypeField()
    attribute_type_object = serializers.PrimaryKeyRelatedField(source='attribute_type', read_only=True)
    value = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)

    class Meta:
        model = InstrumentDownloadSchemeAttribute
        # attribute_type_model = InstrumentAttributeType
        fields = ['id', 'attribute_type', 'attribute_type_object', 'value']

    def __init__(self, *args, **kwargs):
        super(InstrumentDownloadSchemeAttributeSerializer, self).__init__(*args, **kwargs)

        from poms.obj_attrs.serializers import GenericAttributeTypeViewSerializer
        self.fields['attribute_type_object'] = GenericAttributeTypeViewSerializer(source='attribute_type',
                                                                                  read_only=True)

    def validate(self, attrs):
        attribute_type = attrs.get('attribute_type', None)
        if attribute_type:
            if attribute_type.content_type_id != ContentType.objects.get_for_model(Instrument).id:
                self.fields['attribute_type'].fail('does_not_exist', pk_value=attribute_type.id)
        return attrs


class InstrumentDownloadSchemeSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    provider_object = ProviderClassSerializer(source='provider', read_only=True)

    inputs = InstrumentDownloadSchemeInputSerializer(many=True, read_only=False)

    user_code = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)
    name = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH)
    short_name = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)
    public_name = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)
    notes = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)
    instrument_type = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)
    pricing_currency = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)
    price_multiplier = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)
    accrued_currency = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)
    accrued_multiplier = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)
    # daily_pricing_model = ExpressionField(allow_blank=True)
    # payment_size_detail = ExpressionField(allow_blank=True)
    # default_price = ExpressionField(allow_blank=True)
    # default_accrued = ExpressionField(allow_blank=True)
    # price_download_mode = ExpressionField(allow_blank=True)
    maturity_date = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)
    maturity_price = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)
    user_text_1 = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)
    user_text_2 = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)
    user_text_3 = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=True)

    payment_size_detail_object = serializers.PrimaryKeyRelatedField(source='payment_size_detail', read_only=True)
    daily_pricing_model_object = serializers.PrimaryKeyRelatedField(source='daily_pricing_model', read_only=True)
    price_download_scheme = PriceDownloadSchemeField()
    price_download_scheme_object = serializers.PrimaryKeyRelatedField(source='price_download_scheme', read_only=True)
    factor_schedule_method_object = serializers.PrimaryKeyRelatedField(source='factor_schedule_method', read_only=True)
    accrual_calculation_schedule_method_object = serializers.PrimaryKeyRelatedField(
        source='accrual_calculation_schedule_method', read_only=True)

    attributes = InstrumentDownloadSchemeAttributeSerializer(many=True, read_only=False)

    class Meta:
        model = InstrumentDownloadScheme
        fields = [
            'id', 'master_user', 'scheme_name', 'provider', 'provider_object', 'inputs',
            'reference_for_pricing', 'user_code', 'name', 'short_name', 'public_name', 'notes',
            'instrument_type', 'pricing_currency', 'price_multiplier', 'accrued_currency', 'accrued_multiplier',
            'user_text_1', 'user_text_2', 'user_text_3', 'maturity_date', 'maturity_price',
            'payment_size_detail', 'payment_size_detail_object',
            'daily_pricing_model', 'daily_pricing_model_object',
            'price_download_scheme', 'price_download_scheme_object',
            'default_price', 'default_accrued',
            'factor_schedule_method', 'factor_schedule_method_object',
            'accrual_calculation_schedule_method', 'accrual_calculation_schedule_method_object',
            'attributes',
        ]

    def __init__(self, *args, **kwargs):
        super(InstrumentDownloadSchemeSerializer, self).__init__(*args, **kwargs)

        from poms.instruments.serializers import PaymentSizeDetailSerializer, DailyPricingModelSerializer
        self.fields['payment_size_detail_object'] = PaymentSizeDetailSerializer(source='payment_size_detail',
                                                                                read_only=True)
        self.fields['daily_pricing_model_object'] = DailyPricingModelSerializer(source='daily_pricing_model',
                                                                                read_only=True)
        self.fields['price_download_scheme_object'] = PriceDownloadSchemeViewSerializer(source='price_download_scheme',
                                                                                        read_only=True)
        self.fields['factor_schedule_method_object'] = FactorScheduleDownloadMethodSerializer(
            source='factor_schedule_method', read_only=True)
        self.fields['accrual_calculation_schedule_method_object'] = AccrualScheduleDownloadMethodSerializer(
            source='accrual_calculation_schedule_method', read_only=True)

    def create(self, validated_data):
        inputs = validated_data.pop('inputs', None) or []
        attributes = validated_data.pop('attributes', None) or []
        instance = super(InstrumentDownloadSchemeSerializer, self).create(validated_data)
        self.save_inputs(instance, inputs)
        self.save_attributes(instance, attributes)
        return instance

    def update(self, instance, validated_data):
        inputs = validated_data.pop('inputs', empty)
        attributes = validated_data.pop('attributes', None) or []
        instance = super(InstrumentDownloadSchemeSerializer, self).update(instance, validated_data)
        if inputs is not empty:
            self.save_inputs(instance, inputs)
        if attributes is not empty:
            self.save_attributes(instance, attributes)
        return instance

    def save_inputs(self, instance, inputs):
        pk_set = set()
        for input_values in inputs:
            input_id = input_values.pop('id', None)
            input0 = None
            if input_id:
                try:
                    input0 = instance.inputs.get(pk=input_id)
                except ObjectDoesNotExist:
                    pass
            if input0 is None:
                input0 = InstrumentDownloadSchemeInput(scheme=instance)
            for name, value in input_values.items():
                setattr(input0, name, value)
            input0.save()
            pk_set.add(input0.id)
        instance.inputs.exclude(pk__in=pk_set).delete()

    def save_attributes(self, instance, attributes):
        pk_set = set()
        for attr_values in attributes:
            attribute_type = attr_values['attribute_type']
            try:
                attr = instance.attributes.get(attribute_type=attribute_type)
            except ObjectDoesNotExist:
                attr = None
            if attr is None:
                attr = InstrumentDownloadSchemeAttribute(scheme=instance)
            for name, value in attr_values.items():
                setattr(attr, name, value)
            attr.save()
            pk_set.add(attr.id)
        instance.attributes.exclude(pk__in=pk_set).delete()


class PriceDownloadSchemeSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    provider_object = ProviderClassSerializer(source='provider', read_only=True)

    class Meta:
        model = PriceDownloadScheme
        fields = [
            'id', 'master_user', 'scheme_name', 'provider', 'provider_object',
            'bid0', 'bid1', 'bid2', 'bid_multiplier', 'ask0', 'ask1', 'ask2', 'ask_multiplier', 'last',
            'last_multiplier', 'mid', 'mid_multiplier',
            'bid_history', 'bid_history_multiplier', 'ask_history', 'ask_history_multiplier', 'mid_history',
            'mid_history_multiplier', 'last_history', 'last_history_multiplier',
            'currency_fxrate', 'currency_fxrate_multiplier',
        ]


class PriceDownloadSchemeViewSerializer(serializers.ModelSerializer):
    provider_object = ProviderClassSerializer(source='provider', read_only=True)

    class Meta:
        model = PriceDownloadScheme
        fields = [
            'id', 'scheme_name', 'provider', 'provider_object',
        ]


# ------------------


# class CurrencyMappingSerializer(serializers.ModelSerializer):
#     master_user = MasterUserField()
#     provider_object = ProviderClassSerializer(source='provider', read_only=True)
#     currency = CurrencyField()
#     currency_object = serializers.PrimaryKeyRelatedField(source='currency', read_only=True)
#
#     class Meta:
#         model = CurrencyMapping
#         fields = [
#             'id', 'master_user', 'provider', 'provider_object', 'value', 'currency', 'currency_object',
#         ]
#         validators = [
#             UniqueTogetherValidator(
#                 queryset=CurrencyMapping.objects.all(),
#                 fields=('master_user', 'provider', 'value'),
#                 message=ugettext_lazy('The fields provider and value must make a unique set.')
#             )
#         ]
#
#     def __init__(self, *args, **kwargs):
#         super(CurrencyMappingSerializer, self).__init__(*args, **kwargs)
#
#         from poms.currencies.serializers import CurrencyViewSerializer
#         self.fields['currency_object'] = CurrencyViewSerializer(source='currency', read_only=True)


# class InstrumentTypeMappingSerializer(serializers.ModelSerializer):
#     master_user = MasterUserField()
#     provider_object = ProviderClassSerializer(source='provider', read_only=True)
#     instrument_type = InstrumentTypeField()
#     instrument_type_object = serializers.PrimaryKeyRelatedField(source='instrument_type', read_only=True)
#
#     class Meta:
#         model = InstrumentTypeMapping
#         fields = [
#             'id', 'master_user', 'provider', 'provider_object', 'value', 'instrument_type',
#             'instrument_type_object',
#         ]
#         validators = [
#             UniqueTogetherValidator(
#                 queryset=InstrumentTypeMapping.objects.all(),
#                 fields=('master_user', 'provider', 'value'),
#                 message=ugettext_lazy('The fields provider and value must make a unique set.')
#             )
#         ]
#
#     def __init__(self, *args, **kwargs):
#         super(InstrumentTypeMappingSerializer, self).__init__(*args, **kwargs)
#
#         from poms.instruments.serializers import InstrumentTypeViewSerializer
#         self.fields['instrument_type_object'] = InstrumentTypeViewSerializer(source='instrument_type', read_only=True)


# class InstrumentAttributeValueMappingSerializer(serializers.ModelSerializer):
#     master_user = MasterUserField()
#     provider_object = ProviderClassSerializer(source='provider', read_only=True)
#     attribute_type = GenericAttributeTypeField()
#     attribute_type_object = serializers.PrimaryKeyRelatedField(source='attribute_type', read_only=True)
#     classifier = GenericClassifierField(allow_empty=True, allow_null=True)
#     classifier_object = serializers.PrimaryKeyRelatedField(source='classifier', read_only=True)
#
#     class Meta:
#         model = InstrumentAttributeValueMapping
#         fields = [
#             'id', 'master_user', 'provider', 'provider_object', 'value',
#             'attribute_type', 'attribute_type_object', 'value_string', 'value_float', 'value_date',
#             'classifier', 'classifier_object',
#         ]
#         validators = [
#             UniqueTogetherValidator(
#                 queryset=InstrumentAttributeValueMapping.objects.all(),
#                 fields=('master_user', 'provider', 'value'),
#                 message=ugettext_lazy('The fields provider and value must make a unique set.')
#             )
#         ]
#
#     def __init__(self, *args, **kwargs):
#         super(InstrumentAttributeValueMappingSerializer, self).__init__(*args, **kwargs)
#
#         from poms.obj_attrs.serializers import GenericAttributeTypeViewSerializer, GenericClassifierViewSerializer
#         self.fields['attribute_type_object'] = GenericAttributeTypeViewSerializer(source='attribute_type',
#                                                                                   read_only=True)
#         self.fields['classifier_object'] = GenericClassifierViewSerializer(source='classifier', read_only=True)
#
#     def validate(self, attrs):
#         attribute_type = attrs.get('attribute_type', None)
#         if attribute_type:
#             if attribute_type.content_type_id != ContentType.objects.get_for_model(Instrument).id:
#                 self.fields['attribute_type'].fail('does_not_exist', pk_value=attribute_type.id)
#
#         classifier = attrs.get('classifier', None)
#         if classifier:
#             if classifier.attribute_type_id != attribute_type.id:
#                 raise serializers.ValidationError({'classifier': 'Invalid classifier'})
#         return attrs


# class AccrualCalculationModelMappingSerializer(serializers.ModelSerializer):
#     master_user = MasterUserField()
#     provider_object = ProviderClassSerializer(source='provider', read_only=True)
#     accrual_calculation_model_object = serializers.PrimaryKeyRelatedField(source='accrual_calculation_model',
#                                                                           read_only=True)
#
#     class Meta:
#         model = AccrualCalculationModelMapping
#         fields = [
#             'id', 'master_user', 'provider', 'provider_object', 'value', 'accrual_calculation_model',
#             'accrual_calculation_model_object',
#         ]
#         validators = [
#             UniqueTogetherValidator(
#                 queryset=AccrualCalculationModelMapping.objects.all(),
#                 fields=('master_user', 'provider', 'value'),
#                 message=ugettext_lazy('The fields provider and value must make a unique set.')
#             )
#         ]
#
#     def __init__(self, *args, **kwargs):
#         super(AccrualCalculationModelMappingSerializer, self).__init__(*args, **kwargs)
#
#         from poms.instruments.serializers import AccrualCalculationModelSerializer
#         self.fields['accrual_calculation_model_object'] = AccrualCalculationModelSerializer(
#             source='accrual_calculation_model', read_only=True)
#
#
# class PeriodicityMappingSerializer(serializers.ModelSerializer):
#     master_user = MasterUserField()
#     provider_object = ProviderClassSerializer(source='provider', read_only=True)
#     periodicity_object = serializers.PrimaryKeyRelatedField(source='periodicity', read_only=True)
#
#     class Meta:
#         model = PeriodicityMapping
#         fields = [
#             'id', 'master_user', 'provider', 'provider_object', 'value', 'periodicity', 'periodicity_object',
#         ]
#         validators = [
#             UniqueTogetherValidator(
#                 queryset=PeriodicityMapping.objects.all(),
#                 fields=('master_user', 'provider', 'value'),
#                 message=ugettext_lazy('The fields provider and value must make a unique set.')
#             )
#         ]
#
#     def __init__(self, *args, **kwargs):
#         super(PeriodicityMappingSerializer, self).__init__(*args, **kwargs)
#
#         from poms.instruments.serializers import PeriodicitySerializer
#         self.fields['periodicity_object'] = PeriodicitySerializer(source='periodicity', read_only=True)


class AbstractMappingSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    # currency = CurrencyField()
    # currency_object = serializers.PrimaryKeyRelatedField(source='currency', read_only=True)

    class Meta:
        model = AbstractMapping
        fields = [
            'id', 'master_user', 'provider', 'value', 'content_object',
            # 'provider_object', 'content_object_object',
        ]
        # validators = [
        #     UniqueTogetherValidator(
        #         queryset=CurrencyMapping.objects.all(),
        #         fields=('master_user', 'provider', 'value'),
        #         message=ugettext_lazy('The fields provider and value must make a unique set.')
        #     )
        # ]

    def __init__(self, *args, **kwargs):
        super(AbstractMappingSerializer, self).__init__(*args, **kwargs)

        self.fields['provider_object'] = ProviderClassSerializer(source='provider', read_only=True)

        content_object_view_serializer_class = self.get_content_object_view_serializer()
        self.fields['content_object_object'] = content_object_view_serializer_class(source='content_object',
                                                                                    read_only=True)

        model = self.Meta.model
        self.validators.append(
            UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=('master_user', 'provider', 'value'),
                message=ugettext_lazy('The fields provider and value must make a unique set.')
            )
        )

    def get_content_object_view_serializer(self):
        raise NotImplementedError()


class AbstractClassifierMappingSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    # currency = CurrencyField()
    # currency_object = serializers.PrimaryKeyRelatedField(source='currency', read_only=True)

    class Meta:
        model = AbstractMapping
        fields = [
            'id', 'master_user', 'provider', 'value', 'attribute_type', 'content_object',
            # 'provider_object', 'content_object_object',
        ]
        # validators = [
        #     UniqueTogetherValidator(
        #         queryset=CurrencyMapping.objects.all(),
        #         fields=('master_user', 'provider', 'value'),
        #         message=ugettext_lazy('The fields provider and value must make a unique set.')
        #     )
        # ]

    def __init__(self, *args, **kwargs):
        super(AbstractClassifierMappingSerializer, self).__init__(*args, **kwargs)

        self.fields['provider_object'] = ProviderClassSerializer(source='provider', read_only=True)

        self.fields['attribute_type_object'] = GenericAttributeTypeSerializer(source='attribute_type', read_only=True)

        self.fields['content_object_object'] = GenericClassifierSerializer(source='content_object', read_only=True)

        model = self.Meta.model
        self.validators.append(
            UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=('master_user', 'provider', 'value', 'attribute_type'),
                message=ugettext_lazy('The fields provider, value and attribute_type must make a unique set.')
            )
        )


class CurrencyMappingSerializer(AbstractMappingSerializer):
    content_object = CurrencyField()

    class Meta(AbstractMappingSerializer.Meta):
        model = CurrencyMapping

    def __init__(self, *args, **kwargs):
        super(CurrencyMappingSerializer, self).__init__(*args, **kwargs)

        # from poms.currencies.serializers import CurrencyViewSerializer
        # self.fields['currency_object'] = CurrencyViewSerializer(source='currency', read_only=True)

    def get_content_object_view_serializer(self):
        from poms.currencies.serializers import CurrencyViewSerializer
        return CurrencyViewSerializer


class PricingPolicyMappingSerializer(AbstractMappingSerializer):
    content_object = PricingPolicyField()

    class Meta(AbstractMappingSerializer.Meta):
        model = PricingPolicyMapping

    def __init__(self, *args, **kwargs):
        super(PricingPolicyMappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.instruments.serializers import PricingPolicyViewSerializer
        return PricingPolicyViewSerializer


class AccountTypeMappingSerializer(AbstractMappingSerializer):
    content_object = AccountTypeField()

    class Meta(AbstractMappingSerializer.Meta):
        model = AccountTypeMapping

    def __init__(self, *args, **kwargs):
        super(AccountTypeMappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.accounts.serializers import AccountTypeViewSerializer
        return AccountTypeViewSerializer


class InstrumentTypeMappingSerializer(AbstractMappingSerializer):
    content_object = InstrumentTypeField()

    class Meta(AbstractMappingSerializer.Meta):
        model = InstrumentTypeMapping

    def __init__(self, *args, **kwargs):
        super(InstrumentTypeMappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.instruments.serializers import InstrumentTypeViewSerializer
        return InstrumentTypeViewSerializer


class InstrumentAttributeValueMappingSerializer(AbstractMappingSerializer):
    content_object = GenericAttributeTypeField()
    classifier = GenericClassifierField(allow_empty=True, allow_null=True)

    class Meta(AbstractMappingSerializer.Meta):
        model = InstrumentAttributeValueMapping
        fields = AbstractMappingSerializer.Meta.fields + [
            'value_string', 'value_float', 'value_date', 'classifier',
        ]

    def __init__(self, *args, **kwargs):
        super(InstrumentAttributeValueMappingSerializer, self).__init__(*args, **kwargs)

        from poms.obj_attrs.serializers import GenericClassifierViewSerializer
        self.fields['classifier_object'] = GenericClassifierViewSerializer(source='classifier', read_only=True)

    def get_content_object_view_serializer(self):
        from poms.obj_attrs.serializers import GenericAttributeTypeViewSerializer
        return GenericAttributeTypeViewSerializer

    def validate(self, attrs):
        content_object = attrs.get('content_object', None)
        if content_object:
            if content_object.content_type_id != ContentType.objects.get_for_model(Instrument).id:
                self.fields['content_object'].fail('does_not_exist', pk_value=content_object.id)

        classifier = attrs.get('classifier', None)
        if classifier:
            if classifier.attribute_type_id != content_object.id:
                raise serializers.ValidationError({'classifier': 'Invalid classifier'})
        return attrs


class AccrualCalculationModelMappingSerializer(AbstractMappingSerializer):
    content_object = serializers.PrimaryKeyRelatedField(queryset=AccrualCalculationModel.objects.all())

    class Meta(AbstractMappingSerializer.Meta):
        model = AccrualCalculationModelMapping

    def __init__(self, *args, **kwargs):
        super(AccrualCalculationModelMappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.instruments.serializers import AccrualCalculationModelSerializer
        return AccrualCalculationModelSerializer


class PeriodicityMappingSerializer(AbstractMappingSerializer):
    content_object = serializers.PrimaryKeyRelatedField(queryset=Periodicity.objects.all())

    class Meta(AbstractMappingSerializer.Meta):
        model = PeriodicityMapping

    def __init__(self, *args, **kwargs):
        super(PeriodicityMappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.instruments.serializers import PeriodicitySerializer
        return PeriodicitySerializer


class AccountMappingSerializer(AbstractMappingSerializer):
    content_object = AccountField()

    class Meta(AbstractMappingSerializer.Meta):
        model = AccountMapping

    def __init__(self, *args, **kwargs):
        super(AccountMappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.accounts.serializers import AccountViewSerializer
        return AccountViewSerializer


class AccountClassifierMappingSerializer(AbstractClassifierMappingSerializer):
    attribute_type = GenericAttributeTypeField()
    content_object = GenericClassifierField()

    class Meta(AbstractClassifierMappingSerializer.Meta):
        model = AccountClassifierMapping

    def __init__(self, *args, **kwargs):
        super(AccountClassifierMappingSerializer, self).__init__(*args, **kwargs)


class InstrumentMappingSerializer(AbstractMappingSerializer):
    content_object = InstrumentField()

    class Meta(AbstractMappingSerializer.Meta):
        model = InstrumentMapping

    def __init__(self, *args, **kwargs):
        super(InstrumentMappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.instruments.serializers import InstrumentViewSerializer
        return InstrumentViewSerializer


class InstrumentClassifierMappingSerializer(AbstractClassifierMappingSerializer):
    attribute_type = GenericAttributeTypeField()
    content_object = GenericClassifierField()

    class Meta(AbstractClassifierMappingSerializer.Meta):
        model = InstrumentClassifierMapping

    def __init__(self, *args, **kwargs):
        super(InstrumentClassifierMappingSerializer, self).__init__(*args, **kwargs)


class CounterpartyMappingSerializer(AbstractMappingSerializer):
    content_object = CounterpartyField()

    class Meta(AbstractMappingSerializer.Meta):
        model = CounterpartyMapping

    def __init__(self, *args, **kwargs):
        super(CounterpartyMappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.counterparties.serializers import CounterpartyViewSerializer
        return CounterpartyViewSerializer


class CounterpartyClassifierMappingSerializer(AbstractClassifierMappingSerializer):
    attribute_type = GenericAttributeTypeField()
    content_object = GenericClassifierField()

    class Meta(AbstractClassifierMappingSerializer.Meta):
        model = CounterpartyClassifierMapping

    def __init__(self, *args, **kwargs):
        super(CounterpartyClassifierMappingSerializer, self).__init__(*args, **kwargs)


class ResponsibleMappingSerializer(AbstractMappingSerializer):
    content_object = ResponsibleField()

    class Meta(AbstractMappingSerializer.Meta):
        model = ResponsibleMapping

    def __init__(self, *args, **kwargs):
        super(ResponsibleMappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.counterparties.serializers import ResponsibleViewSerializer
        return ResponsibleViewSerializer


class ResponsibleClassifierMappingSerializer(AbstractClassifierMappingSerializer):
    attribute_type = GenericAttributeTypeField()
    content_object = GenericClassifierField()

    class Meta(AbstractClassifierMappingSerializer.Meta):
        model = ResponsibleClassifierMapping

    def __init__(self, *args, **kwargs):
        super(ResponsibleClassifierMappingSerializer, self).__init__(*args, **kwargs)


class PortfolioMappingSerializer(AbstractMappingSerializer):
    content_object = PortfolioField()

    class Meta(AbstractMappingSerializer.Meta):
        model = PortfolioMapping

    def __init__(self, *args, **kwargs):
        super(PortfolioMappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.portfolios.serializers import PortfolioViewSerializer
        return PortfolioViewSerializer


class PortfolioClassifierMappingSerializer(AbstractClassifierMappingSerializer):
    attribute_type = GenericAttributeTypeField()
    content_object = GenericClassifierField()

    class Meta(AbstractClassifierMappingSerializer.Meta):
        model = PortfolioClassifierMapping

    def __init__(self, *args, **kwargs):
        super(PortfolioClassifierMappingSerializer, self).__init__(*args, **kwargs)


class Strategy1MappingSerializer(AbstractMappingSerializer):
    content_object = Strategy1Field()

    class Meta(AbstractMappingSerializer.Meta):
        model = Strategy1Mapping

    def __init__(self, *args, **kwargs):
        super(Strategy1MappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.strategies.serializers import Strategy1ViewSerializer
        return Strategy1ViewSerializer


class Strategy2MappingSerializer(AbstractMappingSerializer):
    content_object = Strategy2Field()

    class Meta(AbstractMappingSerializer.Meta):
        model = Strategy2Mapping

    def __init__(self, *args, **kwargs):
        super(Strategy2MappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.strategies.serializers import Strategy2ViewSerializer
        return Strategy2ViewSerializer


class Strategy3MappingSerializer(AbstractMappingSerializer):
    content_object = Strategy3Field()

    class Meta(AbstractMappingSerializer.Meta):
        model = Strategy3Mapping

    def __init__(self, *args, **kwargs):
        super(Strategy3MappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.strategies.serializers import Strategy3ViewSerializer
        return Strategy3ViewSerializer


class DailyPricingModelMappingSerializer(AbstractMappingSerializer):
    content_object = serializers.PrimaryKeyRelatedField(queryset=DailyPricingModel.objects.all())

    class Meta(AbstractMappingSerializer.Meta):
        model = DailyPricingModelMapping

    def __init__(self, *args, **kwargs):
        super(DailyPricingModelMappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.instruments.serializers import DailyPricingModelSerializer
        return DailyPricingModelSerializer


class PaymentSizeDetailMappingSerializer(AbstractMappingSerializer):
    content_object = serializers.PrimaryKeyRelatedField(queryset=PaymentSizeDetail.objects.all())

    class Meta(AbstractMappingSerializer.Meta):
        model = PaymentSizeDetailMapping

    def __init__(self, *args, **kwargs):
        super(PaymentSizeDetailMappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        from poms.instruments.serializers import PaymentSizeDetailSerializer
        return PaymentSizeDetailSerializer


class PriceDownloadSchemeMappingSerializer(AbstractMappingSerializer):
    content_object = PriceDownloadSchemeField()

    class Meta(AbstractMappingSerializer.Meta):
        model = PriceDownloadSchemeMapping

    def __init__(self, *args, **kwargs):
        super(PriceDownloadSchemeMappingSerializer, self).__init__(*args, **kwargs)

    def get_content_object_view_serializer(self):
        return PriceDownloadSchemeViewSerializer


# ----


class TaskSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    member = MemberField()
    provider_object = ProviderClassSerializer(source='provider', read_only=True)
    is_yesterday = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'master_user', 'member', 'provider', 'provider_object',
            'created', 'modified', 'status',
            'action',
            'is_yesterday',
            'parent', 'children',
            # 'options_object',
            # 'result_object',
        ]

    def get_is_yesterday(self, obj):
        if obj.action == Task.ACTION_PRICING:
            options = obj.options_object or {}
            return options.get('is_yesterday', None)
        return None


class PricingAutomatedScheduleSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    last_run_at = DateTimeTzAwareField(read_only=True)
    next_run_at = DateTimeTzAwareField(read_only=True)

    class Meta:
        model = PricingAutomatedSchedule
        fields = [
            'id', 'master_user',
            'is_enabled', 'cron_expr', 'balance_day', 'load_days', 'fill_days', 'override_existed',
            'last_run_at', 'next_run_at',
        ]
        read_only_fields = ['last_run_at', 'next_run_at']


class ImportInstrumentViewSerializer(ModelWithAttributesSerializer, ModelWithObjectPermissionSerializer,
                                     ModelWithUserCodeSerializer, ModelWithTagSerializer):
    instrument_type = InstrumentTypeField(default=InstrumentTypeDefault())
    instrument_type_object = serializers.PrimaryKeyRelatedField(source='instrument_type', read_only=True)
    pricing_currency = CurrencyField(default=CurrencyDefault())
    pricing_currency_object = serializers.PrimaryKeyRelatedField(source='pricing_currency', read_only=True)
    accrued_currency = CurrencyField(default=CurrencyDefault())
    accrued_currency_object = serializers.PrimaryKeyRelatedField(source='accrued_currency', read_only=True)
    payment_size_detail_object = serializers.PrimaryKeyRelatedField(source='payment_size_detail', read_only=True)
    daily_pricing_model_object = serializers.PrimaryKeyRelatedField(source='daily_pricing_model', read_only=True)
    price_download_scheme = PriceDownloadSchemeField(allow_null=True)
    price_download_scheme_object = serializers.PrimaryKeyRelatedField(source='price_download_scheme', read_only=True)

    accrual_calculation_schedules = serializers.SerializerMethodField()
    factor_schedules = serializers.SerializerMethodField()
    event_schedules = serializers.PrimaryKeyRelatedField(read_only=True, many=True)

    # attributes = serializers.SerializerMethodField()

    # tags = TagField(many=True, required=False, allow_null=True)
    # tags_object = TagViewSerializer(source='tags', many=True, read_only=True)

    class Meta:
        model = Instrument
        fields = [
            'id', 'master_user', 'instrument_type', 'instrument_type_object', 'user_code', 'name', 'short_name',
            'public_name', 'notes', 'is_active', 'is_deleted',
            'pricing_currency', 'pricing_currency_object', 'price_multiplier',
            'accrued_currency', 'accrued_currency_object', 'accrued_multiplier',
            'payment_size_detail', 'payment_size_detail_object', 'default_price', 'default_accrued',
            'user_text_1', 'user_text_2', 'user_text_3',
            'reference_for_pricing', 'daily_pricing_model', 'daily_pricing_model_object',
            'price_download_scheme', 'price_download_scheme_object',
            'maturity_date',
            # 'manual_pricing_formulas',
            'accrual_calculation_schedules', 'factor_schedules', 'event_schedules',
            # 'attributes',
            # 'tags', 'tags_object'
        ]

    def __init__(self, *args, **kwargs):
        super(ImportInstrumentViewSerializer, self).__init__(*args, **kwargs)

        from poms.currencies.serializers import CurrencyViewSerializer
        self.fields['pricing_currency_object'] = CurrencyViewSerializer(source='pricing_currency', read_only=True)
        self.fields['accrued_currency_object'] = CurrencyViewSerializer(source='accrued_currency', read_only=True)

        from poms.instruments.serializers import InstrumentTypeViewSerializer, PaymentSizeDetailSerializer, \
            DailyPricingModelSerializer, EventScheduleSerializer
        self.fields['instrument_type_object'] = InstrumentTypeViewSerializer(source='instrument_type', read_only=True)
        self.fields['daily_pricing_model_object'] = DailyPricingModelSerializer(source='daily_pricing_model',
                                                                                read_only=True)
        self.fields['payment_size_detail_object'] = PaymentSizeDetailSerializer(source='payment_size_detail',
                                                                                read_only=True)
        self.fields['event_schedules'] = EventScheduleSerializer(many=True, required=False, allow_null=True)

        self.fields['price_download_scheme_object'] = PriceDownloadSchemeViewSerializer(source='price_download_scheme',
                                                                                        read_only=True)

        self.fields['attributes'] = serializers.SerializerMethodField()

        # self.fields.pop('manual_pricing_formulas')
        # self.fields.pop('accrual_calculation_schedules')
        # self.fields.pop('factor_schedules')
        self.fields.pop('event_schedules')
        self.fields.pop('tags')
        self.fields.pop('tags_object')
        # self.fields.pop('attributes')
        self.fields.pop('granted_permissions')
        self.fields.pop('user_object_permissions', None)
        self.fields.pop('group_object_permissions', None)

    def get_accrual_calculation_schedules(self, obj):
        from poms.instruments.serializers import AccrualCalculationScheduleSerializer
        if hasattr(obj, '_accrual_calculation_schedules'):
            l = obj._accrual_calculation_schedules
        else:
            l = obj.accrual_calculation_schedules.all()
        return AccrualCalculationScheduleSerializer(instance=l, many=True, read_only=True, context=self.context).data

    def get_factor_schedules(self, obj):
        from poms.instruments.serializers import InstrumentFactorScheduleSerializer
        if hasattr(obj, '_factor_schedules'):
            l = obj._factor_schedules
        else:
            l = obj.factor_schedules.all()
        return InstrumentFactorScheduleSerializer(instance=l, many=True, read_only=True, context=self.context).data

    def get_attributes(self, obj):
        from poms.obj_attrs.serializers import GenericAttributeSerializer
        _l.warn('get_attributes: _attributes=%s', hasattr(obj, '_attributes'))
        if hasattr(obj, '_attributes'):
            l = obj._attributes
        else:
            l = obj.attributes.all()
        return GenericAttributeSerializer(instance=l, many=True, read_only=True, context=self.context).data


class ImportInstrumentEntry(object):
    def __init__(self, master_user=None, member=None, instrument_code=None, instrument_download_scheme=None,
                 task=None, task_result_overrides=None, instrument=None, errors=None):
        self.master_user = master_user
        self.member = member
        self.instrument_code = instrument_code
        self.instrument_download_scheme = instrument_download_scheme
        self.task = task
        self._task_object = None
        self.task_result_overrides = task_result_overrides
        self.instrument = instrument
        self.errors = errors

    @property
    def task_object(self):
        if not self._task_object and self.task:
            self._task_object = self.master_user.tasks.get(pk=self.task)
        return self._task_object

    @task_object.setter
    def task_object(self, value):
        self._task_object = value
        self.task = getattr(value, 'pk', None)


class ImportInstrumentSerializer(serializers.Serializer):
    master_user = MasterUserField()
    member = HiddenMemberField()
    instrument_download_scheme = InstrumentDownloadSchemeField()
    instrument_code = serializers.CharField(required=True, initial='USP16394AG62 Corp')

    task = serializers.IntegerField(required=False, allow_null=True)
    task_object = TaskSerializer(read_only=True)
    task_result = serializers.SerializerMethodField()
    task_result_overrides = serializers.JSONField(default={}, allow_null=True)

    # instrument = serializers.ReadOnlyField()
    errors = serializers.ReadOnlyField()

    def __init__(self, *args, **kwargs):
        super(ImportInstrumentSerializer, self).__init__(*args, **kwargs)
        self.fields['instrument'] = ImportInstrumentViewSerializer(read_only=True)

    def validate(self, attrs):
        master_user = attrs['master_user']
        instrument_download_scheme = attrs['instrument_download_scheme']
        instrument_code = attrs['instrument_code']

        try:
            provider = get_provider(master_user=master_user, provider=instrument_download_scheme.provider_id)
        except ProviderException:
            raise serializers.ValidationError(
                {'instrument_download_scheme':
                     ugettext('Check "%(provider)s" provider configuration.') % {
                         'provider': instrument_download_scheme.provider}
                 })

        if not provider.is_valid_reference(instrument_code):
            raise serializers.ValidationError(
                {'instrument_code':
                     ugettext('Invalid value for "%(provider)s" provider.') % {
                         'reference': instrument_code,
                         'provider': instrument_download_scheme.provider}
                 })

        task_result_overrides = attrs.get('task_result_overrides', None) or {}
        if isinstance(task_result_overrides, str):
            try:
                task_result_overrides = json.loads(task_result_overrides)
            except ValueError:
                raise serializers.ValidationError({'task_result_overrides': ugettext('Invalid JSON string.')})
        if not isinstance(task_result_overrides, dict):
            raise serializers.ValidationError({'task_result_overrides': ugettext('Invalid value.')})

        task_result_overrides = {k: v for k, v in task_result_overrides.items()
                                 if k in instrument_download_scheme.fields}
        attrs['task_result_overrides'] = task_result_overrides
        return attrs

    def create(self, validated_data):
        task_result_overrides = validated_data.get('task_result_overrides', None)
        instance = ImportInstrumentEntry(**validated_data)
        if instance.task:
            task, instrument, errors = download_instrument(
                # instrument_code=instance.instrument_code,
                # instrument_download_scheme=instance.instrument_download_scheme,
                # master_user=instance.master_user,
                # member=instance.member,
                task=instance.task_object,
                value_overrides=task_result_overrides
            )
            instance.task_object = task
            instance.instrument = instrument
            instance.errors = errors
        else:
            task, instrument, errors = download_instrument(
                instrument_code=instance.instrument_code,
                instrument_download_scheme=instance.instrument_download_scheme,
                master_user=instance.master_user,
                member=instance.member
            )
            instance.task_object = task
            instance.instrument = instrument
            instance.errors = errors
        return instance

    def get_task_result(self, obj):
        if obj.task_object.status == Task.STATUS_DONE:
            fields = obj.task_object.options_object['fields']
            result_object = obj.task_object.result_object
            return {k: v for k, v in result_object.items() if k in fields}
        return {}


class ImportTestCertificate(object):

    def __init__(self, master_user=None, member=None,
                 provider_id=None, task=None):

        self.master_user = master_user
        self.member = member
        self.provider_id = provider_id

        self.task = task
        self._task_object = None

    @property
    def task_object(self):
        if not self._task_object and self.task:
            self._task_object = self.master_user.tasks.get(pk=self.task)
        return self._task_object

    @task_object.setter
    def task_object(self, value):
        self._task_object = value
        self.task = getattr(value, 'pk', None)


class ImportPricingEntry(object):
    def __init__(self, master_user=None, member=None,
                 instruments=None, currencies=None,
                 date_from=None, date_to=None, is_yesterday=None,
                 balance_date=None, fill_days=None, override_existed=False,
                 task=None, instrument_histories=None, currency_histories=None):
        self.master_user = master_user
        self.member = member
        self.instruments = instruments
        self.currencies = currencies

        self.date_from = date_from
        self.date_to = date_to
        self.is_yesterday = is_yesterday
        self.balance_date = balance_date
        self.fill_days = fill_days
        self.override_existed = override_existed

        self.task = task
        self._task_object = None
        self.instrument_histories = instrument_histories
        self.currency_histories = currency_histories

    @property
    def task_object(self):
        if not self._task_object and self.task:
            self._task_object = self.master_user.tasks.get(pk=self.task)
        return self._task_object

    @task_object.setter
    def task_object(self, value):
        self._task_object = value
        self.task = getattr(value, 'pk', None)

    @property
    def errors(self):
        t = self.task_object
        if t:
            return t.options_object.get('errors', None)
        return None

    @property
    def instrument_price_missed(self):
        if not self.is_yesterday:
            return []
        result = getattr(self.task_object, 'result_object', {})
        instrument_price_missed = result.get('instrument_price_missed', None)
        if instrument_price_missed:
            instruments_pk = [instr_id for instr_id, _ in instrument_price_missed]
            existed_instrument_prices = {
                (p.instrument_id, p.pricing_policy_id): p
                for p in PriceHistory.objects.filter(instrument__in=instruments_pk, date=self.date_to)
            }

            instrument_price_missed_objects = []
            for instrument_id, pricing_policy_id in instrument_price_missed:
                op = existed_instrument_prices.get((instrument_id, pricing_policy_id), None)
                if op is None:
                    op = PriceHistory(instrument_id=instrument_id, pricing_policy_id=pricing_policy_id,
                                      date=self.date_to)
                instrument_price_missed_objects.append(op)
            return instrument_price_missed_objects
        return []

    @property
    def currency_price_missed(self):
        if not self.is_yesterday:
            return []
        result = getattr(self.task_object, 'result_object', {})
        currency_price_missed = result.get('currency_price_missed', None)
        if currency_price_missed:
            currencies_pk = [instr_id for instr_id, _ in currency_price_missed]
            existed_currency_prices = {
                (p.currency_id, p.pricing_policy_id): p
                for p in CurrencyHistory.objects.filter(currency__in=currencies_pk, date=self.date_to)
            }
            currency_price_missed_objects = []
            for currency_id, pricing_policy_id in currency_price_missed:
                op = existed_currency_prices.get((currency_id, pricing_policy_id), None)
                if op is None:
                    op = CurrencyHistory(currency_id=currency_id, pricing_policy_id=pricing_policy_id,
                                         date=self.date_to)
                currency_price_missed_objects.append(op)
            return currency_price_missed_objects
        return []


class ImportPricingSerializer(serializers.Serializer):
    master_user = MasterUserField()
    member = HiddenMemberField()

    date_from = serializers.DateField(allow_null=True, required=False)
    date_to = serializers.DateField(allow_null=True, required=False)
    is_yesterday = serializers.BooleanField(read_only=True)
    balance_date = serializers.DateField(allow_null=True, required=False)
    fill_days = serializers.IntegerField(initial=0, default=0, min_value=0)
    override_existed = serializers.BooleanField()

    task = serializers.IntegerField(required=False, allow_null=True)
    task_object = TaskSerializer(read_only=True)

    errors = serializers.ReadOnlyField()
    instrument_price_missed = serializers.ReadOnlyField()
    currency_price_missed = serializers.ReadOnlyField()

    def __init__(self, **kwargs):
        super(ImportPricingSerializer, self).__init__(**kwargs)

        from poms.instruments.serializers import PriceHistorySerializer
        self.fields['instrument_price_missed'] = PriceHistorySerializer(read_only=True, many=True)

        from poms.currencies.serializers import CurrencyHistorySerializer
        self.fields['currency_price_missed'] = CurrencyHistorySerializer(read_only=True, many=True)

    def validate(self, attrs):
        attrs = super(ImportPricingSerializer, self).validate(attrs)

        yesterday = timezone.now().date() - timedelta(days=1)

        date_from = attrs.get('date_from', yesterday) or yesterday
        date_to = attrs.get('date_to', yesterday) or yesterday
        if date_from > date_to:
            raise serializers.ValidationError({
                'date_from': ugettext('Invalid date range'),
                'date_to': ugettext('Invalid date range'),
            })

        balance_date = attrs.get('balance_date', date_to) or date_to
        is_yesterday = (date_from == yesterday) and (date_to == yesterday)

        attrs['date_from'] = date_from
        attrs['date_to'] = date_to
        attrs['balance_date'] = balance_date
        attrs['is_yesterday'] = is_yesterday
        attrs['fill_days'] = attrs.get('fill_days', 0) if is_yesterday else 0

        return attrs

    def create(self, validated_data):
        instance = ImportPricingEntry(**validated_data)

        if instance.task:
            task, is_ready = download_pricing(
                master_user=instance.master_user,
                fill_days=instance.fill_days,
                override_existed=instance.override_existed,
                task=instance.task_object
            )
            instance.task_object = task
        else:
            task, is_ready = download_pricing(
                master_user=instance.master_user,
                member=instance.member,
                date_from=instance.date_from,
                date_to=instance.date_to,
                is_yesterday=instance.is_yesterday,
                balance_date=instance.balance_date,
                fill_days=instance.fill_days,
                override_existed=instance.override_existed
            )
            instance.task_object = task
        return instance


class TestCertificateSerializer(serializers.Serializer):
    master_user = MasterUserField()
    member = HiddenMemberField()

    task = serializers.IntegerField(required=False, allow_null=True)
    task_object = TaskSerializer(read_only=True)

    provider_id = serializers.ReadOnlyField()

    def __init__(self, **kwargs):
        super(TestCertificateSerializer, self).__init__(**kwargs)

    def validate(self, attrs):
        attrs = super(TestCertificateSerializer, self).validate(attrs)

        return attrs

    def create(self, validated_data):

        instance = ImportTestCertificate(**validated_data)

        if instance.task:
            task, is_ready = test_certificate(
                master_user=instance.master_user,
                member=instance.member,
                task=instance.task_object
            )
            instance.task_object = task
        else:
            task, is_ready = test_certificate(
                master_user=instance.master_user,
                member=instance.member
            )
            instance.task_object = task

        return instance


# ----------------------------------------


class ComplexTransactionImportSchemeInputSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    name = serializers.CharField(max_length=255, allow_null=False, allow_blank=False,
                                 validators=[
                                     serializers.RegexValidator(regex='\A[a-zA-Z_][a-zA-Z0-9_]*\Z'),
                                 ])

    name_expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH)

    class Meta:
        model = ComplexTransactionImportSchemeInput
        fields = ['id', 'name', 'column', 'name_expr']


class ComplexTransactionImportSchemeFieldSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    transaction_type_input = TransactionTypeInputField()

    class Meta:
        model = ComplexTransactionImportSchemeField
        fields = ['id', 'transaction_type_input', 'value_expr', ]

    def __init__(self, *args, **kwargs):
        super(ComplexTransactionImportSchemeFieldSerializer, self).__init__(*args, **kwargs)

        # TODO: circular import error
        # from poms.transactions.serializers import TransactionTypeInputViewSerializer
        # self.fields['transaction_type_input_object'] = TransactionTypeInputViewSerializer(
        #     source='transaction_type_input', read_only=True)
        pass

    def to_representation(self, instance):
        ret = super(ComplexTransactionImportSchemeFieldSerializer, self).to_representation(instance)

        if instance.transaction_type_input:
            from poms.transactions.serializers import TransactionTypeInputViewSerializer
            s = TransactionTypeInputViewSerializer(instance=instance.transaction_type_input, read_only=True,
                                                   context=self.context)
            ret['transaction_type_input_object'] = s.data

        return ret

        # def to_internal_value(self, data):
        #     _l.error('ComplexTransactionImportSchemeInputSerializer.to_internal_value >')
        #     ret = super(ComplexTransactionImportSchemeFieldSerializer, self).to_internal_value(data)
        #     _l.error('ComplexTransactionImportSchemeInputSerializer.to_internal_value <')
        #     return ret
        #
        # def validate(self, attrs):
        #     _l.error('ComplexTransactionImportSchemeInputSerializer.validate')
        #     transaction_type_input = attrs['transaction_type_input']
        #     # if transaction_type_input.transaction_type_id != rule.transaction_type_id:
        #     #     raise serializers.ValidationError(
        #     #         {'transaction_type_input': ugettext('Invalid transaction type input')})
        #
        #     return attrs


class ComplexTransactionImportSchemeRuleSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    transaction_type = TransactionTypeField()
    fields = ComplexTransactionImportSchemeFieldSerializer(many=True, read_only=False)

    class Meta:
        model = ComplexTransactionImportSchemeRule
        fields = ['id', 'value', 'transaction_type', 'fields']

    def __init__(self, *args, **kwargs):
        super(ComplexTransactionImportSchemeRuleSerializer, self).__init__(*args, **kwargs)

        # TODO: circular import error
        # from poms.transactions.serializers import TransactionTypeViewSerializer
        # self.fields['transaction_type_object'] = TransactionTypeViewSerializer(source='transaction_type',
        #                                                                        read_only=True)
        pass

    def to_representation(self, instance):
        ret = super(ComplexTransactionImportSchemeRuleSerializer, self).to_representation(instance)

        if instance.transaction_type:
            from poms.transactions.serializers import TransactionTypeViewSerializer
            s = TransactionTypeViewSerializer(instance=instance.transaction_type, read_only=True, context=self.context)
            ret['transaction_type_object'] = s.data
        return ret

        # def to_internal_value(self, data):
        #     _l.error('ComplexTransactionImportSchemeRuleSerializer.to_internal_value >')
        #     ret = super(ComplexTransactionImportSchemeRuleSerializer, self).to_internal_value(data)
        #     _l.error('ComplexTransactionImportSchemeRuleSerializer.to_internal_value <')
        #     return ret
        #
        # def validate(self, attrs):
        #     _l.error('ComplexTransactionImportSchemeRuleSerializer.validate')
        #     return attrs


class ComplexTransactionImportSchemeSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    rule_expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH)

    inputs = ComplexTransactionImportSchemeInputSerializer(many=True, read_only=False)
    rules = ComplexTransactionImportSchemeRuleSerializer(many=True, read_only=False)

    class Meta:
        model = ComplexTransactionImportScheme
        fields = ['id', 'master_user', 'scheme_name', 'rule_expr', 'inputs', 'rules', ]

    def __init__(self, *args, **kwargs):
        super(ComplexTransactionImportSchemeSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        inputs = validated_data.pop('inputs', None) or []
        rules = validated_data.pop('rules', None) or []
        instance = super(ComplexTransactionImportSchemeSerializer, self).create(validated_data)
        self.save_inputs(instance, inputs)
        self.save_rules(instance, rules)
        return instance

    def update(self, instance, validated_data):
        inputs = validated_data.pop('inputs', empty)
        rules = validated_data.pop('rules', empty)
        instance = super(ComplexTransactionImportSchemeSerializer, self).update(instance, validated_data)
        if inputs is not empty:
            self.save_inputs(instance, inputs)
        if rules is not empty:
            self.save_rules(instance, rules)
        return instance

    def save_inputs(self, instance, inputs):
        pk_set = set()
        for input_values in inputs:
            input_id = input_values.pop('id', None)
            input0 = None
            if input_id:
                try:
                    input0 = instance.inputs.get(pk=input_id)
                except ObjectDoesNotExist:
                    pass
            if input0 is None:
                input0 = ComplexTransactionImportSchemeInput(scheme=instance)
            for name, value in input_values.items():
                setattr(input0, name, value)
            input0.save()
            pk_set.add(input0.id)
        instance.inputs.exclude(pk__in=pk_set).delete()

    def save_rules(self, instance, rules):
        pk_set = set()
        for rule_values in rules:
            rule_id = rule_values.pop('id', None)
            rule0 = None
            if rule_id:
                try:
                    rule0 = instance.rules.get(pk=rule_id)
                except ObjectDoesNotExist:
                    pass
            if rule0 is None:
                rule0 = ComplexTransactionImportSchemeRule(scheme=instance)

            fields = rule_values.pop('fields', empty) or []
            for name, value in rule_values.items():
                setattr(rule0, name, value)
            rule0.save()
            self.save_fields(rule0, fields)
            pk_set.add(rule0.id)
        instance.rules.exclude(pk__in=pk_set).delete()

    def save_fields(self, rule, fields):
        pk_set = set()
        for field_values in fields:
            field_id = field_values.pop('id', None)
            field0 = None
            if field_id:
                try:
                    field0 = rule.fields.get(pk=field_id)
                except ObjectDoesNotExist:
                    pass
            if field0 is None:
                field0 = ComplexTransactionImportSchemeField(rule=rule)
            for name, value in field_values.items():
                setattr(field0, name, value)

            # TODO check why is that?
            # if field0.transaction_type_input.transaction_type_id != rule.transaction_type_id:
            #     raise serializers.ValidationError(ugettext('Invalid transaction type input. (Hacker has detected!)'))

            field0.save()
            pk_set.add(field0.id)
        rule.fields.exclude(pk__in=pk_set).delete()


class ComplexTransactionCsvFileImport:
    def __init__(self, task_id=None, task_status=None, master_user=None, member=None,
                 scheme=None, file_path=None, skip_first_line=None, delimiter=None, quotechar=None, encoding=None,
                 error_handling=None, missing_data_handler=None, error=None, error_message=None, error_row_index=None,
                 error_rows=None,
                 total_rows=None, processed_rows=None):
        self.task_id = task_id
        self.task_status = task_status

        self.master_user = master_user
        self.member = member

        self.scheme = scheme
        self.file_path = file_path
        self.skip_first_line = bool(skip_first_line)
        self.delimiter = delimiter or ','
        self.quotechar = quotechar or '"'
        self.encoding = encoding or 'utf-8'

        self.error_handling = error_handling or 'continue'
        self.missing_data_handler = missing_data_handler or 'throw_error'
        self.error = error
        self.error_message = error_message
        self.error_row_index = error_row_index
        self.error_rows = error_rows
        self.total_rows = total_rows
        self.processed_rows = processed_rows

    def __str__(self):
        return '%s-%s:%s' % (getattr(self.master_user, 'id', None), getattr(self.member, 'id', None), self.file_path)

    @property
    def break_on_error(self):
        return self.error_handling == 'break'

    @property
    def continue_on_error(self):
        return self.error_handling == 'continue'


class ComplexTransactionCsvFileImportSerializer(serializers.Serializer):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    master_user = MasterUserField()
    member = HiddenMemberField()

    scheme = ComplexTransactionImportSchemeRestField(required=False)
    file = serializers.FileField(required=False, allow_null=True)
    skip_first_line = serializers.BooleanField(required=False, default=True)
    delimiter = serializers.CharField(max_length=2, required=False, initial=',', default=',')
    quotechar = serializers.CharField(max_length=1, required=False, initial='"', default='"')
    encoding = serializers.CharField(max_length=20, required=False, initial='utf-8', default='utf-8')

    error_handling = serializers.ChoiceField(
        choices=[('break', 'Break on first error'), ('continue', 'Try continue')],
        required=False, initial='continue', default='continue'
    )

    missing_data_handler = serializers.ChoiceField(
        choices=[('throw_error', 'Treat as Error'), ('set_defaults', 'Replace with Default Value')],
        required=False, initial='throw_error', default='throw_error'
    )

    error = serializers.ReadOnlyField()
    error_message = serializers.ReadOnlyField()
    error_row_index = serializers.ReadOnlyField()
    error_rows = serializers.ReadOnlyField()
    processed_rows = serializers.ReadOnlyField()
    total_rows = serializers.ReadOnlyField()

    scheme_object = ComplexTransactionImportSchemeSerializer(source='scheme', read_only=True)

    def create(self, validated_data):
        if validated_data.get('task_id', None):
            validated_data.pop('file', None)
        else:
            file = validated_data.pop('file', None)
            if file:
                master_user = validated_data['master_user']
                file_name = '%s-%s' % (timezone.now().strftime('%Y%m%d%H%M%S'), uuid.uuid4().hex)
                file_path = self._get_path(master_user, file_name)
                import_file_storage.save(file_path, file)
                validated_data['file_path'] = file_path
            else:
                raise serializers.ValidationError({'file': ugettext('Required field.')})
        return ComplexTransactionCsvFileImport(**validated_data)

    def _get_path(self, owner, file_name):
        return '%s/%s.dat' % (owner.pk, file_name)

        # def create(self, validated_data):
        #     _l.info('create: %s', validated_data)
        #     try:
        #         master_user = validated_data['master_user']
        #
        #         if validated_data.get('token', None):
        #             file = None
        #             try:
        #                 token = TimestampSigner().unsign(validated_data['token'])
        #                 # token = loads(validated_data['token'])
        #             except BadSignature:
        #                 raise serializers.ValidationError({'token': ugettext('Invalid token.')})
        #             remote_file_path = self._get_path(master_user, token)
        #         else:
        #             file = validated_data['file']
        #             if not file:
        #                 raise serializers.ValidationError({'file': ugettext('This field is required.')})
        #
        #             token = '%s-%s' % (timezone.now().strftime('%Y%m%d%H%M%S'), uuid.uuid4().hex)
        #             # token = {'token': str(uuid.uuid4()), 'date': timezone.now()}
        #             # validated_data['token'] = dumps(token)
        #             validated_data['token'] = TimestampSigner().sign(token)
        #             remote_file_path = self._get_path(master_user, token)
        #
        #             import_file_storage.save(remote_file_path, file)
        #
        #             from poms.integrations.tasks import schedule_file_import_delete
        #             schedule_file_import_delete(remote_file_path)
        #
        #         try:
        #             with import_file_storage.open(remote_file_path, 'rb') as f:
        #                 with NamedTemporaryFile() as tmpf:
        #                     for chunk in f.chunks():
        #                         tmpf.write(chunk)
        #                     tmpf.flush()
        #                     with open(tmpf.name, mode='rt', encoding=validated_data.get('encoding', None)) as cf:
        #                         if validated_data['format'] == FILE_FORMAT_CSV:
        #                             self._read_csv(validated_data, File(cf))
        #
        #         except csv.Error:
        #             raise serializers.ValidationError(ugettext("Invalid file format or file already deleted."))
        #         except (FileNotFoundError, IOError):
        #             raise serializers.ValidationError(ugettext("Invalid file format or file already deleted."))
        #         except:
        #             raise serializers.ValidationError(ugettext("Invalid file format or file already deleted."))
        #
        #         # with import_file_storage.open(tmp_file_name, 'rb') as f:
        #         #     rows = []
        #         #     for row_index, row in enumerate(csv.reader(f)):
        #         #         if row_index == 0 and validated_data['skip_first_line']:
        #         #             continue
        #         #         rows.append(row)
        #         #     validated_data['rows'] = rows
        #
        #         return validated_data
        #     finally:
        #         if validated_data.get('mode', None) != IMPORT_PROCESS:
        #             transaction.set_rollback(True)
        #
        # def _get_path(self, owner, token):
        #     return '%s/%s/%s.dat' % (owner.pk, self.object_type, token)
        #
        # def _read_csv(self, validated_data, file):
        #     rows = []
        #     for row_index, row in enumerate(csv.reader(file, delimiter=validated_data['delimiter'],
        #                                                quotechar=validated_data['quotechar'])):
        #         if (row_index == 0 and validated_data['skip_first_line']) or not row:
        #             continue
        #         self._process_row(validated_data, row_index, row)
        #         rows.append(row)
        #     validated_data['rows'] = rows
        #
        # def _process_row(self, validated_data, row_index, row):
        #     pass
