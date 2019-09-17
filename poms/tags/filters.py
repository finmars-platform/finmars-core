from functools import partial

import django_filters
from django.contrib.contenttypes.models import ContentType
from rest_framework.filters import BaseFilterBackend

from poms.accounts.models import Account
from poms.accounts.models import AccountType
from poms.chats.models import ThreadGroup, Thread
from poms.common.middleware import get_request
from poms.counterparties.models import Counterparty, CounterpartyGroup, ResponsibleGroup
from poms.counterparties.models import Responsible
from poms.currencies.models import Currency
from poms.instruments.models import Instrument
from poms.instruments.models import InstrumentType
from poms.obj_perms.utils import obj_perms_filter_objects_for_view, obj_perms_prefetch
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, Strategy2Subgroup, \
    Strategy2, Strategy3Group, Strategy3Subgroup, Strategy3
from poms.tags.models import Tag
from poms.transactions.models import TransactionType, TransactionTypeGroup


def get_tag_content_types():
    models = [AccountType, Account, Currency, InstrumentType, Instrument, Portfolio,
              CounterpartyGroup, Counterparty, ResponsibleGroup, Responsible,
              Strategy1Group, Strategy1Subgroup, Strategy1,
              Strategy2Group, Strategy2Subgroup, Strategy2,
              Strategy3Group, Strategy3Subgroup, Strategy3,
              TransactionTypeGroup, TransactionType, ThreadGroup, Thread]
    return [ContentType.objects.get_for_model(model).pk for model in models]


class TagFakeFilter(django_filters.Filter):
    def __init__(self, *args, **kwargs):
        super(TagFakeFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        return qs


class TagContentTypeFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(pk__in=get_tag_content_types())


# class TagFilterBackend(BaseFilterBackend):
#     def filter_queryset(self, request, queryset, view):
#         # queryset = queryset.prefetch_related(
#         #     'tags',
#         #     'tags__user_object_permissions', 'tags__user_object_permissions__permission',
#         #     'tags__group_object_permissions', 'tags__group_object_permissions__permission',
#         # )
#         queryset = queryset.prefetch_related('tags')
#         queryset = obj_perms_prefetch(queryset, my=False, lookups_related=[('tags', Tag)])
#         return queryset


def tags_choices(model=None):
    master_user = get_request().user.master_user
    member = get_request().user.member
    content_type = ContentType.objects.get_for_model(model)
    qs = Tag.objects.filter(master_user=master_user, content_types__in=[content_type.id]).order_by('name')
    for t in obj_perms_filter_objects_for_view(member, qs, prefetch=False):
        yield t.id, t.name


class TagFilter(django_filters.MultipleChoiceFilter):
    def __init__(self, *args, **kwargs):
        model = kwargs.pop('model')
        kwargs['field_name'] = 'tags__tag'
        kwargs['choices'] = partial(tags_choices, model=model)
        super(TagFilter, self).__init__(*args, **kwargs)


def tag_content_type_choices():
    queryset = ContentType.objects.all().order_by('app_label', 'model').filter(pk__in=get_tag_content_types())
    for c in queryset:
        yield '%s.%s' % (c.app_label, c.model), c.model_class()._meta.verbose_name


class TagContentTypeFilter(django_filters.MultipleChoiceFilter):
    def __init__(self, *args, **kwargs):
        # queryset = ContentType.objects.all().order_by('app_label', 'model').filter(pk__in=get_tag_content_types())
        # kwargs['choices'] = [('%s.%s' % (c.app_label, c.model), c.model_class()._meta.verbose_name)
        #                      for c in queryset]
        kwargs['choices'] = tag_content_type_choices
        super(TagContentTypeFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        value = value or tuple()
        cvalue = []
        for v in value:
            ctype = v.split('.')
            ctype = ContentType.objects.get_by_natural_key(*ctype)
            cvalue.append(ctype.id)
        return super(TagContentTypeFilter, self).filter(qs, cvalue)
