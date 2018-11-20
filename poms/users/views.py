from __future__ import unicode_literals

import django_filters
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.decorators import detail_route
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import FilterSet
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from poms.accounts.models import AccountType, Account
from poms.chats.models import ThreadGroup
from poms.common.filters import CharFilter, NoOpFilter, ModelExtMultipleChoiceFilter
from poms.common.pagination import BigPagination
from poms.common.views import AbstractModelViewSet, AbstractApiView
from poms.counterparties.models import CounterpartyGroup, Counterparty, ResponsibleGroup, Responsible
from poms.instruments.models import InstrumentType, Instrument
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy1Subgroup, Strategy1Group, Strategy2Subgroup, Strategy2Group, \
    Strategy2, Strategy3, Strategy3Subgroup, Strategy3Group
from poms.users.filters import OwnerByMasterUserFilter, MasterUserFilter
from poms.users.models import MasterUser, Member, Group
from poms.users.permissions import SuperUserOrReadOnly, IsCurrentMasterUser, IsCurrentUser
from poms.users.serializers import GroupSerializer, UserSerializer, MasterUserSerializer, MemberSerializer, \
    PingSerializer, UserSetPasswordSerializer, MasterUserSetCurrentSerializer, UserUnsubscribeSerializer, \
    UserRegisterSerializer
from poms.users.utils import set_master_user


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
            'is_authenticated': request.user.is_authenticated(),
            'is_anonymous': request.user.is_anonymous(),
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

    @detail_route(methods=('PUT',), url_path='set-password', serializer_class=UserSetPasswordSerializer)
    def set_password(self, request, pk=None):
        # user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # return Response(serializer.data)
        return Response()

    @detail_route(methods=('PUT',), url_path='unsubscribe', serializer_class=UserUnsubscribeSerializer)
    def unsubscribe(self, request, pk=None):
        # user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # return Response(serializer.data)
        return Response()


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

    @detail_route(methods=('PUT', 'PATCH',), url_path='set-current', permission_classes=[IsAuthenticated],
                  serializer_class=MasterUserSetCurrentSerializer)
    def set_current(self, request, pk=None):
        instance = self.get_object()
        set_master_user(request, instance)
        return Response({'success': True})


class MemberFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    username = CharFilter()
    first_name = CharFilter()
    last_name = CharFilter()
    email = CharFilter()
    group = ModelExtMultipleChoiceFilter(model=Group, name='groups')

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


class GroupFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()
    member = ModelExtMultipleChoiceFilter(model=Member, field_name='username', name='members')

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
