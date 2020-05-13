from __future__ import unicode_literals

import json
from datetime import date

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import ugettext_lazy
from mptt.models import MPTTModel

from poms.accounts.models import Account
from poms.common.models import NamedModel, AbstractClassModel, FakeDeletableModel, EXPRESSION_FIELD_LENGTH
from poms.common.utils import date_now
from poms.counterparties.models import Responsible, Counterparty
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, InstrumentClass, PricingPolicy, AccrualCalculationModel, Periodicity, \
    EventSchedule
from poms.obj_attrs.models import GenericAttribute
from poms.obj_perms.models import GenericObjectPermission
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.tags.models import TagLink
from poms.transactions.utils import calc_cash_for_contract_for_difference
from poms.users.models import MasterUser, Member, FakeSequence


class TransactionClass(AbstractClassModel):
    BUY = 1
    SELL = 2
    FX_TRADE = 3
    INSTRUMENT_PL = 4
    TRANSACTION_PL = 5
    TRANSFER = 6
    FX_TRANSFER = 7
    CASH_INFLOW = 8
    CASH_OUTFLOW = 9

    DEFAULT = 10

    CLASSES = (
        (BUY, 'BUY', ugettext_lazy("Buy")),
        (SELL, 'SELL', ugettext_lazy("Sell")),
        (FX_TRADE, 'FX_TRADE', ugettext_lazy("FX Trade")),
        (INSTRUMENT_PL, 'INSTRUMENT_PL', ugettext_lazy("Instrument PL")),
        (TRANSACTION_PL, 'TRANSACTION_PL', ugettext_lazy("Transaction PL")),
        (TRANSFER, 'TRANSFER', ugettext_lazy("Transfer")),
        (FX_TRANSFER, 'FX_TRANSFER', ugettext_lazy("FX Transfer")),
        (CASH_INFLOW, 'CASH_INFLOW', ugettext_lazy("Cash-Inflow")),
        (CASH_OUTFLOW, 'CASH_OUTFLOW', ugettext_lazy("Cash-Outflow")),
        (DEFAULT, '-', ugettext_lazy("Default")),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = ugettext_lazy('transaction class')
        verbose_name_plural = ugettext_lazy('transaction classes')


class ActionClass(AbstractClassModel):
    CREATE_INSTRUMENT = 1
    CREATE_INSTRUMENT_PARAMETER = 2

    CLASSES = (
        (CREATE_INSTRUMENT, 'CREATE_INSTRUMENT', ugettext_lazy("Create instrument")),
        (CREATE_INSTRUMENT_PARAMETER, 'CREATE_INSTRUMENT_PARAMETER', ugettext_lazy("Create instrument parameter")),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = ugettext_lazy('action class')
        verbose_name_plural = ugettext_lazy('action classes')


class EventClass(AbstractClassModel):
    ONE_OFF = 1
    REGULAR = 2

    CLASSES = (
        (ONE_OFF, 'ONE_OFF', ugettext_lazy('One-off')),
        (REGULAR, 'REGULAR', ugettext_lazy('Regular')),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = ugettext_lazy('event class')
        verbose_name_plural = ugettext_lazy('event classes')


class NotificationClass(AbstractClassModel):
    # NDATE -> notification_date
    # EDATE -> effective_date

    DONT_REACT = 1
    APPLY_DEF_ON_EDATE = 2
    APPLY_DEF_ON_NDATE = 3

    INFORM_ON_NDATE_WITH_REACT = 4
    INFORM_ON_NDATE_APPLY_DEF = 5
    INFORM_ON_NDATE_DONT_REACT = 6
    INFORM_ON_EDATE_WITH_REACT = 7
    INFORM_ON_EDATE_APPLY_DEF = 8
    INFORM_ON_EDATE_DONT_REACT = 9

    INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_EDATE = 10
    INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_NDATE = 11
    INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_EDATE = 12
    INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_NDATE = 13
    INFORM_ON_NDATE_AND_EDATE_DONT_REACT = 14

    CLASSES = (
        (DONT_REACT, 'DONT_REACT',
         ugettext_lazy("Don't inform (don't react)")),
        (APPLY_DEF_ON_EDATE, 'APPLY_DEF_ON_EDATE',
         ugettext_lazy("Don't inform (apply default on effective date)")),
        (APPLY_DEF_ON_NDATE, 'APPLY_DEF_ON_NDATE',
         ugettext_lazy("Don't inform (apply default on notification date)")),
        (INFORM_ON_NDATE_WITH_REACT, 'INFORM_ON_NDATE_WITH_REACT',
         ugettext_lazy("Inform on notification date (with reaction)")),
        (INFORM_ON_NDATE_APPLY_DEF, 'INFORM_ON_NDATE_APPLY_DEF',
         ugettext_lazy("Inform on notification date (apply default)")),
        (INFORM_ON_NDATE_DONT_REACT, 'INFORM_ON_NDATE_DONT_REACT',
         ugettext_lazy("Inform on notification date (don't react)")),
        (INFORM_ON_EDATE_WITH_REACT, 'INFORM_ON_EDATE_WITH_REACT',
         ugettext_lazy("Inform on effective date (with reaction)")),
        (INFORM_ON_EDATE_APPLY_DEF, 'INFORM_ON_EDATE_APPLY_DEF',
         ugettext_lazy("Inform on effective date (apply default)")),
        (INFORM_ON_EDATE_DONT_REACT, 'INFORM_ON_EDATE_DONT_REACT',
         ugettext_lazy("Inform on effective date (don't react)")),
        (INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_EDATE, 'INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_EDATE',
         ugettext_lazy("Inform on notification date & effective date (with reaction on effective date)")),
        (INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_NDATE, 'INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_NDATE',
         ugettext_lazy("Inform on notification date & effective date (with reaction on notification date)")),
        (INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_EDATE, 'INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_EDATE',
         ugettext_lazy("Inform on notification date & effective date (apply default on effective date)")),
        (INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_NDATE, 'INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_NDATE',
         ugettext_lazy("Inform on notification date & effective date (apply default on notification date)")),
        (INFORM_ON_NDATE_AND_EDATE_DONT_REACT, 'INFORM_ON_NDATE_AND_EDATE_DONT_REACT',
         ugettext_lazy("Inform on notification date & effective date (don't react)")),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = ugettext_lazy('notification class')
        verbose_name_plural = ugettext_lazy('notification classes')

    @staticmethod
    def get_notify_on_effective_date_classes():
        return [

            NotificationClass.INFORM_ON_EDATE_WITH_REACT,
            NotificationClass.INFORM_ON_EDATE_APPLY_DEF,
            NotificationClass.INFORM_ON_EDATE_DONT_REACT,

            NotificationClass.INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_EDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_NDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_EDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_NDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_DONT_REACT,
        ]

    @property
    def is_notify_on_effective_date(self):
        return self.id in NotificationClass.get_notify_on_effective_date_classes()

    @staticmethod
    def get_notify_on_notification_date_classes():
        return [

            NotificationClass.INFORM_ON_NDATE_WITH_REACT,
            NotificationClass.INFORM_ON_NDATE_APPLY_DEF,
            NotificationClass.INFORM_ON_NDATE_DONT_REACT,

            NotificationClass.INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_EDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_NDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_EDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_NDATE,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_DONT_REACT,
        ]

    @property
    def is_notify_on_notification_date(self):
        return self.id in NotificationClass.get_notify_on_notification_date_classes()

    @staticmethod
    def get_apply_default_on_effective_date_classes():
        return [
            NotificationClass.APPLY_DEF_ON_EDATE,
            NotificationClass.INFORM_ON_EDATE_APPLY_DEF,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_EDATE,
        ]

    @property
    def is_apply_default_on_effective_date(self):
        return self.id in NotificationClass.get_apply_default_on_effective_date_classes()

    @staticmethod
    def get_apply_default_on_notification_date_classes():
        return [

            NotificationClass.APPLY_DEF_ON_NDATE,
            NotificationClass.INFORM_ON_NDATE_APPLY_DEF,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_APPLY_DEF_ON_NDATE,

        ]

    @property
    def is_apply_default_on_notification_date(self):
        return self.id in NotificationClass.get_apply_default_on_notification_date_classes()

    @staticmethod
    def get_need_reaction_on_effective_date_classes():
        return [
            NotificationClass.INFORM_ON_EDATE_WITH_REACT,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_EDATE,
        ]

    @property
    def is_need_reaction_on_effective_date(self):
        return self.id in NotificationClass.get_need_reaction_on_effective_date_classes()

    @staticmethod
    def get_need_reaction_on_notification_date_classes():
        return [
            NotificationClass.INFORM_ON_NDATE_WITH_REACT,
            NotificationClass.INFORM_ON_NDATE_AND_EDATE_WITH_REACT_ON_NDATE,
        ]

    @property
    def is_need_reaction_on_notification_date(self):
        return self.id in NotificationClass.get_need_reaction_on_notification_date_classes()


class PeriodicityGroup(AbstractClassModel):
    DAILY = 1
    WEEKLY = 2
    WEEKLY_EOW = 3
    BE_WEEKLY = 4
    BE_WEEKLY_EOW = 5
    MONTHLY = 6
    MONTHLY_EOM = 7
    QUARTERLY = 8
    QUARTERLY_CALENDAR = 9
    SEMI_ANUALLY = 10
    SEMI_ANUALLY_CALENDAR = 11
    ANUALLY = 12
    ANUALLY_CALENDAR = 13
    CLASSES = (
        (DAILY, 'DAILY', ugettext_lazy("daily")),
        (WEEKLY, 'WEEKLY', ugettext_lazy("weekly (+7d)")),
        (WEEKLY_EOW, 'WEEKLY_EOW', ugettext_lazy("weekly (eow)")),
        (BE_WEEKLY, 'BE_WEEKLY', ugettext_lazy("bi-weekly (+14d)")),
        (BE_WEEKLY_EOW, 'BE_WEEKLY_EOW', ugettext_lazy("bi-weekly (eow)")),
        (MONTHLY, 'MONTHLY', ugettext_lazy("monthly (+1m)")),
        (MONTHLY_EOM, 'MONTHLY_EOM', ugettext_lazy("monthly (eom)")),
        (QUARTERLY, 'QUARTERLY', ugettext_lazy("quarterly (+3m)")),
        (QUARTERLY_CALENDAR, 'QUARTERLY_CALENDAR', ugettext_lazy("quarterly (calendar)")),
        (SEMI_ANUALLY, 'SEMI_ANUALLY', ugettext_lazy("semi-anually (+6m)")),
        (SEMI_ANUALLY_CALENDAR, 'SEMI_ANUALLY_CALENDAR', ugettext_lazy("semi-anually (calendar)")),
        (ANUALLY, 'ANUALLY', ugettext_lazy("anually (+12m)")),
        (ANUALLY_CALENDAR, 'ANUALLY_CALENDAR', ugettext_lazy("anually (eoy)")),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = ugettext_lazy('periodicity group')
        verbose_name_plural = ugettext_lazy('periodicity group')


class TransactionTypeGroup(NamedModel, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='transaction_type_groups',
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))
    tags = GenericRelation(TagLink, verbose_name=ugettext_lazy('tags'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('transaction type group')
        verbose_name_plural = ugettext_lazy('transaction type groups')
        permissions = [
            # ('view_transactiontypegroup', 'Can view transaction type group'),
            ('manage_transactiontypegroup', 'Can manage transaction type group'),
        ]


# class TransactionTypeGroupUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(TransactionTypeGroup, related_name='user_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('transaction type groups - user permission')
#         verbose_name_plural = ugettext_lazy('transaction type groups - user permissions')
#
#
# class TransactionTypeGroupGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(TransactionTypeGroup, related_name='group_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('transaction type groups - group permission')
#         verbose_name_plural = ugettext_lazy('transaction type groups - group permissions')


class TransactionType(NamedModel, FakeDeletableModel):

    SHOW_PARAMETERS = 1
    HIDE_PARAMETERS = 2

    VISIBILITY_STATUS_CHOICES = (
        (SHOW_PARAMETERS, ugettext_lazy('Show Parameters')),
        (HIDE_PARAMETERS, ugettext_lazy('Hide Parameters')),
    )

    TYPE_DEFAULT = 1
    TYPE_PROCEDURE = 2  # Complex Transaction will not be created

    TYPE_CHOICES = (
        (TYPE_DEFAULT, ugettext_lazy('Default')),
        (TYPE_PROCEDURE, ugettext_lazy('Procedure')),
    )

    master_user = models.ForeignKey(MasterUser, related_name='transaction_types',
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)
    group = models.ForeignKey(TransactionTypeGroup, null=True, blank=True, on_delete=models.PROTECT,
                              verbose_name=ugettext_lazy('group'))
    date_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                 verbose_name=ugettext_lazy('date expr'))
    display_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                    verbose_name=ugettext_lazy('display expr'))
    instrument_types = models.ManyToManyField('instruments.InstrumentType', related_name='transaction_types',
                                              blank=True, verbose_name=ugettext_lazy('instrument types'))
    is_valid_for_all_portfolios = models.BooleanField(default=True,
                                                      verbose_name=ugettext_lazy('is valid for all portfolios'))
    is_valid_for_all_instruments = models.BooleanField(default=True,
                                                       verbose_name=ugettext_lazy('is valid for all instruments'))

    book_transaction_layout_json = models.TextField(null=True, blank=True,
                                                    verbose_name=ugettext_lazy('book transaction layout json'))

    attributes = GenericRelation(GenericAttribute, verbose_name=ugettext_lazy('attributes'))

    visibility_status = models.PositiveSmallIntegerField(default=SHOW_PARAMETERS, choices=VISIBILITY_STATUS_CHOICES, db_index=True,
                                                         verbose_name=ugettext_lazy('visibility_status')) # settings for complex transaction

    type = models.PositiveSmallIntegerField(default=TYPE_DEFAULT, choices=TYPE_CHOICES, db_index=True,
                                            verbose_name=ugettext_lazy('type'))

    user_text_1 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 1'))

    user_text_2 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 2'))

    user_text_3 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 3'))

    user_text_4 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 4'))

    user_text_5 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 5'))

    user_text_6 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 6'))

    user_text_7 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 7'))

    user_text_8 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 8'))

    user_text_9 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 9'))

    user_text_10 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                    verbose_name=ugettext_lazy('user text 10'))

    user_text_11 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 11'))

    user_text_12 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 12'))

    user_text_13 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 13'))

    user_text_14 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 14'))

    user_text_15 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 15'))

    user_text_16 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 16'))

    user_text_17 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 17'))

    user_text_18 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 18'))

    user_text_19 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 19'))

    user_text_20 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                    verbose_name=ugettext_lazy('user text 20'))

    user_number_1 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 1'))

    user_number_2 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 2'))

    user_number_3 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 3'))

    user_number_4 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 4'))

    user_number_5 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 5'))

    user_number_6 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 6'))

    user_number_7 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 7'))

    user_number_8 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 8'))

    user_number_9 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 9'))

    user_number_10 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                      verbose_name=ugettext_lazy('user number 10'))

    user_number_11 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 11'))

    user_number_12 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 12'))

    user_number_13 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 13'))

    user_number_14 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 14'))

    user_number_15 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 15'))

    user_number_16 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 16'))

    user_number_17 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 17'))

    user_number_18 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 18'))

    user_number_19 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('user number 19'))

    user_number_20 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                      verbose_name=ugettext_lazy('user number 20'))

    user_date_1 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user date 1'))

    user_date_2 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user date 2'))

    user_date_3 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user date 3'))

    user_date_4 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user date 4'))

    user_date_5 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user date 5'))

    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))
    tags = GenericRelation(TagLink, verbose_name=ugettext_lazy('tags'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('transaction type')
        verbose_name_plural = ugettext_lazy('transaction types')
        permissions = [
            # ('view_transactiontype', 'Can view transaction type'),
            ('manage_transactiontype', 'Can manage transaction type'),
        ]
        ordering = ['user_code']

    @property
    def book_transaction_layout(self):
        try:
            return json.loads(self.book_transaction_layout_json) if self.book_transaction_layout_json else None
        except (ValueError, TypeError):
            return None

    @book_transaction_layout.setter
    def book_transaction_layout(self, data):
        self.book_transaction_layout_json = json.dumps(data, cls=DjangoJSONEncoder, sort_keys=True) if data else None


# class TransactionTypeUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(TransactionType, related_name='user_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('transaction types - user permission')
#         verbose_name_plural = ugettext_lazy('transaction types - user permissions')
#
#
# class TransactionTypeGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(TransactionType, related_name='group_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('transaction types - group permission')
#         verbose_name_plural = ugettext_lazy('transaction types - group permissions')


# name - expr
# instr - content_type:instrument
# sccy - content_type:currency
# pos - number
# price - number
# acc - content_type:account

# CONTEXT_PROPERTIES = (
#     (1, ugettext_lazy('Instrument')),
#     (2, ugettext_lazy('Pricing Currency')),
#     (3, ugettext_lazy('Accrued Currency')),
#     (4, ugettext_lazy('Portfolio')),
#     (5, ugettext_lazy('Account')),
#     (6, ugettext_lazy('Strategy 1')),
#     (7, ugettext_lazy('Strategy 2')),
#     (8, ugettext_lazy('Strategy 3')),
#     (9, ugettext_lazy('Position')),
#     (10, ugettext_lazy('Effective Date')),
# )


class TransactionTypeInput(models.Model):
    STRING = 10
    NUMBER = 20
    # EXPRESSION = 30
    DATE = 40
    RELATION = 100
    SELECTOR = 110

    # ACCOUNT = 110
    # INSTRUMENT = 120
    # CURRENCY = 130
    # COUNTERPARTY = 140
    # RESPONSIBLE = 150
    # STRATEGY1 = 161
    # STRATEGY2 = 162
    # STRATEGY3 = 163
    # DAILY_PRICING_MODEL = 170
    # PAYMENT_SIZE_DETAIL = 180
    # INSTRUMENT_TYPE = 190

    TYPES = (
        (NUMBER, ugettext_lazy('Number')),
        (STRING, ugettext_lazy('String')),
        (DATE, ugettext_lazy('Date')),
        # (EXPRESSION, ugettext_lazy('Expression')),
        (RELATION, ugettext_lazy('Relation')),
        (SELECTOR, ugettext_lazy('Selector')),
        # (ACCOUNT, ugettext_lazy('Account')),
        # (INSTRUMENT, ugettext_lazy('Instrument')),
        # (CURRENCY, ugettext_lazy('Currency')),
        # (COUNTERPARTY, ugettext_lazy('Counterparty')),
        # (RESPONSIBLE, ugettext_lazy('Responsible')),
        # (STRATEGY1, ugettext_lazy('Strategy 1')),
        # (STRATEGY2, ugettext_lazy('Strategy 2')),
        # (STRATEGY3, ugettext_lazy('Strategy 3')),
        # (DAILY_PRICING_MODEL, ugettext_lazy('Daily pricing model')),
        # (PAYMENT_SIZE_DETAIL, ugettext_lazy('Payment size detail')),
        # (INSTRUMENT_TYPE, ugettext_lazy('Instrument type'))
    )

    transaction_type = models.ForeignKey(TransactionType, related_name='inputs',
                                         verbose_name=ugettext_lazy('transaction type'), on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name=ugettext_lazy('name'))
    verbose_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=ugettext_lazy('verbose name'))
    value_type = models.PositiveSmallIntegerField(default=NUMBER, choices=TYPES,
                                                  verbose_name=ugettext_lazy('value type'))
    content_type = models.ForeignKey(ContentType, null=True, blank=True, verbose_name=ugettext_lazy('content type'),
                                     on_delete=models.SET_NULL)

    reference_table = models.CharField(max_length=255, null=True, blank=True,
                                       verbose_name=ugettext_lazy('reference table'))

    order = models.IntegerField(default=0, verbose_name=ugettext_lazy('order'))
    value_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True,
                                  verbose_name=ugettext_lazy('value expression'),
                                  help_text=ugettext_lazy('this is expression for recalculate value'))

    is_fill_from_context = models.BooleanField(default=False, verbose_name=ugettext_lazy('is fill from context'))
    context_property = models.CharField(max_length=255, null=True, blank=True,
                                        verbose_name=ugettext_lazy('context property'))

    value = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True,
                             verbose_name=ugettext_lazy('value'),
                             help_text=ugettext_lazy('this is expression for default value'))
    account = models.ForeignKey('accounts.Account', null=True, blank=True, on_delete=models.PROTECT, related_name='+',
                                verbose_name=ugettext_lazy('account'))
    instrument_type = models.ForeignKey('instruments.InstrumentType', null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='+', verbose_name=ugettext_lazy('instrument type'))
    instrument = models.ForeignKey('instruments.Instrument', null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='+', verbose_name=ugettext_lazy('instrument'))
    currency = models.ForeignKey('currencies.Currency', null=True, blank=True, on_delete=models.PROTECT,
                                 related_name='+', verbose_name=ugettext_lazy('currency'))
    counterparty = models.ForeignKey('counterparties.Counterparty', null=True, blank=True, on_delete=models.PROTECT,
                                     related_name='+', verbose_name=ugettext_lazy('counterparty'))
    responsible = models.ForeignKey('counterparties.Responsible', null=True, blank=True, on_delete=models.PROTECT,
                                    related_name='+', verbose_name=ugettext_lazy('responsible'))
    portfolio = models.ForeignKey('portfolios.Portfolio', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='+', verbose_name=ugettext_lazy('portfolio'))
    strategy1 = models.ForeignKey('strategies.Strategy1', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='+', verbose_name=ugettext_lazy('strategy 1'))
    strategy2 = models.ForeignKey('strategies.Strategy2', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='+', verbose_name=ugettext_lazy('strategy 2'))
    strategy3 = models.ForeignKey('strategies.Strategy3', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='+', verbose_name=ugettext_lazy('strategy 3'))
    daily_pricing_model = models.ForeignKey('instruments.DailyPricingModel', null=True, blank=True,
                                            on_delete=models.PROTECT, related_name='+',
                                            verbose_name=ugettext_lazy('daily pricing model'))
    payment_size_detail = models.ForeignKey('instruments.PaymentSizeDetail', null=True, blank=True,
                                            on_delete=models.PROTECT, related_name='+',
                                            verbose_name=ugettext_lazy('payment size detail'))
    price_download_scheme = models.ForeignKey('integrations.PriceDownloadScheme', null=True, blank=True,
                                              on_delete=models.PROTECT, related_name='+',
                                              verbose_name=ugettext_lazy('price download scheme'))
    pricing_policy = models.ForeignKey('instruments.PricingPolicy', null=True, blank=True,
                                       on_delete=models.PROTECT, related_name='+',
                                       verbose_name=ugettext_lazy('pricing policy'))

    periodicity = models.ForeignKey('instruments.Periodicity', null=True, blank=True,
                                    on_delete=models.PROTECT, related_name='+',
                                    verbose_name=ugettext_lazy('periodicity'))

    accrual_calculation_model = models.ForeignKey('instruments.AccrualCalculationModel', null=True, blank=True,
                                                  on_delete=models.PROTECT, related_name='+',
                                                  verbose_name=ugettext_lazy('accrual calculation model'))

    event_class = models.ForeignKey(EventClass, null=True, blank=True,
                                    on_delete=models.PROTECT, related_name='+',
                                    verbose_name=ugettext_lazy('event class'))

    notification_class = models.ForeignKey(NotificationClass, null=True, blank=True,
                                           on_delete=models.PROTECT, related_name='+',
                                           verbose_name=ugettext_lazy('notification class'))

    class Meta:
        verbose_name = ugettext_lazy('transaction type input')
        verbose_name_plural = ugettext_lazy('transaction type inputs')
        unique_together = [
            ['transaction_type', 'name'],
        ]
        index_together = [
            ['transaction_type', 'order'],
        ]
        ordering = ['name']

    def __str__(self):
        if self.value_type == self.RELATION:
            return '%s: %s' % (self.name, self.content_type)
        else:
            return '%s: %s' % (self.name, self.get_value_type_display())

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.verbose_name:
            self.verbose_name = self.name
        super(TransactionTypeInput, self).save(force_insert=force_insert, force_update=force_update, using=using,
                                               update_fields=update_fields)

    @property
    def can_recalculate(self):

        return bool(self.value_expr) and self.value_type in [TransactionTypeInput.STRING, TransactionTypeInput.SELECTOR,
                                                             TransactionTypeInput.DATE,
                                                             TransactionTypeInput.NUMBER, TransactionTypeInput.RELATION]


class TransactionTypeInputSettings(models.Model):

    transaction_type_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True,
                                               unique=True,
                                               on_delete=models.CASCADE, related_name='settings',
                                               verbose_name=ugettext_lazy('transaction type input'))

    linked_inputs_names = models.TextField(blank=True, default='', null=True, verbose_name=ugettext_lazy('linked_input_names'))


class RebookReactionChoice():
    CREATE = 0  # Used in Instrument Action
    SKIP = 1  # is not in use
    OVERWRITE = 2  # Used in Instrument Action
    CLEAR_AND_WRITE = 3
    CREATE_IF_NOT_EXIST = 4

    FIND_OR_CREATE = 5  # Used in Instrument Action
    CLEAR_AND_WRITE_OR_SKIP = 6
    CLEAR = 7

    choices = ((CREATE, 'Create'),  # simple entity create
               (SKIP, 'Skip'),  # skip creating of entity
               (OVERWRITE, 'Overwrite'),  # rewrite entity if the same user_code already exists, if not -> create
               (CLEAR_AND_WRITE, 'Clear all & Create'),
               # Special rewrite for entities without user_code (e.g.  Accruals schedule in Instrument)
               (CREATE_IF_NOT_EXIST, 'Create if not exist'),
               (CLEAR_AND_WRITE_OR_SKIP, 'If book: Clear & Append. If rebook: Skip')
               # Create if there is no entity with same user_code, otherwise skip
               )


class TransactionTypeAction(models.Model):
    transaction_type = models.ForeignKey(TransactionType, related_name='actions', on_delete=models.PROTECT,
                                         verbose_name=ugettext_lazy('transaction type'))
    order = models.IntegerField(default=0, verbose_name=ugettext_lazy('order'))
    action_notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('action notes'))

    rebook_reaction = models.IntegerField(default=0, choices=RebookReactionChoice.choices)

    condition_expr = models.CharField(max_length=1000, blank=True, default='',
                                      verbose_name=ugettext_lazy('condition expression'))

    class Meta:
        verbose_name = ugettext_lazy('action')
        verbose_name_plural = ugettext_lazy('actions')
        # unique_together = [
        #     ['transaction_type', 'order']
        # ]
        index_together = [
            ['transaction_type', 'order'],
        ]
        ordering = ['order']

    def __str__(self):
        return 'Action #%s' % self.order


class TransactionTypeActionInstrument(TransactionTypeAction):
    user_code = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                 verbose_name=ugettext_lazy('user code'))
    name = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('name'))
    public_name = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('public name'))
    short_name = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                  verbose_name=ugettext_lazy('short name'))
    notes = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                             verbose_name=ugettext_lazy('notes'))

    instrument_type = models.ForeignKey('instruments.InstrumentType', null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='+', verbose_name=ugettext_lazy('instrument type'))
    instrument_type_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                              related_name='+', verbose_name=ugettext_lazy('instrument type input'))

    pricing_currency = models.ForeignKey('currencies.Currency', null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name='+', verbose_name=ugettext_lazy('pricing currency'))
    pricing_currency_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                               related_name='+', verbose_name=ugettext_lazy('pricing currency input'))

    price_multiplier = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.0',
                                        verbose_name=ugettext_lazy('price multiplier'))

    accrued_currency = models.ForeignKey('currencies.Currency', null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name='+', verbose_name=ugettext_lazy('accrued currency'))
    accrued_currency_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                               related_name='+', verbose_name=ugettext_lazy('accrued currency input'))

    accrued_multiplier = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.0',
                                          verbose_name=ugettext_lazy('accrued multiplier'))

    payment_size_detail = models.ForeignKey('instruments.PaymentSizeDetail', null=True, blank=True,
                                            on_delete=models.SET_NULL, related_name='+',
                                            verbose_name=ugettext_lazy('payment size detail'))
    payment_size_detail_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True,
                                                  on_delete=models.SET_NULL,
                                                  related_name='+',
                                                  verbose_name=ugettext_lazy('payment size detail input'))

    default_price = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.0',
                                     verbose_name=ugettext_lazy('default price'))
    default_accrued = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.0',
                                       verbose_name=ugettext_lazy('default accrued'))

    user_text_1 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 1'))
    user_text_2 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 2'))
    user_text_3 = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('user text 3'))

    reference_for_pricing = models.CharField(max_length=100, blank=True, default='',
                                             verbose_name=ugettext_lazy('reference for pricing'))
    daily_pricing_model = models.ForeignKey('instruments.DailyPricingModel', null=True, blank=True,
                                            on_delete=models.SET_NULL, related_name='+',
                                            verbose_name=ugettext_lazy('daily pricing model'))
    daily_pricing_model_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True,
                                                  on_delete=models.SET_NULL,
                                                  related_name='+',
                                                  verbose_name=ugettext_lazy('daily pricing model input'))
    price_download_scheme = models.ForeignKey('integrations.PriceDownloadScheme', on_delete=models.SET_NULL, null=True,
                                              blank=True, verbose_name=ugettext_lazy('price download scheme'))
    price_download_scheme_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True,
                                                    on_delete=models.SET_NULL, related_name='+',
                                                    verbose_name=ugettext_lazy('price download scheme input'))
    maturity_date = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='now()',
                                     verbose_name=ugettext_lazy('maturity date'))
    maturity_price = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.0',
                                      verbose_name=ugettext_lazy('default price'))

    class Meta:
        verbose_name = ugettext_lazy('transaction type action instrument')
        verbose_name_plural = ugettext_lazy('transaction type action instruments')

    def __str__(self):
        return 'Instrument action #%s' % self.order


class TransactionTypeActionTransaction(TransactionTypeAction):
    transaction_class = models.ForeignKey(TransactionClass, on_delete=models.PROTECT, related_name='+',
                                          verbose_name=ugettext_lazy('transaction class'))

    instrument = models.ForeignKey(Instrument, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                   verbose_name=ugettext_lazy('instrument'))
    instrument_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name='+', verbose_name=ugettext_lazy('instrument input'))
    instrument_phantom = models.ForeignKey(TransactionTypeActionInstrument, null=True, blank=True,
                                           on_delete=models.SET_NULL, related_name='+',
                                           verbose_name=ugettext_lazy('instrument phantom'))

    transaction_currency = models.ForeignKey(Currency, null=True, blank=True, on_delete=models.SET_NULL,
                                             related_name='+', verbose_name=ugettext_lazy('transaction currency'))
    transaction_currency_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True,
                                                   on_delete=models.SET_NULL, related_name='+',
                                                   verbose_name=ugettext_lazy('transaction currency input'))

    position_size_with_sign = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.',
                                               verbose_name=ugettext_lazy('position size with sign'))

    settlement_currency = models.ForeignKey(Currency, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='+', verbose_name=ugettext_lazy('settlement currency'))
    settlement_currency_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True,
                                                  on_delete=models.SET_NULL,
                                                  related_name='+',
                                                  verbose_name=ugettext_lazy('settlement currency input'))

    cash_consideration = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.',
                                          verbose_name=ugettext_lazy('cash consideration'))
    principal_with_sign = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.',
                                           verbose_name=ugettext_lazy('principal with sign'))
    carry_with_sign = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.',
                                       verbose_name=ugettext_lazy('carry with sign'))
    overheads_with_sign = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.',
                                           verbose_name=ugettext_lazy('overheads with sign'))

    portfolio = models.ForeignKey(Portfolio, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                  verbose_name=ugettext_lazy('portfolio'))
    portfolio_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='+', verbose_name=ugettext_lazy('portfolio input'))

    account_position = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                         verbose_name=ugettext_lazy('account position'))
    account_position_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                               related_name='+', verbose_name=ugettext_lazy('account position input'))

    account_cash = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                     verbose_name=ugettext_lazy('account cash'))
    account_cash_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                           related_name='+', verbose_name=ugettext_lazy('account cash input'))

    account_interim = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                        verbose_name=ugettext_lazy('account interim'))
    account_interim_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                              related_name='+', verbose_name=ugettext_lazy('account interim input'))

    accounting_date = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                       verbose_name=ugettext_lazy('accounting date'))
    cash_date = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                 verbose_name=ugettext_lazy('cash date'))

    strategy1_position = models.ForeignKey(Strategy1, null=True, blank=True, on_delete=models.SET_NULL,
                                           related_name='+', verbose_name=ugettext_lazy('strategy 1 position'))
    strategy1_position_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                                 related_name='+',
                                                 verbose_name=ugettext_lazy('strategy 1 position input'))

    strategy1_cash = models.ForeignKey(Strategy1, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                       verbose_name=ugettext_lazy('strategy 1 cash'))
    strategy1_cash_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                             related_name='+', verbose_name=ugettext_lazy('strategy 1 cash input'))

    strategy2_position = models.ForeignKey(Strategy2, null=True, blank=True, on_delete=models.SET_NULL,
                                           related_name='+', verbose_name=ugettext_lazy('strategy 2 position'))
    strategy2_position_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                                 related_name='+',
                                                 verbose_name=ugettext_lazy('strategy 2 position input'))

    strategy2_cash = models.ForeignKey(Strategy2, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                       verbose_name=ugettext_lazy('strategy 2 cash'))
    strategy2_cash_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                             related_name='+', verbose_name=ugettext_lazy('strategy 2 cash input'))

    strategy3_position = models.ForeignKey(Strategy3, null=True, blank=True, on_delete=models.SET_NULL,
                                           related_name='+', verbose_name=ugettext_lazy('strategy 3 position'))
    strategy3_position_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                                 related_name='+',
                                                 verbose_name=ugettext_lazy('strategy 3 position input'))

    strategy3_cash = models.ForeignKey(Strategy3, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                       verbose_name=ugettext_lazy('strategy 3 cash'))
    strategy3_cash_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                             related_name='+', verbose_name=ugettext_lazy('strategy 3 cash input'))

    linked_instrument = models.ForeignKey(Instrument, null=True, blank=True, on_delete=models.SET_NULL,
                                          related_name='+',
                                          verbose_name=ugettext_lazy('linked instrument'))
    linked_instrument_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                                related_name='+', verbose_name=ugettext_lazy('linked instrument input'))
    linked_instrument_phantom = models.ForeignKey(TransactionTypeActionInstrument, null=True, blank=True,
                                                  on_delete=models.SET_NULL, related_name='+',
                                                  verbose_name=ugettext_lazy('linked instrument phantom'))

    allocation_balance = models.ForeignKey(Instrument, null=True, blank=True, on_delete=models.SET_NULL,
                                           related_name='+', verbose_name=ugettext_lazy('allocation balance'))
    allocation_balance_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                                 related_name='+',
                                                 verbose_name=ugettext_lazy('allocation balance input'))
    allocation_balance_phantom = models.ForeignKey(TransactionTypeActionInstrument, null=True, blank=True,
                                                   on_delete=models.SET_NULL, related_name='+',
                                                   verbose_name=ugettext_lazy('allocation balance phantom'))

    allocation_pl = models.ForeignKey(Instrument, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                      verbose_name=ugettext_lazy('allocation pl'))
    allocation_pl_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name='+', verbose_name=ugettext_lazy('allocation pl input'))
    allocation_pl_phantom = models.ForeignKey(TransactionTypeActionInstrument, null=True, blank=True,
                                              on_delete=models.SET_NULL, related_name='+',
                                              verbose_name=ugettext_lazy('allocation pl phantom'))

    responsible = models.ForeignKey(Responsible, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                    verbose_name=ugettext_lazy('responsible'))
    responsible_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                          related_name='+', verbose_name=ugettext_lazy('responsible input'))

    counterparty = models.ForeignKey(Counterparty, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                     verbose_name=ugettext_lazy('counterparty'))
    counterparty_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                           related_name='+', verbose_name=ugettext_lazy('counterparty input'))

    reference_fx_rate = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.0',
                                         verbose_name=ugettext_lazy('reference FX-rate'))

    factor = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.0',
                              verbose_name=ugettext_lazy('factor'))
    trade_price = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.0',
                                   verbose_name=ugettext_lazy('trade price'))
    position_amount = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.0',
                                       verbose_name=ugettext_lazy('position amount'))
    principal_amount = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.0',
                                        verbose_name=ugettext_lazy('principal amount'))
    carry_amount = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.0',
                                    verbose_name=ugettext_lazy('carry amount'))
    overheads = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.0',
                                 verbose_name=ugettext_lazy('overheads'))

    notes = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                             verbose_name=ugettext_lazy('notes'))

    class Meta:
        verbose_name = ugettext_lazy('transaction type action transaction')
        verbose_name_plural = ugettext_lazy('transaction type action transactions')

    def __str__(self):
        return 'Transaction action #%s' % self.order


class TransactionTypeActionInstrumentFactorSchedule(TransactionTypeAction):
    instrument = models.ForeignKey(Instrument, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                   verbose_name=ugettext_lazy('instrument'))
    instrument_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name='+', verbose_name=ugettext_lazy('instrument input'))
    instrument_phantom = models.ForeignKey(TransactionTypeActionInstrument, null=True, blank=True,
                                           on_delete=models.SET_NULL, related_name='+',
                                           verbose_name=ugettext_lazy('instrument phantom'))

    effective_date = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                      verbose_name=ugettext_lazy('effective date'))

    factor_value = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.0',
                                    verbose_name=ugettext_lazy('factor value'))

    class Meta:
        verbose_name = ugettext_lazy('transaction type action instrument factor schedule')
        verbose_name_plural = ugettext_lazy('transaction type action instrument factor schedules')

    def __str__(self):
        return 'InstrumentFactor action #%s' % self.order


class TransactionTypeActionInstrumentManualPricingFormula(TransactionTypeAction):
    instrument = models.ForeignKey(Instrument, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                   verbose_name=ugettext_lazy('instrument'))
    instrument_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name='+', verbose_name=ugettext_lazy('instrument input'))
    instrument_phantom = models.ForeignKey(TransactionTypeActionInstrument, null=True, blank=True,
                                           on_delete=models.SET_NULL, related_name='+',
                                           verbose_name=ugettext_lazy('instrument phantom'))

    pricing_policy = models.ForeignKey(PricingPolicy, null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name='+',
                                       verbose_name=ugettext_lazy('pricing policy'))
    pricing_policy_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                             related_name='+', verbose_name=ugettext_lazy('pricing policy input'))

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    notes = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='',
                             verbose_name=ugettext_lazy('notes'))

    class Meta:
        verbose_name = ugettext_lazy('transaction type action instrument manual pricing formula')
        verbose_name_plural = ugettext_lazy('transaction type action instrument manual pricing formula')

    def __str__(self):
        return 'InstrumentManualPricingFormula action #%s' % self.order


class TransactionTypeActionInstrumentAccrualCalculationSchedules(TransactionTypeAction):
    instrument = models.ForeignKey(Instrument, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                   verbose_name=ugettext_lazy('instrument'))
    instrument_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name='+', verbose_name=ugettext_lazy('instrument input'))
    instrument_phantom = models.ForeignKey(TransactionTypeActionInstrument, null=True, blank=True,
                                           on_delete=models.SET_NULL, related_name='+',
                                           verbose_name=ugettext_lazy('instrument phantom'))

    accrual_calculation_model = models.ForeignKey(AccrualCalculationModel, null=True, blank=True,
                                                  on_delete=models.SET_NULL, related_name='+',
                                                  verbose_name=ugettext_lazy('accrual calculation model'))

    accrual_calculation_model_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True,
                                                        on_delete=models.SET_NULL,
                                                        related_name='+',
                                                        verbose_name=ugettext_lazy('accrual calculation model input'))

    periodicity = models.ForeignKey(Periodicity, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                    verbose_name=ugettext_lazy('periodicity'))

    periodicity_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                          related_name='+',
                                          verbose_name=ugettext_lazy('periodicity input'))

    accrual_start_date = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                          verbose_name=ugettext_lazy('accrual start date'))

    first_payment_date = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                          verbose_name=ugettext_lazy('first payment date'))

    accrual_size = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0.0',
                                    verbose_name=ugettext_lazy('accrual size'))

    periodicity_n = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('periodicity n'))

    notes = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='',
                             verbose_name=ugettext_lazy('notes'))

    class Meta:
        verbose_name = ugettext_lazy('transaction type action instrument accrual calculation schedules')
        verbose_name_plural = ugettext_lazy('transaction type action instrument accrual calculation schedules')

    def __str__(self):
        return 'InstrumentAccrualCalculationSchedules action #%s' % self.order


class TransactionTypeActionInstrumentEventSchedule(TransactionTypeAction):
    instrument = models.ForeignKey(Instrument, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                   verbose_name=ugettext_lazy('instrument'))
    instrument_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name='+', verbose_name=ugettext_lazy('instrument input'))
    instrument_phantom = models.ForeignKey(TransactionTypeActionInstrument, null=True, blank=True,
                                           on_delete=models.SET_NULL, related_name='+',
                                           verbose_name=ugettext_lazy('instrument phantom'))

    periodicity = models.ForeignKey(Periodicity, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                    verbose_name=ugettext_lazy('periodicity'))

    periodicity_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                          related_name='+',
                                          verbose_name=ugettext_lazy('periodicity input'))

    notification_class = models.ForeignKey(NotificationClass, null=True, blank=True, on_delete=models.SET_NULL,
                                           related_name='+',
                                           verbose_name=ugettext_lazy('notification class'))

    notification_class_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                                 related_name='+',
                                                 verbose_name=ugettext_lazy('notification class input'))

    event_class = models.ForeignKey(EventClass, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                    verbose_name=ugettext_lazy('event class'))

    event_class_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                          related_name='+',
                                          verbose_name=ugettext_lazy('event class input'))

    effective_date = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                      verbose_name=ugettext_lazy('effective date'))

    final_date = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                  verbose_name=ugettext_lazy('final date'))

    is_auto_generated = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                         verbose_name=ugettext_lazy('is autogenerated'))

    notify_in_n_days = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                        verbose_name=ugettext_lazy('notify in n days'))

    periodicity_n = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                     verbose_name=ugettext_lazy('periodicity n'))

    name = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='',
                            verbose_name=ugettext_lazy('name'))

    description = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='',
                                   verbose_name=ugettext_lazy('description'))

    class Meta:
        verbose_name = ugettext_lazy('transaction type action instrument event schedules')
        verbose_name_plural = ugettext_lazy('transaction type action instrument event schedules')

    def __str__(self):
        return 'TransactionTypeActionInstrumentEventSchedules action #%s' % self.order


class TransactionTypeActionInstrumentEventScheduleAction(TransactionTypeAction):
    event_schedule = models.ForeignKey(EventSchedule, null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name='+',
                                       verbose_name=ugettext_lazy('event schedule'))
    event_schedule_input = models.ForeignKey(TransactionTypeInput, null=True, blank=True, on_delete=models.SET_NULL,
                                             related_name='+', verbose_name=ugettext_lazy('event schedule input'))

    #  on_delete=models.PROTECT, TODO check later phantom permossions
    event_schedule_phantom = models.ForeignKey(TransactionTypeActionInstrumentEventSchedule, null=True, blank=True,
                                               related_name='+',
                                               verbose_name=ugettext_lazy('event schedule phantom'),
                                               on_delete=models.SET_NULL)

    transaction_type_from_instrument_type = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='',
                                                             verbose_name=ugettext_lazy('text'))

    is_book_automatic = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default=False,
                                         verbose_name=ugettext_lazy("is book automatic"),
                                         help_text=ugettext_lazy('If checked - is book automatic'))

    is_sent_to_pending = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default=False,
                                          verbose_name=ugettext_lazy("is sent to pending"),
                                          help_text=ugettext_lazy('If checked - is sent to pending'))

    button_position = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='0',
                                       verbose_name=ugettext_lazy('button position'))

    text = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='',
                            verbose_name=ugettext_lazy('text'))

    class Meta:
        verbose_name = ugettext_lazy('transaction type action instrument event schedule action')
        verbose_name_plural = ugettext_lazy('transaction type action instrument event schedule actions')

    def __str__(self):
        return 'TransactionTypeActionInstrumentEventScheduleAction action #%s' % self.order


class TransactionTypeActionExecuteCommand(TransactionTypeAction):

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    class Meta:
        verbose_name = ugettext_lazy('transaction type action execute command action')
        verbose_name_plural = ugettext_lazy('transaction type action execute command actions')

    def __str__(self):
        return 'TransactionTypeActionExecuteCommand action #%s' % self.order


class EventToHandle(NamedModel):
    master_user = models.ForeignKey(MasterUser, related_name='events_to_handle',
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)
    transaction_type = models.ForeignKey(TransactionType, on_delete=models.PROTECT,
                                         verbose_name=ugettext_lazy('transaction type'))
    notification_date = models.DateField(null=True, blank=True,
                                         verbose_name=ugettext_lazy('notification date'))
    effective_date = models.DateField(null=True, blank=True,
                                      verbose_name=ugettext_lazy('effective date'))

    class Meta(NamedModel.Meta):
        verbose_name = ugettext_lazy('event to handle')
        verbose_name_plural = ugettext_lazy('events to handle')


class ComplexTransaction(FakeDeletableModel):
    PRODUCTION = 1
    PENDING = 2
    STATUS_CHOICES = (
        (PRODUCTION, ugettext_lazy('Production')),
        (PENDING, ugettext_lazy('Pending')),
    )

    SHOW_PARAMETERS = 1
    HIDE_PARAMETERS = 2

    VISIBILITY_STATUS_CHOICES = (
        (SHOW_PARAMETERS, ugettext_lazy('Show Parameters')),
        (HIDE_PARAMETERS, ugettext_lazy('Hide Parameters')),
    )


    master_user = models.ForeignKey(MasterUser, related_name='complex_transactions',
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    transaction_type = models.ForeignKey(TransactionType, on_delete=models.PROTECT,
                                         verbose_name=ugettext_lazy('transaction type'))

    is_locked = models.BooleanField(default=False, db_index=True, verbose_name=ugettext_lazy('is locked'))
    is_canceled = models.BooleanField(default=False, db_index=True, verbose_name=ugettext_lazy('is canceled'))
    error_code = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=ugettext_lazy('error code'))

    date = models.DateField(default=date_now, db_index=True, verbose_name=ugettext_lazy("date"))
    status = models.PositiveSmallIntegerField(default=PRODUCTION, choices=STATUS_CHOICES, db_index=True,
                                              verbose_name=ugettext_lazy('status'))

    visibility_status = models.PositiveSmallIntegerField(default=SHOW_PARAMETERS, choices=VISIBILITY_STATUS_CHOICES, db_index=True,
                                                           verbose_name=ugettext_lazy('visibility_status'))

    code = models.IntegerField(default=0, verbose_name=ugettext_lazy('code'))

    text = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('text'))

    user_text_1 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 1'))

    user_text_2 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 2'))

    user_text_3 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 3'))

    user_text_4 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 4'))

    user_text_5 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 5'))

    user_text_6 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 6'))

    user_text_7 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 7'))

    user_text_8 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 8'))

    user_text_9 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 9'))

    user_text_10 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 10'))

    user_text_11 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 11'))

    user_text_12 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 12'))

    user_text_13 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 13'))

    user_text_14 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 14'))

    user_text_15 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 15'))

    user_text_16 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 16'))

    user_text_17 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 17'))

    user_text_18 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 18'))

    user_text_19 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 19'))

    user_text_20 = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('user text 20'))

    user_number_1 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 1'))

    user_number_2 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 2'))

    user_number_3 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 3'))

    user_number_4 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 4'))

    user_number_5 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 5'))

    user_number_6 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 6'))

    user_number_7 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 7'))

    user_number_8 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 8'))

    user_number_9 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 9'))

    user_number_10 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 10'))

    user_number_11 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 11'))

    user_number_12 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 12'))

    user_number_13 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 13'))

    user_number_14 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 14'))

    user_number_15 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 15'))

    user_number_16 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 16'))

    user_number_17 = models.IntegerField(null=True,  verbose_name=ugettext_lazy('user number 17'))

    user_number_18 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 18'))

    user_number_19 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 19'))

    user_number_20 = models.IntegerField(null=True, verbose_name=ugettext_lazy('user number 20'))

    user_date_1 = models.DateField(blank=True, db_index=True, null=True, verbose_name=ugettext_lazy("user date 1"))

    user_date_2 = models.DateField(blank=True, db_index=True, null=True, verbose_name=ugettext_lazy("user date 2"))

    user_date_3 = models.DateField(blank=True, db_index=True, null=True, verbose_name=ugettext_lazy("user date 3"))

    user_date_4 = models.DateField(blank=True, db_index=True, null=True, verbose_name=ugettext_lazy("user date 4"))

    user_date_5 = models.DateField(blank=True, db_index=True, null=True, verbose_name=ugettext_lazy("user date 5"))

    attributes = GenericRelation(GenericAttribute, verbose_name=ugettext_lazy('attributes'))

    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))

    class Meta:
        verbose_name = ugettext_lazy('complex transaction')
        verbose_name_plural = ugettext_lazy('complex transactions')
        index_together = [
            ['transaction_type', 'code']
        ]
        ordering = ['code']

        permissions = (
            ("view_complextransaction_show_parameters", "Show Parameters"),
            ("view_complextransaction_hide_parameters", "Hide Parameters"),
        )

    def __str__(self):
        return str(self.code)

    def save(self, *args, **kwargs):
        print("Complex Transaction Save text %s" % self.text)
        print("Complex Transaction Save date %s" % self.date)

        if self.code is None or self.code == 0:
            self.code = FakeSequence.next_value(self.transaction_type.master_user, 'complex_transaction', d=100)
        super(ComplexTransaction, self).save(*args, **kwargs)


class ComplexTransactionInput(models.Model):
    complex_transaction = models.ForeignKey(ComplexTransaction, on_delete=models.CASCADE, related_name='inputs',
                                            verbose_name=ugettext_lazy('complex transaction'))
    transaction_type_input = models.ForeignKey(TransactionTypeInput, on_delete=models.CASCADE, related_name='+',
                                               verbose_name=ugettext_lazy('transaction type input'))

    value_string = models.TextField(default='', blank=True, verbose_name=ugettext_lazy('value string'))
    value_float = models.FloatField(default=0.0, verbose_name=ugettext_lazy('value float'))
    value_date = models.DateField(default=date.min, verbose_name=ugettext_lazy('value date'))

    account = models.ForeignKey('accounts.Account', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                verbose_name=ugettext_lazy('account'))
    instrument_type = models.ForeignKey('instruments.InstrumentType', null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='+', verbose_name=ugettext_lazy('instrument type'))
    instrument = models.ForeignKey('instruments.Instrument', null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='+', verbose_name=ugettext_lazy('instrument'))
    currency = models.ForeignKey('currencies.Currency', null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='+', verbose_name=ugettext_lazy('currency'))
    counterparty = models.ForeignKey('counterparties.Counterparty', null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='+', verbose_name=ugettext_lazy('counterparty'))
    responsible = models.ForeignKey('counterparties.Responsible', null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='+', verbose_name=ugettext_lazy('responsible'))
    portfolio = models.ForeignKey('portfolios.Portfolio', null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='+', verbose_name=ugettext_lazy('portfolio'))
    strategy1 = models.ForeignKey('strategies.Strategy1', null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='+', verbose_name=ugettext_lazy('strategy 1'))
    strategy2 = models.ForeignKey('strategies.Strategy2', null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='+', verbose_name=ugettext_lazy('strategy 2'))
    strategy3 = models.ForeignKey('strategies.Strategy3', null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='+', verbose_name=ugettext_lazy('strategy 3'))
    daily_pricing_model = models.ForeignKey('instruments.DailyPricingModel', null=True, blank=True,
                                            on_delete=models.SET_NULL, related_name='+',
                                            verbose_name=ugettext_lazy('daily pricing model'))
    payment_size_detail = models.ForeignKey('instruments.PaymentSizeDetail', null=True, blank=True,
                                            on_delete=models.SET_NULL, related_name='+',
                                            verbose_name=ugettext_lazy('payment size detail'))
    price_download_scheme = models.ForeignKey('integrations.PriceDownloadScheme', null=True, blank=True,
                                              on_delete=models.SET_NULL, related_name='+',
                                              verbose_name=ugettext_lazy('price download scheme'))

    pricing_policy = models.ForeignKey('instruments.PricingPolicy', null=True, blank=True,
                                       on_delete=models.SET_NULL, related_name='+',
                                       verbose_name=ugettext_lazy('pricing policy'))

    periodicity = models.ForeignKey('instruments.Periodicity', null=True, blank=True,
                                    on_delete=models.PROTECT, related_name='+',
                                    verbose_name=ugettext_lazy('periodicity'))

    accrual_calculation_model = models.ForeignKey('instruments.AccrualCalculationModel', null=True, blank=True,
                                                  on_delete=models.PROTECT, related_name='+',
                                                  verbose_name=ugettext_lazy('accrual calculation model'))

    event_class = models.ForeignKey(EventClass, null=True, blank=True,
                                    on_delete=models.PROTECT, related_name='+',
                                    verbose_name=ugettext_lazy('event class'))

    notification_class = models.ForeignKey(NotificationClass, null=True, blank=True,
                                           on_delete=models.PROTECT, related_name='+',
                                           verbose_name=ugettext_lazy('notification class'))

    class Meta:
        verbose_name = ugettext_lazy('complex transaction input')
        verbose_name_plural = ugettext_lazy('complex transaction inputs')
        unique_together = [
            ['complex_transaction', 'transaction_type_input', ]
        ]

# class Transaction(FakeDeletableModel):
class Transaction(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='transactions', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    complex_transaction = models.ForeignKey(ComplexTransaction, on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='transactions',
                                            verbose_name=ugettext_lazy('complex transaction'))
    complex_transaction_order = models.PositiveSmallIntegerField(default=0.0, verbose_name=ugettext_lazy(
        'complex transaction order'))
    transaction_code = models.IntegerField(default=0, verbose_name=ugettext_lazy('transaction code'))
    transaction_class = models.ForeignKey(TransactionClass, on_delete=models.PROTECT,
                                          verbose_name=ugettext_lazy("transaction class"))

    # is_locked = models.BooleanField(default=False, db_index=True, verbose_name=ugettext_lazy('is locked'))
    is_canceled = models.BooleanField(default=False, db_index=True, verbose_name=ugettext_lazy('is canceled'))

    error_code = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=ugettext_lazy('error code'))

    # Position related
    instrument = models.ForeignKey(Instrument, related_name='transactions', on_delete=models.PROTECT, null=True,
                                   blank=True, verbose_name=ugettext_lazy("instrument"))
    transaction_currency = models.ForeignKey(Currency, related_name='transactions',
                                             on_delete=models.PROTECT, null=True, blank=True,
                                             verbose_name=ugettext_lazy("transaction currency"))
    position_size_with_sign = models.FloatField(default=0.0, verbose_name=ugettext_lazy("position size with sign"))

    # Cash related
    settlement_currency = models.ForeignKey(Currency, related_name='transactions_settlement_currency',
                                            on_delete=models.PROTECT, verbose_name=ugettext_lazy("settlement currency"))
    cash_consideration = models.FloatField(default=0.0, verbose_name=ugettext_lazy("cash consideration"))

    # P&L related
    principal_with_sign = models.FloatField(default=0.0, verbose_name=ugettext_lazy("principal with sign"))
    carry_with_sign = models.FloatField(default=0.0, verbose_name=ugettext_lazy("carry with sign"))
    overheads_with_sign = models.FloatField(default=0.0, verbose_name=ugettext_lazy("overheads with sign"))

    # accounting dates
    transaction_date = models.DateField(editable=False, default=date_now, db_index=True,
                                        verbose_name=ugettext_lazy("transaction date"))
    accounting_date = models.DateField(default=date_now, db_index=True, verbose_name=ugettext_lazy("accounting date"))
    cash_date = models.DateField(default=date_now, db_index=True, verbose_name=ugettext_lazy("cash date"))

    # portfolio
    portfolio = models.ForeignKey(Portfolio, on_delete=models.PROTECT, verbose_name=ugettext_lazy("portfolio"))

    # accounts
    account_position = models.ForeignKey(Account, related_name='transactions_account_position',
                                         on_delete=models.PROTECT, null=True, blank=True,
                                         verbose_name=ugettext_lazy("account position"))
    account_cash = models.ForeignKey(Account, related_name='transactions_account_cash', on_delete=models.PROTECT,
                                     null=True, blank=True, verbose_name=ugettext_lazy("account cash"))
    account_interim = models.ForeignKey(Account, related_name='transactions_account_interim', on_delete=models.PROTECT,
                                        null=True, blank=True, verbose_name=ugettext_lazy("account interim"))

    # strategies
    strategy1_position = models.ForeignKey(Strategy1, related_name='transactions_strategy1_position',
                                           null=True, blank=True, on_delete=models.PROTECT,
                                           verbose_name=ugettext_lazy("strategy 1 cash"))
    strategy1_cash = models.ForeignKey(Strategy1, related_name='transactions_strategy1_cash',
                                       null=True, blank=True, on_delete=models.PROTECT,
                                       verbose_name=ugettext_lazy("strategy 1 position"))
    strategy2_position = models.ForeignKey(Strategy2, related_name='transactions_strategy2_position',
                                           null=True, blank=True, on_delete=models.PROTECT,
                                           verbose_name=ugettext_lazy("strategy 2 cash"))
    strategy2_cash = models.ForeignKey(Strategy2, related_name='transactions_strategy2_cash',
                                       null=True, blank=True, on_delete=models.PROTECT,
                                       verbose_name=ugettext_lazy("strategy 2 position"))
    strategy3_position = models.ForeignKey(Strategy3, related_name='transactions_strategy3_position',
                                           null=True, blank=True, on_delete=models.PROTECT,
                                           verbose_name=ugettext_lazy("strategy 3 cash"))
    strategy3_cash = models.ForeignKey(Strategy3, related_name='transactions_strategy3_cash',
                                       null=True, blank=True, on_delete=models.PROTECT,
                                       verbose_name=ugettext_lazy("strategy 3 position"))

    # responsible & counterparty

    responsible = models.ForeignKey(Responsible, related_name='transactions',
                                    on_delete=models.PROTECT, null=True, blank=True,
                                    verbose_name=ugettext_lazy("responsible"),
                                    help_text=ugettext_lazy("Trader or transaction executor"))
    counterparty = models.ForeignKey(Counterparty, related_name='transactions',
                                     on_delete=models.PROTECT, null=True, blank=True,
                                     verbose_name=ugettext_lazy("counterparty"))

    # linked instrument

    linked_instrument = models.ForeignKey(Instrument, related_name='transactions_linked',
                                          on_delete=models.PROTECT, null=True, blank=True,
                                          verbose_name=ugettext_lazy("linked instrument"))

    # allocations

    allocation_balance = models.ForeignKey(Instrument, related_name='transactions_allocation_balance',
                                           on_delete=models.PROTECT, null=True, blank=True,
                                           verbose_name=ugettext_lazy("allocation balance"))

    allocation_pl = models.ForeignKey(Instrument, related_name='transactions_allocation_pl',
                                      on_delete=models.PROTECT, null=True, blank=True,
                                      verbose_name=ugettext_lazy("allocation P&L"))

    reference_fx_rate = models.FloatField(default=0.0, verbose_name=ugettext_lazy("reference fx-rate"),
                                          help_text=ugettext_lazy(
                                              "FX rate to convert from Settlement ccy to Instrument "
                                              "Ccy on Accounting Date (trade date)"))

    # other
    is_locked = models.BooleanField(default=False, verbose_name=ugettext_lazy("is locked"),
                                    help_text=ugettext_lazy('If checked - transaction cannot be changed'))
    # is_canceled = models.BooleanField(default=False, verbose_name=ugettext_lazy("is canceled"),
    #                                   help_text=ugettext_lazy('If checked - transaction is cancelled'))

    factor = models.FloatField(default=0.0, verbose_name=ugettext_lazy("factor"),
                               help_text=ugettext_lazy('Multiplier (for calculations on the form)'))
    trade_price = models.FloatField(default=0.0, verbose_name=ugettext_lazy("trade price"),
                                    help_text=ugettext_lazy('Price (for calculations on the form)'))

    ytm_at_cost = models.FloatField(default=0.0, verbose_name=ugettext_lazy("YTM at cost"),
                                    help_text=ugettext_lazy('YTM at cost'))

    position_amount = models.FloatField(default=0.0, verbose_name=ugettext_lazy("position amount"),
                                        help_text=ugettext_lazy(
                                            'Absolute value of Position with Sign (for calculations on the form)'))
    principal_amount = models.FloatField(default=0.0, verbose_name=ugettext_lazy("principal amount"),
                                         help_text=ugettext_lazy(
                                             'Absolute value of Principal with Sign (for calculations on the form)'))
    carry_amount = models.FloatField(default=0.0, verbose_name=ugettext_lazy("carry amount"),
                                     help_text=ugettext_lazy(
                                         'Absolute value of Carry with Sign (for calculations on the form)'))
    overheads = models.FloatField(default=0.0, verbose_name=ugettext_lazy("overheads"),
                                  help_text=ugettext_lazy(
                                      'Absolute value of overheads (for calculations on the form)'))

    notes = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('notes'))

    attributes = GenericRelation(GenericAttribute, verbose_name=ugettext_lazy('attributes'))



    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))

    class Meta:
        verbose_name = ugettext_lazy('transaction')
        verbose_name_plural = ugettext_lazy('transactions')
        index_together = [
            ['master_user', 'transaction_code']
        ]
        ordering = ['transaction_date', 'transaction_code']

        permissions = (
            ("partial_view_transaction", "Partial View"),
        )

    def __str__(self):
        return str(self.transaction_code)

    @property
    def is_buy(self):
        return self.transaction_class_id == TransactionClass.BUY

    @property
    def is_sell(self):
        return self.transaction_class_id == TransactionClass.SELL

    @property
    def is_fx_trade(self):
        return self.transaction_class_id == TransactionClass.FX_TRADE

    @property
    def is_instrument_pl(self):
        return self.transaction_class_id == TransactionClass.INSTRUMENT_PL

    @property
    def is_transaction_pl(self):
        return self.transaction_class_id == TransactionClass.TRANSACTION_PL

    @property
    def is_transfer(self):
        return self.transaction_class_id == TransactionClass.TRANSFER

    @property
    def is_fx_transfer(self):
        return self.transaction_class_id == TransactionClass.FX_TRANSFER

    @property
    def is_cash_inflow(self):
        return self.transaction_class_id == TransactionClass.CASH_INFLOW

    @property
    def is_cash_outflow(self):
        return self.transaction_class_id == TransactionClass.CASH_OUTFLOW

    def save(self, *args, **kwargs):
        calc_cash = kwargs.pop('calc_cash', False)

        self.transaction_date = min(self.accounting_date, self.cash_date)
        if self.transaction_code is None or self.transaction_code == 0:
            if self.complex_transaction is None:
                self.transaction_code = FakeSequence.next_value(self.master_user, 'transaction')
            else:
                self.transaction_code = self.complex_transaction.code + self.complex_transaction_order
        super(Transaction, self).save(*args, **kwargs)

        if calc_cash:
            self.calc_cash_by_formulas()

    def is_can_calc_cash_by_formulas(self):
        return self.transaction_class_id in [TransactionClass.BUY, TransactionClass.SELL] \
               and self.instrument.instrument_type.instrument_class_id == InstrumentClass.CONTRACT_FOR_DIFFERENCE

    def calc_cash_by_formulas(self, save=True):
        if self.is_can_calc_cash_by_formulas():
            calc_cash_for_contract_for_difference(
                transaction=self,
                instrument=self.instrument,
                portfolio=self.portfolio,
                account=self.account_position,
                member=None,
                is_calculate_for_newer=True,
                is_calculate_for_all=False,
                save=save
            )


# class TransactionAttributeType(AbstractAttributeType):
#     object_permissions = GenericRelation(GenericObjectPermission)
#
#     class Meta(AbstractAttributeType.Meta):
#         verbose_name = ugettext_lazy('transaction attribute type')
#         verbose_name_plural = ugettext_lazy('transaction attribute types')
#         permissions = [
#             ('view_transactionattributetype', 'Can view transaction attribute type'),
#             ('manage_transactionattributetype', 'Can manage transaction attribute type'),
#         ]


# class TransactionAttributeTypeUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(TransactionAttributeType, related_name='user_object_permissions',
#                                        verbose_name=ugettext_lazy("content object"))
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('transaction attribute types - user permission')
#         verbose_name_plural = ugettext_lazy('transaction attribute types - user permissions')
#
#
# class TransactionAttributeTypeGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(TransactionAttributeType, related_name='group_object_permissions',
#                                        verbose_name=ugettext_lazy("content object"))
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('transaction attribute types - group permission')
#         verbose_name_plural = ugettext_lazy('transaction attribute types - group permissions')


# class TransactionClassifier(AbstractClassifier):
#     attribute_type = models.ForeignKey(TransactionAttributeType, related_name='classifiers',
#                                        verbose_name=ugettext_lazy('attribute type'))
#     parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True,
#                             verbose_name=ugettext_lazy('parent'))
#
#     class Meta(AbstractClassifier.Meta):
#         verbose_name = ugettext_lazy('transaction classifier')
#         verbose_name_plural = ugettext_lazy('transaction classifiers')
#
#
# class TransactionAttributeTypeOption(AbstractAttributeTypeOption):
#     member = models.ForeignKey(Member, related_name='transaction_attribute_type_options',
#                                verbose_name=ugettext_lazy("member"))
#     attribute_type = models.ForeignKey(TransactionAttributeType, related_name='options',
#                                        verbose_name=ugettext_lazy("attribute type"))
#
#     class Meta(AbstractAttributeTypeOption.Meta):
#         verbose_name = ugettext_lazy('transaction attribute types - option')
#         verbose_name_plural = ugettext_lazy('transaction attribute types - options')
#
#
# class TransactionAttribute(AbstractAttribute):
#     attribute_type = models.ForeignKey(TransactionAttributeType, related_name='attributes',
#                                        verbose_name=ugettext_lazy("attribute type"))
#     content_object = models.ForeignKey(Transaction, related_name='attributes',
#                                        verbose_name=ugettext_lazy("content object"))
#     classifier = models.ForeignKey(TransactionClassifier, on_delete=models.SET_NULL, null=True, blank=True,
#                                    verbose_name=ugettext_lazy('classifier'))
#
#     class Meta(AbstractAttribute.Meta):
#         verbose_name = ugettext_lazy('transaction attribute')
#         verbose_name_plural = ugettext_lazy('transaction attributes')


class ExternalCashFlow(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='external_cash_flows',
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)
    date = models.DateField(default=date_now, db_index=True,
                            verbose_name=ugettext_lazy("date"))
    portfolio = models.ForeignKey(Portfolio, related_name='external_cash_flows', on_delete=models.PROTECT,
                                  verbose_name=ugettext_lazy("portfolio"))
    account = models.ForeignKey(Account, related_name='external_cash_flows', on_delete=models.PROTECT,
                                verbose_name=ugettext_lazy("account"))
    currency = models.ForeignKey(Currency, related_name='external_cash_flows', on_delete=models.PROTECT,
                                 verbose_name=ugettext_lazy("currency"))
    amount = models.FloatField(default=0.,
                               verbose_name=ugettext_lazy("amount"))

    class Meta:
        verbose_name = ugettext_lazy('external cash flow')
        verbose_name_plural = ugettext_lazy('external cash flows')
        ordering = ['date']

    def __str__(self):
        return '%s: %s - %s - %s - %s = %s' % (self.date, self.portfolio, self.account, list(self.strategies.all()),
                                               self.currency, self.amount)


class ExternalCashFlowStrategy(models.Model):
    external_cash_flow = models.ForeignKey(ExternalCashFlow, related_name='strategies',
                                           verbose_name=ugettext_lazy("external cash flow"), on_delete=models.CASCADE)
    order = models.IntegerField(default=0, verbose_name=ugettext_lazy("order"))
    strategy1 = models.ForeignKey(Strategy1, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="external_cash_flow_strategies1",
                                  verbose_name=ugettext_lazy("strategy1"))
    strategy2 = models.ForeignKey(Strategy2, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="external_cash_flow_strategies2",
                                  verbose_name=ugettext_lazy("strategy2"))
    strategy3 = models.ForeignKey(Strategy3, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="external_cash_flow_strategies3",
                                  verbose_name=ugettext_lazy("strategy3"))

    class Meta:
        verbose_name = ugettext_lazy('external cash flow strategy')
        verbose_name_plural = ugettext_lazy('external cash flow strtegies')
        ordering = ['order']

    def __str__(self):
        return '%s' % self.strategy
