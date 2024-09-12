import json
import logging

from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

from poms.instruments.models import Instrument, InstrumentType
from poms.obj_attrs.models import GenericAttributeType

_l = logging.getLogger("poms.instruments")


class OwnerByPermissionedInstrumentFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        instruments = Instrument.objects.filter(master_user=request.user.master_user)
        return queryset.filter(instrument__in=instruments)


class OwnerByInstrumentTypeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        instrument_types = InstrumentType.objects.filter(
            master_user=request.user.master_user
        )
        return queryset.filter(instrument_type__in=instrument_types)


class OwnerByInstrumentAttributeTypeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        instrument_attribute_types = GenericAttributeType.objects.filter(
            master_user=request.user.master_user
        )
        return queryset.filter(attribute_type__in=instrument_attribute_types)


class PriceHistoryObjectPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset


class GeneratedEventPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset


class InstrumentSelectSpecialQueryFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        query = request.query_params.get("query", "")
        instrument_type = request.query_params.get("instrument_type", "")

        pieces = query.split(" ")

        options = Q()

        name_q = Q()
        user_code_q = Q()
        short_name_q = Q()
        reference_for_pricing_q = Q()
        instrument_type_user_code = Q()

        for piece in pieces:
            name_q.add(Q(name__icontains=piece), Q.AND)

        for piece in pieces:
            user_code_q.add(Q(user_code__icontains=piece), Q.AND)

        for piece in pieces:
            short_name_q.add(Q(short_name__icontains=piece), Q.AND)

        for piece in pieces:
            reference_for_pricing_q.add(
                Q(reference_for_pricing__icontains=piece), Q.AND
            )

        for piece in pieces:
            instrument_type_user_code.add(
                Q(instrument_type__user_code__icontains=piece), Q.AND
            )

        options.add(Q(name__icontains=query), Q.OR)
        options.add(Q(user_code__icontains=query), Q.OR)
        options.add(Q(short_name__icontains=query), Q.OR)

        options.add(name_q, Q.OR)
        options.add(user_code_q, Q.OR)
        options.add(short_name_q, Q.OR)
        options.add(reference_for_pricing_q, Q.OR)
        options.add(instrument_type_user_code, Q.OR)

        if instrument_type:
            options.add(Q(instrument_type__user_code=instrument_type), Q.AND)

        return queryset.filter(options)


class ListDatesFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        dates = request.query_params.getlist("dates", None)

        return queryset.filter(date__in=dates) if dates else queryset


class InstrumentsUserCodeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        user_codes = request.query_params.getlist("user_codes", None)

        if user_codes:
            return queryset.filter(instrument__user_code__in=user_codes)

        return queryset


class IdentifierKeysValuesFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        keys_values = request.query_params.get('identifier_keys_values', None)

        if keys_values is None:
            return queryset

        filter_data = json.loads(keys_values)
        filter_q = Q()
        for key, value in filter_data.items():
            filter_q &= Q(**{f"identifier__{key}": value})

        return queryset.filter(filter_q)
