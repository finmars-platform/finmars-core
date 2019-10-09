import csv

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch
from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
from django.utils.datetime_safe import datetime
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from poms.accounts.models import AccountType, Account
from poms.accounts.serializers import AccountTypeSerializer
from poms.common.utils import delete_keys_from_dict, recursive_callback
from poms.common.views import AbstractModelViewSet
from poms.complex_import.models import ComplexImportScheme, ComplexImportSchemeAction, \
    ComplexImportSchemeActionCsvImport, ComplexImportSchemeActionTransactionImport
from poms.complex_import.serializers import ComplexImportSchemeSerializer
from poms.counterparties.models import Counterparty, Responsible
from poms.csv_import.models import CsvField, EntityField, CsvImportScheme
from poms.csv_import.serializers import CsvImportSchemeSerializer
from poms.currencies.models import Currency
from poms.currencies.serializers import CurrencySerializer
from poms.instruments.models import InstrumentType, Instrument, Periodicity, DailyPricingModel, PaymentSizeDetail, \
    AccrualCalculationModel, PricingPolicy
from poms.instruments.serializers import InstrumentTypeSerializer, PricingPolicySerializer
from poms.integrations.models import InstrumentDownloadScheme, InstrumentDownloadSchemeInput, \
    InstrumentDownloadSchemeAttribute, PriceDownloadScheme, ComplexTransactionImportScheme, \
    ComplexTransactionImportSchemeInput, ComplexTransactionImportSchemeRule, ComplexTransactionImportSchemeField, \
    PricingAutomatedSchedule, PortfolioMapping, CurrencyMapping, InstrumentTypeMapping, AccountMapping, \
    InstrumentMapping, CounterpartyMapping, ResponsibleMapping, Strategy1Mapping, Strategy2Mapping, Strategy3Mapping, \
    PeriodicityMapping, DailyPricingModelMapping, PaymentSizeDetailMapping, AccrualCalculationModelMapping, \
    PriceDownloadSchemeMapping, AccountTypeMapping, PricingPolicyMapping
from poms.integrations.serializers import PricingAutomatedScheduleSerializer, ComplexTransactionImportSchemeSerializer, \
    AccountTypeMappingSerializer, InstrumentTypeMappingSerializer, PricingPolicyMappingSerializer, \
    PriceDownloadSchemeMappingSerializer, PeriodicityMappingSerializer, DailyPricingModelMappingSerializer, \
    PaymentSizeDetailMappingSerializer, AccrualCalculationModelMappingSerializer
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier
from poms.obj_attrs.serializers import GenericClassifierViewSerializer, GenericClassifierNodeSerializer, \
    GenericAttributeTypeSerializer
from poms.portfolios.models import Portfolio
from poms.reference_tables.models import ReferenceTable, ReferenceTableRow
from poms.reports.models import BalanceReportCustomField, PLReportCustomField, TransactionReportCustomField
from poms.reports.serializers import BalanceReportCustomFieldSerializer, PLReportCustomFieldSerializer, \
    TransactionReportCustomFieldSerializer
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.tags.utils import get_tag_prefetch
from poms.transactions.models import TransactionType, TransactionTypeInput, TransactionTypeAction, \
    TransactionTypeActionInstrument, TransactionTypeActionTransaction, TransactionTypeGroup, \
    TransactionTypeActionInstrumentAccrualCalculationSchedules, TransactionTypeActionInstrumentEventSchedule, \
    TransactionTypeActionInstrumentEventScheduleAction, TransactionTypeActionInstrumentFactorSchedule, \
    TransactionTypeActionInstrumentManualPricingFormula, NotificationClass, EventClass, TransactionClass

from rest_framework.exceptions import ValidationError

from django.core import serializers
import json

from poms.transactions.serializers import TransactionTypeSerializer, TransactionTypeGroupSerializer
from poms.ui.models import EditLayout, ListLayout, Bookmark, TransactionUserFieldModel, InstrumentUserFieldModel, \
    DashboardLayout

from django.forms.models import model_to_dict

from rest_framework.parsers import MultiPartParser

from io import StringIO

import time

from poms.ui.serializers import ListLayoutSerializer, DashboardLayoutSerializer, InstrumentUserFieldSerializer, \
    TransactionUserFieldSerializer, EditLayoutSerializer
from poms.users.models import EcosystemDefault


def get_content_type_by_name(name):
    pieces = name.split('.')
    app_label_title = pieces[0]
    model_title = pieces[1]

    content_type = ContentType.objects.get(app_label=app_label_title, model=model_title)

    return content_type


class ConfigurationImportAsJsonViewSet(AbstractModelViewSet):
    http_method_names = ['post']

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

                if 'content' in item:

                    for content_object in item['content']:
                        pieces = content_object['content_type'].split('.')
                        app_label = pieces[0]
                        model = pieces[1]

                        content_type = ContentType.objects.get(app_label=app_label, model=model)

                        content_object['content_type_id'] = content_type.id

                        serializer = GenericAttributeTypeSerializer(data=content_object,
                                                                    context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save(content_type=content_type)

        print('Import Configuration Attribute Types done %s' % (time.perf_counter() - st))

    def import_instrument_types(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'instruments.instrumenttype' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:
                        content_object['one_off_event'] = self.ecosystem_default.transaction_type.pk
                        content_object['regular_event'] = self.ecosystem_default.transaction_type.pk

                        serializer = InstrumentTypeSerializer(data=content_object,
                                                              context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        print('Import Configuration Instrument Types done %s' % (time.perf_counter() - st))

    def import_account_types(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'accounts.accounttype' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:
                        serializer = AccountTypeSerializer(data=content_object,
                                                           context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        print('Import Configuration Account Types done %s' % (time.perf_counter() - st))

    def import_transaction_types_groups(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'transactions.transactiontypegroup' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:
                        serializer = TransactionTypeGroupSerializer(data=content_object,
                                                                    context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        print('Import Configuration Transaction Types Groups done %s' % (time.perf_counter() - st))

    def import_transaction_types(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'transactions.transactiontype' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:

                        try:
                            group = TransactionTypeGroup.objects.get(master_user=self.master_user,
                                                                     user_code=content_object['___group__user_code'])
                            content_object['group'] = group.pk
                        except TransactionTypeGroup.DoesNotExist:
                            content_object['group'] = self.ecosystem_default.transaction_type_group.pk

                        self.sync_transaction_type_inputs(content_object)
                        self.sync_transaction_type_actions(content_object)

                        serializer = TransactionTypeSerializer(data=content_object,
                                                               context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        print('Import Configuration Transaction Types done %s' % (time.perf_counter() - st))

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
                        except TransactionType.DoesnotExist:
                            instrument_type.factor_down = self.ecosystem_default.transaction_type.pk

                        try:
                            item = TransactionType.objects.get(master_user=self.master_user,
                                                               user_code=content_object['___factor_same__user_code'])
                            instrument_type.factor_same = item
                        except TransactionType.DoesnotExist:
                            instrument_type.factor_same = self.ecosystem_default.transaction_type.pk

                        try:
                            item = TransactionType.objects.get(master_user=self.master_user,
                                                               user_code=content_object['___factor_up__user_code'])
                            instrument_type.factor_up = item
                        except TransactionType.DoesnotExist:
                            instrument_type.factor_up = self.ecosystem_default.transaction_type.pk

                        try:
                            item = TransactionType.objects.get(master_user=self.master_user,
                                                               user_code=content_object['___one_off_event__user_code'])
                            instrument_type.one_off_event = item
                        except TransactionType.DoesnotExist:
                            instrument_type.one_off_event = self.ecosystem_default.transaction_type.pk

                        try:
                            item = TransactionType.objects.get(master_user=self.master_user,
                                                               user_code=content_object['___regular_event__user_code'])
                            instrument_type.regular_event = item
                        except TransactionType.DoesnotExist:
                            instrument_type.regular_event = self.ecosystem_default.transaction_type.pk

                        instrument_type.save()

        print('Import Configuration Overwrite Instrument Types done %s' % (time.perf_counter() - st))

    def import_custom_columns_balance_report(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'reports.balancereportcustomfield' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:
                        serializer = BalanceReportCustomFieldSerializer(data=content_object,
                                                                        context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        print('Import Configuration Custom Columns Balance Report done %s' % (time.perf_counter() - st))

    def import_custom_columns_pl_report(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'reports.plreportcustomfield' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:
                        serializer = PLReportCustomFieldSerializer(data=content_object,
                                                                   context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        print('Import Configuration Custom Columns PL Report done %s' % (time.perf_counter() - st))

    def import_custom_columns_transaction_report(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'reports.transactionreportcustomfield' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:
                        serializer = TransactionReportCustomFieldSerializer(data=content_object,
                                                                            context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        print('Import Configuration Custom Columns Transaction Report done %s' % (time.perf_counter() - st))

    def import_edit_layouts(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'ui.editlayout' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:
                        content_object['member'] = self.member.pk

                        serializer = EditLayoutSerializer(data=content_object,
                                                          context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        print('Import Configuration Edit Layouts done %s' % (time.perf_counter() - st))

    def import_list_layouts(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'ui.listlayout' in item['entity'] or 'ui.reportlayout' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:
                        content_object['member'] = self.member.pk

                        serializer = ListLayoutSerializer(data=content_object,
                                                          context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        print('Import Configuration List Layouts done %s' % (time.perf_counter() - st))

    def sync_dashboard_layout_component_type_settings(self, component_type):

        if 'settings' in component_type:

            if component_type['settings']:

                if 'content_type' in component_type['settings'] and 'layout_name' in component_type['settings']:

                    content_type = get_content_type_by_name(
                        component_type['settings']['content_type'])

                    try:
                        component_type['settings']['layout'] = ListLayout.objects.get(
                            member=self.member, content_type=content_type,
                            name__exact=component_type['settings']['layout_name']).pk
                    except ListLayout.DoesNotExist:
                        print("layout is not found")

    def import_dashboard_layouts(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'ui.dashboardlayout' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:
                        content_object['member'] = self.member.pk

                        for component_type in content_object['data']['components_types']:
                            self.sync_dashboard_layout_component_type_settings(component_type)

                        for tab in content_object['data']['tabs']:
                            for row in tab['layout']['rows']:
                                for column in row['columns']:
                                    self.sync_dashboard_layout_component_type_settings(column['data'])

                        if 'layout' in content_object['data']['fixed_area']:
                            for row in content_object['fixed_area']['rows']:
                                for column in row['columns']:
                                    self.sync_dashboard_layout_component_type_settings(column['data'])

                        serializer = DashboardLayoutSerializer(data=content_object,
                                                               context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        print('Import Configuration Dashboard Layouts done %s' % (time.perf_counter() - st))

    def import_transaction_import_schemes(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'integrations.complextransactionimportscheme' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:

                        for rule in content_object['rules']:

                            try:
                                rule['transaction_type'] = TransactionType.objects.get(master_user=self.master_user,
                                                                                       user_code=rule[
                                                                                           '___transaction_type__user_code']).pk
                            except TransactionType.DoesNotExist:
                                print('Cant find Transaction Type form %s' % content_object['scheme_name'])

                            if rule['transaction_type']:

                                for field in rule['fields']:

                                    try:
                                        field['transaction_type_input'] = TransactionTypeInput.objects.get(
                                            transaction_type=rule['transaction_type'], name=field['___input__name']).pk
                                    except TransactionTypeInput.DoesNotExist:
                                        print('Cant find Input %s' % field['___input__name'])

                        serializer = ComplexTransactionImportSchemeSerializer(data=content_object,
                                                                              context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        print('Import Configuration Transaction Import Scheme done %s' % (time.perf_counter() - st))

    def import_simple_import_schemes(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'csv_import.csvimportscheme' in item['entity']:

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

                                    print('Cant find attribute %s' % entity_field['___dynamic_attribute_id__user_code'])

                                    entity_field['dynamic_attribute_id'] = None

                        serializer = CsvImportSchemeSerializer(data=content_object,
                                                               context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        print('Import Configuration Simple Import Scheme done %s' % (time.perf_counter() - st))

    def import_complex_import_schemes(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'complex_import.compleximportscheme' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:

                        for action in content_object['actions']:

                            if action['csv_import_scheme']:

                                try:
                                    action['csv_import_scheme']['csv_import_scheme'] = CsvImportScheme.objects.get(
                                        master_user=self.master_user, scheme_name=action['csv_import_scheme'][
                                            '___csv_import_scheme__scheme_name']).pk
                                except CsvImportScheme.DoesNotExist:
                                    print('Scheme %s is not found' % action['csv_import_scheme'][
                                        '___csv_import_scheme__scheme_name'])

                            if action['complex_transaction_import_scheme']:
                                try:
                                    action['complex_transaction_import_scheme'][
                                        'complex_transaction_import_scheme'] = ComplexTransactionImportScheme.objects.get(
                                        master_user=self.master_user,
                                        scheme_name=action['complex_transaction_import_scheme'][
                                            '___complex_transaction_import_scheme__scheme_name']).pk
                                except CsvImportScheme.DoesNotExist:
                                    print('Scheme %s is not found' % action['complex_transaction_import_scheme'][
                                        '___complex_transaction_import_scheme__scheme_name'])

                        serializer = ComplexImportSchemeSerializer(data=content_object,
                                                                   context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        print('Import Configuration Complex Import Scheme done %s' % (time.perf_counter() - st))

    def import_currencies(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'currencies.currency' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:

                        try:
                            serializer = CurrencySerializer(data=content_object,
                                                            context={'request': self.request})
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                        except Exception as e:
                            print(e)

        print('Import Configuration Currency done %s' % (time.perf_counter() - st))

    def import_pricing_policies(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'instruments.pricingpolicy' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:
                        serializer = PricingPolicySerializer(data=content_object,
                                                             context={'request': self.request})
                        serializer.is_valid(raise_exception=True)

                        try:
                            serializer.instance = PricingPolicy.objects.get(
                                master_user=self.master_user, user_code=content_object['user_code'])
                        except PricingPolicy.DoesNotExist:
                            pass

                        serializer.save()

        print('Import Configuration Pricing Policy done %s' % (time.perf_counter() - st))

    def import_pricing_automated_schedule(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'integrations.pricingautomatedschedule' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:

                        try:
                            serializer = PricingAutomatedScheduleSerializer(data=content_object,
                                                                            context={'request': self.request})
                            serializer.is_valid(raise_exception=True)

                            try:
                                serializer.instance = PricingAutomatedSchedule.objects.get(master_user=self.master_user)
                            except PricingAutomatedSchedule.DoesNotExist:
                                pass

                            serializer.save()
                        except Exception as e:
                            print(e)

        print('Import Configuration Pricing Automated Schedule done %s' % (time.perf_counter() - st))

    def import_instrument_user_fields(self, configuration_section):
        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'ui.instrumentuserfieldmodel' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:

                        try:
                            serializer = InstrumentUserFieldSerializer(data=content_object,
                                                                       context={'request': self.request})
                            serializer.is_valid(raise_exception=True)

                            try:
                                serializer.instance = InstrumentUserFieldModel.objects.get(master_user=self.master_user,
                                                                                           key=content_object['key'])
                            except InstrumentUserFieldModel.DoesNotExist:
                                pass

                            serializer.save()
                        except Exception as e:
                            print(e)

        print('Import Configuration Instrument User Fields done %s' % (time.perf_counter() - st))

    def import_transaction_user_fields(self, configuration_section):

        st = time.perf_counter()

        for item in configuration_section['items']:

            if 'ui.transactionuserfieldmodel' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:

                        try:
                            serializer = TransactionUserFieldSerializer(data=content_object,
                                                                        context={'request': self.request})
                            serializer.is_valid(raise_exception=True)

                            try:
                                serializer.instance = TransactionUserFieldModel.objects.get(
                                    master_user=self.master_user, key=content_object['key'])
                            except TransactionUserFieldModel.DoesNotExist:
                                pass

                            serializer.save()
                        except Exception as e:
                            print(e)

        print('Import Configuration Transaction User Fields done %s' % (time.perf_counter() - st))

    # Configuration import logic end

    def import_configuration(self, configuration_section):

        st = time.perf_counter()

        if 'items' in configuration_section:
            self.import_attribute_types(configuration_section)
            self.import_currencies(configuration_section)
            self.import_pricing_policies(configuration_section)

            self.import_pricing_automated_schedule(configuration_section)

            self.import_account_types(configuration_section)

            self.import_instrument_types(configuration_section)
            self.import_transaction_types_groups(configuration_section)
            self.import_transaction_types(configuration_section)
            self.overwrite_instrument_types(configuration_section)

            self.import_custom_columns_balance_report(configuration_section)
            self.import_custom_columns_pl_report(configuration_section)
            self.import_custom_columns_transaction_report(configuration_section)

            self.import_edit_layouts(configuration_section)
            self.import_list_layouts(configuration_section)
            self.import_dashboard_layouts(configuration_section)

            self.import_transaction_import_schemes(configuration_section)
            self.import_simple_import_schemes(configuration_section)
            self.import_complex_import_schemes(configuration_section)

            self.import_instrument_user_fields(configuration_section)
            self.import_transaction_user_fields(configuration_section)

        print('Import Configuration done %s' % (time.perf_counter() - st))

    def import_mappings(self, mappings_section):

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

        if 'items' in mappings_section:
            for entity_object in mappings_section['items']:

                for content_object in entity_object['content']:

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
                                master_user=self.master_user, scheme_name__exact=content_object['___scheme_name']).pk

                        except map_to_model[entity_object['entity']].DoesNotExist:
                            error = True

                    if error == False:
                        serializer = map_to_serializer[entity_object['entity']](data=content_object,
                                                                                context={'request': self.request})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        print('Import Mappings done %s' % (time.perf_counter() - st))

    def create(self, request, *args, **kwargs):

        self.master_user = self.request.user.master_user
        self.member = self.request.user.member
        self.ecosystem_default = EcosystemDefault.objects.get(master_user=self.master_user)

        configuration_section = None
        mappings_section = None

        st = time.perf_counter()

        if 'body' in request.data:

            for section in request.data['body']:

                if section['section_name'] == 'configuration':
                    configuration_section = section

                if section['section_name'] == 'mappings':
                    mappings_section = section

        if configuration_section:
            self.import_configuration(configuration_section)

        if mappings_section:
            self.import_mappings(mappings_section)

        print('Import done %s' % (time.perf_counter() - st))

        return Response({
            'status': 'OK'
        }, status=status.HTTP_202_ACCEPTED)
