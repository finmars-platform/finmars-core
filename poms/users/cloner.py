import logging
from collections import defaultdict
from uuid import uuid4

import pytz
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from poms.accounts.models import AccountType, Account
from poms.chats.models import ThreadGroup
from poms.counterparties.models import CounterpartyGroup, Counterparty, ResponsibleGroup, Responsible
from poms.currencies.models import Currency, CurrencyHistory
from poms.instruments.models import PricingPolicy, DailyPricingModel, InstrumentClass, AccrualCalculationModel, \
    PaymentSizeDetail, Periodicity, CostMethod, InstrumentType, Instrument, ManualPricingFormula, PriceHistory, \
    AccrualCalculationSchedule, InstrumentFactorSchedule, EventScheduleConfig, EventSchedule, EventScheduleAction
from poms.integrations.models import PriceDownloadScheme, ProviderClass, AccrualScheduleDownloadMethod, \
    FactorScheduleDownloadMethod, InstrumentDownloadScheme, InstrumentDownloadSchemeInput, \
    CurrencyMapping, InstrumentTypeMapping, AccrualCalculationModelMapping, PeriodicityMapping, AccountMapping, \
    InstrumentMapping, CounterpartyMapping, ResponsibleMapping, PortfolioMapping, Strategy1Mapping, Strategy2Mapping, \
    Strategy3Mapping, DailyPricingModelMapping, PaymentSizeDetailMapping, PriceDownloadSchemeMapping, \
    PricingAutomatedSchedule, ComplexTransactionImportScheme, ComplexTransactionImportSchemeInput, \
    ComplexTransactionImportSchemeField, ImportConfig
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, Strategy2Subgroup, \
    Strategy2, Strategy3Group, Strategy3Subgroup, Strategy3
from poms.tags.models import Tag
from poms.transactions.models import TransactionClass, ActionClass, EventClass, NotificationClass, TransactionTypeGroup, \
    TransactionType, TransactionTypeInput, TransactionTypeActionInstrument, TransactionTypeActionTransaction
from poms.ui.models import ListLayout, EditLayout
from poms.users.models import Group, Member

_l = logging.getLogger('poms.users.cloner')


class FullDataCloner(object):
    def __init__(self, source_master_user):
        self._now = None
        self._source_master_user = source_master_user
        self._source_owner = None
        self._target_master_user = None
        self._target_owner = None

        self._pk_map = defaultdict(dict)
        self._source_objects = defaultdict(dict)
        self._target_objects = defaultdict(dict)

    @transaction.atomic()
    def clone(self):
        _l.debug('clone: master_user=%s, timezone=%s', self._source_master_user.pk, self._source_master_user.timezone)

        if self._source_master_user.timezone:
            try:
                src_tz = pytz.timezone(self._source_master_user.timezone)
            except:
                src_tz = settings.TIME_ZONE
        else:
            src_tz = settings.TIME_ZONE

        with timezone.override(src_tz):
            self._now = timezone.localtime(timezone.now())
            self._clone()

    def _clone(self):
        self._target_master_user = self._simple_clone(None, self._source_master_user, 'name', 'language', 'timezone')
        self._target_master_user.name = '{} ({:%H:%M %d.%m.%Y})'.format(
            self._target_master_user,
            self._now
        )

        self._load_consts()

        self._users_1()
        self._accounts()
        self._chats()
        self._counterparties()

        self._instruments_1()
        self._integrations_1()

        self._currencies()

        self._instruments_2()

        self._portfolios_1()
        self._strategies_1()

        self._transactions_1()

        # the end
        self._instruments_3()
        self._integrations_2()

        self._simple_clone(self._target_master_user, self._source_master_user,
                           'system_currency', 'currency', 'account_type', 'account', 'counterparty_group',
                           'counterparty', 'responsible_group', 'responsible', 'portfolio', 'instrument_type',
                           'instrument', 'strategy1_group', 'strategy1_subgroup', 'strategy1', 'strategy2_group',
                           'strategy2_subgroup', 'strategy2', 'strategy3_group', 'strategy3_subgroup', 'strategy3',
                           'thread_group', 'transaction_type_group', 'mismatch_portfolio', 'mismatch_account',
                           'notification_business_days')

        self._tags()
        self._ui()

        # transaction.set_rollback(True)

    def _load_consts(self):
        for source in ContentType.objects.all():
            self._add_pk_map(source, source)

        for source in Permission.objects.all():
            self._add_pk_map(source, source)

        for source in InstrumentClass.objects.all():
            self._add_pk_map(source, source)

        for source in DailyPricingModel.objects.all():
            self._add_pk_map(source, source)

        for source in AccrualCalculationModel.objects.all():
            self._add_pk_map(source, source)

        for source in PaymentSizeDetail.objects.all():
            self._add_pk_map(source, source)

        for source in Periodicity.objects.all():
            self._add_pk_map(source, source)

        for source in CostMethod.objects.all():
            self._add_pk_map(source, source)

        for source in ProviderClass.objects.all():
            self._add_pk_map(source, source)

        for source in FactorScheduleDownloadMethod.objects.all():
            self._add_pk_map(source, source)

        for source in AccrualScheduleDownloadMethod.objects.all():
            self._add_pk_map(source, source)

        for source in TransactionClass.objects.all():
            self._add_pk_map(source, source)

        for source in ActionClass.objects.all():
            self._add_pk_map(source, source)

        for source in EventClass.objects.all():
            self._add_pk_map(source, source)

        for source in NotificationClass.objects.all():
            self._add_pk_map(source, source)

    def _users_1(self):
        self._source_owner = self._source_master_user.members.filter(is_owner=True).order_by('join_date').first()

        username = '%s@fake.finmars.com' % str(uuid4().hex)
        user = User.objects.create_user(username, email=username)
        self._target_owner = Member.objects.create(master_user=self._target_master_user, user=user, is_owner=True,
                                                   is_admin=True)
        if self._source_owner:
            self._add_pk_map(self._target_owner, self._source_owner)

        self._simple_list_clone(Group, None, 'master_user', 'name')

    def _accounts(self):
        self._simple_list_clone(AccountType, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted', 'show_transaction_details',
                                'transaction_details_expr')

        self._simple_list_clone(Account, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted', 'type', 'is_valid_for_all_portfolios')

    def _chats(self):
        self._simple_list_clone(ThreadGroup, None, 'master_user', 'name', 'is_deleted')

    def _counterparties(self):
        self._simple_list_clone(CounterpartyGroup, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted')

        self._simple_list_clone(Counterparty, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted', 'group', 'is_valid_for_all_portfolios')

        self._simple_list_clone(ResponsibleGroup, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted')

        self._simple_list_clone(Responsible, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted', 'group', 'is_valid_for_all_portfolios')

    def _currencies(self):
        self._simple_list_clone(Currency, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted', 'reference_for_pricing', 'daily_pricing_model',
                                'price_download_scheme')
        self._simple_list_clone(CurrencyHistory, 'currency__master_user', 'currency', 'pricing_policy', 'date',
                                'fx_rate', pk_map=False)

    def _instruments_1(self):
        self._simple_list_clone(PricingPolicy, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'expr')

    def _instruments_2(self):
        self._simple_list_clone(InstrumentType, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted', 'instrument_class', store=True)

        self._simple_list_clone(Instrument, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted', 'instrument_type', 'is_active',
                                'pricing_currency', 'price_multiplier', 'accrued_currency', 'accrued_multiplier',
                                'payment_size_detail', 'default_price', 'default_accrued',
                                'user_text_1', 'user_text_2', 'user_text_3',
                                'reference_for_pricing', 'daily_pricing_model', 'price_download_scheme',
                                'maturity_date', 'maturity_price')

        self._simple_list_clone(ManualPricingFormula, 'instrument__master_user', 'instrument', 'pricing_policy', 'expr',
                                'notes')

        self._simple_list_clone(AccrualCalculationSchedule, 'instrument__master_user', 'instrument',
                                'accrual_start_date', 'first_payment_date', 'accrual_size',
                                'accrual_calculation_model', 'periodicity', 'periodicity_n', 'notes')

        self._simple_list_clone(InstrumentFactorSchedule, 'instrument__master_user', 'instrument', 'effective_date',
                                'factor_value')

        self._simple_list_clone(PriceHistory, 'instrument__master_user', 'instrument', 'pricing_policy', 'date',
                                'principal_price', 'accrued_price', pk_map=False)

        self._simple_list_clone(EventScheduleConfig, None, 'master_user', 'name', 'description', 'notification_class',
                                'notify_in_n_days', 'action_text', 'action_is_sent_to_pending',
                                'action_is_book_automatic')

    def _instruments_3(self):
        self._simple_list_clone_2(InstrumentType, None, 'one_off_event', 'regular_event', 'factor_same', 'factor_up',
                                  'factor_down', pk_map=False)

        self._simple_list_clone(EventSchedule, 'instrument__master_user', 'instrument', 'name', 'description',
                                'event_class',
                                'notification_class', 'effective_date', 'notify_in_n_days',
                                'periodicity', 'periodicity_n', 'final_date', 'is_auto_generated',
                                'accrual_calculation_schedule', 'factor_schedule')

        self._simple_list_clone(EventScheduleAction, 'event_schedule__instrument__master_user', 'event_schedule',
                                'transaction_type', 'text', 'is_sent_to_pending',
                                'is_book_automatic', 'button_position')

    def _integrations_1(self):
        ImportConfig.objects.create(
            master_user=self._target_master_user,
            provider=ProviderClass.objects.get(pk=ProviderClass.BLOOMBERG)
        )

        self._simple_list_clone(PriceDownloadScheme, None, 'master_user', 'scheme_name', 'provider',
                                'bid0', 'bid1', 'bid2', 'bid_multiplier',
                                'ask0', 'ask1', 'ask2', 'ask_multiplier', 'last',
                                'last', 'mid', 'mid_multiplier',
                                'bid_history', 'bid_history_multiplier',
                                'ask_history', 'ask_history_multiplier',
                                'mid_history', 'mid_history_multiplier',
                                'last_history', 'last_history_multiplier',
                                'currency_fxrate', 'currency_fxrate_multiplier')

        self._simple_list_clone(PricingAutomatedSchedule, None, 'master_user', 'is_enabled', 'cron_expr', 'balance_day',
                                'load_days', 'fill_days', 'override_existed')

    def _integrations_2(self):
        self._simple_list_clone(InstrumentDownloadScheme, None, 'master_user', 'scheme_name', 'provider',
                                'reference_for_pricing', 'user_code', 'name', 'short_name', 'public_name', 'notes',
                                'instrument_type', 'pricing_currency', 'price_multiplier', 'accrued_currency',
                                'accrued_multiplier', 'maturity_date', 'user_text_1', 'user_text_2', 'user_text_3',
                                'payment_size_detail', 'daily_pricing_model', 'price_download_scheme', 'default_price',
                                'default_accrued', 'factor_schedule_method', 'accrual_calculation_schedule_method')

        self._simple_list_clone(InstrumentDownloadSchemeInput, 'scheme__master_user', 'scheme', 'name', 'field')

        # TODO: uncomment after attributes
        # self._simple_list_clone(InstrumentDownloadSchemeAttribute, 'scheme__master_user', 'scheme', 'attribute_type', 'value')

        self._simple_list_clone(CurrencyMapping, None, 'master_user', 'provider', 'value', 'content_object')

        self._simple_list_clone(InstrumentTypeMapping, None, 'master_user', 'provider', 'value', 'content_object')

        # TODO: uncomment after attributes
        # self._simple_list_clone(InstrumentAttributeValueMapping, None, 'master_user', 'provider', 'value',
        #                         'attribute_type', 'value_string', 'value_float', 'value_date', 'classifier')

        self._simple_list_clone(AccrualCalculationModelMapping, None, 'master_user', 'provider', 'value',
                                'content_object')

        self._simple_list_clone(PeriodicityMapping, None, 'master_user', 'provider', 'value', 'content_object')

        self._simple_list_clone(AccountMapping, None, 'master_user', 'provider', 'value', 'content_object')

        self._simple_list_clone(InstrumentMapping, None, 'master_user', 'provider', 'value', 'content_object')

        self._simple_list_clone(CounterpartyMapping, None, 'master_user', 'provider', 'value', 'content_object')

        self._simple_list_clone(ResponsibleMapping, None, 'master_user', 'provider', 'value', 'content_object')

        self._simple_list_clone(PortfolioMapping, None, 'master_user', 'provider', 'value', 'content_object')

        self._simple_list_clone(Strategy1Mapping, None, 'master_user', 'provider', 'value', 'content_object')

        self._simple_list_clone(Strategy2Mapping, None, 'master_user', 'provider', 'value', 'content_object')

        self._simple_list_clone(Strategy3Mapping, None, 'master_user', 'provider', 'value', 'content_object')

        self._simple_list_clone(DailyPricingModelMapping, None, 'master_user', 'provider', 'value', 'content_object')

        self._simple_list_clone(PaymentSizeDetailMapping, None, 'master_user', 'provider', 'value', 'content_object')

        self._simple_list_clone(PriceDownloadSchemeMapping, None, 'master_user', 'provider', 'value', 'content_object')

        self._simple_list_clone(ComplexTransactionImportScheme, None, 'master_user', 'scheme_name', 'rule_expr')

        self._simple_list_clone(ComplexTransactionImportSchemeInput, 'scheme__master_user', 'scheme', 'name', 'column')

        self._simple_list_clone(ComplexTransactionImportSchemeRule, 'scheme__master_user', 'scheme', 'value',
                                'transaction_type')

        self._simple_list_clone(ComplexTransactionImportSchemeField, 'rule__scheme__master_user', 'rule',
                                'transaction_type_input', 'value_expr')

    def _portfolios_1(self):
        self._simple_list_clone(Portfolio, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted', store=True)

    def _portfolios_2(self):
        self._simple_list_clone_2(Portfolio, None, 'accounts', 'responsibles', 'counterparties', 'transaction_types',
                                  pk_map=False)

    def _strategies_1(self):
        self._simple_list_clone(Strategy1Group, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted')

        self._simple_list_clone(Strategy1Subgroup, 'group__master_user', 'master_user', 'group', 'user_code', 'name',
                                'short_name', 'public_name', 'notes', 'is_deleted')

        self._simple_list_clone(Strategy1, 'subgroup__group__master_user', 'master_user', 'subgroup', 'user_code',
                                'name', 'short_name', 'public_name', 'notes', 'is_deleted')

        self._simple_list_clone(Strategy2Group, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted')

        self._simple_list_clone(Strategy2Subgroup, 'group__master_user', 'master_user', 'group', 'user_code', 'name',
                                'short_name', 'public_name', 'notes', 'is_deleted')

        self._simple_list_clone(Strategy2, 'subgroup__group__master_user', 'master_user', 'subgroup', 'user_code',
                                'name', 'short_name', 'public_name', 'notes', 'is_deleted')

        self._simple_list_clone(Strategy3Group, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted')

        self._simple_list_clone(Strategy3Subgroup, 'group__master_user', 'master_user', 'group', 'user_code', 'name',
                                'short_name', 'public_name', 'notes', 'is_deleted')

        self._simple_list_clone(Strategy3, 'subgroup__group__master_user', 'master_user', 'subgroup', 'user_code',
                                'name', 'short_name', 'public_name', 'notes', 'is_deleted')

    def _transactions_1(self):
        self._simple_list_clone(TransactionTypeGroup, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted')

        self._simple_list_clone(TransactionType, None, 'master_user', 'user_code', 'name', 'short_name',
                                'public_name', 'notes', 'is_deleted', 'group', 'date_expr', 'display_expr',
                                'instrument_types', 'is_valid_for_all_portfolios', 'is_valid_for_all_instruments',
                                'book_transaction_layout_json')

        self._simple_list_clone(TransactionTypeInput, 'transaction_type__master_user',
                                'transaction_type', 'name', 'verbose_name', 'value_type', 'content_type',
                                'order', 'value_expr', 'is_fill_from_context', 'value', 'account', 'instrument_type',
                                'instrument', 'currency', 'counterparty', 'responsible', 'portfolio', 'strategy1',
                                'strategy2', 'strategy3', 'daily_pricing_model', 'payment_size_detail',
                                'price_download_scheme')

        self._simple_list_clone(TransactionTypeActionInstrument, 'transaction_type__master_user',
                                'transaction_type', 'order', 'action_notes',
                                'user_code', 'name', 'public_name', 'short_name', 'notes', 'instrument_type',
                                'instrument_type_input', 'pricing_currency', 'pricing_currency_input',
                                'price_multiplier', 'accrued_currency', 'accrued_currency_input', 'accrued_multiplier',
                                'payment_size_detail', 'payment_size_detail_input', 'default_price', 'default_accrued',
                                'user_text_1', 'user_text_2', 'user_text_3', 'reference_for_pricing',
                                'daily_pricing_model', 'daily_pricing_model_input', 'price_download_scheme',
                                'price_download_scheme_input', 'maturity_date', 'maturity_price')

        self._simple_list_clone(TransactionTypeActionTransaction, 'transaction_type__master_user',
                                'transaction_type', 'order', 'action_notes',
                                'transaction_class', 'portfolio', 'portfolio_input', 'instrument', 'instrument_input',
                                'instrument_phantom', 'transaction_currency', 'transaction_currency_input',
                                'position_size_with_sign', 'settlement_currency', 'settlement_currency_input',
                                'cash_consideration', 'principal_with_sign', 'carry_with_sign', 'overheads_with_sign',
                                'account_position', 'account_position_input', 'account_cash', 'account_cash_input',
                                'account_interim', 'account_interim_input', 'accounting_date', 'cash_date',
                                'strategy1_position', 'strategy1_position_input', 'strategy1_cash',
                                'strategy1_cash_input', 'strategy2_position', 'strategy2_position_input',
                                'strategy2_cash', 'strategy2_cash_input', 'strategy3_position',
                                'strategy3_position_input', 'strategy3_cash', 'strategy3_cash_input',
                                'linked_instrument', 'linked_instrument_input', 'linked_instrument_phantom',
                                'allocation_balance', 'allocation_balance_input', 'allocation_balance_phantom',
                                'allocation_pl', 'allocation_pl_input', 'allocation_pl_phantom',
                                'responsible', 'responsible_input', 'counterparty', 'counterparty_input',
                                'reference_fx_rate', 'factor', 'trade_price', 'position_amount', 'principal_amount',
                                'carry_amount', 'overheads', 'notes', )

    def _tags(self):
        # self._simple_list_clone(Tag, None, 'master_user', 'user_code', 'name', 'short_name', 'public_name', 'notes',
        #                         'content_types', 'account_types', 'accounts', 'currencies', 'instrument_types',
        #                         'instruments', 'counterparty_groups', 'counterparties', 'responsible_groups',
        #                         'responsibles', 'portfolios', 'transaction_type_groups', 'transaction_types',
        #                         'strategy1_groups', 'strategy1_subgroups', 'strategies1', 'strategy2_groups',
        #                         'strategy2_subgroups', 'strategies2', 'strategy3_groups', 'strategy3_subgroups',
        #                         'strategies3', 'thread_groups', )
        self._simple_list_clone(Tag, 'master_user', 'master_user', 'user_code', 'name', 'short_name', 'public_name',
                                'notes', 'content_types')

    def _ui(self):

        if self._source_owner:
            self._simple_list_clone(ListLayout, 'member__master_user', 'member', 'content_type', 'json_data', 'name',
                                    'is_default', pk_map=False, filter={'member': self._source_owner})
            self._simple_list_clone(EditLayout, 'member__master_user', 'member', 'content_type', 'json_data',
                                    pk_map=False, filter={'member': self._source_owner})

        pass

    def _attribute_types(self, type_model, classifier_model, value_model):
        _l.debug('clone %s', type_model)
        for source in type_model.objects.filter(master_user=self._source_master_user):
            self._simple_clone(None, source, 'master_user', 'user_code', 'name', 'short_name',
                               'public_name', 'notes', 'value_type', 'order')

        _l.debug('clone %s', classifier_model)
        for source in classifier_model.objects.filter(attribute_type__master_user=self._source_master_user):
            # TODO: classifier is tree!
            # self._simple_clone(None, source, 'attribute_type', 'name')
            pass

        _l.debug('clone %s', value_model)
        for source in value_model.objects.filter(attribute_type__master_user=self._source_master_user):
            # TODO: uncomment when classifier is ready
            # self._simple_clone(None, source, 'attribute_type', 'content_object', 'classifier')
            pass

    def _object_permissions(self, object_permission_model):
        _l.debug('clone %s', object_permission_model)
        for source in object_permission_model.filter(content_object__master_user=self._source_master_user):
            self._simple_clone(None, source, 'content_object', 'group', 'permission', 'value_string', 'value_float',
                               'value_date')

    def _simple_list_clone(self, model, master_user_path, *fields, pk_map=True, store=False, filter=None):
        # _l.debug('clone %s', model)

        fields_select_related = []
        fields_prefetch_related = []
        for item in fields:
            field = model._meta.get_field(item)
            if field.one_to_one:
                pass
            elif field.one_to_many:
                # fields_select_related.append(field.name)
                pass
            elif field.many_to_many:
                fields_prefetch_related.append(field.name)

        if not master_user_path:
            master_user_path = 'master_user'

        filter = filter or {}
        filter[master_user_path] = self._source_master_user
        qs = model.objects.filter(**filter)
        # qs = model.objects.filter(**{master_user_path: self._source_master_user})

        if fields_select_related:
            qs = qs.select_related(*fields_select_related)
        if fields_prefetch_related:
            qs = qs.prefetch_related(*fields_prefetch_related)

        _l.debug('clone %s: count=%s', model._meta.model_name, qs.count())
        for source in qs:
            self._simple_clone(None, source, *fields, pk_map=pk_map, store=store)

    def _simple_list_clone_2(self, model, master_user_path, *fields, pk_map=True, store=False):
        _l.debug('clone2 %s ', model._meta.model_name)
        for source in self._source_get_objects(model).values():
            target_pk = self._get_related_from_pk_map(source, source.pk)
            target = self._target_get_object(source, target_pk)
            self._simple_clone(target, source, *fields, pk_map=False)

    def _simple_clone(self, target, source, *fields, pk_map=True, store=False):
        content_type = ContentType.objects.get_for_model(source)
        if not target:
            target = content_type.model_class()()

        for item in fields:
            field = target._meta.get_field(item)

            if field.one_to_one:
                attr_name = field.get_attname()
                value = getattr(source, attr_name)
                value = self._get_related_from_pk_map(field.related_model, value)
                setattr(target, attr_name, value)
            elif field.one_to_many:
                pass
            elif field.many_to_one:
                attr_name = field.get_attname()
                value = getattr(source, attr_name)
                value = self._get_related_from_pk_map(field.related_model, value)
                setattr(target, attr_name, value)
            elif field.many_to_many:
                pass
            else:
                value = getattr(source, item)
                setattr(target, item, value)

        target.save()
        # if settings.DEBUG:
        #     _l.debug('cloned - %s: %s -> %s', content_type, source.pk, target.pk)

        for item in fields:
            field = target._meta.get_field(item)
            if field.many_to_many:
                values = getattr(source, item).values_list('id', flat=True)
                values = [self._get_related_from_pk_map(field.rel.to, pk) for pk in values]
                values = field.rel.to.objects.filter(pk__in=values)
                setattr(target, item, values)

        if pk_map:
            self._add_pk_map(target, source)

        if store:
            self._source_add_object(source)
            self._target_add_object(target)

        return target

    def _source_add_object(self, source):
        content_type = ContentType.objects.get_for_model(source)
        objects = self._source_objects[content_type.id]
        objects[source.id] = source

    def _source_get_objects(self, source):
        content_type = ContentType.objects.get_for_model(source)
        objects = self._source_objects[content_type.id]
        return objects

    def _source_get_object(self, source, pk):
        content_type = ContentType.objects.get_for_model(source)
        objects = self._source_objects[content_type.id]
        return objects[pk]

    def _target_add_object(self, target):
        content_type = ContentType.objects.get_for_model(target)
        objects = self._target_objects[content_type.id]
        objects[target.id] = target

    def _target_get_objects(self, target):
        content_type = ContentType.objects.get_for_model(target)
        objects = self._target_objects[content_type.id]
        return objects

    def _target_get_object(self, target, pk):
        content_type = ContentType.objects.get_for_model(target)
        objects = self._target_objects[content_type.id]
        return objects[pk]

    def _add_pk_map(self, target, source):
        content_type = ContentType.objects.get_for_model(target)
        cobjects = self._pk_map[content_type.pk]
        cobjects[source.pk] = target.pk

    def _get_related_from_pk_map(self, model, pk):
        if pk is None:
            return None
        content_type = ContentType.objects.get_for_model(model)
        objects = self._pk_map[content_type.pk]
        return objects[pk]
