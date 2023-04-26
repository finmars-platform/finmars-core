from logging import getLogger

import django_filters
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.settings import api_settings

from poms.accounts.models import Account
from poms.common.filters import CharFilter, ModelExtWithPermissionMultipleChoiceFilter, NoOpFilter, \
    GroupsAttributeFilter, AttributeFilter, EntitySpecificFilter
from poms.common.pagination import CustomPaginationMixin
from poms.common.utils import get_list_of_entity_attributes
from poms.counterparties.models import Responsible, Counterparty
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet, \
    GenericClassifierViewSet
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionGroupFilter, \
    ObjectPermissionPermissionFilter
from poms.obj_perms.permissions import PomsConfigurationPermission
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet, AbstractEvGroupWithObjectPermissionViewSet
from poms.portfolios.models import Portfolio, PortfolioRegister, PortfolioRegisterRecord, PortfolioBundle
from poms.portfolios.serializers import PortfolioSerializer, PortfolioLightSerializer, PortfolioEvSerializer, \
    PortfolioRegisterSerializer, PortfolioRegisterEvSerializer, PortfolioRegisterRecordSerializer, \
    PortfolioRegisterRecordEvSerializer, PortfolioBundleSerializer, \
    PortfolioBundleEvSerializer
from poms.portfolios.tasks import calculate_portfolio_register_record, calculate_portfolio_register_price_history
from poms.transactions.models import TransactionType
from poms.users.filters import OwnerByMasterUserFilter

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
    # account = ModelExtWithPermissionMultipleChoiceFilter(model=Account, field_name='accounts')
    # responsible = ModelExtWithPermissionMultipleChoiceFilter(model=Responsible, field_name='responsibles')
    # counterparty = ModelExtWithPermissionMultipleChoiceFilter(model=Counterparty, field_name='counterparties')
    # transaction_type = ModelExtWithPermissionMultipleChoiceFilter(model=TransactionType, field_name='transaction_types')
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
        # Prefetch('accounts', queryset=Account.objects.select_related('type')),
        # Prefetch('responsibles', queryset=Responsible.objects.select_related('group')),
        # Prefetch('counterparties', queryset=Counterparty.objects.select_related('group')),
        # Prefetch('transaction_types', queryset=TransactionType.objects.select_related('group')),
        get_attributes_prefetch(),
        # *get_permissions_prefetch_lookups(
        #     (None, Portfolio),
        #     ('accounts', Account),
        #     ('accounts__type', AccountType),
        #     ('counterparties', Counterparty),
        #     ('counterparties__group', CounterpartyGroup),
        #     ('responsibles', Responsible),
        #     ('responsibles__group', ResponsibleGroup),
        #     ('transaction_types', TransactionType),
        #     ('transaction_types__group', TransactionTypeGroup),
        # )
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

    def create(self, request, *args, **kwargs):
        # Probably pointless on portfolio create
        # Because you cannot book transaction without portfolio
        # calculate_portfolio_register_record.apply_async(
        #     link=[
        #         calculate_portfolio_register_price_history.s()
        #     ])

        _l.info("Create Portfolio")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):

        # trigger recalc after book properly
        # calculate_portfolio_register_record.apply_async(
        #     link=[
        #         calculate_portfolio_register_price_history.s()
        #     ])

        _l.info("Update Portfolio")

        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='light', serializer_class=PortfolioLightSerializer)
    def list_light(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        result = self.get_paginated_response(serializer.data)

        return result

    @action(detail=False, methods=['get'], url_path='attributes')
    def list_attributes(self, request, *args, **kwargs):

        items = [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10
            },
            {
                "key": "accounts",
                "name": "Accounts",
                "value_content_type": "accounts.account",
                "value_entity": "account",
                "code": "user_code",
                "value_type": "mc_field"

            },
            {
                "key": "responsibles",
                "name": "Responsibles",
                "value_content_type": "counterparties.responsible",
                "value_entity": "responsible",
                "code": "user_code",
                "value_type": "mc_field"
            },
            {
                "key": "counterparties",
                "name": "Counterparties",
                "value_content_type": "counterparties.counterparty",
                "value_entity": "counterparty",
                "code": "user_code",
                "value_type": "mc_field"
            },
            {
                "key": "transaction_types",
                "name": "Transaction types",
                "value_content_type": "transactions.transactiontype",
                "value_entity": "transaction-type",
                "code": "user_code",
                "value_type": "mc_field"
            }
        ]

        items = items + get_list_of_entity_attributes('portfolios.portfolio')

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items
        }

        return Response(result)


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

# DEPRECATED
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

        portfolio_ids = request.data['portfolio_ids']

        master_user = request.user.master_user

        # Trigger Recalc Properly
        # calculate_portfolio_register_record.apply_async(
        #     kwargs={'portfolio_ids': portfolio_ids})

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

        linked_instrument_id = instance.linked_instrument_id

        self.perform_destroy(instance)

        _l.info("Destroy portfolio register linked_instrument_id %s" % linked_instrument_id)
        _l.info("Destroy portfolio register keep_instrument %s" % keep_instrument)

        self.perform_destroy(instance)

        if keep_instrument != 'true':
            if linked_instrument_id:
                _l.info("initing fake delete for instrument")

                from poms.instruments.models import Instrument
                instrument = Instrument.objects.get(id=linked_instrument_id)
                instrument.fake_delete()

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
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter
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


class PortfolioBundleFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = PortfolioBundle
        fields = []


class PortfolioBundleEvFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = PortfolioBundle
        fields = []


class PortfolioBundleViewSet(AbstractWithObjectPermissionViewSet):
    queryset = PortfolioBundle.objects.select_related(
        'master_user',
    )
    serializer_class = PortfolioBundleSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter
    ]
    filter_class = PortfolioBundleFilterSet
    ordering_fields = [
    ]


class PortfolioBundleEvViewSet(AbstractWithObjectPermissionViewSet):
    queryset = PortfolioRegisterRecord.objects.select_related(
        'master_user',
    )
    serializer_class = PortfolioBundleEvSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter
    ]
    filter_class = PortfolioBundleEvFilterSet
    ordering_fields = [
    ]


class PortfolioBundleEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = PortfolioBundle.objects.select_related(
        'master_user',
    )

    serializer_class = PortfolioBundleSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = PortfolioBundleFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter
    ]
