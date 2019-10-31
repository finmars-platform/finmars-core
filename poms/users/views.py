from __future__ import unicode_literals

from django.utils import translation

import django_filters
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_filters.rest_framework import FilterSet
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.decorators import action

from rest_framework.exceptions import PermissionDenied

from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ViewSet, ModelViewSet, ViewSetMixin

from poms.accounts.models import AccountType, Account
from poms.chats.models import ThreadGroup, Thread
from poms.common.filters import CharFilter, NoOpFilter, ModelExtMultipleChoiceFilter
from poms.common.mixins import UpdateModelMixinExt, DestroyModelFakeMixin
from poms.common.pagination import BigPagination
from poms.common.views import AbstractModelViewSet, AbstractApiView, AbstractViewSet
from poms.complex_import.models import ComplexImportSchemeAction, ComplexImportScheme
from poms.counterparties.models import CounterpartyGroup, Counterparty, ResponsibleGroup, Responsible
from poms.currencies.models import Currency
from poms.instruments.models import InstrumentType, Instrument
from poms.integrations.models import InstrumentDownloadScheme
from poms.obj_attrs.models import GenericAttributeType
from poms.obj_perms.models import GenericObjectPermission
from poms.obj_perms.utils import get_permissions_prefetch_lookups, assign_perms3, \
    get_view_perms, get_all_perms, append_perms3
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy1Subgroup, Strategy1Group, Strategy2Subgroup, Strategy2Group, \
    Strategy2, Strategy3, Strategy3Subgroup, Strategy3Group
from poms.transactions.models import TransactionType, TransactionTypeInput, TransactionTypeAction, \
    TransactionTypeActionInstrument, Transaction, ComplexTransaction, TransactionTypeGroup
from poms.users.filters import OwnerByMasterUserFilter, MasterUserFilter, OwnerByUserFilter, InviteToMasterUserFilter, \
    IsMemberFilterBackend
from poms.users.models import MasterUser, Member, Group, ResetPasswordToken, InviteToMasterUser, EcosystemDefault
from poms.users.permissions import SuperUserOrReadOnly, IsCurrentMasterUser, IsCurrentUser
from poms.users.serializers import GroupSerializer, UserSerializer, MasterUserSerializer, MemberSerializer, \
    PingSerializer, UserSetPasswordSerializer, MasterUserSetCurrentSerializer, UserUnsubscribeSerializer, \
    UserRegisterSerializer, MasterUserCreateSerializer, EmailSerializer, PasswordTokenSerializer, \
    InviteToMasterUserSerializer, InviteCreateSerializer, EcosystemDefaultSerializer, MasterUserLightSerializer
from poms.users.utils import set_master_user

from datetime import timedelta
from django.conf import settings
from rest_framework import parsers, renderers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy

from django.core.mail import send_mail


class ObtainAuthTokenViewSet(AbstractApiView, ViewSet):
    parser_classes = (FormParser, MultiPartParser, JSONParser,)
    serializer_class = AuthTokenSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        Token.objects.filter(user=user).delete()
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})


class PingViewSet(AbstractApiView, ViewSet):
    permission_classes = [AllowAny, ]

    @method_decorator(ensure_csrf_cookie)
    def list(self, request, *args, **kwargs):
        serializer = PingSerializer(instance={
            'message': 'pong',
            'version': request.version,
            'is_authenticated': request.user.is_authenticated,
            'is_anonymous': request.user.is_anonymous,
            'now': timezone.template_localtime(timezone.now()),
        })
        return Response(serializer.data)


class ProtectedPingViewSet(PingViewSet):
    permission_classes = [IsAuthenticated, ]


class LoginViewSet(ViewSet):
    permission_classes = []
    parser_classes = [FormParser, MultiPartParser, JSONParser, ]
    serializer_class = AuthTokenSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return Response({'success': True})


class LogoutViewSet(ViewSet):
    def create(self, request, *args, **kwargs):
        logout(request)
        return Response({'success': True})


class UserRegisterViewSet(AbstractApiView, ViewSet):
    serializer_class = UserRegisterSerializer
    permission_classes = []
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.save()
        user = validated_data['user']
        login(request, user)
        return Response({'success': True})


class MasterUserCreateViewSet(ViewSet):
    serializer_class = MasterUserCreateSerializer
    # authentication_classes = [IsAuthenticated]
    # authentication_classes = []
    permission_classes = [
        IsAuthenticated
    ]

    def create(self, request, *args, **kwargs):

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.save()
        name = validated_data['name']
        description = validated_data['description']

        master_user = MasterUser.objects.create_master_user(
            user=request.user,
            language=translation.get_language(), name=name, description=description)

        member = Member.objects.create(user=request.user, master_user=master_user, is_owner=True, is_admin=True)
        member.save()

        admin_group = Group.objects.get(master_user=master_user, role=Group.ADMIN)
        admin_group.members.add(member.id)
        admin_group.save()

        return Response({'id': master_user.id, 'name': master_user.name, 'description': master_user.description})


class MasterUserCreateCheckUniquenessViewSet(ViewSet):
    permission_classes = [
        IsAuthenticated
    ]

    def list(self, request, *args, **kwargs):

        result = True

        name = request.query_params.get('name')

        try:
            master_user = MasterUser.objects.get(name=name)

            result = False

        except MasterUser.DoesNotExist:
            result = True

        return Response({'unique': result})


def get_password_reset_token_expiry_time():
    """
    Returns the password reset token expirty time in hours (default: 24)
    Set Django SETTINGS.DJANGO_REST_MULTITOKENAUTH_RESET_TOKEN_EXPIRY_TIME to overwrite this time
    :return: expiry time
    """
    # get token validation time
    return getattr(settings, 'DJANGO_REST_MULTITOKENAUTH_RESET_TOKEN_EXPIRY_TIME', 24)


class ResetPasswordConfirmViewSet(AbstractApiView, ViewSet):
    """
    An Api View which provides a method to reset a password based on a unique token
    """
    throttle_classes = ()
    permission_classes = []
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = PasswordTokenSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['password']
        token = serializer.validated_data['token']

        # get token validation time
        password_reset_token_validation_time = get_password_reset_token_expiry_time()

        # find token
        reset_password_token = ResetPasswordToken.objects.filter(key=token).first()

        if reset_password_token is None:
            return Response({'status': 'notfound'}, status=status.HTTP_404_NOT_FOUND)

        # check expiry date
        expiry_date = reset_password_token.created_at + timedelta(hours=password_reset_token_validation_time)

        if timezone.now() > expiry_date:
            # delete expired token
            reset_password_token.delete()
            return Response({'status': 'expired'}, status=status.HTTP_404_NOT_FOUND)

        # change users password
        if reset_password_token.user.has_usable_password():
            # pre_password_reset.send(sender=self.__class__, user=reset_password_token.user)
            reset_password_token.user.set_password(password)
            reset_password_token.user.save()
            # post_password_reset.send(sender=self.__class__, user=reset_password_token.user)

        # Delete all password reset tokens for this user
        ResetPasswordToken.objects.filter(user=reset_password_token.user).delete()

        return Response({'status': 'OK'})


class ResetPasswordRequestTokenViewSet(AbstractApiView, ViewSet):
    """
    An Api View which provides a method to request a password reset token based on an e-mail address
    Sends a signal reset_password_token_created when a reset token was created
    """
    throttle_classes = ()
    permission_classes = []
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = EmailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        # before we continue, delete all existing expired tokens
        password_reset_token_validation_time = get_password_reset_token_expiry_time()

        # datetime.now minus expiry hours
        now_minus_expiry_time = timezone.now() - timedelta(hours=password_reset_token_validation_time)

        # delete all tokens where created_at < now - 24 hours
        ResetPasswordToken.objects.filter(created_at__lte=now_minus_expiry_time).delete()

        # find a user by email address (case insensitive search)
        users = User.objects.filter(email__iexact=email)

        active_user_found = False

        # iterate over all users and check if there is any user that is active
        # also check whether the password can be changed (is useable), as there could be users that are not allowed
        # to change their password (e.g., LDAP user)
        for user in users:
            if user.is_active and user.has_usable_password():
                active_user_found = True

        # No active user found, raise a validation error
        if not active_user_found:
            raise ValidationError({
                'email': ValidationError(
                    ugettext_lazy(
                        "There is no active user associated with this e-mail address or the password can not be changed"),
                    code='invalid')}
            )

        # last but not least: iterate over all users that are active and can change their password
        # and create a Reset Password Token and send a signal with the created token

        for user in users:

            if user.is_active and user.has_usable_password():
                # define the token as none for now
                token = None

                # check if the user already has a token
                if user.password_reset_tokens.all().count() > 0:
                    # yes, already has a token, re-use this token
                    token = user.password_reset_tokens.all()[0]
                else:
                    # no token exists, generate a new token
                    token = ResetPasswordToken.objects.create(
                        user=user,
                        user_agent=request.META['HTTP_USER_AGENT'],
                        ip_address=request.META['REMOTE_ADDR']
                    )

                link = "https://finmars.com/forgot-password-confirm.html?token=%s" % token.key

                message = "Your password reset link is: %s" % link

                subject = "Password reset"
                recipient_list = [user.email]

                send_mail(subject, message, None, recipient_list, html_message=message)

                print("token %s " % token.key)

        return Response({'status': 'OK'})


class UserViewSet(AbstractModelViewSet):
    queryset = User.objects
    serializer_class = UserSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        IsCurrentUser,
    ]

    # filter_backends = AbstractReadOnlyModelViewSet.filter_backends + [
    #     UserFilter
    # ]

    # def get_serializer_class(self):
    #     # print(self.action)
    #     # print(self.request.method)
    #     if self.action == 'change_password':
    #         return UserSetPasswordSerializer
    #     return super(UserViewSet, self).get_serializer_class()

    def get_queryset(self):
        qs = super(UserViewSet, self).get_queryset()
        qs = qs.filter(id=self.request.user.id)
        return qs

    def get_object(self):
        return self.request.user

    def create(self, request, *args, **kwargs):
        raise PermissionDenied()

    @action(detail=True, methods=('PUT',), url_path='set-password', serializer_class=UserSetPasswordSerializer)
    def set_password(self, request, pk=None):
        # user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # return Response(serializer.data)
        return Response()

    @action(detail=True, methods=('PUT',), url_path='unsubscribe', serializer_class=UserUnsubscribeSerializer)
    def unsubscribe(self, request, pk=None):
        # user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # return Response(serializer.data)
        return Response()


class UserMemberViewSet(AbstractModelViewSet):
    queryset = Member.objects
    serializer_class = MemberSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
    ]
    filter_backends = [IsMemberFilterBackend]

class MasterUserViewSet(AbstractModelViewSet):
    queryset = MasterUser.objects.select_related(
        'currency',
        'system_currency',
        'account_type',
        'account',
        'account__type',
        'counterparty_group',
        'counterparty',
        'counterparty__group',
        'responsible_group',
        'responsible',
        'responsible__group',
        'instrument_type',
        'instrument_type__instrument_class',
        'instrument',
        'instrument__instrument_type',
        'instrument__instrument_type__instrument_class',
        'portfolio',
        'strategy1_group',
        'strategy1_subgroup',
        'strategy1_subgroup__group',
        'strategy1',
        'strategy1__subgroup',
        'strategy1__subgroup__group',
        'strategy2_group',
        'strategy2_subgroup',
        'strategy2_subgroup__group',
        'strategy2',
        'strategy2__subgroup',
        'strategy2__subgroup__group',
        'strategy3_group',
        'strategy3_subgroup',
        'strategy3_subgroup__group',
        'strategy3',
        'strategy3__subgroup',
        'strategy3__subgroup__group',
        'thread_group',
        'mismatch_portfolio',
        'mismatch_account',
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            ('account_type', AccountType),
            ('account', Account),
            ('account__type', AccountType),
            ('counterparty_group', CounterpartyGroup),
            ('counterparty', Counterparty),
            ('counterparty__group', CounterpartyGroup),
            ('responsible_group', ResponsibleGroup),
            ('responsible', Responsible),
            ('responsible__group', ResponsibleGroup),
            ('instrument_type', InstrumentType),
            ('instrument', Instrument),
            ('instrument__instrument_type', InstrumentType),
            ('portfolio', Portfolio),
            ('strategy1_group', Strategy1Group),
            ('strategy1_subgroup', Strategy1Subgroup),
            ('strategy1_subgroup__group', Strategy1Group),
            ('strategy1', Strategy1),
            ('strategy1__subgroup', Strategy1Subgroup),
            ('strategy1__subgroup__group', Strategy1Group),
            ('strategy2_group', Strategy2Group),
            ('strategy2_subgroup', Strategy2Subgroup),
            ('strategy2_subgroup__group', Strategy2Group),
            ('strategy2', Strategy2),
            ('strategy2__subgroup', Strategy2Subgroup),
            ('strategy2__subgroup__group', Strategy2Group),
            ('strategy3_group', Strategy3Group),
            ('strategy3_subgroup', Strategy3Subgroup),
            ('strategy3_subgroup__group', Strategy3Group),
            ('strategy3', Strategy3),
            ('strategy3__subgroup', Strategy3Subgroup),
            ('strategy3__subgroup__group', Strategy3Group),
            ('thread_group', ThreadGroup),
            ('mismatch_portfolio', Portfolio),
            ('mismatch_account', Account),
            ('mismatch_account__type', AccountType),
        )
    )
    serializer_class = MasterUserSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        IsCurrentMasterUser,
        SuperUserOrReadOnly,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        MasterUserFilter,
    ]
    ordering_fields = [
        'name',
    ]
    pagination_class = BigPagination

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]
        if lookup_value == '0':
            return self.request.user.master_user
        return super(MasterUserViewSet, self).get_object()

    def create(self, request, *args, **kwargs):
        raise PermissionDenied()

    @action(detail=True, methods=('PUT', 'PATCH',), url_path='set-current', permission_classes=[IsAuthenticated],
                  serializer_class=MasterUserSetCurrentSerializer)
    def set_current(self, request, pk=None):
        instance = self.get_object()
        set_master_user(request, instance)
        return Response({'success': True})


class MasterUserLightViewSet(AbstractModelViewSet):
    queryset = MasterUser.objects.prefetch_related('members')
    serializer_class = MasterUserLightSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        IsCurrentMasterUser,
        SuperUserOrReadOnly,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        MasterUserFilter,
    ]
    ordering_fields = [
        'name',
    ]
    pagination_class = BigPagination

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]
        if lookup_value == '0':
            return self.request.user.master_user
        return super(MasterUserLightViewSet, self).get_object()

    def create(self, request, *args, **kwargs):
        raise PermissionDenied()

    @action(detail=True, methods=('PUT', 'PATCH',), url_path='set-current', permission_classes=[IsAuthenticated],
            serializer_class=MasterUserSetCurrentSerializer)
    def set_current(self, request, pk=None):
        instance = self.get_object()
        set_master_user(request, instance)
        return Response({'success': True})


class EcosystemDefaultViewSet(AbstractModelViewSet):
    queryset = EcosystemDefault.objects.select_related(
        'currency',
        'account_type',
        'account',
        'account__type',
        'counterparty_group',
        'counterparty',
        'counterparty__group',
        'responsible_group',
        'responsible',
        'responsible__group',
        'instrument_type',
        'instrument_type__instrument_class',
        'instrument',
        'instrument__instrument_type',
        'instrument__instrument_type__instrument_class',
        'portfolio',
        'strategy1_group',
        'strategy1_subgroup',
        'strategy1_subgroup__group',
        'strategy1',
        'strategy1__subgroup',
        'strategy1__subgroup__group',
        'strategy2_group',
        'strategy2_subgroup',
        'strategy2_subgroup__group',
        'strategy2',
        'strategy2__subgroup',
        'strategy2__subgroup__group',
        'strategy3_group',
        'strategy3_subgroup',
        'strategy3_subgroup__group',
        'strategy3',
        'strategy3__subgroup',
        'strategy3__subgroup__group',
        'thread_group',
        'mismatch_portfolio',
        'mismatch_account',
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            ('account_type', AccountType),
            ('account', Account),
            ('account__type', AccountType),
            ('counterparty_group', CounterpartyGroup),
            ('counterparty', Counterparty),
            ('counterparty__group', CounterpartyGroup),
            ('responsible_group', ResponsibleGroup),
            ('responsible', Responsible),
            ('responsible__group', ResponsibleGroup),
            ('instrument_type', InstrumentType),
            ('instrument', Instrument),
            ('instrument__instrument_type', InstrumentType),
            ('portfolio', Portfolio),
            ('strategy1_group', Strategy1Group),
            ('strategy1_subgroup', Strategy1Subgroup),
            ('strategy1_subgroup__group', Strategy1Group),
            ('strategy1', Strategy1),
            ('strategy1__subgroup', Strategy1Subgroup),
            ('strategy1__subgroup__group', Strategy1Group),
            ('strategy2_group', Strategy2Group),
            ('strategy2_subgroup', Strategy2Subgroup),
            ('strategy2_subgroup__group', Strategy2Group),
            ('strategy2', Strategy2),
            ('strategy2__subgroup', Strategy2Subgroup),
            ('strategy2__subgroup__group', Strategy2Group),
            ('strategy3_group', Strategy3Group),
            ('strategy3_subgroup', Strategy3Subgroup),
            ('strategy3_subgroup__group', Strategy3Group),
            ('strategy3', Strategy3),
            ('strategy3__subgroup', Strategy3Subgroup),
            ('strategy3__subgroup__group', Strategy3Group),
            ('thread_group', ThreadGroup),
            ('mismatch_portfolio', Portfolio),
            ('mismatch_account', Account),
            ('mismatch_account__type', AccountType),
        )
    )
    serializer_class = EcosystemDefaultSerializer
    permission_classes = AbstractModelViewSet.permission_classes + []
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter
    ]
    ordering_fields = [
        'name',
    ]
    pagination_class = BigPagination


class MemberFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    username = CharFilter()
    first_name = CharFilter()
    last_name = CharFilter()
    email = CharFilter()
    group = ModelExtMultipleChoiceFilter(model=Group, field_name='groups')

    class Meta:
        model = Member
        fields = []


class MemberViewSet(AbstractModelViewSet):
    queryset = Member.objects.select_related(
        'user'
    ).prefetch_related(
        'groups'
    )
    serializer_class = MemberSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        SuperUserOrReadOnly,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = MemberFilterSet
    ordering_fields = [
        'username', 'first_name', 'last_name', 'email',
    ]
    pagination_class = BigPagination

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]
        if lookup_value == '0':
            return self.request.user.member
        return super(MemberViewSet, self).get_object()

    def update(self, request, *args, **kwargs):

        owner = Member.objects.get(master_user=request.user.master_user, is_owner=True)
        admin_group = Group.objects.get(master_user=request.user.master_user, role=Group.ADMIN)

        if not request.data and not request.data['id']:
            raise PermissionDenied()

        if owner.id == request.data['id']:

            if not request.data['groups']:
                raise PermissionDenied()

            if admin_group.id not in request.data['groups']:
                raise PermissionDenied()

        return super(GroupViewSet).update(request, *args, **kwargs)

    def perform_destroy(self, instance):

        if instance.is_owner == True:
            raise PermissionDenied()

        return super(MemberViewSet, self).perform_destroy(instance)


class GroupFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()
    member = ModelExtMultipleChoiceFilter(model=Member, field_name='username')
    # member = ModelExtMultipleChoiceFilter(model=Member, field_name='username', name='members')

    class Meta:
        model = Group
        fields = []


class GroupViewSet(AbstractModelViewSet):
    queryset = Group.objects.select_related(
        'master_user'
    ).prefetch_related(
        'members'
    )
    serializer_class = GroupSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        SuperUserOrReadOnly,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = GroupFilterSet
    ordering_fields = [
        'name',
    ]
    pagination_class = BigPagination

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        if request.data.get('is_public', None):
            instance.grant_all_permissions_to_public_group(instance, request.user.master_user)

        return Response(serializer.data)

    def update(self, request, *args, **kwargs):

        owner = Member.objects.get(master_user=request.user.master_user, is_owner=True)

        if owner.id not in request.data['members']:
            raise PermissionDenied()

        return super(GroupViewSet, self).update(request, *args, **kwargs)

    def perform_destroy(self, instance):

        # TODO important to know: Deletion of the group leads to GenericObjectPermission deletion

        if instance.role == Group.ADMIN:
            raise PermissionDenied()

        GenericObjectPermission.objects.filter(group=instance).delete()
        instance.delete()


class InviteToMasterUserFilterSet(FilterSet):
    id = NoOpFilter()
    to_user = ModelExtMultipleChoiceFilter(model=User, field_name='to_user',)
    from_member = ModelExtMultipleChoiceFilter(model=Member, field_name='from_member',)

    class Meta:
        model = InviteToMasterUser
        fields = []



class InviteFromMasterUserViewSet(AbstractApiView, UpdateModelMixinExt, DestroyModelFakeMixin, ModelViewSet):
    queryset = InviteToMasterUser.objects.select_related(
        'from_member',
    )
    serializer_class = InviteToMasterUserSerializer
    permission_classes = AbstractModelViewSet.permission_classes + []
    filter_backends = [
        OwnerByUserFilter,
    ]
    filter_class = InviteToMasterUserFilterSet
    ordering_fields = [
    ]
    pagination_class = BigPagination



class InviteToUserViewSet(AbstractApiView, UpdateModelMixinExt, DestroyModelFakeMixin, ModelViewSet):
    queryset = InviteToMasterUser.objects.select_related(
        'from_member',
    )
    serializer_class = InviteToMasterUserSerializer
    permission_classes = AbstractModelViewSet.permission_classes + []
    filter_backends = [
        OwnerByMasterUserFilter,
    ]
    filter_class = InviteToMasterUserFilterSet
    ordering_fields = [
    ]
    pagination_class = BigPagination


class CreateInviteViewSet(AbstractApiView, ModelViewSet):
    serializer_class = InviteCreateSerializer
    permission_classes = [
        IsAuthenticated
    ]


class LeaveMasterUserViewSet(AbstractApiView, ViewSet):
    permission_classes = [
        IsAuthenticated
    ]

    @method_decorator(ensure_csrf_cookie)
    def retrieve(self, request, pk=None, *args, **kwargs):

        if not request.user.member:
            raise PermissionDenied()

        if request.user.member.is_owner:
            raise PermissionDenied()

        Member.objects.get(user=request.user.id, master_user=pk).delete()

        # return Response("You left from %s master user" % request.user.master_user.name)
        return Response(status=status.HTTP_200_OK)


class DeleteMasterUserViewSet(AbstractApiView, ViewSet, ):
    permission_classes = [
        IsAuthenticated
    ]

    @method_decorator(ensure_csrf_cookie)
    def destroy(self, request, pk=None, *args, **kwargs):

        master_user_id = pk

        if not request.user.member:
            raise PermissionDenied()

        if not request.user.member.is_owner:
            raise PermissionDenied()

        master_user = MasterUser.objects.get(id=master_user_id)

        try:
            Member.objects.get(master_user=master_user_id, user=request.user.id)
        except EcosystemDefault.DoesNotExist:
            raise PermissionDenied()

        try:
            ecosystem_default = EcosystemDefault.objects.get(master_user=master_user_id)
            ecosystem_default.delete()
        except EcosystemDefault.DoesNotExist:
            print("EcosystemDefault Already deleted")

        ThreadGroup.objects.filter(master_user=master_user_id).delete()

        Transaction.objects.filter(master_user=master_user_id).delete()
        ComplexTransaction.objects.filter(master_user=master_user_id).delete()

        ComplexImportScheme.objects.filter(master_user=master_user_id).delete()

        Instrument.objects.filter(master_user=master_user_id).delete()
        InstrumentType.objects.filter(master_user=master_user_id).delete()

        transaction_types = TransactionType.objects.filter(master_user=master_user_id)

        TransactionTypeAction.objects.filter(transaction_type__in=transaction_types).delete()
        TransactionTypeInput.objects.filter(transaction_type__in=transaction_types).delete()

        TransactionType.objects.filter(master_user=master_user_id).delete()

        InstrumentDownloadScheme.objects.filter(master_user=master_user_id).delete()

        Account.objects.filter(master_user=master_user_id).delete()
        AccountType.objects.filter(master_user=master_user_id).delete()
        Currency.objects.filter(master_user=master_user_id).delete()
        Strategy1.objects.filter(master_user=master_user_id).delete()
        Strategy2.objects.filter(master_user=master_user_id).delete()
        Strategy3.objects.filter(master_user=master_user_id).delete()
        Strategy1Subgroup.objects.filter(master_user=master_user_id).delete()
        Strategy2Subgroup.objects.filter(master_user=master_user_id).delete()
        Strategy3Subgroup.objects.filter(master_user=master_user_id).delete()
        Strategy1Group.objects.filter(master_user=master_user_id).delete()
        Strategy2Group.objects.filter(master_user=master_user_id).delete()
        Strategy3Group.objects.filter(master_user=master_user_id).delete()

        MasterUser.objects.get(id=master_user_id).delete()

        # return Response("Master user %s has been deleted." % request.user.master_user.name)
        return Response(status=status.HTTP_200_OK,
                        data={"message": "Master user %s has been deleted." % master_user.name})


class GetCurrentMasterUserViewSet(AbstractViewSet):
    serializer_class = MasterUserSerializer
    permission_classes = [
        IsAuthenticated
    ]

    def list(self, request, pk=None, *args, **kwargs):
        serializer = self.get_serializer(request.user.master_user)

        return Response(serializer.data)
