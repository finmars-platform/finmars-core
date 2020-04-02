import time
from celery import shared_task
from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import ValidationError

from poms.accounts.models import Account, AccountType
from poms.accounts.serializers import AccountTypeSerializer
from poms.complex_import.models import ComplexImportScheme
from poms.complex_import.serializers import ComplexImportSchemeSerializer
from poms.configuration_import.recovery import ConfigurationRecoveryHandler
from poms.counterparties.models import Responsible, Counterparty
from poms.csv_import.models import CsvImportScheme
from poms.csv_import.serializers import CsvImportSchemeSerializer
from poms.currencies.models import Currency
from poms.currencies.serializers import CurrencySerializer
from poms.instruments.models import InstrumentType, DailyPricingModel, PaymentSizeDetail, Instrument, PricingPolicy, \
    Periodicity, AccrualCalculationModel
from poms.instruments.serializers import InstrumentTypeSerializer, PricingPolicySerializer
from poms.integrations.models import PriceDownloadScheme, ComplexTransactionImportScheme, PricingAutomatedSchedule, \
    Task, AccountTypeMapping, InstrumentTypeMapping, PricingPolicyMapping, PriceDownloadSchemeMapping, \
    PeriodicityMapping, DailyPricingModelMapping, PaymentSizeDetailMapping, AccrualCalculationModelMapping, \
    InstrumentDownloadScheme
from poms.integrations.serializers import ComplexTransactionImportSchemeSerializer, PricingAutomatedScheduleSerializer, \
    AccountTypeMappingSerializer, InstrumentTypeMappingSerializer, PricingPolicyMappingSerializer, \
    PriceDownloadSchemeMappingSerializer, PeriodicityMappingSerializer, DailyPricingModelMappingSerializer, \
    PaymentSizeDetailMappingSerializer, AccrualCalculationModelMappingSerializer, InstrumentDownloadSchemeSerializer
from poms.obj_attrs.models import GenericAttributeType
from poms.obj_attrs.serializers import GenericAttributeTypeSerializer
from poms.portfolios.models import Portfolio
from poms.pricing.models import InstrumentPricingScheme, CurrencyPricingScheme, PricingProcedure
from poms.pricing.serializers import InstrumentPricingSchemeSerializer, CurrencyPricingSchemeSerializer, \
    PricingProcedureSerializer
from poms.reference_tables.models import ReferenceTable
from poms.reference_tables.serializers import ReferenceTableSerializer
from poms.reports.models import BalanceReportCustomField, PLReportCustomField, TransactionReportCustomField
from poms.reports.serializers import BalanceReportCustomFieldSerializer, PLReportCustomFieldSerializer, \
    TransactionReportCustomFieldSerializer
from poms.schedules.models import PricingSchedule
from poms.schedules.serializers import PricingScheduleSerializer
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.transactions.models import TransactionClass, TransactionTypeGroup, TransactionType, TransactionTypeInput
from poms.transactions.serializers import TransactionTypeGroupSerializer, TransactionTypeSerializer
from poms.ui.models import ListLayout, InstrumentUserFieldModel, TransactionUserFieldModel, DashboardLayout, EditLayout, \
    ContextMenuLayout, TemplateLayout
from poms.ui.serializers import EditLayoutSerializer, ListLayoutSerializer, DashboardLayoutSerializer, \
    InstrumentUserFieldSerializer, TransactionUserFieldSerializer, ContextMenuLayoutSerializer, TemplateLayoutSerializer
from poms.users.models import EcosystemDefault

from logging import getLogger

_l = getLogger('poms.configuration_import')


def dump(obj):
    for attr in dir(obj):
        _l.info("obj.%s = %r" % (attr, getattr(obj, attr)))


def get_content_type_by_name(name):
    pieces = name.split('.')
    app_label_title = pieces[0]
    model_title = pieces[1]

    content_type = ContentType.objects.get(app_label=app_label_title, model=model_title)

    return content_type


class ProxyUser(object):

    def __init__(self, member, master_user):
        self.member = member
        self.master_user = master_user


class ProxyRequest(object):

    def __init__(self, user):
        self.user = user


def check_configuration_section(configuration_access_table):
    result = True

    for key, value in configuration_access_table.items():

        if not value:
            result = False

    return result


def get_data_access_table(member):
    result = {

        'portfolios.portfolio': False,
        'accounts.account': False,
        'instruments.instrument': False,
        'counterparties.counterparty': False,
        'counterparties.responsible': False,
        'currencies.currency': False,
        'strategies.strategy1': False,
        'strategies.strategy2': False,
        'strategies.strategy3': False,
        'instruments.instrumenttype': False,
        'transactions.transactiontype': False,
        'accounts.accounttype': False
    }

    for group in member.groups.all():
        if group.permission_table:

            if group.permission_table['data']:

                for perm_config in group.permission_table['data']:

                    result[perm_config['content_type']] = False

                    if perm_config['data']['create_objects']:
                        result[perm_config['content_type']] = True

    if member.is_admin:

        for key, value in result.items():
            result[key] = True

    return result


def get_configuration_access_table(member):
    result = {
        'obj_attrs.attributetype': False,
        'reference_tables.referencetable': False,
        'ui.templatelayout': False,
        'integrations.mappingtable': False,
        'integrations.pricedownloadscheme': False,
        'integrations.instrumentdownloadscheme': False,
        'csv_import.csvimportscheme': False,
        'integrations.complextransactionimportscheme': False,
        'complex_import.compleximportscheme': False,
        'ui.userfield': False
    }

    if member.is_admin:
        result = {
            'obj_attrs.attributetype': True,
            'reference_tables.referencetable': True,
            'ui.templatelayout': True,
            'integrations.mappingtable': True,
            'integrations.pricedownloadscheme': True,
            'integrations.instrumentdownloadscheme': True,
            'csv_import.csvimportscheme': True,
            'integrations.complextransactionimportscheme': True,
            'complex_import.compleximportscheme': True,
            'ui.userfield': True
        }

    if not member.is_admin:
        for group in member.groups.all():
            if group.permission_table:

                if group.permission_table['configuration']:

                    for perm_config in group.permission_table['configuration']:

                        if not result[perm_config['content_type']]:

                            if perm_config['data']['creator_view']:
                                result[perm_config['content_type']] = True

    return result


class ImportManager(object):

    def __init__(self, instance, update_state):

        # _l.info('master_user %s ' % instance.master_user)
        # _l.info('class instance %s' % instance.master_user.__class__.__name__)

        self.master_user = instance.master_user
        self.member = instance.member
        self.ecosystem_default = EcosystemDefault.objects.get(master_user=self.master_user)

        self.update_task_state = update_state
        self.instance = instance

        self.instance.stats = {}
        self.instance.stats['configuration'] = {}
        self.instance.stats['mappings'] = {}

        self.data_access_table = get_data_access_table(self.member)
        self.configuration_access_table = get_configuration_access_table(self.member)

        _l.info('self.access_table %s' % self.data_access_table)
        _l.info('self.configuration_access_table %s' % self.configuration_access_table)

        self.configuration_recovery_handler = ConfigurationRecoveryHandler()

        # _l.info('self.master_user %s ' % self.master_user)
        # _l.info('self.class instance %s' % self.master_user.__class__.__name__)

    def count_progress_total(self):

        total_rows = 0

        if 'body' in self.instance.data:

            for section in self.instance.data['body']:

                if section['section_name'] == 'configuration':
                    configuration_section = section

                    if 'items' in configuration_section:
                        for entity_object in configuration_section['items']:

                            for content_object in entity_object['content']:
                                total_rows = total_rows + 1

                if section['section_name'] == 'mappings':
                    mappings_section = section

                    if 'items' in mappings_section:
                        for entity_object in mappings_section['items']:

                            for content_object in entity_object['content']:
                                total_rows = total_rows + 1

        self.instance.total_rows = total_rows

        self.update_task_state(task_id=self.instance.task_id, state=Task.STATUS_PENDING,
                               meta={'total_rows': self.instance.total_rows,
                                     'processed_rows': self.instance.processed_rows})

    def update_progress(self):

        self.instance.processed_rows = self.instance.processed_rows + 1

        if self.instance.processed_rows > self.instance.total_rows:  # TODO  Somehow processed rows become bigger then total total rows, check for duplicate
            self.instance.processed_rows = self.instance.total_rows

        self.update_task_state(task_id=self.instance.task_id, state=Task.STATUS_PENDING,
                               meta={'total_rows': self.instance.total_rows,
                                     'processed_rows': self.instance.processed_rows})

    def get_serializer_context(self):

        # proxy_user = ProxyUser(self.master_user, self.member) # Master user will be passed as (tuple) instead of MasterUser instance - MAGIC!!
        proxy_user = ProxyUser(self.member, self.master_user)
        proxy_request = ProxyRequest(proxy_user)

        context = {
            'request': proxy_request
        }

        # _l.info('user %s ' % context['request'].user)
        # _l.info('user class instance %s' % context['request'].user.__class__.__name__)
        # 
        # _l.info('master_user %s ' % context['request'].user.master_user)
        # _l.info('master_user class instance %s' % context['request'].user.master_user.__class__.__name__)
        # 
        # _l.info('member %s ' % context['request'].user.member)
        # _l.info('member class instance %s' % context['request'].user.member.__class__.__name__)

        return context

    def sync_transaction_type_inputs(self, content_object):

        for input_object in content_object['inputs']:

            if input_object['value_type'] == 100:

                if input_object['account']:
                    input_object['account'] = self.ecosystem_default.account.pk

                if input_object['accrual_calculation_model']:
                    input_object['accrual_calculation_model'] = self.ecosystem_default.accrual_calculation_model.pk

                if input_object['counterparty']:
                    input_object['counterparty'] = self.ecosystem_default.counterparty.pk

                if input_object['currency']:
                    input_object['currency'] = self.ecosystem_default.currency.pk

                if input_object['daily_pricing_model']:
                    input_object['daily_pricing_model'] = self.ecosystem_default.daily_pricing_model.pk

                if input_object['instrument']:
                    input_object['instrument'] = self.ecosystem_default.instrument.pk

                if input_object['instrument_type']:
                    input_object['instrument_type'] = self.ecosystem_default.instrument_type.pk

                if input_object['payment_size_detail']:
                    input_object['payment_size_detail'] = self.ecosystem_default.payment_size_detail.pk

                if input_object['periodicity']:
                    input_object['periodicity'] = self.ecosystem_default.periodicity.pk

                if input_object['portfolio']:
                    input_object['portfolio'] = self.ecosystem_default.portfolio.pk

                if input_object['price_download_scheme']:
                    input_object['price_download_scheme'] = self.ecosystem_default.price_download_scheme.pk

                if input_object['pricing_policy']:
                    input_object['pricing_policy'] = self.ecosystem_default.pricing_policy.pk

                if input_object['responsible']:
                    input_object['responsible'] = self.ecosystem_default.responsible.pk

                if input_object['strategy1']:
                    input_object['strategy1'] = self.ecosystem_default.strategy1.pk

                if input_object['strategy2']:
                    input_object['strategy2'] = self.ecosystem_default.strategy2.pk

                if input_object['strategy3']:
                    input_object['strategy3'] = self.ecosystem_default.strategy3.pk

                # if input_object['notification_class']: # TODO find a way to set - as value
                #     input_object['notification_class'] = self.ecosystem_default.notification_class.pk
                #
                # if input_object['event_class']:
                #     input_object['event_class'] = self.ecosystem_default.event_class.pk

    def sync_transaction_type_action_instrument(self, action_object):

        item_object = action_object['instrument']

        if item_object['instrument_type']:
            try:
                item_object['instrument_type'] = InstrumentType.objects.get(master_user=self.master_user,
                                                                            user_code=item_object[
                                                                                '___instrument_type__user_code']).pk
            except InstrumentType.DoesNotExist:
                item_object['instrument_type'] = self.ecosystem_default.instrument_type.pk

        if item_object['daily_pricing_model']:
            try:
                item_object['daily_pricing_model'] = DailyPricingModel.objects.get(system_code=item_object[
                    '___daily_pricing_model__system_code']).pk
            except DailyPricingModel.DoesNotExist:
                item_object['daily_pricing_model'] = self.ecosystem_default.daily_pricing_model.pk

        if item_object['payment_size_detail']:
            try:
                item_object['payment_size_detail'] = PaymentSizeDetail.objects.get(system_code=item_object[
                    '___payment_size_detail__system_code']).pk
            except PaymentSizeDetail.DoesNotExist:
                item_object['payment_size_detail'] = self.ecosystem_default.payment_size_detail.pk

        if item_object['price_download_scheme']:
            try:
                item_object['price_download_scheme'] = PriceDownloadScheme.objects.get(master_user=self.master_user,
                                                                                       scheme_name=item_object[
                                                                                           '___price_download_scheme__scheme_name']).pk
            except PriceDownloadScheme.DoesNotExist:
                item_object['price_download_scheme'] = self.ecosystem_default.instrument_type.pk

        if item_object['accrued_currency']:
            try:
                item_object['accrued_currency'] = Currency.objects.get(master_user=self.master_user,
                                                                       user_code=item_object[
                                                                           '___accrued_currency__user_code']).pk
            except Currency.DoesNotExist:
                item_object['accrued_currency'] = self.ecosystem_default.currency.pk

        if item_object['pricing_currency']:
            try:
                item_object['pricing_currency'] = Currency.objects.get(master_user=self.master_user,
                                                                       user_code=item_object[
                                                                           '___pricing_currency__user_code']).pk
            except Currency.DoesNotExist:
                item_object['pricing_currency'] = self.ecosystem_default.currency.pk

    def sync_transaction_type_action_transaction(self, action_object):

        item_object = action_object['transaction']

        if item_object['account_interim']:
            try:
                item_object['account_interim'] = Account.objects.get(master_user=self.master_user,
                                                                     user_code=item_object[
                                                                         '___account_interim__user_code']).pk
            except Account.DoesNotExist:
                item_object['account_interim'] = self.ecosystem_default.account.pk

        if item_object['account_cash']:
            try:
                item_object['account_cash'] = Account.objects.get(master_user=self.master_user,
                                                                  user_code=item_object[
                                                                      '___account_cash__user_code']).pk
            except Account.DoesNotExist:
                item_object['account_cash'] = self.ecosystem_default.account.pk

        if item_object['account_position']:
            try:
                item_object['account_position'] = Account.objects.get(master_user=self.master_user,
                                                                      user_code=item_object[
                                                                          '___account_position__user_code']).pk
            except Account.DoesNotExist:
                item_object['account_position'] = self.ecosystem_default.account.pk

        if item_object['allocation_balance']:
            try:
                item_object['allocation_balance'] = Instrument.objects.get(master_user=self.master_user,
                                                                           user_code=item_object[
                                                                               '___allocation_balance__user_code']).pk
            except Instrument.DoesNotExist:
                item_object['allocation_balance'] = self.ecosystem_default.instrument.pk

        if item_object['allocation_pl']:
            try:
                item_object['allocation_pl'] = Instrument.objects.get(master_user=self.master_user,
                                                                      user_code=item_object[
                                                                          '___allocation_pl__user_code']).pk
            except Instrument.DoesNotExist:
                item_object['allocation_pl'] = self.ecosystem_default.instrument.pk

        if item_object['instrument']:
            try:
                item_object['instrument'] = Instrument.objects.get(master_user=self.master_user,
                                                                   user_code=item_object[
                                                                       '___instrument__user_code']).pk
            except Instrument.DoesNotExist:
                item_object['instrument'] = self.ecosystem_default.instrument.pk

        if item_object['linked_instrument']:
            try:
                item_object['linked_instrument'] = Instrument.objects.get(master_user=self.master_user,
                                                                          user_code=item_object[
                                                                              '___linked_instrument__user_code']).pk
            except Instrument.DoesNotExist:
                item_object['linked_instrument'] = self.ecosystem_default.instrument.pk

        if item_object['portfolio']:
            try:
                item_object['portfolio'] = Portfolio.objects.get(master_user=self.master_user,
                                                                 user_code=item_object[
                                                                     '___portfolio__user_code']).pk
            except Portfolio.DoesNotExist:
                item_object['portfolio'] = self.ecosystem_default.portfolio.pk

        if item_object['responsible']:
            try:
                item_object['responsible'] = Responsible.objects.get(master_user=self.master_user,
                                                                     user_code=item_object[
                                                                         '___responsible__user_code']).pk
            except Responsible.DoesNotExist:
                item_object['responsible'] = self.ecosystem_default.responsible.pk

        if item_object['counterparty']:
            try:
                item_object['counterparty'] = Counterparty.objects.get(master_user=self.master_user,
                                                                       user_code=item_object[
                                                                           '___counterparty__user_code']).pk
            except Counterparty.DoesNotExist:
                item_object['counterparty'] = self.ecosystem_default.counterparty.pk

        if item_object['settlement_currency']:
            try:
                item_object['settlement_currency'] = Currency.objects.get(master_user=self.master_user,
                                                                          user_code=item_object[
                                                                              '___settlement_currency__user_code']).pk
            except Currency.DoesNotExist:
                item_object['settlement_currency'] = self.ecosystem_default.currency.pk

        if item_object['transaction_currency']:
            try:
                item_object['transaction_currency'] = Currency.objects.get(master_user=self.master_user,
                                                                           user_code=item_object[
                                                                               '___transaction_currency__user_code']).pk
            except Currency.DoesNotExist:
                item_object['transaction_currency'] = self.ecosystem_default.currency.pk

        if item_object['transaction_class']:
            try:
                item_object['transaction_class'] = TransactionClass.objects.get(
                    system_code=item_object[
                        '___transaction_class__system_code']).pk
            except TransactionClass.DoesNotExist:
                item_object['transaction_class'] = TransactionClass.objects.get(
                    system_code='-').pk

        if item_object['strategy1_cash']:
            try:
                item_object['strategy1_cash'] = Strategy1.objects.get(master_user=self.master_user,
                                                                      user_code=item_object[
                                                                          '___strategy1_cash__user_code']).pk
            except Strategy1.DoesNotExist:
                item_object['strategy1_cash'] = self.ecosystem_default.strategy1.pk

        if item_object['strategy1_position']:
            try:
                item_object['strategy1_position'] = Strategy1.objects.get(master_user=self.master_user,
                                                                          user_code=item_object[
                                                                              '___strategy1_position__user_code']).pk
            except Strategy1.DoesNotExist:
                item_object['strategy1_position'] = self.ecosystem_default.strategy1.pk

        if item_object['strategy2_cash']:
            try:
                item_object['strategy2_cash'] = Strategy2.objects.get(master_user=self.master_user,
                                                                      user_code=item_object[
                                                                          '___strategy2_cash__user_code']).pk
            except Strategy2.DoesNotExist:
                item_object['strategy2_cash'] = self.ecosystem_default.strategy2.pk

        if item_object['strategy2_position']:
            try:
                item_object['strategy2_position'] = Strategy2.objects.get(master_user=self.master_user,
                                                                          user_code=item_object[
                                                                              '___strategy2_position__user_code']).pk
            except Strategy2.DoesNotExist:
                item_object['strategy2_position'] = self.ecosystem_default.strategy2.pk

        if item_object['strategy3_cash']:
            try:
                item_object['strategy3_cash'] = Strategy3.objects.get(master_user=self.master_user,
                                                                      user_code=item_object[
                                                                          '___strategy3_cash__user_code']).pk
            except Strategy3.DoesNotExist:
                item_object['strategy3_cash'] = self.ecosystem_default.strategy3.pk

        if item_object['strategy3_position']:
            try:
                item_object['strategy3_position'] = Strategy3.objects.get(master_user=self.master_user,
                                                                          user_code=item_object[
                                                                              '___strategy3_position__user_code']).pk
            except Strategy3.DoesNotExist:
                item_object['strategy3_position'] = self.ecosystem_default.strategy3.pk

    def sync_transaction_type_action_manual_pricing_formula(self, action_object):

        item_object = action_object['instrument_manual_pricing_formula']

        if item_object['pricing_policy']:
            try:
                item_object['pricing_policy'] = PricingPolicy.objects.get(master_user=self.master_user,
                                                                          user_code=item_object[
                                                                              '___pricing_policy__user_code']).pk
            except PricingPolicy.DoesNotExist:
                item_object['pricing_policy'] = self.ecosystem_default.pricing_policy.pk

    def sync_transaction_type_actions(self, content_object):

        for action_object in content_object['actions']:

            if action_object['instrument']:
                self.sync_transaction_type_action_instrument(action_object)

            if action_object['transaction']:
                self.sync_transaction_type_action_transaction(action_object)

            if action_object['instrument_manual_pricing_formula']:
                self.sync_transaction_type_action_manual_pricing_formula(action_object)

    def import_attribute_types(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'obj_attrs' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:
                        pieces = content_object['content_type'].split('.')
                        app_label = pieces[0]
                        model = pieces[1]

                        content_type = ContentType.objects.get(app_label=app_label, model=model)

                        content_object['content_type_id'] = content_type.id

                        serializer = GenericAttributeTypeSerializer(data=content_object,
                                                                    context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:

                            serializer.is_valid(raise_exception=True)
                            serializer.save(content_type=content_type)

                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                instance = GenericAttributeType.objects.get(master_user=self.master_user,
                                                                            user_code=content_object['user_code'],
                                                                            content_type=content_type)

                                serializer = GenericAttributeTypeSerializer(data=content_object,
                                                                            instance=instance,
                                                                            context=self.get_serializer_context())
                                serializer.is_valid(raise_exception=True)
                                serializer.save()

                            else:
                                _l.info('error %s' % error)
                                stats['status'] = 'error'
                                # stats['message'] = error

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Attribute Types done %s' % (time.perf_counter() - st))

    def import_instrument_types(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'instruments.instrumenttype' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:
                        content_object['one_off_event'] = self.ecosystem_default.transaction_type.pk
                        content_object['regular_event'] = self.ecosystem_default.transaction_type.pk


                        if 'pricing_policies' in content_object:

                            for policy in content_object['pricing_policies']:

                                if '___pricing_policy__user_code' in policy:

                                    try:
                                        policy['pricing_policy'] = PricingPolicy.objects.get(
                                            master_user=self.master_user,
                                            user_code=policy['___pricing_policy__user_code']).pk

                                    except PricingPolicy.DoesNotExist:
                                        policy['pricing_policy'] = self.ecosystem_default.pricing_policy.pk

                                if '___pricing_scheme__user_code' in policy:

                                    try:
                                        policy['pricing_scheme'] = InstrumentPricingScheme.objects.get(
                                            master_user=self.master_user,
                                            user_code=policy['___pricing_scheme__user_code']).pk

                                    except InstrumentPricingScheme.DoesNotExist:

                                        policy['pricing_scheme'] = None

                                        # policy['pricing_scheme'] = InstrumentPricingScheme.objects.get(
                                        #     master_user=self.master_user,
                                        #     user_code='-').pk  # TODO Add to EcosystemDefaults



                        serializer = InstrumentTypeSerializer(data=content_object,
                                                              context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                instance = InstrumentType.objects.get(master_user=self.master_user,
                                                                      user_code=content_object['user_code'])

                                serializer = InstrumentTypeSerializer(data=content_object,
                                                                      instance=instance,
                                                                      context=self.get_serializer_context())
                                serializer.is_valid(raise_exception=True)
                                serializer.save()

                            else:

                                _l.info('error %s' % error)
                                stats['status'] = 'error'

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Instrument Types done %s' % (time.perf_counter() - st))

    def import_account_types(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'accounts.accounttype' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:
                        serializer = AccountTypeSerializer(data=content_object,
                                                           context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                instance = AccountType.objects.get(master_user=self.master_user,
                                                                   user_code=content_object['user_code'])

                                serializer = AccountTypeSerializer(data=content_object,
                                                                   instance=instance,
                                                                   context=self.get_serializer_context())
                                serializer.is_valid(raise_exception=True)
                                serializer.save()

                            else:
                                _l.info('error %s' % error)
                                stats['status'] = 'error'

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Account Types done %s' % (time.perf_counter() - st))

    def import_transaction_types_groups(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'transactions.transactiontypegroup' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:
                        serializer = TransactionTypeGroupSerializer(data=content_object,
                                                                    context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                instance = TransactionTypeGroup.objects.get(master_user=self.master_user,
                                                                            user_code=content_object['user_code'])

                                serializer = TransactionTypeGroupSerializer(data=content_object,
                                                                            instance=instance,
                                                                            context=self.get_serializer_context())
                                serializer.is_valid(raise_exception=True)
                                serializer.save()

                            else:
                                _l.info('error %s' % error)
                                stats['status'] = 'error'

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Transaction Types Groups done %s' % (time.perf_counter() - st))

    def import_transaction_types(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'transactions.transactiontype' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        try:
                            group = TransactionTypeGroup.objects.get(master_user=self.master_user,
                                                                     user_code=content_object['___group__user_code'])
                            content_object['group'] = group.pk
                        except (KeyError, TransactionTypeGroup.DoesNotExist):
                            content_object['group'] = self.ecosystem_default.transaction_type_group.pk

                        if 'inputs' in content_object:
                            self.sync_transaction_type_inputs(content_object)

                        if 'actions' in content_object:
                            self.sync_transaction_type_actions(content_object)

                        serializer = TransactionTypeSerializer(data=content_object,
                                                               context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                instance = TransactionType.objects.get(master_user=self.master_user,
                                                                       user_code=content_object['user_code'])

                                serializer = TransactionTypeSerializer(data=content_object,
                                                                       instance=instance,
                                                                       context=self.get_serializer_context())
                                serializer.is_valid(raise_exception=True)
                                serializer.save()

                            else:
                                _l.info('error %s' % error)
                                stats['status'] = 'error'

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Transaction Types done %s' % (time.perf_counter() - st))

    def overwrite_instrument_types(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'instruments.instrumenttype' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:

                        instrument_type = InstrumentType.objects.get(master_user=self.master_user,
                                                                     user_code=content_object['user_code'])

                        try:
                            item = TransactionType.objects.get(master_user=self.master_user,
                                                               user_code=content_object['___factor_down__user_code'])
                            instrument_type.factor_down = item
                        except TransactionType.DoesNotExist:
                            instrument_type.factor_down_id = self.ecosystem_default.transaction_type.pk

                        try:
                            item = TransactionType.objects.get(master_user=self.master_user,
                                                               user_code=content_object['___factor_same__user_code'])
                            instrument_type.factor_same = item
                        except TransactionType.DoesNotExist:
                            instrument_type.factor_same_id = self.ecosystem_default.transaction_type.pk

                        try:
                            item = TransactionType.objects.get(master_user=self.master_user,
                                                               user_code=content_object['___factor_up__user_code'])
                            instrument_type.factor_up = item
                        except TransactionType.DoesNotExist:
                            instrument_type.factor_up_id = self.ecosystem_default.transaction_type.pk

                        try:
                            item = TransactionType.objects.get(master_user=self.master_user,
                                                               user_code=content_object['___one_off_event__user_code'])
                            instrument_type.one_off_event = item
                        except TransactionType.DoesNotExist:
                            instrument_type.one_off_event_id = self.ecosystem_default.transaction_type.pk

                        try:
                            item = TransactionType.objects.get(master_user=self.master_user,
                                                               user_code=content_object['___regular_event__user_code'])
                            instrument_type.regular_event = item
                        except TransactionType.DoesNotExist:
                            instrument_type.regular_event_id = self.ecosystem_default.transaction_type.pk

                        instrument_type.save()

        _l.info('Import Configuration Overwrite Instrument Types done %s' % (time.perf_counter() - st))

    def import_custom_columns_balance_report(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'reports.balancereportcustomfield' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:
                        serializer = BalanceReportCustomFieldSerializer(data=content_object,
                                                                        context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                instance = BalanceReportCustomField.objects.get(master_user=self.master_user,
                                                                                user_code=content_object['user_code'])

                                serializer = BalanceReportCustomFieldSerializer(data=content_object,
                                                                                instance=instance,
                                                                                context=self.get_serializer_context())
                                serializer.is_valid(raise_exception=True)
                                serializer.save()

                            else:

                                _l.info('error %s' % error)
                                stats['status'] = 'error'

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Custom Columns Balance Report done %s' % (time.perf_counter() - st))

    def import_custom_columns_pl_report(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'reports.plreportcustomfield' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:
                        serializer = PLReportCustomFieldSerializer(data=content_object,
                                                                   context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                instance = PLReportCustomField.objects.get(master_user=self.master_user,
                                                                           user_code=content_object['user_code'])

                                serializer = PLReportCustomFieldSerializer(data=content_object,
                                                                           instance=instance,
                                                                           context=self.get_serializer_context())
                                serializer.is_valid(raise_exception=True)
                                serializer.save()

                            else:

                                _l.info('error %s' % error)
                                stats['status'] = 'error'

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Custom Columns PL Report done %s' % (time.perf_counter() - st))

    def import_custom_columns_transaction_report(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'reports.transactionreportcustomfield' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:
                        serializer = TransactionReportCustomFieldSerializer(data=content_object,
                                                                            context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                instance = TransactionReportCustomField.objects.get(master_user=self.master_user,
                                                                                    user_code=content_object[
                                                                                        'user_code'])

                                serializer = TransactionReportCustomFieldSerializer(data=content_object,
                                                                                    instance=instance,
                                                                                    context=self.get_serializer_context())
                                serializer.is_valid(raise_exception=True)
                                serializer.save()

                            else:

                                _l.info('error %s' % error)
                                stats['status'] = 'error'

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Custom Columns Transaction Report done %s' % (time.perf_counter() - st))

    def import_edit_layouts(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'ui.editlayout' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:
                        content_object['member'] = self.member.pk

                        serializer = EditLayoutSerializer(data=content_object,
                                                          context=self.get_serializer_context())

                        content_type = get_content_type_by_name(content_object['content_type'])

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                try:

                                    instance = EditLayout.objects.get(member=self.member, content_type=content_type)

                                    serializer = EditLayoutSerializer(data=content_object,
                                                                      instance=instance,
                                                                      context=self.get_serializer_context())
                                    serializer.is_valid(raise_exception=True)
                                    serializer.save()

                                except Exception as error:

                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Edit Layout for %s' % content_type.model

                            else:

                                _l.info('error %s' % error)
                                stats['status'] = 'error'
                                stats['error']['message'] = 'Edit Layout for %s already exists' % content_type.model

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Edit Layouts done %s' % (time.perf_counter() - st))

    def import_list_layouts(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'ui.listlayout' in item['entity'] or 'ui.reportlayout' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        content_object['member'] = self.member.pk

                        if 'data' in content_object:

                            if 'reportOptions' in content_object['data']:

                                if 'pricing_policy' in content_object['data']['reportOptions']:

                                    try:
                                        content_object['data']['reportOptions'][
                                            'pricing_policy'] = PricingPolicy.objects.get(master_user=self.master_user,
                                                                                          user_code=
                                                                                          content_object['data'][
                                                                                              'reportOptions'][
                                                                                              'pricing_policy_object'][
                                                                                              'user_code']).pk
                                    except (KeyError, PricingPolicy.DoesNotExist):
                                        print("Pricing Policy does not exist")
                                        pass

                                if 'report_currency' in content_object['data']['reportOptions']:

                                    try:
                                        content_object['data']['reportOptions'][
                                            'report_currency'] = Currency.objects.get(master_user=self.master_user,
                                                                                      user_code=content_object['data'][
                                                                                          'reportOptions'][
                                                                                          'report_currency_object'][
                                                                                          'user_code']).pk
                                    except (KeyError, Currency.DoesNotExist):
                                        print("Currency does not exist")
                                        pass

                        serializer = ListLayoutSerializer(data=content_object,
                                                          context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }


                        try:
                            serializer.is_valid(raise_exception=True)

                            # _l.info('Layout import name %s ' % content_object['name'])

                            serializer.save()
                        except ValidationError:

                            if self.instance.mode == 'overwrite':

                                try:

                                    content_type = get_content_type_by_name(content_object['content_type'])

                                    # _l.info('Layout overwrite content_type %s ' % content_type)
                                    # _l.info('Layout import name %s ' % content_object['name'])

                                    layout = ListLayout.objects.get(member=self.member, name=content_object['name'],
                                                                    content_type=content_type)

                                    layout.data = content_object['data']

                                    layout.save()

                                except Exception as error:
                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite List Layout for %s' % content_object['name']
                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'List Layout %s already exists' % content_object['name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration List Layouts done %s' % (time.perf_counter() - st))

    def import_context_menu_layouts(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'ui.contextmenulayout' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        content_object['member'] = self.member.pk


                        serializer = ContextMenuLayoutSerializer(data=content_object,
                                                          context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }


                        try:
                            serializer.is_valid(raise_exception=True)

                            # _l.info('Layout import name %s ' % content_object['name'])

                            serializer.save()
                        except ValidationError:

                            if self.instance.mode == 'overwrite':

                                try:

                                    layout = ContextMenuLayout.objects.get(member=self.member, name=content_object['name'],
                                                                    type=content_object['type'])

                                    layout.data = content_object['data']

                                    layout.save()

                                except Exception as error:
                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Context Menu Layout for %s' % content_object['name']
                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Context Menu Layout %s already exists' % content_object['name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration List Layouts done %s' % (time.perf_counter() - st))

    def import_reference_tables(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'reference_tables.referencetable' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        content_object['member'] = self.member.pk


                        serializer = ReferenceTableSerializer(data=content_object,
                                                                 context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }


                        try:
                            serializer.is_valid(raise_exception=True)

                            # _l.info('Layout import name %s ' % content_object['name'])

                            serializer.save()
                        except ValidationError:

                            if self.instance.mode == 'overwrite':

                                try:

                                    instance = ReferenceTable.objects.get(master_user=self.master_user,
                                                                               user_code=content_object['name'])

                                    serializer = ReferenceTableSerializer(data=content_object,
                                                                               instance=instance,
                                                                               context=self.get_serializer_context())
                                    serializer.is_valid(raise_exception=True)
                                    serializer.save()

                                except Exception as error:
                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Reference Table Layout for %s' % content_object['name']
                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Reference Table %s already exists' % content_object['name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Reference Table done %s' % (time.perf_counter() - st))

    def import_template_layouts(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'ui.templatelayout' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        content_object['member'] = self.member.pk

                        serializer = TemplateLayoutSerializer(data=content_object,
                                                          context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }


                        try:
                            serializer.is_valid(raise_exception=True)

                            # _l.info('Layout import name %s ' % content_object['name'])

                            serializer.save()
                        except ValidationError:

                            if self.instance.mode == 'overwrite':

                                try:

                                    layout = TemplateLayout.objects.get(member=self.member, name=content_object['name'],
                                                                        type=content_object['type'])

                                    layout.data = content_object['data']

                                    layout.save()

                                except Exception as error:
                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Template Layout for %s' % content_object['name']
                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Template Layout %s already exists' % content_object['name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration List Layouts done %s' % (time.perf_counter() - st))

    def sync_dashboard_layout_component_type_settings(self, component_type):

        if 'settings' in component_type:

            if component_type['settings']:

                if 'content_type' in component_type['settings'] and 'layout_name' in component_type['settings']:

                    content_type = get_content_type_by_name(
                        component_type['settings']['content_type'])

                    try:

                        # _l.info('layout content_type %s' % content_type)
                        # _l.info('layout name %s' % component_type['settings']['layout_name'])

                        component_type['settings']['layout'] = ListLayout.objects.get(
                            member=self.member, content_type=content_type,
                            name__exact=component_type['settings']['layout_name']).pk
                    except ListLayout.DoesNotExist:
                        _l.info("layout is not found")

                    self.update_progress()

    def import_dashboard_layouts(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'ui.dashboardlayout' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        # _l.info('Dashboard layout name %s' % content_object['name'])

                        content_object['member'] = self.member.pk

                        if 'data' in content_object:

                            if 'components_types' in content_object['data']:

                                for component_type in content_object['data']['components_types']:
                                    self.sync_dashboard_layout_component_type_settings(component_type)

                            if 'tabs' in content_object['data']:

                                for tab in content_object['data']['tabs']:
                                    for row in tab['layout']['rows']:
                                        for column in row['columns']:
                                            self.sync_dashboard_layout_component_type_settings(column['data'])

                            if 'fixed_area' in content_object['data']:

                                if 'layout' in content_object['data']['fixed_area']:
                                    for row in content_object['data']['fixed_area']['layout']['rows']:
                                        for column in row['columns']:
                                            self.sync_dashboard_layout_component_type_settings(column['data'])

                        serializer = DashboardLayoutSerializer(data=content_object,
                                                               context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except ValidationError:

                            if self.instance.mode == 'overwrite':

                                try:

                                    layout = DashboardLayout.objects.get(member=self.member,
                                                                         name=content_object['name'])

                                    layout.data = content_object['data']

                                    layout.save()

                                except Exception as error:
                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Dashboard Layout for %s' % content_object['name']
                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Dashboard Layout %s already exists' % content_object['name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Dashboard Layouts done %s' % (time.perf_counter() - st))

    def import_download_instrument_schemes(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'integrations.instrumentdownloadscheme' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        _l.info('content_object %s '  % content_object )

                        if '___price_download_scheme__scheme_name' in content_object:

                            try:
                                content_object["price_download_scheme"] = PriceDownloadScheme.objects.get(
                                scheme_name=content_object["___price_download_scheme__scheme_name"], master_user=self.master_user).id
                            except PriceDownloadScheme.DoesNotExist:
                                content_object["price_download_scheme"] = self.ecosystem_default.price_download_scheme.id

                        serializer = InstrumentDownloadSchemeSerializer(data=content_object,
                                                                              context=self.get_serializer_context())
                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                try:

                                    instance = InstrumentDownloadScheme.objects.get(master_user=self.master_user,
                                                                                          scheme_name=content_object[
                                                                                              'scheme_name'])

                                    serializer = InstrumentDownloadSchemeSerializer(data=content_object,
                                                                                          instance=instance,
                                                                                          context=self.get_serializer_context())
                                    serializer.is_valid(raise_exception=True)
                                    serializer.save()

                                except Exception as error:

                                    _l.info('Overwrite Error: Instrument Download Scheme - %s' % error)

                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Instrument Download Scheme for %s' % content_object['scheme_name']

                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Transaction Instrument Download %s already exists' % content_object['scheme_name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Instrument Download Scheme done %s' % (time.perf_counter() - st))

    def import_transaction_import_schemes(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'integrations.complextransactionimportscheme' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        _l.info('content_object %s '  % content_object )

                        if 'rule_scenarios' in content_object:

                            for rule in content_object['rule_scenarios']:

                                try:
                                    rule['transaction_type'] = TransactionType.objects.get(master_user=self.master_user,
                                                                                           user_code=rule[
                                                                                               '___transaction_type__user_code']).pk
                                except TransactionType.DoesNotExist:
                                    _l.info('Cant find Transaction Type form %s' % content_object['scheme_name'])

                                if rule['transaction_type']:

                                    for field in rule['fields']:

                                        try:
                                            field['transaction_type_input'] = TransactionTypeInput.objects.get(
                                                transaction_type=rule['transaction_type'],
                                                name=field['___input__name']).pk
                                        except TransactionTypeInput.DoesNotExist:
                                            _l.info('Cant find Input %s' % field['___input__name'])

                        serializer = ComplexTransactionImportSchemeSerializer(data=content_object,
                                                                              context=self.get_serializer_context())
                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                try:

                                    instance = ComplexTransactionImportScheme.objects.get(master_user=self.master_user,
                                                                                          scheme_name=content_object[
                                                                                              'scheme_name'])

                                    serializer = ComplexTransactionImportSchemeSerializer(data=content_object,
                                                                                          instance=instance,
                                                                                          context=self.get_serializer_context())
                                    serializer.is_valid(raise_exception=True)
                                    serializer.save()

                                except Exception as error:

                                    _l.info('Overwrite Error: Transaction Import Scheme - %s' % error)

                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Transaction Import Scheme for %s' % content_object['scheme_name']

                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Transaction Import Scheme %s already exists' % content_object['scheme_name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Transaction Import Scheme done %s' % (time.perf_counter() - st))

    def import_simple_import_schemes(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'csv_import.csvimportscheme' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        pieces = content_object['content_type'].split('.')
                        app_label_title = pieces[0]
                        model_title = pieces[1]

                        content_type = ContentType.objects.get(app_label=app_label_title, model=model_title)

                        for entity_field in content_object['entity_fields']:

                            if '___dynamic_attribute_id__user_code' in entity_field:

                                try:

                                    entity_field['dynamic_attribute_id'] = GenericAttributeType.objects.get(
                                        master_user=self.master_user,
                                        user_code=entity_field['___dynamic_attribute_id__user_code'],
                                        content_type=content_type).pk

                                except GenericAttributeType.DoesNotExist:

                                    _l.info(
                                        'Cant find attribute %s' % entity_field['___dynamic_attribute_id__user_code'])

                                    entity_field['dynamic_attribute_id'] = None

                        serializer = CsvImportSchemeSerializer(data=content_object,
                                                               context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                try:

                                    instance = CsvImportScheme.objects.get(master_user=self.master_user,
                                                                           scheme_name=content_object['scheme_name'])

                                    serializer = CsvImportSchemeSerializer(data=content_object,
                                                                           instance=instance,
                                                                           context=self.get_serializer_context())
                                    serializer.is_valid(raise_exception=True)
                                    serializer.save()

                                except Exception as error:

                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Simple Import Scheme for %s' % content_object['scheme_name']

                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Simple Import Scheme %s already exists' % content_object['scheme_name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Simple Import Scheme done %s' % (time.perf_counter() - st))

    def import_complex_import_schemes(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'complex_import.compleximportscheme' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        for action in content_object['actions']:

                            if action['csv_import_scheme']:

                                try:
                                    action['csv_import_scheme']['csv_import_scheme'] = CsvImportScheme.objects.get(
                                        master_user=self.master_user, scheme_name=action['csv_import_scheme'][
                                            '___csv_import_scheme__scheme_name']).pk
                                except CsvImportScheme.DoesNotExist:
                                    _l.info('Scheme %s is not found' % action['csv_import_scheme'][
                                        '___csv_import_scheme__scheme_name'])

                            if action['complex_transaction_import_scheme']:
                                try:
                                    action['complex_transaction_import_scheme'][
                                        'complex_transaction_import_scheme'] = ComplexTransactionImportScheme.objects.get(
                                        master_user=self.master_user,
                                        scheme_name=action['complex_transaction_import_scheme'][
                                            '___complex_transaction_import_scheme__scheme_name']).pk
                                except ComplexTransactionImportScheme.DoesNotExist:
                                    _l.info('Scheme %s is not found' % action['complex_transaction_import_scheme'][
                                        '___complex_transaction_import_scheme__scheme_name'])

                        serializer = ComplexImportSchemeSerializer(data=content_object,
                                                                   context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                try:

                                    instance = ComplexImportScheme.objects.get(master_user=self.master_user,
                                                                               scheme_name=content_object['scheme_name'])

                                    serializer = ComplexImportSchemeSerializer(data=content_object,
                                                                               instance=instance,
                                                                               context=self.get_serializer_context())
                                    serializer.is_valid(raise_exception=True)
                                    serializer.save()

                                except Exception as error:

                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Complex Import Scheme for %s' % content_object['scheme_name']

                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Complex Import Scheme %s already exists' % content_object['scheme_name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Complex Import Scheme done %s' % (time.perf_counter() - st))

    def import_currencies(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'currencies.currency' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        serializer = CurrencySerializer(data=content_object,
                                                        context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                try:

                                    instance = Currency.objects.get(master_user=self.master_user,
                                                                    user_code=content_object['user_code'])

                                    if 'pricing_policies' in content_object:

                                        for policy in content_object['pricing_policies']:

                                            if '___pricing_policy__user_code' in policy:

                                                try:
                                                    policy['pricing_policy'] = PricingPolicy.objects.get(
                                                        master_user=self.master_user,
                                                        user_code=policy['___pricing_policy__user_code']).pk

                                                except PricingPolicy.DoesNotExist:
                                                    policy['pricing_policy'] = self.ecosystem_default.pricing_policy.pk

                                            if '___pricing_scheme__user_code' in policy:

                                                try:
                                                    policy['pricing_scheme'] = CurrencyPricingScheme.objects.get(
                                                        master_user=self.master_user,
                                                        user_code=policy['___pricing_policy__user_code']).pk

                                                except CurrencyPricingScheme.DoesNotExist:
                                                    policy['pricing_scheme'] = None
                                                    # policy['pricing_scheme'] = CurrencyPricingScheme.objects.get(
                                                    #     master_user=self.master_user,
                                                    #     user_code='-').pk  # TODO Add to EcosystemDefaults


                                    serializer = CurrencySerializer(data=content_object,
                                                                    instance=instance,
                                                                    context=self.get_serializer_context())
                                    serializer.is_valid(raise_exception=True)
                                    serializer.save()

                                    _l.info("Currency Overwritten %s" % instance)

                                except Exception as error:

                                    _l.info("Currency Error overwrite %s" % error)

                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Currency %s' % content_object['name']

                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Currency %s already exists' % content_object['name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Currency done %s' % (time.perf_counter() - st))

    def import_pricing_policies(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'instruments.pricingpolicy' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:


                        if '__default_instrument_pricing_scheme__user_code' in content_object:

                            try:

                                content_object['default_instrument_pricing_scheme'] = InstrumentPricingScheme.objects.get(
                                    master_user=self.master_user,
                                    user_code=content_object['__default_instrument_pricing_scheme__user_code']).pk

                            except Exception as e:
                                _l.info("Cant map default instrument pricing scheme. Error: %s" % e)

                        if '__default_currency_pricing_scheme__user_code' in content_object:

                            try:

                                content_object['default_currency_pricing_scheme'] = CurrencyPricingScheme.objects.get(
                                    master_user=self.master_user,
                                    user_code=content_object['__default_currency_pricing_scheme__user_code']).pk

                            except Exception as e:
                                _l.info("Cant map default currency pricing scheme. Error: %s" % e)


                        serializer = PricingPolicySerializer(data=content_object,
                                                             context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:

                            serializer.is_valid(raise_exception=True)
                            serializer.save()

                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                try:

                                    instance = PricingPolicy.objects.get(master_user=self.master_user,
                                                                         user_code=content_object['user_code'])

                                    serializer = PricingPolicySerializer(data=content_object,
                                                                         instance=instance,
                                                                         context=self.get_serializer_context())
                                    serializer.is_valid(raise_exception=True)
                                    serializer.save()

                                except Exception as error:

                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Pricing Policy %s' % content_object['name']

                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Pricing Policy %s already exists' % content_object['name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Pricing Policy done %s' % (time.perf_counter() - st))

    def import_pricing_automated_schedule(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'integrations.pricingautomatedschedule' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        serializer = PricingAutomatedScheduleSerializer(data=content_object,
                                                                        context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)

                            try:
                                serializer.instance = PricingAutomatedSchedule.objects.get(master_user=self.master_user)
                            except PricingAutomatedSchedule.DoesNotExist:
                                pass

                            serializer.save()
                        except Exception as error:

                            stats['status'] = 'error'
                            stats['error']['message'] = 'Can\'t Import Price Download Schedule'


                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Pricing Automated Schedule done %s' % (time.perf_counter() - st))

    def import_instrument_user_fields(self, configuration_section):
        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'ui.instrumentuserfieldmodel' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        serializer = InstrumentUserFieldSerializer(data=content_object,
                                                                   context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                try:

                                    instance = InstrumentUserFieldModel.objects.get(master_user=self.master_user,
                                                                                    key=content_object['key'])

                                    serializer = InstrumentUserFieldSerializer(data=content_object,
                                                                               instance=instance,
                                                                               context=self.get_serializer_context())
                                    serializer.is_valid(raise_exception=True)
                                    serializer.save()

                                except Exception as error:
                                    stats['status'] = 'error'
                                    stats['error']['message'] = 'Can\'t overwrite Instrument User Field %s ' % content_object['name']

                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Instrument User Field %s already exists' % content_object['name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Instrument User Fields done %s' % (time.perf_counter() - st))

    def import_transaction_user_fields(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'ui.transactionuserfieldmodel' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        serializer = TransactionUserFieldSerializer(data=content_object,
                                                                    context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:

                            serializer.is_valid(raise_exception=True)

                            try:
                                serializer.instance = TransactionUserFieldModel.objects.get(
                                    master_user=self.master_user, key=content_object['key'])
                            except TransactionUserFieldModel.DoesNotExist:
                                pass

                            serializer.save()
                        except Exception as error:
                            stats['status'] = 'error'
                            stats['error']['message'] = 'Transaction User Field %s already exists' % content_object['name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Transaction User Fields done %s' % (time.perf_counter() - st))

    def import_instrument_pricing_schemes(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'pricing.instrumentpricingscheme' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        serializer = InstrumentPricingSchemeSerializer(data=content_object,
                                                               context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                try:

                                    instance = InstrumentPricingScheme.objects.get(master_user=self.master_user,
                                                                           name=content_object['name'])

                                    serializer = InstrumentPricingSchemeSerializer(data=content_object,
                                                                           instance=instance,
                                                                           context=self.get_serializer_context())
                                    serializer.is_valid(raise_exception=True)
                                    serializer.save()

                                except Exception as error:

                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Instrument Pricing Scheme for %s' % content_object['name']

                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Instrument Pricing Scheme %s already exists' % content_object['name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Instrument Pricing Scheme done %s' % (time.perf_counter() - st))

    def import_currency_pricing_schemes(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'pricing.currencypricingscheme' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        serializer = CurrencyPricingSchemeSerializer(data=content_object,
                                                                       context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                try:

                                    instance = CurrencyPricingScheme.objects.get(master_user=self.master_user,
                                                                                   name=content_object['name'])

                                    serializer = CurrencyPricingSchemeSerializer(data=content_object,
                                                                                   instance=instance,
                                                                                   context=self.get_serializer_context())
                                    serializer.is_valid(raise_exception=True)
                                    serializer.save()

                                except Exception as error:

                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Currency Pricing Scheme for %s' % content_object['name']

                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Currency Pricing Scheme %s already exists' % content_object['name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Currency Pricing Scheme done %s' % (time.perf_counter() - st))

    def import_pricing_schedules(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'schedules.pricingschedule' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        serializer = PricingScheduleSerializer(data=content_object,
                                                                     context=self.get_serializer_context())

                        procedures = PricingProcedure.objects.filter(master_user=self.master_user, user_code__in=content_object['pricing_procedures__user_codes'])

                        content_object['pricing_procedures'] = []

                        for procedure in procedures:
                            content_object['pricing_procedures'].append(procedure.id)


                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                try:

                                    instance = PricingSchedule.objects.get(master_user=self.master_user,
                                                                                 name=content_object['name'])

                                    serializer = PricingScheduleSerializer(data=content_object,
                                                                                 instance=instance,
                                                                                 context=self.get_serializer_context())
                                    serializer.is_valid(raise_exception=True)
                                    serializer.save()

                                except Exception as error:

                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Pricing Schedule for %s' % content_object['name']

                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Currency Pricing Schedule %s already exists' % content_object['name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Pricing Schedules done %s' % (time.perf_counter() - st))

    def import_pricing_procedures(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'pricing.pricingprocedure' in item['entity']:

                self.instance.stats['configuration'][item['entity']] = []

                if 'content' in item:

                    for content_object in item['content']:

                        serializer = PricingProcedureSerializer(data=content_object,
                                                                     context=self.get_serializer_context())

                        stats = {
                            'content_type': item['entity'],
                            'mode': self.instance.mode,
                            'item': content_object,
                            'error': {
                                'message': None
                            },
                            'status': 'info'
                        }

                        try:
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as error:

                            if self.instance.mode == 'overwrite':

                                try:

                                    instance = PricingProcedure.objects.get(master_user=self.master_user,
                                                                                 name=content_object['name'])

                                    serializer = PricingProcedureSerializer(data=content_object,
                                                                                   instance=instance,
                                                                                   context=self.get_serializer_context())
                                    serializer.is_valid(raise_exception=True)
                                    serializer.save()

                                except Exception as error:

                                    stats['status'] = 'error'
                                    stats['error'][
                                        'message'] = 'Can\'t Overwrite Pricing Procedure for %s' % content_object['name']

                            else:

                                stats['status'] = 'error'
                                stats['error']['message'] = 'Pricing Procedure %s already exists' % content_object['name']

                        self.instance.stats['configuration'][item['entity']].append(stats)

                        self.update_progress()

        _l.info('Import Configuration Pricing Procedure done %s' % (time.perf_counter() - st))

    # Configuration import logic end

    def print_entities_in_file(self, configuration_section):

        for item in configuration_section['items']:

            _l.info("In file: %s" % item['entity'])

    def import_configuration(self, configuration_section):

        self.configuration_recovery_handler.set_configuration(configuration_section)

        configuration_section = self.configuration_recovery_handler.process_recovery()

        # try:

        st = time.perf_counter()

        if 'items' in configuration_section:

            self.print_entities_in_file(configuration_section)

            can_import = check_configuration_section(self.configuration_access_table)

            #
            # Import order matters
            #

            if can_import:
                self.import_attribute_types(configuration_section)  # configuration section
            else:
                _l.info("Permission Error: Attributes types")

            if self.data_access_table['currencies.currency']:
                self.import_currencies(configuration_section)  # data section
            else:
                _l.info("Permission Error: Currencies")

            if self.data_access_table['accounts.accounttype']:
                self.import_account_types(configuration_section)  # data section
            else:
                _l.info("Permission Error: Account Type")

            if self.data_access_table['instruments.instrumenttype']:
                self.import_instrument_types(configuration_section)  # data section
            else:
                _l.info("Permission Error: Instrument Type")

            self.import_transaction_types_groups(configuration_section)  # unknown

            if self.data_access_table['transactions.transactiontype']:
                self.import_transaction_types(configuration_section)  # data section
            else:
                _l.info("Permission Error: Transaction Type")

            if self.data_access_table['instruments.instrumenttype']:
                self.overwrite_instrument_types(configuration_section)  # data section
            else:
                _l.info("Permission Error: Instrument Type")

            # Configuration section

            if can_import:
                self.import_custom_columns_balance_report(configuration_section)
                self.import_custom_columns_pl_report(configuration_section)
                self.import_custom_columns_transaction_report(configuration_section)

                self.import_transaction_import_schemes(configuration_section)
                self.import_simple_import_schemes(configuration_section)
                self.import_complex_import_schemes(configuration_section)

                self.import_download_instrument_schemes(configuration_section)

                self.import_instrument_user_fields(configuration_section)
                self.import_transaction_user_fields(configuration_section)

                self.import_instrument_pricing_schemes(configuration_section)
                self.import_currency_pricing_schemes(configuration_section)
                self.import_pricing_procedures(configuration_section)
                self.import_pricing_schedules(configuration_section)

            if can_import:
                self.import_pricing_policies(configuration_section)  # configuration section
                self.import_pricing_automated_schedule(configuration_section)  # configuration section
            else:
                _l.info("Permission Error: Pricing Policies")

            # User Interface

            self.import_edit_layouts(configuration_section)
            self.import_list_layouts(configuration_section)
            self.import_template_layouts(configuration_section)
            self.import_context_menu_layouts(configuration_section)
            self.import_reference_tables(configuration_section)
            self.import_dashboard_layouts(configuration_section)

        _l.info('Import Configuration done %s' % (time.perf_counter() - st))

        # except Exception as error:
        #
        #     _l.info('Import Configuration Error %s' % error)

    def import_mappings(self, mappings_section):

        try:

            st = time.perf_counter()

            map_to_serializer = {
                'integrations.accounttypemapping': AccountTypeMappingSerializer,
                'integrations.instrumenttypemapping': InstrumentTypeMappingSerializer,
                'integrations.pricingpolicymapping': PricingPolicyMappingSerializer,
                'integrations.pricedownloadschememapping': PriceDownloadSchemeMappingSerializer,
                'integrations.periodicitymapping': PeriodicityMappingSerializer,
                'integrations.dailypricingmodelmapping': DailyPricingModelMappingSerializer,
                'integrations.paymentsizedetailmapping': PaymentSizeDetailMappingSerializer,
                'integrations.accrualcalculationmodelmapping': AccrualCalculationModelMappingSerializer,
            }

            map_to_model = {
                'integrations.accounttypemapping': AccountType,
                'integrations.instrumenttypemapping': InstrumentType,
                'integrations.pricingpolicymapping': PricingPolicy,
                'integrations.pricedownloadschememapping': PriceDownloadScheme,
                'integrations.periodicitymapping': Periodicity,
                'integrations.dailypricingmodelmapping': DailyPricingModel,
                'integrations.paymentsizedetailmapping': PaymentSizeDetail,
                'integrations.accrualcalculationmodelmapping': AccrualCalculationModel,
            }

            map_to_mapping = {
                'integrations.accounttypemapping': AccountTypeMapping,
                'integrations.instrumenttypemapping': InstrumentTypeMapping,
                'integrations.pricingpolicymapping': PricingPolicyMapping,
                'integrations.pricedownloadschememapping': PriceDownloadSchemeMapping,
                'integrations.periodicitymapping': PeriodicityMapping,
                'integrations.dailypricingmodelmapping': DailyPricingModelMapping,
                'integrations.paymentsizedetailmapping': PaymentSizeDetailMapping,
                'integrations.accrualcalculationmodelmapping': AccrualCalculationModelMapping,
            }

            can_import = check_configuration_section(self.configuration_access_table)

            if can_import:

                if 'items' in mappings_section:
                    for entity_object in mappings_section['items']:

                        self.instance.stats['mappings'][entity_object['entity']] = []

                        for content_object in entity_object['content']:

                            stats = {
                                'content_type': entity_object['entity'],
                                'mode': self.instance.mode,
                                'item': content_object,
                                'error': {
                                    'message': None
                                },
                                'status': 'info'
                            }

                            error = False

                            if '___system_code' in content_object:
                                content_object['content_object'] = map_to_model[entity_object['entity']].objects.get(
                                    system_code=content_object['___system_code']).pk

                            if '___user_code' in content_object:

                                try:
                                    content_object['content_object'] = map_to_model[entity_object['entity']].objects.get(
                                        master_user=self.master_user, user_code__exact=content_object['___user_code']).pk

                                except map_to_model[entity_object['entity']].DoesNotExist:
                                    error = True

                            if '___scheme_name' in content_object:

                                try:
                                    content_object['content_object'] = map_to_model[entity_object['entity']].objects.get(
                                        master_user=self.master_user,
                                        scheme_name__exact=content_object['___scheme_name']).pk

                                except map_to_model[entity_object['entity']].DoesNotExist:
                                    error = True

                            if error == False:
                                serializer = map_to_serializer[entity_object['entity']](data=content_object,
                                                                                        context=self.get_serializer_context())

                                try:
                                    serializer.is_valid(raise_exception=True)
                                    serializer.save()
                                except Exception as error:

                                    if self.instance.mode == 'overwrite':

                                        try:

                                            instance = map_to_mapping[entity_object['entity']].objects.get(
                                                    value=content_object['value'],
                                                    master_user=self.master_user, content_object=content_object['content_object'])

                                            serializer = map_to_serializer[entity_object['entity']](data=content_object,
                                                                                                    instance=instance,
                                                                                                    context=self.get_serializer_context())

                                            serializer.is_valid(raise_exception=True)

                                            serializer.save()


                                        except Exception as error:

                                            _l.info('error %s' % error)

                                            stats['status'] = 'error'

                                            if '___system_code' in content_object:
                                                stats['error']['message'] = 'Can\'t Overwrite Mapping %s' % content_object['___system_code']

                                            if '___user_code' in content_object:
                                                stats['error']['message'] = 'Can\'t Overwrite  Mapping %s' % content_object['___user_code']

                                            if '___scheme_name' in content_object:
                                                stats['error']['message'] = 'Can\'t Overwrite  Mapping %s' % content_object['___scheme_name']

                                    else:
                                        stats['status'] = 'error'

                                        if '___system_code' in content_object:
                                            stats['error']['message'] = 'Mapping %s already exists' % content_object['___system_code']

                                        if '___user_code' in content_object:
                                            stats['error']['message'] = 'Mapping %s already exists' % content_object['___user_code']

                                        if '___scheme_name' in content_object:
                                            stats['error']['message'] = 'Mapping %s already exists' % content_object['___scheme_name']

                            self.instance.stats['mappings'][entity_object['entity']].append(stats)

                            self.update_progress()
            else:
                _l.info('Permission Error: Mappings')

            _l.info('Import Mappings done %s' % (time.perf_counter() - st))

        except Exception as error:

            _l.info('Import Mappings Error %s' % error)

@shared_task(name='configuration_import.configuration_import_as_json', bind=True)
def configuration_import_as_json(self, instance):
    _l.info('instance %s' % instance)
    _l.info('instance.mode %s' % instance.mode)
    # _l.info('instance.data %s' % instance.data)

    import_manager = ImportManager(instance, self.update_state)

    configuration_section = None
    mappings_section = None

    st = time.perf_counter()

    if 'body' in instance.data:

        for section in instance.data['body']:

            _l.info('section_name %s' % section['section_name'])

            if section['section_name'] == 'configuration':
                configuration_section = section

            if section['section_name'] == 'mappings':
                mappings_section = section

    import_manager.count_progress_total()

    if configuration_section:
        import_manager.import_configuration(configuration_section)

    if mappings_section:
        import_manager.import_mappings(mappings_section)

    _l.info('Import done %s' % (time.perf_counter() - st))

    return instance
