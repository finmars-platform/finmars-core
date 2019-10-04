from functools import partial

import django_filters
from django.contrib.contenttypes.models import ContentType
from rest_framework.filters import BaseFilterBackend

from poms.accounts.models import Account
from poms.accounts.models import AccountType
from poms.chats.models import ThreadGroup, Thread
from poms.counterparties.models import Counterparty, CounterpartyGroup, ResponsibleGroup
from poms.counterparties.models import Responsible
from poms.currencies.models import Currency, CurrencyHistory
from poms.instruments.models import Instrument, PriceHistory
from poms.instruments.models import InstrumentType
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, Strategy2Subgroup, \
    Strategy2, Strategy3Group, Strategy3Subgroup, Strategy3
from poms.transactions.models import TransactionType, TransactionTypeGroup
