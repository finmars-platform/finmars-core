from __future__ import unicode_literals

from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.serializers import ListSerializer

from poms.common.fields import ExpressionField, FloatEvalField, DateTimeTzAwareField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.common.serializers import PomsClassSerializer, ModelWithUserCodeSerializer
from poms.common.utils import date_now
from poms.currencies.fields import CurrencyDefault
from poms.currencies.serializers import CurrencyField
from poms.instruments.fields import InstrumentField, InstrumentTypeField, PricingPolicyField, InstrumentTypeDefault
from poms.instruments.models import Instrument, PriceHistory, InstrumentClass, DailyPricingModel, \
    AccrualCalculationModel, PaymentSizeDetail, Periodicity, CostMethod, InstrumentType, \
    ManualPricingFormula, AccrualCalculationSchedule, InstrumentFactorSchedule, EventSchedule, \
    PricingPolicy, EventScheduleAction, EventScheduleConfig, GeneratedEvent
from poms.integrations.fields import PriceDownloadSchemeField
from poms.obj_attrs.serializers import ModelWithAttributesSerializer
from poms.obj_perms.serializers import ModelWithObjectPermissionSerializer
from poms.pricing.serializers import InstrumentPricingSchemeSerializer, CurrencyPricingSchemeSerializer
from poms.tags.serializers import ModelWithTagSerializer
from poms.transactions.fields import TransactionTypeField
from poms.users.fields import MasterUserField


class InstrumentClassSerializer(PomsClassSerializer):
    class Meta(PomsClassSerializer.Meta):
        model = InstrumentClass


class InstrumentClassViewSerializer(PomsClassSerializer):
    class Meta:
        model = InstrumentClass
        fields = ['id', 'system_code', 'name']


class DailyPricingModelSerializer(PomsClassSerializer):
    class Meta(PomsClassSerializer.Meta):
        model = DailyPricingModel


class DailyPricingModelViewSerializer(PomsClassSerializer):
    class Meta:
        model = DailyPricingModel
        fields = ['id', 'system_code', 'name']


class AccrualCalculationModelSerializer(PomsClassSerializer):
    class Meta(PomsClassSerializer.Meta):
        model = AccrualCalculationModel


class AccrualCalculationModelViewSerializer(PomsClassSerializer):
    class Meta:
        model = AccrualCalculationModel
        fields = ['id', 'system_code', 'name']


class PaymentSizeDetailSerializer(PomsClassSerializer):
    class Meta(PomsClassSerializer.Meta):
        model = PaymentSizeDetail


class PaymentSizeDetailViewSerializer(PomsClassSerializer):
    class Meta:
        model = PaymentSizeDetail
        fields = ['id', 'system_code', 'name']


class PeriodicitySerializer(PomsClassSerializer):
    class Meta(PomsClassSerializer.Meta):
        model = Periodicity


class PeriodicityViewSerializer(PomsClassSerializer):
    class Meta:
        model = Periodicity
        fields = ['id', 'system_code', 'name']


class CostMethodSerializer(PomsClassSerializer):
    class Meta(PomsClassSerializer.Meta):
        model = CostMethod


class CostMethodViewSerializer(PomsClassSerializer):
    class Meta:
        model = CostMethod
        fields = ['id', 'system_code', 'name']


class PricingPolicySerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()
    expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, allow_blank=False, allow_null=False)

    class Meta:
        model = PricingPolicy
        fields = ['id', 'master_user', 'user_code', 'name', 'short_name', 'notes', 'expr',
                  'default_instrument_pricing_scheme', 'default_currency_pricing_scheme']

    def __init__(self, *args, **kwargs):
        super(PricingPolicySerializer, self).__init__(*args, **kwargs)

        self.fields['default_instrument_pricing_scheme_object'] = InstrumentPricingSchemeSerializer(source='default_instrument_pricing_scheme', read_only=True)
        self.fields['default_currency_pricing_scheme_object'] = CurrencyPricingSchemeSerializer(source='default_currency_pricing_scheme', read_only=True)



class PricingPolicyViewSerializer(ModelWithUserCodeSerializer):
    class Meta:
        model = PricingPolicy
        fields = ['id', 'user_code', 'name', 'short_name', 'notes', 'expr']


# class InstrumentClassifierSerializer(AbstractClassifierSerializer):
#     class Meta(AbstractClassifierSerializer.Meta):
#         model = InstrumentClassifier
#
#
# class InstrumentClassifierNodeSerializer(AbstractClassifierNodeSerializer):
#     class Meta(AbstractClassifierNodeSerializer.Meta):
#         model = InstrumentClassifier


class InstrumentTypeSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer,
                               ModelWithTagSerializer, ModelWithAttributesSerializer):
    master_user = MasterUserField()
    instrument_class_object = InstrumentClassSerializer(source='instrument_class', read_only=True)
    one_off_event = TransactionTypeField(allow_null=True, required=False)
    one_off_event_object = serializers.PrimaryKeyRelatedField(source='one_off_event', read_only=True)
    regular_event = TransactionTypeField(allow_null=True, required=False)
    regular_event_object = serializers.PrimaryKeyRelatedField(source='regular_event', read_only=True)
    factor_same = TransactionTypeField(allow_null=True, required=False)
    factor_same_object = serializers.PrimaryKeyRelatedField(source='factor_same', read_only=True)
    factor_up = TransactionTypeField(allow_null=True, required=False)
    factor_up_object = serializers.PrimaryKeyRelatedField(source='factor_up', read_only=True)
    factor_down = TransactionTypeField(allow_null=True, required=False)
    factor_down_object = serializers.PrimaryKeyRelatedField(source='factor_down', read_only=True)

    # tags = TagField(many=True, required=False, allow_null=True)
    # tags_object = TagViewSerializer(source='tags', many=True, read_only=True)

    class Meta:
        model = InstrumentType
        fields = [
            'id', 'master_user', 'instrument_class', 'instrument_class_object',
            'user_code', 'name', 'short_name', 'public_name',
            'notes', 'is_default', 'is_deleted', 'one_off_event', 'one_off_event_object',
            'regular_event', 'regular_event_object', 'factor_same', 'factor_same_object',
            'factor_up', 'factor_up_object', 'factor_down', 'factor_down_object',
            'is_enabled'
            # 'tags', 'tags_object',
        ]

    def __init__(self, *args, **kwargs):
        super(InstrumentTypeSerializer, self).__init__(*args, **kwargs)

        from poms.transactions.serializers import TransactionTypeViewSerializer
        self.fields['one_off_event_object'] = TransactionTypeViewSerializer(source='one_off_event', read_only=True)
        self.fields['regular_event_object'] = TransactionTypeViewSerializer(source='regular_event', read_only=True)
        self.fields['factor_same_object'] = TransactionTypeViewSerializer(source='factor_same', read_only=True)
        self.fields['factor_up_object'] = TransactionTypeViewSerializer(source='factor_up', read_only=True)
        self.fields['factor_down_object'] = TransactionTypeViewSerializer(source='factor_down', read_only=True)

    def validate(self, attrs):
        instrument_class = attrs.get('instrument_class', None)
        one_off_event = attrs.get('one_off_event', None)
        regular_event = attrs.get('regular_event', None)

        if instrument_class:
            errors = {}
            if instrument_class.has_one_off_event and one_off_event is None:
                errors['one_off_event'] = self.fields['one_off_event'].error_messages['required']
            if instrument_class.has_regular_event and regular_event is None:
                errors['regular_event'] = self.fields['regular_event'].error_messages['required']

            if errors:
                raise ValidationError(errors)

        return attrs


class InstrumentTypeViewSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer):
    instrument_class_object = InstrumentClassSerializer(source='instrument_class', read_only=True)

    class Meta:
        model = InstrumentType
        fields = [
            'id', 'instrument_class', 'instrument_class_object', 'user_code', 'name', 'short_name',
            'public_name',
        ]


# class InstrumentAttributeTypeSerializer(AbstractAttributeTypeSerializer):
#     classifiers = InstrumentClassifierSerializer(required=False, allow_null=True, many=True)
#
#     class Meta(AbstractAttributeTypeSerializer.Meta):
#         model = InstrumentAttributeType
#         fields = AbstractAttributeTypeSerializer.Meta.fields + ['classifiers']
#
#
# class InstrumentAttributeTypeViewSerializer(AbstractAttributeTypeSerializer):
#     class Meta(AbstractAttributeTypeSerializer.Meta):
#         model = InstrumentAttributeType
#
#
# class InstrumentAttributeSerializer(AbstractAttributeSerializer):
#     attribute_type = InstrumentAttributeTypeField()
#     classifier = InstrumentClassifierField(required=False, allow_null=True)
#
#     class Meta(AbstractAttributeSerializer.Meta):
#         model = InstrumentAttribute
#         fields = AbstractAttributeSerializer.Meta.fields + ['attribute_type', 'classifier']


class InstrumentSerializer(ModelWithAttributesSerializer, ModelWithObjectPermissionSerializer,
                           ModelWithUserCodeSerializer, ModelWithTagSerializer):
    master_user = MasterUserField()
    instrument_type = InstrumentTypeField(default=InstrumentTypeDefault())
    instrument_type_object = InstrumentTypeViewSerializer(source='instrument_type', read_only=True)
    pricing_currency = CurrencyField(default=CurrencyDefault())
    pricing_currency_object = serializers.PrimaryKeyRelatedField(source='pricing_currency', read_only=True)
    accrued_currency = CurrencyField(default=CurrencyDefault())
    accrued_currency_object = serializers.PrimaryKeyRelatedField(source='accrued_currency', read_only=True)
    payment_size_detail_object = PaymentSizeDetailSerializer(source='payment_size_detail', read_only=True)
    daily_pricing_model_object = DailyPricingModelSerializer(source='daily_pricing_model', read_only=True)
    price_download_scheme = PriceDownloadSchemeField(allow_null=True, required=False)
    price_download_scheme_object = serializers.PrimaryKeyRelatedField(source='price_download_scheme', read_only=True)

    manual_pricing_formulas = serializers.PrimaryKeyRelatedField(many=True, required=False, allow_null=True,
                                                                 read_only=True)
    accrual_calculation_schedules = serializers.PrimaryKeyRelatedField(many=True, required=False, allow_null=True,
                                                                       read_only=True)
    factor_schedules = serializers.PrimaryKeyRelatedField(many=True, required=False, allow_null=True, read_only=True)
    event_schedules = serializers.PrimaryKeyRelatedField(many=True, required=False, allow_null=True, read_only=True)

    # attributes = InstrumentAttributeSerializer(many=True, required=False, allow_null=True)

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
            'maturity_date', 'maturity_price',
            'manual_pricing_formulas', 'accrual_calculation_schedules', 'factor_schedules', 'event_schedules',
            'is_enabled'
            # 'attributes',
            # 'tags', 'tags_object'
        ]

    def __init__(self, *args, **kwargs):
        super(InstrumentSerializer, self).__init__(*args, **kwargs)

        from poms.currencies.serializers import CurrencyViewSerializer
        self.fields['pricing_currency_object'] = CurrencyViewSerializer(source='pricing_currency', read_only=True)
        self.fields['accrued_currency_object'] = CurrencyViewSerializer(source='accrued_currency', read_only=True)

        from poms.integrations.serializers import PriceDownloadSchemeViewSerializer
        self.fields['price_download_scheme_object'] = PriceDownloadSchemeViewSerializer(source='price_download_scheme',
                                                                                        read_only=True)

        self.fields['manual_pricing_formulas'] = ManualPricingFormulaSerializer(many=True, required=False,
                                                                                allow_null=True)
        self.fields['accrual_calculation_schedules'] = AccrualCalculationScheduleSerializer(many=True, required=False,
                                                                                            allow_null=True)
        self.fields['factor_schedules'] = InstrumentFactorScheduleSerializer(many=True, required=False, allow_null=True)
        self.fields['event_schedules'] = EventScheduleSerializer(many=True, required=False, allow_null=True)

    def create(self, validated_data):
        manual_pricing_formulas = validated_data.pop('manual_pricing_formulas', None)
        accrual_calculation_schedules = validated_data.pop('accrual_calculation_schedules', None)
        factor_schedules = validated_data.pop('factor_schedules', None)
        event_schedules = validated_data.pop('event_schedules', None)

        instance = super(InstrumentSerializer, self).create(validated_data)

        self.save_manual_pricing_formulas(instance, True, manual_pricing_formulas)
        self.save_accrual_calculation_schedules(instance, True, accrual_calculation_schedules)
        self.save_factor_schedules(instance, True, factor_schedules)
        self.save_event_schedules(instance, True, event_schedules)

        # self.rebuild_event_schedules(instance, True)

        return instance

    def update(self, instance, validated_data):
        manual_pricing_formulas = validated_data.pop('manual_pricing_formulas', empty)
        accrual_calculation_schedules = validated_data.pop('accrual_calculation_schedules', empty)
        factor_schedules = validated_data.pop('factor_schedules', empty)
        event_schedules = validated_data.pop('event_schedules', empty)

        instance = super(InstrumentSerializer, self).update(instance, validated_data)

        if manual_pricing_formulas is not empty:
            self.save_manual_pricing_formulas(instance, False, manual_pricing_formulas)
        if accrual_calculation_schedules is not empty:
            self.save_accrual_calculation_schedules(instance, False, accrual_calculation_schedules)
        if factor_schedules is not empty:
            self.save_factor_schedules(instance, False, factor_schedules)
        if event_schedules is not empty:
            self.save_event_schedules(instance, False, event_schedules)

        self.calculate_prices_accrued_price(instance, False)
        # self.rebuild_event_schedules(instance, False)

        return instance

    def save_instr_related(self, instrument, created, instrument_attr, model, validated_data, accept=None):
        validated_data = validated_data or []
        # if validated_data is None:
        #     return

        related_attr = getattr(instrument, instrument_attr)
        processed = {}

        for attr in validated_data:
            oid = attr.get('id', None)
            if oid:
                try:
                    o = related_attr.get(id=oid)
                except ObjectDoesNotExist:
                    o = model(instrument=instrument)
            else:
                o = model(instrument=instrument)
            if callable(accept):
                if not accept(attr, o):
                    if o:
                        processed[o.id] = o
                    continue
            for k, v in attr.items():
                if k not in ['id', 'instrument', 'actions']:
                    setattr(o, k, v)
            o.save()
            processed[o.id] = o
            attr['id'] = o.id

        if not created:
            related_attr.exclude(id__in=processed.keys()).delete()

        return processed

    def save_manual_pricing_formulas(self, instrument, created, manual_pricing_formulas):
        self.save_instr_related(instrument, created, 'manual_pricing_formulas', ManualPricingFormula,
                                manual_pricing_formulas)

    def save_accrual_calculation_schedules(self, instrument, created, accrual_calculation_schedules):
        self.save_instr_related(instrument, created, 'accrual_calculation_schedules', AccrualCalculationSchedule,
                                accrual_calculation_schedules)

    def save_factor_schedules(self, instrument, created, factor_schedules):
        self.save_instr_related(instrument, created, 'factor_schedules', InstrumentFactorSchedule, factor_schedules)

    def save_event_schedules(self, instrument, created, event_schedules):
        event_schedules = event_schedules or []
        events = self.save_instr_related(instrument, created, 'event_schedules', EventSchedule, event_schedules,
                                         accept=lambda attr, obj: not obj.is_auto_generated if obj else True)

        for es in event_schedules:
            try:
                event_schedule = events[es['id']]
            except KeyError:
                continue
            if event_schedule.is_auto_generated:
                continue

            actions_data = es.get('actions', None)
            if actions_data is None:
                continue

            processed = set()
            for action_data in actions_data:
                oid = action_data.get('id', None)
                if oid:
                    try:
                        o = event_schedule.actions.get(id=oid)
                    except ObjectDoesNotExist:
                        o = EventScheduleAction(event_schedule=event_schedule)
                else:
                    o = EventScheduleAction(event_schedule=event_schedule)

                for k, v in action_data.items():
                    if k not in ['id', 'event_schedule', ]:
                        setattr(o, k, v)
                o.save()
                processed.add(o.id)
                action_data['id'] = o.id

            if not created:
                event_schedule.actions.exclude(id__in=processed).delete()

    def calculate_prices_accrued_price(self, instrument, created):
        instrument.calculate_prices_accrued_price()

    def rebuild_event_schedules(self, instrument, created):
        try:
            instrument.rebuild_event_schedules()
        except ValueError as e:
            raise ValidationError({'instrument_type': '%s' % e})


class InstrumentViewSerializer(ModelWithObjectPermissionSerializer):
    instrument_type_object = InstrumentTypeViewSerializer(source='instrument_type', read_only=True)

    # pricing_currency_object = serializers.PrimaryKeyRelatedField(source='pricing_currency', read_only=True)
    # accrued_currency_object = serializers.PrimaryKeyRelatedField(source='accrued_currency', read_only=True)

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Instrument
        fields = [
            'id', 'instrument_type', 'instrument_type_object', 'user_code', 'name', 'short_name',
            'public_name', 'notes', 'is_active', 'is_deleted',
            # 'pricing_currency', 'pricing_currency_object', 'price_multiplier',
            # 'accrued_currency', 'accrued_currency_object', 'accrued_multiplier',
            # 'payment_size_detail', 'payment_size_detail_object', 'default_price', 'default_accrued',
            'user_text_1', 'user_text_2', 'user_text_3',
            'maturity_date',
        ]

    def __init__(self, *args, **kwargs):
        super(InstrumentViewSerializer, self).__init__(*args, **kwargs)

        # from poms.currencies.serializers import CurrencyViewSerializer
        # self.fields['pricing_currency_object'] = CurrencyViewSerializer(source='pricing_currency', read_only=True)
        # self.fields['accrued_currency_object'] = CurrencyViewSerializer(source='accrued_currency', read_only=True)


class ManualPricingFormulaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    pricing_policy = PricingPolicyField(allow_null=False)
    pricing_policy_object = PricingPolicyViewSerializer(source='pricing_policy', read_only=True)

    class Meta:
        model = ManualPricingFormula
        fields = ['id', 'pricing_policy', 'pricing_policy_object', 'expr', 'notes']


class AccrualCalculationScheduleSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    periodicity_n = serializers.IntegerField(required=False, default=0, initial=0, min_value=0, max_value=10 * 365)
    accrual_calculation_model_object = AccrualCalculationModelSerializer(source='accrual_calculation_model',
                                                                         read_only=True)
    periodicity_object = PeriodicitySerializer(source='periodicity', read_only=True)

    class Meta:
        model = AccrualCalculationSchedule
        fields = [
            'id', 'accrual_start_date', 'first_payment_date', 'accrual_size', 'accrual_calculation_model',
            'accrual_calculation_model_object', 'periodicity', 'periodicity_object', 'periodicity_n', 'notes']

    def validate(self, attrs):
        periodicity = attrs['periodicity']
        if periodicity:
            periodicity_n = attrs.get('periodicity_n', 0)
            try:
                periodicity.to_timedelta(n=periodicity_n)
            except ValueError:
                v = serializers.MinValueValidator(1)
                try:
                    v(periodicity_n)
                except serializers.ValidationError as e:
                    raise ValidationError({'periodicity_n': [str(e)]})
                except serializers.DjangoValidationError as e:
                    raise ValidationError({'periodicity_n': e.messages})
        return attrs


class InstrumentFactorScheduleSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)

    class Meta:
        model = InstrumentFactorSchedule
        fields = ['id', 'effective_date', 'factor_value']


class EventScheduleActionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    text = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=True, allow_blank=True, allow_null=True)
    transaction_type = TransactionTypeField()
    transaction_type_object = serializers.PrimaryKeyRelatedField(source='transaction_type', read_only=True)
    display_text = serializers.SerializerMethodField()

    class Meta:
        model = EventScheduleAction
        fields = ['id', 'transaction_type', 'transaction_type_object', 'text', 'is_sent_to_pending',
                  'is_book_automatic', 'button_position', 'display_text']

    def __init__(self, *args, **kwargs):
        super(EventScheduleActionSerializer, self).__init__(*args, **kwargs)

        from poms.transactions.serializers import TransactionTypeViewSerializer
        self.fields['transaction_type_object'] = TransactionTypeViewSerializer(source='transaction_type',
                                                                               read_only=True)

    def get_display_text(self, obj):
        r = self.root
        if isinstance(r, ListSerializer):
            r = r.child
        if isinstance(r, GeneratedEventSerializer):
            return r.generate_text(obj.text)
        return None


class EventScheduleSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    periodicity_n = serializers.IntegerField(required=False, default=0, initial=0, min_value=0, max_value=10 * 365)
    actions = EventScheduleActionSerializer(many=True, required=False, allow_null=True)
    event_class_object = serializers.PrimaryKeyRelatedField(source='event_class', read_only=True)
    notification_class_object = serializers.PrimaryKeyRelatedField(source='notification_class', read_only=True)
    periodicity_object = PeriodicitySerializer(source='periodicity', read_only=True)
    name = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=True, allow_blank=True, allow_null=True)
    description = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, allow_null=True)

    display_name = serializers.SerializerMethodField()
    display_description = serializers.SerializerMethodField()

    class Meta:
        model = EventSchedule
        fields = [
            'id', 'name', 'description', 'event_class', 'event_class_object', 'notification_class',
            'notification_class_object', 'effective_date', 'notify_in_n_days', 'periodicity', 'periodicity_object',
            'periodicity_n', 'final_date', 'is_auto_generated',
            'display_name', 'display_description',
            'actions',
        ]
        read_only_fields = ['is_auto_generated']

    def __init__(self, *args, **kwargs):
        super(EventScheduleSerializer, self).__init__(*args, **kwargs)

        from poms.transactions.serializers import EventClassSerializer, NotificationClassSerializer
        self.fields['event_class_object'] = EventClassSerializer(source='event_class', read_only=True)
        self.fields['notification_class_object'] = NotificationClassSerializer(source='notification_class',
                                                                               read_only=True)

    def validate(self, attrs):
        periodicity = attrs['periodicity']
        if periodicity:
            periodicity_n = attrs.get('periodicity_n', 0)
            try:
                periodicity.to_timedelta(n=periodicity_n)
            except ValueError:
                v = serializers.MinValueValidator(1)
                try:
                    v(periodicity_n)
                except serializers.ValidationError as e:
                    raise ValidationError({'periodicity_n': [str(e)]})
                except serializers.DjangoValidationError as e:
                    raise ValidationError({'periodicity_n': e.messages})
        return attrs

    def get_display_name(self, obj):
        r = self.root
        if isinstance(r, ListSerializer):
            r = r.child
        if isinstance(r, GeneratedEventSerializer):
            return r.generate_text(obj.name)
        return None

    def get_display_description(self, obj):
        r = self.root
        if isinstance(r, ListSerializer):
            r = r.child
        if isinstance(r, GeneratedEventSerializer):
            return r.generate_text(obj.description)
        return None


class InstrumentCalculatePricesAccruedPriceSerializer(serializers.Serializer):
    begin_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        begin_date = attrs.get('begin_date', None)
        end_date = attrs.get('end_date', None)
        if begin_date is None and end_date is None:
            attrs['begin_date'] = attrs['end_date'] = date_now() - timedelta(days=1)
        return attrs


class PriceHistorySerializer(serializers.ModelSerializer):
    instrument = InstrumentField()
    instrument_object = InstrumentViewSerializer(source='instrument', read_only=True)
    pricing_policy = PricingPolicyField(allow_null=False)
    pricing_policy_object = PricingPolicySerializer(source='pricing_policy', read_only=True)
    principal_price = FloatEvalField()
    accrued_price = FloatEvalField()

    class Meta:
        model = PriceHistory
        fields = [
            'id', 'instrument', 'instrument_object', 'pricing_policy', 'pricing_policy_object',
            'date', 'principal_price', 'accrued_price'
        ]

    def __init__(self, *args, **kwargs):
        super(PriceHistorySerializer, self).__init__(*args, **kwargs)
        # if 'request' not in self.context:
        #     self.fields.pop('url')


class GeneratedEventSerializer(serializers.ModelSerializer):
    status_date = DateTimeTzAwareField(read_only=True)
    # is_need_reaction = serializers.SerializerMethodField()
    is_need_reaction = serializers.BooleanField(read_only=True)

    class Meta:
        model = GeneratedEvent
        fields = [
            'id', 'effective_date', 'notification_date', 'status', 'status_date', 'event_schedule',
            'instrument', 'portfolio', 'account', 'strategy1', 'strategy2', 'strategy3', 'position',
            'is_need_reaction',
            'action', 'transaction_type', 'member',
        ]
        read_only_fields = fields

    def __init__(self, *args, **kwargs):
        super(GeneratedEventSerializer, self).__init__(*args, **kwargs)
        self._current_instance = None

        self.fields['event_schedule_object'] = EventScheduleSerializer(source='event_schedule', read_only=True)
        self.fields['instrument_object'] = InstrumentViewSerializer(source='instrument', read_only=True)

        from poms.portfolios.serializers import PortfolioViewSerializer
        self.fields['portfolio_object'] = PortfolioViewSerializer(source='portfolio', read_only=True)

        from poms.accounts.serializers import AccountViewSerializer
        self.fields['account_object'] = AccountViewSerializer(source='account', read_only=True)

        from poms.strategies.serializers import Strategy1ViewSerializer, Strategy2ViewSerializer, \
            Strategy3ViewSerializer
        self.fields['strategy1_object'] = Strategy1ViewSerializer(source='strategy1', read_only=True)
        self.fields['strategy2_object'] = Strategy2ViewSerializer(source='strategy2', read_only=True)
        self.fields['strategy3_object'] = Strategy3ViewSerializer(source='strategy3', read_only=True)

        self.fields['action_object'] = EventScheduleActionSerializer(source='action', read_only=True)

        from poms.transactions.serializers import TransactionTypeViewSerializer
        self.fields['transaction_type_object'] = TransactionTypeViewSerializer(source='transaction_type',
                                                                               read_only=True)

        from poms.users.serializers import MemberViewSerializer
        self.fields['member_object'] = MemberViewSerializer(source='member', read_only=True)

    def to_representation(self, instance):
        self._current_instance = instance
        try:
            return super(GeneratedEventSerializer, self).to_representation(instance)
        finally:
            self._current_instance = None

    # def get_is_need_reaction(self, obj):
    #     now = date_now()
    #     return obj.action is None and (
    #         obj.is_need_reaction_on_notification_date(now) or obj.is_need_reaction_on_effective_date(now)
    #     )

    def generate_text(self, exr, names=None):
        # # member = get_member_from_context(self.context)
        # names = names or {}
        # if obj is None:
        #     obj = self._current_instance
        # names.update({
        #     # 'event': obj,
        #     # 'effective_date': serializers.DateField().to_representation(obj.effective_date),
        #     # 'notification_date': serializers.DateField().to_representation(obj.notification_date),
        #     'effective_date': obj.effective_date,
        #     'notification_date': obj.notification_date,
        #     # 'event_schedule': obj.event_schedule,
        #     # 'instrument':  formula.get_model_data(obj.instrument, InstrumentViewSerializer, context=self.context),
        #     # 'portfolio': formula.get_model_data(obj.portfolio, PortfolioViewSerializer, context=self.context),
        #     # 'account': formula.get_model_data(obj.account, AccountViewSerializer, context=self.context),
        #     # 'strategy1': formula.get_model_data(obj.strategy1, Strategy1ViewSerializer, context=self.context),
        #     # 'strategy2': formula.get_model_data(obj.strategy2, Strategy2ViewSerializer, context=self.context),
        #     # 'strategy3': formula.get_model_data(obj.strategy3, Strategy3ViewSerializer, context=self.context),
        #     'instrument': obj.instrument,
        #     'portfolio': obj.portfolio,
        #     'account': obj.account,
        #     'strategy1': obj.strategy1,
        #     'strategy2': obj.strategy2,
        #     'strategy3': obj.strategy3,
        #     'position': obj.position,
        # })
        # # import json
        # # print(json.dumps(names, indent=2))
        # try:
        #     return formula.safe_eval(exr, names=names, context=self.context)
        # except formula.InvalidExpression as e:
        #     return '<InvalidExpression>'
        return self._current_instance.generate_text(exr, names=names, context=self.context)


class EventScheduleConfigSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    name = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH)
    description = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH)
    notification_class_object = serializers.PrimaryKeyRelatedField(source='notification_class', read_only=True)

    class Meta:
        model = EventScheduleConfig
        fields = [
            'id', 'master_user', 'name', 'description', 'notification_class', 'notification_class_object',
            'notify_in_n_days', 'action_text', 'action_is_sent_to_pending', 'action_is_book_automatic',
        ]

    def __init__(self, *args, **kwargs):
        super(EventScheduleConfigSerializer, self).__init__(*args, **kwargs)

        from poms.transactions.serializers import NotificationClassSerializer
        self.fields['notification_class_object'] = NotificationClassSerializer(source='notification_class',
                                                                               read_only=True)
