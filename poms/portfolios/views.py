from __future__ import unicode_literals

import django_filters

from django.db.models import Prefetch
from django_filters.rest_framework import FilterSet
from rest_framework import status

from poms.accounts.models import Account, AccountType
from poms.common.filters import CharFilter, ModelExtWithPermissionMultipleChoiceFilter, NoOpFilter, \
    GroupsAttributeFilter, AttributeFilter, EntitySpecificFilter

from poms.common.pagination import CustomPaginationMixin
from poms.counterparties.models import Responsible, Counterparty, CounterpartyGroup, ResponsibleGroup
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet, \
    GenericClassifierViewSet
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionGroupFilter, \
    ObjectPermissionPermissionFilter
from poms.obj_perms.permissions import PomsConfigurationPermission
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet, AbstractEvGroupWithObjectPermissionViewSet
from poms.portfolios.models import Portfolio, PortfolioRegister, PortfolioRegisterRecord
from poms.portfolios.serializers import PortfolioSerializer, PortfolioLightSerializer, PortfolioEvSerializer, \
    PortfolioRegisterSerializer, PortfolioRegisterEvSerializer, PortfolioRegisterRecordSerializer, \
    PortfolioRegisterRecordEvSerializer, CalculateRecordsSerializer
from poms.transactions.models import TransactionType, TransactionTypeGroup
from poms.users.filters import OwnerByMasterUserFilter
from rest_framework.decorators import action

from poms.portfolios.tasks import calculate_portfolio_register_record, calculate_portfolio_register_price_history

from rest_framework.settings import api_settings
from rest_framework.response import Response

from logging import getLogger

_l = getLogger('poms.portfolios')




class PortfolioAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Portfolio
    target_model_serializer = PortfolioSerializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


class PortfolioClassifierViewSet(GenericClassifierViewSet):
    target_model = Portfolio


class PortfolioFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    account = ModelExtWithPermissionMultipleChoiceFilter(model=Account, field_name='accounts')
    responsible = ModelExtWithPermissionMultipleChoiceFilter(model=Responsible, field_name='responsibles')
    counterparty = ModelExtWithPermissionMultipleChoiceFilter(model=Counterparty, field_name='counterparties')
    transaction_type = ModelExtWithPermissionMultipleChoiceFilter(model=TransactionType, field_name='transaction_types')
    member = ObjectPermissionMemberFilter(object_permission_model=Portfolio)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Portfolio)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Portfolio)
    attribute_types = GroupsAttributeFilter()
    attribute_values = GroupsAttributeFilter()

    class Meta:
        model = Portfolio
        fields = []


class PortfolioViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Portfolio.objects.select_related(
        'master_user',
    ).prefetch_related(
        Prefetch('accounts', queryset=Account.objects.select_related('type')),
        Prefetch('responsibles', queryset=Responsible.objects.select_related('group')),
        Prefetch('counterparties', queryset=Counterparty.objects.select_related('group')),
        Prefetch('transaction_types', queryset=TransactionType.objects.select_related('group')),
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Portfolio),
            ('accounts', Account),
            ('accounts__type', AccountType),
            ('counterparties', Counterparty),
            ('counterparties__group', CounterpartyGroup),
            ('responsibles', Responsible),
            ('responsibles__group', ResponsibleGroup),
            ('transaction_types', TransactionType),
            ('transaction_types__group', TransactionTypeGroup),
        )
    )
    serializer_class = PortfolioSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    filter_class = PortfolioFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]


class PortfolioLightFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()

    class Meta:
        model = Portfolio
        fields = []


class PortfolioEvFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    account = ModelExtWithPermissionMultipleChoiceFilter(model=Account, field_name='accounts')
    responsible = ModelExtWithPermissionMultipleChoiceFilter(model=Responsible, field_name='responsibles')
    counterparty = ModelExtWithPermissionMultipleChoiceFilter(model=Counterparty, field_name='counterparties')
    transaction_type = ModelExtWithPermissionMultipleChoiceFilter(model=TransactionType, field_name='transaction_types')
    member = ObjectPermissionMemberFilter(object_permission_model=Portfolio)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Portfolio)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Portfolio)
    attribute_types = GroupsAttributeFilter()
    attribute_values = GroupsAttributeFilter()

    class Meta:
        model = Portfolio
        fields = []


class PortfolioEvViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Portfolio.objects.select_related(
        'master_user',
    ).prefetch_related(
        'attributes',
        'attributes__classifier',
        # get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Portfolio),
        )
    )
    serializer_class = PortfolioEvSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    filter_class = PortfolioEvFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]


class PortfolioLightViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Portfolio.objects.select_related(
        'master_user',
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Portfolio),
        )
    )
    serializer_class = PortfolioLightSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter
    ]
    filter_class = PortfolioLightFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]


class PortfolioEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Portfolio.objects.select_related(
        'master_user',
    ).prefetch_related(
        get_attributes_prefetch()
    )

    serializer_class = PortfolioSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = PortfolioFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]





class PortfolioRegisterAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = PortfolioRegister
    target_model_serializer = PortfolioRegisterSerializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


class PortfolioRegisterFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()


    class Meta:
        model = PortfolioRegister
        fields = []


class PortfolioRegisterEvFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()

    class Meta:
        model = PortfolioRegister
        fields = []



class PortfolioRegisterViewSet(AbstractWithObjectPermissionViewSet):
    queryset = PortfolioRegister.objects.select_related(
        'master_user',
    ).prefetch_related(
        get_attributes_prefetch(),
    )
    serializer_class = PortfolioRegisterSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    filter_class = PortfolioRegisterFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]

    @action(detail=False, methods=['post'], url_path='calculate-records')
    def calculate_records(self, request):

        _l.debug("Run Calculate Portfolio Registry Records data %s" % request.data)

        portfolio_register_ids = request.data['portfolio_register_ids']

        master_user = request.user.master_user

        calculate_portfolio_register_record.apply_async(kwargs={'portfolio_register_ids': portfolio_register_ids, 'master_users': [master_user.id]})

        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'], url_path='calculate-price-history')
    def calculate_price_history(self, request):

        _l.debug("Run Calculate Portfolio Registry navs data %s" % request.data)

        master_user = request.user.master_user

        calculate_portfolio_register_price_history.apply_async()

        return Response({'status': 'ok'})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        keep_instrument = request.data.get('keep_instrument')

        if keep_instrument != 'true':
            instance.linked_instrument.delete()

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

class PortfolioRegisterEvViewSet(AbstractWithObjectPermissionViewSet):
    queryset = PortfolioRegister.objects.select_related(
        'master_user',
    ).prefetch_related(
        'attributes',
        'attributes__classifier',
    )
    serializer_class = PortfolioRegisterEvSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    filter_class = PortfolioRegisterEvFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]


class PortfolioRegisterEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = PortfolioRegister.objects.select_related(
        'master_user',
    ).prefetch_related(
        get_attributes_prefetch()
    )

    serializer_class = PortfolioRegisterSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = PortfolioRegisterFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


# Portfolio Register Record

class PortfolioRegisterRecordFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = PortfolioRegisterRecord
        fields = []


class PortfolioRegisterRecordEvFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = PortfolioRegisterRecord
        fields = []


class PortfolioRegisterRecordViewSet(AbstractWithObjectPermissionViewSet):
    queryset = PortfolioRegisterRecord.objects.select_related(
        'master_user',
    )
    serializer_class = PortfolioRegisterRecordSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter
    ]
    filter_class = PortfolioRegisterRecordFilterSet
    ordering_fields = [
    ]




class PortfolioRegisterRecordEvViewSet(AbstractWithObjectPermissionViewSet):
    queryset = PortfolioRegisterRecord.objects.select_related(
        'master_user',
    )
    serializer_class = PortfolioRegisterRecordEvSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter
    ]
    filter_class = PortfolioRegisterRecordEvFilterSet
    ordering_fields = [
    ]


class PortfolioRegisterRecordEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = PortfolioRegisterRecord.objects.select_related(
        'master_user',
    )

    serializer_class = PortfolioRegisterRecordSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = PortfolioRegisterRecordFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter
    ]
