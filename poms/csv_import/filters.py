from functools import partial

import django_filters
from django.contrib.contenttypes.models import ContentType
from rest_framework.filters import BaseFilterBackend

from poms.accounts.models import Account
from poms.accounts.models import AccountType
from poms.chats.models import ThreadGroup, Thread
from poms.counterparties.models import Counterparty, CounterpartyGroup, ResponsibleGroup
from poms.counterparties.models import Responsible
from poms.currencies.models import Currency
from poms.instruments.models import Instrument
from poms.instruments.models import InstrumentType
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, Strategy2Subgroup, \
    Strategy2, Strategy3Group, Strategy3Subgroup, Strategy3
from poms.transactions.models import TransactionType, TransactionTypeGroup


def get_scheme_content_types():
    models = [AccountType, Account, Currency, InstrumentType, Instrument, Portfolio,
              CounterpartyGroup, Counterparty, ResponsibleGroup, Responsible,
              Strategy1Group, Strategy1Subgroup, Strategy1,
              Strategy2Group, Strategy2Subgroup, Strategy2,
              Strategy3Group, Strategy3Subgroup, Strategy3,
              TransactionTypeGroup, TransactionType, ThreadGroup, Thread]
    return [ContentType.objects.get_for_model(model).pk for model in models]


def scheme_content_type_choices():
    queryset = ContentType.objects.all().order_by('app_label', 'model').filter(pk__in=get_scheme_content_types())
    for c in queryset:
        yield '%s.%s' % (c.app_label, c.model), c.model_class()._meta.verbose_name


class SchemeContentTypeFilter(django_filters.MultipleChoiceFilter):
    def __init__(self, *args, **kwargs):

        kwargs['choices'] = scheme_content_type_choices
        super(SchemeContentTypeFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        value = value or tuple()
        cvalue = []
        for v in value:
            ctype = v.split('.')
            ctype = ContentType.objects.get_by_natural_key(*ctype)
            cvalue.append(ctype.id)
        return super(SchemeContentTypeFilter, self).filter(qs, cvalue)
