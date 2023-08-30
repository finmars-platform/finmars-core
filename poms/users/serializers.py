from __future__ import unicode_literals

import smtplib
from logging import getLogger

from django.conf import settings
from django.contrib.auth import get_user_model, authenticate, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.utils import translation
from django.utils.translation import gettext_lazy
from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.fields import empty
from rest_framework.validators import UniqueValidator

from poms.accounts.fields import AccountTypeField, AccountField
from poms.common.fields import DateTimeTzAwareField
from poms.common.finmars_authorizer import AuthorizerService
from poms.counterparties.fields import CounterpartyField, ResponsibleField, CounterpartyGroupField, \
    ResponsibleGroupField
from poms.currencies.fields import CurrencyField
from poms.instruments.fields import InstrumentTypeField, InstrumentField, PricingPolicyField, PeriodicityField
from poms.portfolios.fields import PortfolioField
from poms.strategies.fields import Strategy1Field, Strategy2Field, Strategy3Field, Strategy1SubgroupField, \
    Strategy1GroupField, Strategy2GroupField, Strategy2SubgroupField, Strategy3GroupField, Strategy3SubgroupField
from poms.transactions.fields import TransactionTypeField
from poms.ui.models import ListLayout, EditLayout
from poms.users.fields import MasterUserField, MemberField, GroupField, HiddenMemberField, RoleField, \
    AccessPolicyField
from poms.users.models import MasterUser, UserProfile,  Member, TIMEZONE_CHOICES,  \
    EcosystemDefault, OtpToken, UsercodePrefix
from poms.users.utils import get_user_from_context, get_master_user_from_context, get_member_from_context

_l = getLogger('poms.users')


class PingSerializer(serializers.Serializer):
    message = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)
    current_master_user_id = serializers.IntegerField(required=False, allow_null=True)
    current_member_id = serializers.IntegerField(required=False, allow_null=True)
    is_authenticated = serializers.BooleanField(read_only=True)
    is_anonymous = serializers.BooleanField(read_only=True)
    now = serializers.DateTimeField(read_only=True)


class LoginSerializer(AuthTokenSerializer):
    pass


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordTokenSerializer(serializers.Serializer):
    password = serializers.CharField(label=gettext_lazy("Password"), style={'input_type': 'password'})
    token = serializers.CharField()


class MasterUserCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(allow_blank=True)

    def create(self, validated_data):
        name = validated_data.get('name')
        description = validated_data.get('description')

        if MasterUser.objects.filter(name=name).exists():
            error = {"name": [gettext_lazy('Name already in use.')]}
            raise serializers.ValidationError(error)

        return validated_data


class MasterUserCopy:
    def __init__(self, task_id=None, task_status=None, master_user=None, member=None, name=None, description=None,
                 reference_master_user=None):
        self.task_id = task_id
        self.task_status = task_status

        self.name = name
        self.reference_master_user = reference_master_user

        self.master_user = master_user
        self.member = member

    def __str__(self):
        return '%s:%s' % (getattr(self.master_user, 'name', None), self.name)


class MasterUserCopySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False, allow_null=True)
    reference_master_user = serializers.IntegerField(required=False, allow_null=True)

    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    master_user = MasterUserField()
    member = HiddenMemberField()

    def create(self, validated_data):

        if validated_data.get('task_id', None):
            validated_data.pop('name', None)
            validated_data.pop('reference_master_user', None)

        else:

            name = validated_data.get('name')

            if MasterUser.objects.filter(name=name).exists():
                error = {"name": [gettext_lazy('Name already in use.')]}
                raise serializers.ValidationError(error)

        return MasterUserCopy(**validated_data)


class UserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=30, required=True)
    password = serializers.CharField(max_length=128, required=True, style={'input_type': 'password'})
    # account_type = serializers.CharField(max_length=30, required=True)
    # first_name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    # last_name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    # name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    email = serializers.CharField(max_length=255, required=False, allow_blank=True)
    access_key = serializers.CharField(max_length=8, required=False, allow_blank=True)

    def create(self, validated_data):
        username = validated_data.get('username')
        password = validated_data.get('password')
        email = validated_data.get('email')
        account_type = validated_data.get('account_type')
        access_key = validated_data.get('access_key')
        # first_name = validated_data.get('first_name', '')
        # last_name = validated_data.get('last_name', '')
        # name = validated_data.get('last_name', '')
        # name = name or ('%s %s' % (last_name, first_name))

        user_model = get_user_model()

        if user_model.objects.filter(username=username).exists():
            error = {"username": [gettext_lazy('User already exist.')]}
            raise serializers.ValidationError(error)

        if user_model.objects.filter(email=email).exists():
            error = {"email": [gettext_lazy('Email already exist.')]}
            raise serializers.ValidationError(error)

        user = user_model.objects.create_user(username=username, password=password, email=email)

        if account_type == 'database':
            MasterUser.objects.create_master_user(user=user, language=translation.get_language(), name=username)

        user = authenticate(username=username, password=password)

        validated_data['user'] = user
        return validated_data


# class PasswordChangeSerializer(serializers.Serializer):
#     password = serializers.CharField(required=True, max_length=128, style={'input_type': 'password'})
#     new_password = serializers.CharField(required=True, max_length=128, style={'input_type': 'password'})
#
#     def create(self, validated_data):
#         user = get_user_from_context(self.context)
#         password = validated_data['password']
#         if user.check_password(password):
#             new_password = validated_data['new_password']
#             user.set_password(new_password)
#             return validated_data
#         raise PermissionDenied(gettext_lazy('Invalid password'))


class UserProfileSerializer(serializers.ModelSerializer):
    language = serializers.ChoiceField(choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)
    timezone = serializers.ChoiceField(choices=TIMEZONE_CHOICES)
    two_factor_verification = serializers.BooleanField()

    class Meta:
        model = UserProfile
        fields = ['language', 'timezone', 'two_factor_verification']


class UserSerializer(serializers.ModelSerializer):
    # url = serializers.HyperlinkedIdentityField(view_name='user-detail')
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'profile']
        read_only_fields = ['username']

    def create(self, validated_data):
        # profile_data = validated_data.pop('profile', {})
        # user = User.objects.create(**validated_data)
        # user.profile.language = profile_data.get('language', settings.LANGUAGE_CODE)
        # user.profile.timezone = profile_data.get('timezone', settings.TIME_ZONE)
        # user.profile.save()
        # # UserProfile.objects.create(user=user, **profile_data)
        return None

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', empty)

        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)
        instance.save()

        if profile_data is not empty:
            profile = instance.profile
            profile.language = profile_data.get('language', profile.language)
            profile.timezone = profile_data.get('timezone', profile.timezone)
            profile.two_factor_verification = profile_data.get('two_factor_verification',
                                                               profile.two_factor_verification)
            profile.save()

        return instance


class UserSetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(allow_null=False, allow_blank=False, required=True, write_only=True,
                                     style={'input_type': 'password'})
    new_password = serializers.CharField(allow_null=False, allow_blank=False, required=True, write_only=True,
                                         style={'input_type': 'password'})

    def validate(self, attrs):
        user = get_user_from_context(self.context)
        password = attrs['password']
        new_password = attrs['new_password']

        if not user.check_password(password):
            raise serializers.ValidationError({'password': gettext_lazy('bad password')})

        try:
            validate_password(new_password, user)
        except serializers.DjangoValidationError as e:
            raise serializers.ValidationError({'new_password': e.messages})

        return attrs

    def create(self, validated_data):
        user = get_user_from_context(self.context)
        user.set_password(validated_data['new_password'])
        user.save(update_fields=['password'])
        update_session_auth_hash(self.context['request'], user)
        return validated_data

    def update(self, instance, validated_data):
        return self.create(validated_data)


class UserUnsubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField(allow_null=False, allow_blank=False, required=True, write_only=True)

    def validate(self, attrs):
        user = get_user_from_context(self.context)
        if attrs['email'] != user.email:
            raise serializers.ValidationError({'email': 'Invalid email'})
        return attrs

    def create(self, validated_data):
        email = validated_data['email']
        return validated_data

    def update(self, instance, validated_data):
        return self.create(validated_data)


class MasterUserSerializer(serializers.ModelSerializer):
    # url = serializers.HyperlinkedIdentityField(view_name='masteruser-detail')
    language = serializers.ChoiceField(choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)
    timezone = serializers.ChoiceField(choices=TIMEZONE_CHOICES)

    # is_current = serializers.SerializerMethodField()
    # is_admin = serializers.SerializerMethodField()
    # is_owner = serializers.SerializerMethodField()
    # system_currency = CurrencyField()

    # currency = CurrencyField()
    # account_type = AccountTypeField()
    # account = AccountField()
    # counterparty_group = CounterpartyGroupField()
    # counterparty = CounterpartyField()
    # responsible_group = ResponsibleGroupField()
    # responsible = ResponsibleField()
    # instrument_type = InstrumentTypeField()
    # instrument = InstrumentField()
    # portfolio = PortfolioField()
    # strategy1_group = Strategy1GroupField()
    # strategy1_subgroup = Strategy1SubgroupField()
    # strategy1 = Strategy1Field()
    # strategy2_group = Strategy2GroupField()
    # strategy2_subgroup = Strategy2SubgroupField()
    # strategy2 = Strategy2Field()
    # strategy3_group = Strategy3GroupField()
    # strategy3_subgroup = Strategy3SubgroupField()
    # strategy3 = Strategy3Field()
    # mismatch_portfolio = PortfolioField()
    # mismatch_account = AccountField()
    # pricing_policy = PricingPolicyField()
    # transaction_type = TransactionTypeField()

    class Meta:
        model = MasterUser
        fields = [
            'id', 'name', 'description', 'user_code_counters',
            # 'is_current', 'is_admin', 'is_owner',
            'language',
            'status',
            'timezone',
            'notification_business_days',
            'journal_status',
            'journal_storage_policy',
            # 'system_currency',
            # 'currency',
            # 'account_type', 'account',
            # 'counterparty_group', 'counterparty',
            # 'responsible_group', 'responsible',
            # 'instrument_type', 'instrument',
            # 'portfolio',
            # 'price_download_scheme',
            # 'strategy1_group', 'strategy1_subgroup', 'strategy1',
            # 'strategy2_group', 'strategy2_subgroup', 'strategy2',
            # 'strategy3_group', 'strategy3_subgroup', 'strategy3',
            # 'thread_group',
            # 'mismatch_portfolio', 'mismatch_account',
            # 'pricing_policy', 'transaction_type'
        ]

    def __init__(self, *args, **kwargs):
        super(MasterUserSerializer, self).__init__(*args, **kwargs)

        # from poms.accounts.serializers import AccountTypeViewSerializer, AccountViewSerializer
        # from poms.counterparties.serializers import CounterpartyGroupViewSerializer, CounterpartyViewSerializer, \
        #     ResponsibleGroupViewSerializer, ResponsibleViewSerializer
        # from poms.instruments.serializers import InstrumentViewSerializer, InstrumentTypeViewSerializer
        # from poms.portfolios.serializers import PortfolioViewSerializer
        # from poms.strategies.serializers import Strategy1GroupViewSerializer, Strategy1SubgroupViewSerializer, \
        #     Strategy1ViewSerializer, Strategy2GroupViewSerializer, Strategy2SubgroupViewSerializer, \
        #     Strategy2ViewSerializer, Strategy3GroupViewSerializer, Strategy3SubgroupViewSerializer, \
        #     Strategy3ViewSerializer
        # from poms.transactions.serializers import TransactionTypeViewSerializer
        # from poms.instruments.serializers import PricingPolicyViewSerializer

        # self.fields['system_currency_object'] = CurrencyViewSerializer(source='system_currency', read_only=True)
        # self.fields['currency_object'] = CurrencyViewSerializer(source='currency', read_only=True)

        # self.fields['account_type_object'] = AccountTypeViewSerializer(source='account_type', read_only=True)
        # self.fields['account_object'] = AccountViewSerializer(source='account', read_only=True)
        #
        # self.fields['counterparty_group_object'] = CounterpartyGroupViewSerializer(source='counterparty_group',
        #                                                                            read_only=True)
        # self.fields['counterparty_object'] = CounterpartyViewSerializer(source='counterparty', read_only=True)
        # self.fields['responsible_group_object'] = ResponsibleGroupViewSerializer(source='responsible_group',
        #                                                                          read_only=True)
        # self.fields['responsible_object'] = ResponsibleViewSerializer(source='responsible', read_only=True)
        #
        # self.fields['instrument_object'] = InstrumentViewSerializer(source='instrument', read_only=True)
        # self.fields['instrument_type_object'] = InstrumentTypeViewSerializer(source='instrument_type', read_only=True)
        #
        # self.fields['portfolio_object'] = PortfolioViewSerializer(source='portfolio', read_only=True)
        #
        # self.fields['strategy1_group_object'] = Strategy1GroupViewSerializer(source='strategy1_group', read_only=True)
        # self.fields['strategy1_subgroup_object'] = Strategy1SubgroupViewSerializer(source='strategy1_subgrou',
        #                                                                            read_only=True)
        # self.fields['strategy1_object'] = Strategy1ViewSerializer(source='strategy1', read_only=True)
        # self.fields['strategy2_group_object'] = Strategy2GroupViewSerializer(source='strategy2_group', read_only=True)
        # self.fields['strategy2_subgroup_object'] = Strategy2SubgroupViewSerializer(source='strategy2_subgroup',
        #                                                                            read_only=True)
        # self.fields['strategy2_object'] = Strategy2ViewSerializer(source='strategy2', read_only=True)
        # self.fields['strategy3_group_object'] = Strategy3GroupViewSerializer(source='strategy3_group', read_only=True)
        # self.fields['strategy3_subgroup_object'] = Strategy3SubgroupViewSerializer(source='strategy3_subgroup',
        #                                                                            read_only=True)
        # self.fields['strategy3_object'] = Strategy3ViewSerializer(source='strategy3', read_only=True)
        #
        # self.fields['thread_group_object'] = ThreadGroupViewSerializer(source='thread_group', read_only=True)
        #
        # self.fields['mismatch_portfolio_object'] = PortfolioViewSerializer(source='mismatch_portfolio', read_only=True)
        # self.fields['mismatch_account_object'] = AccountViewSerializer(source='mismatch_account', read_only=True)
        #
        # self.fields['pricing_policy_object'] = PricingPolicyViewSerializer(source='pricing_policy', read_only=True)
        # self.fields['transaction_type_object'] = TransactionTypeViewSerializer(source='transaction_type',
        #                                                                        read_only=True)

    # def to_representation(self, instance):
    #     ret = super(MasterUserSerializer, self).to_representation(instance)
    #     is_current = self.get_is_current(instance)
    #     is_admin = self.get_is_admin(instance)
    #     is_owner = self.get_is_owner(instance)
    #     if not is_current:
    #         for k in list(ret.keys()):
    #             if k not in ['id', 'name', 'is_current', 'description', 'is_admin', 'is_owner']:
    #                 ret.pop(k)
    #     return ret

    # def get_is_current(self, obj):
    #     master_user = get_master_user_from_context(self.context)
    #
    #     if master_user:
    #         return obj.id == master_user.id
    #     return False

    # def get_is_admin(self, obj):
    #
    #     user = get_user_from_context(self.context)
    #
    #     member = Member.objects.get(master_user=obj.id, user=user.id)
    #
    #     return member.is_admin
    #
    # def get_is_owner(self, obj):
    #
    #     user = get_user_from_context(self.context)
    #
    #     member = Member.objects.get(master_user=obj.id, user=user.id)
    #
    #     return member.is_owner


class MasterUserLightSerializer(serializers.ModelSerializer):
    # url = serializers.HyperlinkedIdentityField(view_name='masteruser-detail')
    language = serializers.ChoiceField(choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)
    timezone = serializers.ChoiceField(choices=TIMEZONE_CHOICES)
    # is_current = serializers.SerializerMethodField()
    # is_admin = serializers.SerializerMethodField()
    # is_owner = serializers.SerializerMethodField()

    members = MemberField(many=True, required=False)
    members_object = serializers.PrimaryKeyRelatedField(source='members', read_only=True, many=True)

    class Meta:
        model = MasterUser
        fields = [
            'id', 'name', 'description', 'language',
            'timezone', 'members', 'members_object'

        ]

    def __init__(self, *args, **kwargs):
        super(MasterUserLightSerializer, self).__init__(*args, **kwargs)

        self.fields['members_object'] = MemberViewSerializer(source='members', many=True, read_only=True)

    def to_representation(self, instance):
        ret = super(MasterUserLightSerializer, self).to_representation(instance)

        # is_current = self.get_is_current(instance)
        # is_admin = self.get_is_admin(ret)
        # is_owner = self.get_is_owner(ret)
        # if not is_current:
        #     for k in list(ret.keys()):
        #         if k not in ['id', 'name', 'is_current', 'description', 'is_admin', 'is_owner']:
        #             ret.pop(k)

        ret['is_current'] = self.get_is_current(instance)
        ret['is_admin'] = self.get_is_admin(ret)
        ret['is_owner'] = self.get_is_owner(ret)
        ret.pop('members')
        ret.pop('members_object')

        return ret

    def get_is_current(self, obj):

        master_user = get_master_user_from_context(self.context)

        if master_user:
            return obj.id == master_user.id
        return False

    def get_is_admin(self, obj):

        result = False

        user = get_user_from_context(self.context)

        for member in obj['members_object']:
            if member['user'] == user.id:
                result = member['is_admin']

        return result

    def get_is_owner(self, obj):

        result = False

        user = get_user_from_context(self.context)

        for member in obj['members_object']:
            if member['user'] == user.id:
                result = member['is_owner']

        return result


class OtpTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtpToken
        fields = [
            'id', 'name', 'is_active'
        ]


class EcosystemDefaultSerializer(serializers.ModelSerializer):
    currency = CurrencyField()
    account_type = AccountTypeField()
    account = AccountField()
    counterparty_group = CounterpartyGroupField()
    counterparty = CounterpartyField()
    responsible_group = ResponsibleGroupField()
    responsible = ResponsibleField()
    instrument_type = InstrumentTypeField()
    instrument = InstrumentField()
    portfolio = PortfolioField()
    strategy1_group = Strategy1GroupField()
    strategy1_subgroup = Strategy1SubgroupField()
    strategy1 = Strategy1Field()
    strategy2_group = Strategy2GroupField()
    strategy2_subgroup = Strategy2SubgroupField()
    strategy2 = Strategy2Field()
    strategy3_group = Strategy3GroupField()
    strategy3_subgroup = Strategy3SubgroupField()
    strategy3 = Strategy3Field()
    mismatch_portfolio = PortfolioField()
    mismatch_account = AccountField()
    pricing_policy = PricingPolicyField()
    transaction_type = TransactionTypeField()

    periodicity = PeriodicityField()

    class Meta:
        model = EcosystemDefault
        fields = [
            'id',
            'currency',
            'account_type', 'account',
            'counterparty_group', 'counterparty',
            'responsible_group', 'responsible',
            'instrument_type', 'instrument',
            'portfolio',
            'strategy1_group', 'strategy1_subgroup', 'strategy1',
            'strategy2_group', 'strategy2_subgroup', 'strategy2',
            'strategy3_group', 'strategy3_subgroup', 'strategy3',
            'mismatch_portfolio', 'mismatch_account',
            'pricing_policy', 'transaction_type',
            'instrument_class', 'accrual_calculation_model', 'pricing_condition',
            'payment_size_detail', 'periodicity',

            'instrument_pricing_scheme', 'currency_pricing_scheme'
        ]

    def __init__(self, *args, **kwargs):
        super(EcosystemDefaultSerializer, self).__init__(*args, **kwargs)

        from poms.currencies.serializers import CurrencyViewSerializer
        from poms.accounts.serializers import AccountTypeViewSerializer, AccountViewSerializer
        from poms.counterparties.serializers import CounterpartyGroupViewSerializer, CounterpartyViewSerializer, \
            ResponsibleGroupViewSerializer, ResponsibleViewSerializer
        from poms.instruments.serializers import InstrumentViewSerializer, InstrumentTypeViewSerializer, \
            AccrualCalculationModelViewSerializer, \
            InstrumentClassViewSerializer, PaymentSizeDetailViewSerializer, \
            PeriodicityViewSerializer, PricingConditionViewSerializer
        from poms.portfolios.serializers import PortfolioViewSerializer
        from poms.strategies.serializers import Strategy1GroupViewSerializer, Strategy1SubgroupViewSerializer, \
            Strategy1ViewSerializer, Strategy2GroupViewSerializer, Strategy2SubgroupViewSerializer, \
            Strategy2ViewSerializer, Strategy3GroupViewSerializer, Strategy3SubgroupViewSerializer, \
            Strategy3ViewSerializer
        from poms.transactions.serializers import TransactionTypeViewSerializer
        from poms.instruments.serializers import PricingPolicyViewSerializer
        from poms.pricing.serializers import InstrumentPricingSchemeSerializer, CurrencyPricingSchemeSerializer

        self.fields['accrual_calculation_model_object'] = AccrualCalculationModelViewSerializer(
            source='accrual_calculation_model', read_only=True)

        # self.fields['daily_pricing_model_object'] = DailyPricingModelViewSerializer(
        #     source='daily_pricing_model', read_only=True)

        self.fields['pricing_condition_object'] = PricingConditionViewSerializer(
            source='pricing_condition', read_only=True)

        self.fields['payment_size_detail_object'] = PaymentSizeDetailViewSerializer(
            source='payment_size_detail', read_only=True)

        self.fields['periodicity_object'] = PeriodicityViewSerializer(
            source='periodicity', read_only=True)

        self.fields['instrument_pricing_scheme_object'] = InstrumentPricingSchemeSerializer(
            source='instrument_pricing_scheme', read_only=True)

        self.fields['currency_pricing_scheme_object'] = CurrencyPricingSchemeSerializer(
            source='currency_pricing_scheme', read_only=True)

        self.fields['instrument_class_object'] = InstrumentClassViewSerializer(
            source='instrument_class', read_only=True)

        # self.fields['price_download_scheme_object'] = PriceDownloadSchemeViewSerializer(
        #     source='price_download_scheme', read_only=True)

        self.fields['currency_object'] = CurrencyViewSerializer(source='currency', read_only=True)

        self.fields['account_type_object'] = AccountTypeViewSerializer(source='account_type', read_only=True)
        self.fields['account_object'] = AccountViewSerializer(source='account', read_only=True)

        self.fields['counterparty_group_object'] = CounterpartyGroupViewSerializer(source='counterparty_group',
                                                                                   read_only=True)
        self.fields['counterparty_object'] = CounterpartyViewSerializer(source='counterparty', read_only=True)
        self.fields['responsible_group_object'] = ResponsibleGroupViewSerializer(source='responsible_group',
                                                                                 read_only=True)
        self.fields['responsible_object'] = ResponsibleViewSerializer(source='responsible', read_only=True)

        self.fields['instrument_object'] = InstrumentViewSerializer(source='instrument', read_only=True)
        self.fields['instrument_type_object'] = InstrumentTypeViewSerializer(source='instrument_type', read_only=True)

        self.fields['portfolio_object'] = PortfolioViewSerializer(source='portfolio', read_only=True)

        self.fields['strategy1_group_object'] = Strategy1GroupViewSerializer(source='strategy1_group', read_only=True)
        self.fields['strategy1_subgroup_object'] = Strategy1SubgroupViewSerializer(source='strategy1_subgroup',
                                                                                   read_only=True)
        self.fields['strategy1_object'] = Strategy1ViewSerializer(source='strategy1', read_only=True)

        self.fields['strategy2_group_object'] = Strategy2GroupViewSerializer(source='strategy2_group', read_only=True)
        self.fields['strategy2_subgroup_object'] = Strategy2SubgroupViewSerializer(source='strategy2_subgroup',
                                                                                   read_only=True)
        self.fields['strategy2_object'] = Strategy2ViewSerializer(source='strategy2', read_only=True)

        self.fields['strategy3_group_object'] = Strategy3GroupViewSerializer(source='strategy3_group', read_only=True)
        self.fields['strategy3_subgroup_object'] = Strategy3SubgroupViewSerializer(source='strategy3_subgroup',
                                                                                   read_only=True)
        self.fields['strategy3_object'] = Strategy3ViewSerializer(source='strategy3', read_only=True)

        self.fields['pricing_policy_object'] = PricingPolicyViewSerializer(source='pricing_policy', read_only=True)
        self.fields['transaction_type_object'] = TransactionTypeViewSerializer(source='transaction_type',
                                                                               read_only=True)

        self.fields['mismatch_portfolio_object'] = PortfolioViewSerializer(source='mismatch_portfolio', read_only=True)
        self.fields['mismatch_account_object'] = AccountViewSerializer(source='mismatch_account', read_only=True)


class MasterUserSetCurrentSerializer(serializers.Serializer):
    def create(self, validated_data):
        return validated_data

    def update(self, instance, validated_data):
        return self.create(validated_data)


# class MemberMiniSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Member
#         fields = ['id', 'username', 'first_name', 'last_name', 'display_name', ]
#         read_only_fields = ['id', 'username', 'first_name', 'last_name', 'display_name', ]
#
#     def get_is_current(self, obj):
#         member = get_member_from_context(self.context)
#         return obj.id == member.id


class MemberSerializer(serializers.ModelSerializer):

    master_user = MasterUserField()
    username = serializers.CharField(read_only=False)
    join_date = DateTimeTzAwareField(read_only=True)

    groups = GroupField(source='iam_groups', many=True, required=False)
    groups_object = serializers.PrimaryKeyRelatedField(source='iam_groups', read_only=True, many=True)

    roles = RoleField(source='iam_roles', many=True, required=False)
    roles_object = serializers.PrimaryKeyRelatedField(source='iam_roles', read_only=True, many=True)

    access_policies = AccessPolicyField(source='iam_access_policies', many=True, required=False)
    access_policies_object = serializers.PrimaryKeyRelatedField(source='iam_access_policies', read_only=True, many=True)

    data = serializers.JSONField(allow_null=True, required=False)

    class Meta:
        model = Member
        fields = [
            'id', 'master_user',
            'join_date', 'is_owner', 'is_admin', 'is_superuser',
            'notification_level', 'interface_level',
            'is_deleted', 'username', 'first_name', 'last_name',

            'groups', 'groups_object',
            'roles', 'roles_object',
            'access_policies', 'access_policies_object',
            'data',
            'status'
        ]
        read_only_fields = [
            'master_user', 'join_date', 'is_superuser', 'is_deleted',
            'first_name', 'last_name', 'display_name',
        ]

    def __init__(self, *args, **kwargs):
        super(MemberSerializer, self).__init__(*args, **kwargs)
        from poms.iam.serializers import IamRoleSerializer, IamGroupSerializer, IamAccessPolicySerializer
        self.fields['groups_object'] = IamGroupSerializer(source='iam_groups', many=True, read_only=True)
        self.fields['access_policies_object'] = IamAccessPolicySerializer(source='iam_access_policies', many=True, read_only=True)
        self.fields['roles_object'] = IamRoleSerializer(source='iam_roles', many=True, read_only=True)


    def create(self, validated_data):

        _l.info('member create %s' % validated_data)

        username = validated_data.get('username')
        status = Member.STATUS_INVITED
        validated_data['status'] = status
        member = super(MemberSerializer, self).create(validated_data)

        member.user = User.objects.create(username=username)# TODO maybe need to do more smart things here
        member.save()

        return member

    def update(self, instance, validated_data):
        validated_data.pop('username', None)
        return super(MemberSerializer, self).update(instance, validated_data)


class MemberViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['id', 'username', 'first_name', 'last_name', 'display_name', 'is_owner', 'is_admin', 'user']
        read_only_fields = ['id', 'username', 'first_name', 'last_name', ]

    def get_is_current(self, obj):
        member = get_member_from_context(self.context)
        return obj.id == member.id


class UsercodePrefixSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    class Meta:
        model = UsercodePrefix
        fields = ['id', 'master_user', 'value', 'notes']

