from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

from poms.accounts.models import Account
from poms.counterparties.models import Counterparty
from poms.counterparties.models import Responsible
from poms.currencies.models import Currency
from poms.instruments.models import InstrumentType, Instrument, DailyPricingModel, PaymentSizeDetail, PricingPolicy, \
    Periodicity, AccrualCalculationModel
from poms.integrations.models import PriceDownloadScheme
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionGroupFilter, \
    ObjectPermissionPermissionFilter
from poms.obj_perms.models import GenericObjectPermission
from poms.obj_perms.utils import obj_perms_filter_objects_for_view, obj_perms_filter_objects
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.transactions.models import Transaction, EventClass, NotificationClass


class TransactionObjectPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        master_user = request.user.master_user
        member = request.user.member

        # if member.is_superuser:
        #     return queryset
        #
        # portfolio_qs = obj_perms_filter_objects_for_view(member, Portfolio.objects.filter(master_user=master_user))
        # account_qs = obj_perms_filter_objects_for_view(member, Account.objects.filter(master_user=master_user))
        # # minimize inlined SQL
        # portfolio_qs = list(portfolio_qs.values_list('id', flat=True))
        # account_qs = list(account_qs.values_list('id', flat=True))
        # queryset = queryset.filter(
        #     Q(portfolio__in=portfolio_qs) |
        #     (Q(account_position__in=account_qs) | Q(account_cash__in=account_qs) | Q(account_interim__in=account_qs))
        # )
        # return queryset
        return self.filter_qs(queryset, master_user, member)

    @classmethod
    def filter_qs(self, queryset, master_user, member):
        if member.is_superuser:
            return queryset

        queryset = obj_perms_filter_objects_for_view(member, queryset)

        # portfolio_qs = obj_perms_filter_objects_for_view(member, Portfolio.objects.filter(master_user=master_user))
        # account_qs = obj_perms_filter_objects_for_view(member, Account.objects.filter(master_user=master_user))
        # # minimize inlined SQL
        # portfolio_qs = list(portfolio_qs.values_list('id', flat=True))
        # account_qs = list(account_qs.values_list('id', flat=True))
        # queryset = queryset.filter(
        #     Q(portfolio__in=portfolio_qs) |
        #     (Q(account_position__in=account_qs) | Q(account_cash__in=account_qs) | Q(account_interim__in=account_qs))
        # )
        return queryset


class TransactionTypeInputContentTypeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        models = [Account, Instrument, InstrumentType, Currency, Counterparty, Responsible, Portfolio,
                  Strategy1, Strategy2, Strategy3, DailyPricingModel, PaymentSizeDetail, PriceDownloadScheme,
                  PricingPolicy, Periodicity, AccrualCalculationModel, EventClass, NotificationClass]
        ctypes = [ContentType.objects.get_for_model(model).pk for model in models]
        return queryset.filter(pk__in=ctypes)


class ComplexTransactionPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):

        return queryset.filter(master_user=request.user.master_user)

        # trn_qs = Transaction.objects.filter(master_user=request.user.master_user)
        # trn_qs = TransactionObjectPermissionFilter().filter_queryset(request, trn_qs, view)
        #
        #
        # return queryset.filter(
        #     transaction_type__master_user=request.user.master_user,
        #     pk__in=trn_qs.values_list('complex_transaction', flat=True)
        # )


class TransactionObjectPermissionMemberFilter(ObjectPermissionMemberFilter):
    # def get_user_filter_q(self, value):
    #     user_lookup_name, user_obj_perms_model = get_user_obj_perms_model(self.object_permission_model)
    #     pk_q = user_obj_perms_model.objects.filter(member__groups__in=value).values_list(
    #         'content_object__id', flat=True)
    #
    #     if issubclass(self.object_permission_model, Account):
    #         return Q(account_position__in=pk_q) | Q(account_cash__in=pk_q) | Q(account_interim__in=pk_q)
    #     elif issubclass(self.object_permission_model, Portfolio):
    #         return Q(portfolio__in=pk_q)
    #     else:
    #         raise ValueError('Invalid object_permission_model')
    #
    # def get_group_filter_q(self, value):
    #     group_lookup_name, group_obj_perms_model = get_group_obj_perms_model(self.object_permission_model)
    #     pk_q = group_obj_perms_model.objects.filter(group__in=value).values_list('content_object__id', flat=True)
    #
    #     if issubclass(self.object_permission_model, Account):
    #         return Q(account_position__in=pk_q) | Q(account_cash__in=pk_q) | Q(account_interim__in=pk_q)
    #     elif issubclass(self.object_permission_model, Portfolio):
    #         return Q(portfolio__in=pk_q)
    #     else:
    #         raise ValueError('Invalid object_permission_model')

    def get_permission_filter(self, value):
        ctype = ContentType.objects.get_for_model(self.object_permission_model)
        pk_q = Q(
            pk__in=GenericObjectPermission.objects.filter(
                content_type=ctype, permission__content_type=ctype,
            ).filter(
                Q(member__in=value) | Q(group__members__in=value)
            ).values_list('object_id', flat=True)
        )

        if issubclass(self.object_permission_model, Account):
            return Q(account_position__in=pk_q) | Q(account_cash__in=pk_q) | Q(account_interim__in=pk_q)
        elif issubclass(self.object_permission_model, Portfolio):
            return Q(portfolio__in=pk_q)
        else:
            raise ValueError('Invalid object_permission_model')


class TransactionObjectPermissionGroupFilter(ObjectPermissionGroupFilter):
    # def get_user_filter_q(self, value):
    #     user_lookup_name, user_obj_perms_model = get_user_obj_perms_model(self.object_permission_model)
    #     pk_q = user_obj_perms_model.objects.filter(member__groups__in=value).values_list(
    #         'content_object__id', flat=True)
    #
    #     if issubclass(self.object_permission_model, Account):
    #         return Q(account_position__in=pk_q) | Q(account_cash__in=pk_q) | Q(account_interim__in=pk_q)
    #     elif issubclass(self.object_permission_model, Portfolio):
    #         return Q(portfolio__in=pk_q)
    #     else:
    #         raise ValueError('Invalid object_permission_model')
    #
    # def get_group_filter_q(self, value):
    #     group_lookup_name, group_obj_perms_model = get_group_obj_perms_model(self.object_permission_model)
    #     pk_q = group_obj_perms_model.objects.filter(group__in=value).values_list(
    #         'content_object__id', flat=True)
    #     if issubclass(self.object_permission_model, Account):
    #         return Q(account_position__in=pk_q) | Q(account_cash__in=pk_q) | Q(account_interim__in=pk_q)
    #     elif issubclass(self.object_permission_model, Portfolio):
    #         return Q(portfolio__in=pk_q)
    #     else:
    #         raise ValueError('Invalid object_permission_model')

    def get_permission_filter(self, value):
        ctype = ContentType.objects.get_for_model(self.object_permission_model)
        pk_q = Q(
            pk__in=GenericObjectPermission.objects.filter(
                content_type=ctype, permission__content_type=ctype,
            ).filter(
                Q(member__groups__in=value) | Q(group__in=value)
            ).values_list('object_id', flat=True)
        )
        if issubclass(self.object_permission_model, Account):
            return Q(account_position__in=pk_q) | Q(account_cash__in=pk_q) | Q(account_interim__in=pk_q)
        elif issubclass(self.object_permission_model, Portfolio):
            return Q(portfolio__in=pk_q)
        else:
            raise ValueError('Invalid object_permission_model')


class TransactionObjectPermissionPermissionFilter(ObjectPermissionPermissionFilter):
    # def get_user_filter_q(self, value):
    #     user_lookup_name, user_obj_perms_model = get_user_obj_perms_model(self.object_permission_model)
    #     pk_q = user_obj_perms_model.objects.filter(permission__codename__in=value).values_list(
    #         'content_object__id', flat=True)
    #
    #     if issubclass(self.object_permission_model, Account):
    #         return Q(account_position__in=pk_q) | Q(account_cash__in=pk_q) | Q(account_interim__in=pk_q)
    #     elif issubclass(self.object_permission_model, Portfolio):
    #         return Q(portfolio__in=pk_q)
    #     else:
    #         raise ValueError('Invalid object_permission_model')
    #
    # def get_group_filter_q(self, value):
    #     group_lookup_name, group_obj_perms_model = get_group_obj_perms_model(self.object_permission_model)
    #     pk_q = group_obj_perms_model.objects.filter(permission__codename__in=value).values_list(
    #         'content_object__id', flat=True)
    #     if issubclass(self.object_permission_model, Account):
    #         return Q(account_position__in=pk_q) | Q(account_cash__in=pk_q) | Q(account_interim__in=pk_q)
    #     elif issubclass(self.object_permission_model, Portfolio):
    #         return Q(portfolio__in=pk_q)
    #     else:
    #         raise ValueError('Invalid object_permission_model')

    def get_permission_filter(self, value):
        ctype = ContentType.objects.get_for_model(self.object_permission_model)
        pk_q = Q(
            pk__in=GenericObjectPermission.objects.filter(
                content_type=ctype, permission__content_type=ctype,
                permission__codename__in=value
            ).values_list('object_id', flat=True)
        )
        if issubclass(self.object_permission_model, Account):
            return Q(account_position__in=pk_q) | Q(account_cash__in=pk_q) | Q(account_interim__in=pk_q)
        elif issubclass(self.object_permission_model, Portfolio):
            return Q(portfolio__in=pk_q)
        else:
            raise ValueError('Invalid object_permission_model')


class ComplexTransactionSpecificFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):

        # print("ComplexTransactionSpecificFilter before %s" % len(queryset))

        is_locked = False
        is_canceled = False
        is_partially_visible = False

        member = request.user.member

        if 'ev_options' in request.data:

            if 'complex_transaction_filters' in request.data['ev_options']:

                if 'locked' in request.data['ev_options']['complex_transaction_filters']:

                    is_locked = True

                if 'ignored' in request.data['ev_options']['complex_transaction_filters']:

                    is_canceled = True

                if 'partially_visible' in request.data['ev_options']['complex_transaction_filters']:

                    is_partially_visible = True

        # print('is_locked %s' % is_locked)
        # print('is_canceled %s' % is_canceled)
        # print('is_partial_visible %s' % is_partial_visible)

        queryset = queryset.exclude(is_locked=is_locked, is_canceled=is_canceled)

        partially_visible_permissions = ['view_complextransaction_show_parameters', 'view_complextransaction_hide_parameters']
        full_visible_permissions = ['view_complextransaction']

        if not member.is_admin:

            if is_partially_visible:
                queryset = obj_perms_filter_objects(member, partially_visible_permissions, queryset,
                                                    prefetch=False)
            else:
                queryset = obj_perms_filter_objects(member, full_visible_permissions, queryset,
                                                    prefetch=False)

        # print("ComplexTransactionSpecificFilter after %s" % len(queryset))

        return queryset

