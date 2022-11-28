from __future__ import unicode_literals

import logging

from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

from poms.accounts.models import Account
from poms.instruments.models import Instrument, InstrumentType
from poms.obj_attrs.models import GenericAttributeType
from poms.obj_perms.utils import obj_perms_filter_objects_for_view
from poms.portfolios.models import Portfolio

_l = logging.getLogger('poms.instruments')


class OwnerByInstrumentFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        instruments = Instrument.objects.filter(master_user=request.user.master_user)
        return queryset.filter(instrument__in=instruments)


class OwnerByPermissionedInstrumentFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        instruments = Instrument.objects.filter(master_user=request.user.master_user)
        return queryset.filter(instrument__in=instruments)


class OwnerByInstrumentTypeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        instrument_types = InstrumentType.objects.filter(master_user=request.user.master_user)
        return queryset.filter(instrument_type__in=instrument_types)


class OwnerByInstrumentAttributeTypeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        instrument_attribute_types = GenericAttributeType.objects.filter(master_user=request.user.master_user)
        return queryset.filter(attribute_type__in=instrument_attribute_types)


class PriceHistoryObjectPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        member = request.user.member
        master_user = request.user.master_user
        if member.is_superuser:
            return queryset
        instrument_qs = obj_perms_filter_objects_for_view(member, Instrument.objects.filter(master_user=master_user))
        queryset = queryset.filter(instrument__in=instrument_qs)
        return queryset


# class InstrumentTypeFilter(ModelWithPermissionMultipleChoiceFilter):
#     model = InstrumentType
#
#
# class InstrumentFilter(ModelWithPermissionMultipleChoiceFilter):
#     model = Instrument


class GeneratedEventPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        member = request.user.member
        master_user = request.user.master_user

        if member.is_superuser:
            return queryset
        # instrument_qs = obj_perms_filter_objects_for_view(member, Instrument.objects.filter(master_user=master_user))
        portfolio_qs = obj_perms_filter_objects_for_view(member, Portfolio.objects.filter(master_user=master_user))
        account_qs = obj_perms_filter_objects_for_view(member, Account.objects.filter(master_user=master_user))
        # strategy1_qs = obj_perms_filter_objects_for_view(member, Strategy1.objects.filter(master_user=master_user))
        # strategy2_qs = obj_perms_filter_objects_for_view(member, Strategy2.objects.filter(master_user=master_user))

        # strategy3_qs = obj_perms_filter_objects_for_view(member, Strategy3.objects.filter(master_user=master_user))
        #

        # queryset = queryset.filter(instrument__in=instrument_qs, portfolio__in=portfolio_qs, account__in=account_qs,
        #                            strategy1__in=strategy1_qs, strategy2__in=strategy2_qs, strategy3__in=strategy3_qs)

        queryset = queryset.filter(portfolio__in=portfolio_qs, account__in=account_qs)

        return queryset


class InstrumentSelectSpecialQueryFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):

        query = request.query_params.get('query', '')
        instrument_type = request.query_params.get('instrument_type', '')

        pieces = query.split(' ')

        options = Q()

        name_q = Q()
        user_code_q = Q()
        short_name_q = Q()
        reference_for_pricing_q = Q()
        instrument_type_name = Q()
        instrument_type_user_code = Q()

        for piece in pieces:
            name_q.add(Q(name__icontains=piece), Q.AND)

        for piece in pieces:
            user_code_q.add(Q(user_code__icontains=piece), Q.AND)

        for piece in pieces:
            short_name_q.add(Q(short_name__icontains=piece), Q.AND)

        for piece in pieces:
            reference_for_pricing_q.add(Q(reference_for_pricing__icontains=piece), Q.AND)

        # for piece in pieces:
        #     instrument_type_name.add(Q(instrument_type__name__icontains=piece), Q.OR)

        for piece in pieces:
            instrument_type_user_code.add(Q(instrument_type__user_code__icontains=piece), Q.AND)

        # _l.info('query %s' % query)

        options.add(Q(name__icontains=query), Q.OR)
        options.add(Q(user_code__icontains=query), Q.OR)
        options.add(Q(short_name__icontains=query), Q.OR)

        options.add(name_q, Q.OR)
        options.add(user_code_q, Q.OR)
        options.add(short_name_q, Q.OR)
        options.add(reference_for_pricing_q, Q.OR)
        # options.add(instrument_type_name, Q.AND)
        options.add(instrument_type_user_code, Q.OR)

        if instrument_type:
            options.add(Q(instrument_type__user_code=instrument_type), Q.AND)

        queryset = queryset.filter(options)

        return queryset
