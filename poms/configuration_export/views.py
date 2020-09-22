import csv
import os

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
from poms.common.utils import delete_keys_from_dict, recursive_callback
from poms.common.views import AbstractModelViewSet
from poms.complex_import.models import ComplexImportScheme, ComplexImportSchemeAction, \
    ComplexImportSchemeActionCsvImport, ComplexImportSchemeActionTransactionImport
from poms.counterparties.models import Counterparty, Responsible
from poms.csv_import.models import CsvField, EntityField, CsvImportScheme
from poms.currencies.models import Currency
from poms.instruments.models import InstrumentType, Instrument, Periodicity, DailyPricingModel, PaymentSizeDetail, \
    AccrualCalculationModel, PricingPolicy, PricingCondition
from poms.integrations.models import InstrumentDownloadScheme, InstrumentDownloadSchemeInput, \
    InstrumentDownloadSchemeAttribute, PriceDownloadScheme, ComplexTransactionImportScheme, \
    ComplexTransactionImportSchemeInput, ComplexTransactionImportSchemeField, \
    PricingAutomatedSchedule, PortfolioMapping, CurrencyMapping, InstrumentTypeMapping, AccountMapping, \
    InstrumentMapping, CounterpartyMapping, ResponsibleMapping, Strategy1Mapping, Strategy2Mapping, Strategy3Mapping, \
    PeriodicityMapping, DailyPricingModelMapping, PaymentSizeDetailMapping, AccrualCalculationModelMapping, \
    PriceDownloadSchemeMapping, AccountTypeMapping, PricingPolicyMapping, ComplexTransactionImportSchemeRuleScenario, \
    ComplexTransactionImportSchemeReconScenario, ComplexTransactionImportSchemeReconField, \
    ComplexTransactionImportSchemeSelectorValue, ComplexTransactionImportSchemeCalculatedInput, PricingConditionMapping
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier
from poms.obj_attrs.serializers import GenericClassifierViewSerializer, GenericClassifierNodeSerializer, \
    GenericAttributeTypeSerializer
from poms.obj_perms.utils import obj_perms_filter_objects
from poms.portfolios.models import Portfolio
from poms.pricing.models import InstrumentPricingScheme, CurrencyPricingScheme,  CurrencyPricingPolicy, \
    InstrumentTypePricingPolicy
from poms.pricing.serializers import InstrumentPricingSchemeSerializer, CurrencyPricingSchemeSerializer, \
    CurrencyPricingPolicySerializer, InstrumentTypePricingPolicySerializer
from poms.procedures.models import PricingProcedure
from poms.reconciliation.models import TransactionTypeReconField
from poms.reference_tables.models import ReferenceTable, ReferenceTableRow
from poms.reports.models import BalanceReportCustomField, PLReportCustomField, TransactionReportCustomField
from poms.schedules.models import Schedule
from poms.schedules.serializers import ScheduleSerializer
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.tags.utils import get_tag_prefetch
from poms.transactions.models import TransactionType, TransactionTypeInput, TransactionTypeAction, \
    TransactionTypeActionInstrument, TransactionTypeActionTransaction, TransactionTypeGroup, \
    TransactionTypeActionInstrumentAccrualCalculationSchedules, TransactionTypeActionInstrumentEventSchedule, \
    TransactionTypeActionInstrumentEventScheduleAction, TransactionTypeActionInstrumentFactorSchedule, \
    TransactionTypeActionInstrumentManualPricingFormula, NotificationClass, EventClass, TransactionClass, \
    TransactionTypeInputSettings

from rest_framework.exceptions import ValidationError

from django.core import serializers
import json

from poms.transactions.serializers import TransactionTypeSerializer
from poms.ui.models import EditLayout, ListLayout, Bookmark, TransactionUserFieldModel, InstrumentUserFieldModel, \
    DashboardLayout, TemplateLayout, ContextMenuLayout, EntityTooltip, ColorPalette, ColorPaletteColor

from django.forms.models import model_to_dict

from poms.ui.serializers import BookmarkSerializer
from poms_app import settings


def to_json_objects(items):
    return json.loads(serializers.serialize("json", items))


def to_json_single(item):
    return json.loads(serializers.serialize("json", [item]))[0]


def delete_prop(items, prop):
    for item in items:
        item.pop(prop, None)


def clear_none_attrs(item):
    for (key, value) in list(item.items()):
        if value is None:
            del item[key]

def clear_system_date_attrs(item):

    if 'created' in item:
        del item['created']
    if 'modified' in item:
        del item['modified']


def unwrap_items(items):
    result = []

    for item in items:
        result.append(item["fields"])

    return result


codename_set = ['view_%(model_name)s', 'change_%(model_name)s', 'manage_%(model_name)s',
                'view_%(model_name)s_show_parameters', 'view_%(model_name)s_hide_parameters']


def get_current_version():

    version_path = os.path.join(settings.BASE_DIR, 'data', 'version.txt')

    version = None

    if os.path.isfile(version_path):

        with open(version_path, 'r') as f:

            try:
                version = f.read()

            except Exception as e:
                print("Can't get Version")

    return version


def check_configuration_section(access_table):

    result = True

    print('access_table %s  ' % access_table)

    for key, value in access_table.items():

        if not value:
            result = False

    return result

def get_codename_set(model_cls):
    kwargs = {
        'app_label': model_cls._meta.app_label,
        'model_name': model_cls._meta.model_name
    }
    return {perm % kwargs for perm in codename_set}


def permission_filter(queryset, member):
    return obj_perms_filter_objects(member, get_codename_set(queryset.model), queryset,
                                    prefetch=False)


def get_access_table(member):

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

class ConfigurationExportViewSet(AbstractModelViewSet):

    def list(self, request):

        self._master_user = request.user.master_user
        self._member = request.user.member
        self._request = request

        self.access_table = get_access_table(self._member)

        print(self.access_table)

        response = HttpResponse(content_type='application/json')
        # response['Content-Disposition'] = 'attachment; filename="data-%s.json"' % str(datetime.now().date())

        configuration = self.createConfiguration()

        response.write(json.dumps(configuration))

        return response

    def createConfiguration(self):
        configuration = {}
        configuration["head"] = {}
        configuration["head"]["date"] = str(datetime.now().date())
        configuration["head"]["version"] = str(get_current_version())
        configuration["body"] = []

        can_export = check_configuration_section(self.access_table)

        transaction_types = self.get_transaction_types()
        transaction_type_groups = self.get_transaction_type_groups()
        edit_layouts = self.get_edit_layouts()
        list_layouts = self.get_list_layouts()
        entity_tooltips = self.get_entity_tooltips()
        color_palettes = self.get_color_palettes()
        template_layouts = self.get_template_layouts()
        context_menu_layouts = self.get_context_menu_layouts()
        dashboard_layouts = self.get_dashboard_layouts()
        report_layouts = self.get_report_layouts()
        bookmarks = self.get_bookmarks()
        csv_import_schemes = self.get_csv_import_schemes()
        complex_import_schemes = self.get_complex_import_schemes()
        instrument_download_schemes = self.get_instrument_download_schemes()
        price_download_schemes = self.get_price_download_schemes()
        complex_transaction_import_scheme = self.get_complex_transaction_import_scheme()
        account_types = self.get_account_types()
        instrument_types = self.get_instrument_types()
        pricing_automated_schedule = self.get_pricing_automated_schedule()
        pricing_policies = self.get_pricing_policies()
        currencies = self.get_currencies()

        reference_tables = self.get_reference_tables()

        portfolio_attribute_types = self.get_entity_attribute_types('portfolios', 'portfolio')
        currency_attribute_types = self.get_entity_attribute_types('currencies', 'currency')
        account_attribute_types = self.get_entity_attribute_types('accounts', 'account')
        account_type_attribute_types = self.get_entity_attribute_types('accounts', 'accounttype')

        responsible_attribute_types = self.get_entity_attribute_types('counterparties', 'responsible')
        counterparty_attribute_types = self.get_entity_attribute_types('counterparties', 'counterparty')

        instrument_attribute_types = self.get_entity_attribute_types('instruments', 'instrument')
        instrument_type_attribute_types = self.get_entity_attribute_types('instruments', 'instrumenttype')

        transaction_type_attribute_types = self.get_entity_attribute_types('transactions', 'transactiontype')

        strategy1_attribute_types = self.get_entity_attribute_types('strategies', 'strategy1')
        strategy2_attribute_types = self.get_entity_attribute_types('strategies', 'strategy2')
        strategy3_attribute_types = self.get_entity_attribute_types('strategies', 'strategy3')

        balance_report_custom_fields = self.get_balance_report_custom_fields()
        pl_report_custom_fields = self.get_pl_report_custom_fields()
        transaction_report_custom_fields = self.get_transaction_report_custom_fields()

        get_transaction_user_fields = self.get_transaction_user_fields()
        instrument_user_fields = self.get_instrument_user_fields()

        # Pricing

        instrument_pricing_schemes = self.get_instrument_pricing_schemes()
        currency_pricing_schemes = self.get_currency_pricing_schemes()
        pricing_procedures = self.get_pricing_procedures()
        schedules = self.get_schedules()


        if can_export:

            configuration["body"].append(transaction_types)
            configuration["body"].append(transaction_type_groups)
            configuration["body"].append(edit_layouts)
            configuration["body"].append(list_layouts)

            if self.access_table['ui.templatelayout']:
                configuration["body"].append(template_layouts)

            configuration["body"].append(context_menu_layouts)
            configuration["body"].append(dashboard_layouts)
            configuration["body"].append(report_layouts)
            configuration["body"].append(bookmarks)

            if self.access_table['csv_import.csvimportscheme']:
                configuration["body"].append(csv_import_schemes)

            if self.access_table['complex_import.compleximportscheme']:
                configuration["body"].append(complex_import_schemes)

            if self.access_table['integrations.pricedownloadscheme']:
                configuration["body"].append(price_download_schemes)

            if self.access_table['integrations.instrumentdownloadscheme']:
                configuration["body"].append(instrument_download_schemes)

            if self.access_table['integrations.complextransactionimportscheme']:
                configuration["body"].append(complex_transaction_import_scheme)

            configuration["body"].append(account_types)
            configuration["body"].append(currencies)
            configuration["body"].append(pricing_policies)
            configuration["body"].append(instrument_types)
            configuration["body"].append(pricing_automated_schedule)

            if self.access_table['reference_tables.referencetable']:
                configuration["body"].append(reference_tables)

            if self.access_table['obj_attrs.attributetype']:
                configuration["body"].append(portfolio_attribute_types)
                configuration["body"].append(currency_attribute_types)
                configuration["body"].append(account_attribute_types)
                configuration["body"].append(account_type_attribute_types)
                configuration["body"].append(responsible_attribute_types)
                configuration["body"].append(counterparty_attribute_types)
                configuration["body"].append(instrument_attribute_types)
                configuration["body"].append(instrument_type_attribute_types)
                configuration["body"].append(transaction_type_attribute_types)

            configuration["body"].append(strategy1_attribute_types)
            configuration["body"].append(strategy2_attribute_types)
            configuration["body"].append(strategy3_attribute_types)

            configuration["body"].append(balance_report_custom_fields)
            configuration["body"].append(pl_report_custom_fields)
            configuration["body"].append(transaction_report_custom_fields)

            if self.access_table['ui.userfield']:
                configuration["body"].append(get_transaction_user_fields)
                configuration["body"].append(instrument_user_fields)

            configuration["body"].append(entity_tooltips)
            configuration["body"].append(color_palettes)


            # pricing

            configuration["body"].append(instrument_pricing_schemes)
            configuration["body"].append(currency_pricing_schemes)
            configuration["body"].append(pricing_procedures)

            configuration["body"].append(schedules)


        else:

            configuration["body"].append(edit_layouts)
            configuration["body"].append(list_layouts)

            configuration["body"].append(context_menu_layouts)
            configuration["body"].append(dashboard_layouts)
            configuration["body"].append(report_layouts)
            configuration["body"].append(bookmarks)


        return configuration

    def get_input_prop_by_content_type(self, input):

        if input.content_type.model == 'account':
            return {
                'prop': 'account',
                'code': 'user_code'
            }
        if input.content_type.model == 'instrumenttype':
            return {
                'prop': 'instrument_type',
                'code': 'user_code'
            }
        if input.content_type.model == 'instrument':
            return {
                'prop': 'instrument',
                'code': 'user_code'
            }
        if input.content_type.model == 'currency':
            return {
                'prop': 'currency',
                'code': 'user_code'
            }
        if input.content_type.model == 'counterparty':
            return {
                'prop': 'counterparty',
                'code': 'user_code'
            }
        if input.content_type.model == 'responsible':
            return {
                'prop': 'responsible',
                'code': 'user_code'
            }
        if input.content_type.model == 'portfolio':
            return {
                'prop': 'portfolio',
                'code': 'user_code'
            }
        if input.content_type.model == 'strategy1':
            return {
                'prop': 'strategy1',
                'code': 'user_code'
            }
        if input.content_type.model == 'strategy2':
            return {
                'prop': 'strategy2',
                'code': 'user_code'
            }
        if input.content_type.model == 'strategy3':
            return {
                'prop': 'strategy3',
                'code': 'user_code'
            }
        if input.content_type.model == 'dailypricingmodel':
            return {
                'prop': 'daily_pricing_model',
                'code': 'system_code'
            }
        if input.content_type.model == 'paymentsizedetail':
            return {
                'prop': 'payment_size_detail',
                'code': 'system_code'
            }
        if input.content_type.model == 'pricedownloadscheme':
            return {
                'prop': 'payment_size_detail',
                'code': 'scheme_name'
            }
        if input.content_type.model == 'pricingpolicy':
            return {
                'prop': 'pricing_policy',
                'code': 'user_code'
            }
        if input.content_type.model == 'periodicity':
            return {
                'prop': 'periodicity',
                'code': 'system_code'
            }
        if input.content_type.model == 'accrualcalculationmodel':
            return {
                'prop': 'accrual_calculation_model',
                'code': 'system_code'
            }
        if input.content_type.model == 'eventclass':
            return {
                'prop': 'event_class',
                'code': 'system_code'
            }
        if input.content_type.model == 'notificationclass':
            return {
                'prop': 'notification_class',
                'code': 'system_code'
            }

    def get_transaction_type_inputs(self, transaction_type):

        inputs = to_json_objects(
            TransactionTypeInput.objects.select_related('settings').filter(transaction_type__id=transaction_type["pk"]))

        for input_model in TransactionTypeInput.objects.select_related('settings').filter(transaction_type__id=transaction_type["pk"]):

            if input_model.content_type:
                for input_json in inputs:

                    if input_model.pk == input_json['pk']:

                        input_json["fields"]["content_type"] = '%s.%s' % (
                            input_model.content_type.app_label, input_model.content_type.model)

                        if input_model.value_type == 100:

                            input_prop = self.get_input_prop_by_content_type(input_model)

                            if input_json["fields"][input_prop['prop']]:
                                model = apps.get_model(app_label=input_model.content_type.app_label,
                                                       model_name=input_model.content_type.model)

                                key = '___{}__{}'
                                key = key.format(input_prop['prop'], input_prop['code'])

                                try:

                                    obj = model.objects.get(
                                        pk=getattr(input_model, input_model.content_type.model).pk)

                                    input_json["fields"][key] = getattr(obj, input_prop['code'])

                                except AttributeError:
                                    input_json["fields"][key] = None

                        settings = input_model.settings.all()

                        if len(settings):
                            input_json["fields"]["settings"] = {
                                "linked_inputs_names": settings[0].linked_inputs_names
                            }



        results = unwrap_items(inputs)

        delete_prop(results, 'transaction_type')

        # for item in results:
        #     item.pop('transaction_type', None)

        return results

    def get_transaction_recon_fields(self, transaction_type):

        recon_fields = to_json_objects(
            TransactionTypeReconField.objects.filter(transaction_type__id=transaction_type["pk"]))
        results = unwrap_items(recon_fields)

        delete_prop(results, 'transaction_type')

        return results


    def add_user_code_to_relation(self, json_obj, transaction_type_action_key):

        relation_keys = {
            'instrument': [
                {
                    'key': 'accrued_currency',
                    'model': Currency
                },
                {
                    'key': 'daily_pricing_model',
                    'model': DailyPricingModel
                },
                {
                    'key': 'instrument_type',
                    'model': InstrumentType
                },
                {
                    'key': 'payment_size_detail',
                    'model': PaymentSizeDetail
                },
                {
                    'key': 'price_download_scheme',
                    'model': PriceDownloadScheme
                }, {
                    'key': 'pricing_currency',
                    'model': Currency
                }],
            'transaction': [
                {
                    'key': 'account_cash',
                    'model': Account
                },
                {
                    'key': 'account_interim',
                    'model': Account
                },
                {
                    'key': 'account_position',
                    'model': Account
                },
                {
                    'key': 'allocation_balance',
                    'model': Instrument
                },
                {
                    'key': 'allocation_pl',
                    'model': Instrument
                },
                {
                    'key': 'instrument',
                    'model': Instrument
                },
                {
                    'key': 'linked_instrument',
                    'model': Instrument
                },
                {
                    'key': 'portfolio',
                    'model': Portfolio
                },
                {
                    'key': 'responsible',
                    'model': Responsible
                },
                {
                    'key': 'counterparty',
                    'model': Counterparty
                },
                {
                    'key': 'settlement_currency',
                    'model': Currency
                },
                {
                    'key': 'strategy1_cash',
                    'model': Strategy1
                },
                {
                    'key': 'strategy1_position',
                    'model': Strategy1
                },
                {
                    'key': 'strategy2_cash',
                    'model': Strategy2
                },
                {
                    'key': 'strategy2_position',
                    'model': Strategy2
                },
                {
                    'key': 'strategy3_cash',
                    'model': Strategy3
                },
                {
                    'key': 'strategy3_position',
                    'model': Strategy3
                },
                {
                    'key': 'transaction_class',
                    'model': TransactionClass
                },
                {
                    'key': 'transaction_currency',
                    'model': Currency
                }
            ],
            'instrument_factor_schedule': [{
                'key': 'instrument',
                'model': Instrument
            }],
            'instrument_manual_pricing_formula': [{
                'key': 'instrument',
                'model': Instrument
            }, {
                'key': 'pricing_policy',
                'model': PricingPolicy
            }],
            'instrument_accrual_calculation_schedules': [
                {
                    'key': 'instrument',
                    'model': Instrument
                },
                {
                    'key': 'periodicity',
                    'model': Periodicity
                },
                {
                    'key': 'accrual_calculation_model',
                    'model': AccrualCalculationModel
                }],
            'instrument_event_schedule': [
                {
                    'key': 'instrument',
                    'model': Instrument
                },
                {
                    'key': 'periodicity',
                    'model': Periodicity
                },
                {
                    'key': 'notification_class',
                    'model': NotificationClass
                },
                {
                    'key': 'event_class',
                    'model': EventClass
                }]

        }

        # print('relation_keys %s' % relation_keys)

        if transaction_type_action_key not in relation_keys:
            return

        # print('transaction_type_action_key %s' % transaction_type_action_key)

        for attr in relation_keys[transaction_type_action_key]:

            if json_obj[attr['key']] is not None:

                obj = attr['model'].objects.get(pk=json_obj[attr['key']])

                if hasattr(obj, 'user_code'):
                    json_obj['___%s__user_code' % attr['key']] = obj.user_code

                if hasattr(obj, 'system_code'):
                    json_obj['___%s__system_code' % attr['key']] = obj.system_code

                if hasattr(obj, 'scheme_name'):
                    json_obj['___%s__scheme_name' % attr['key']] = obj.scheme_name

    def get_transaction_type_actions(self, transaction_type):
        results = []

        actions_order = TransactionTypeAction.objects.filter(transaction_type__id=transaction_type["pk"])

        actions_instrument = TransactionTypeActionInstrument.objects.filter(transaction_type__id=transaction_type["pk"])
        actions_transaction = TransactionTypeActionTransaction.objects.filter(
            transaction_type__id=transaction_type["pk"])

        actions_instrument_accrual_calculation_schedule = TransactionTypeActionInstrumentAccrualCalculationSchedules.objects.filter(
            transaction_type__id=transaction_type["pk"])

        actions_instrument_event_schedule = TransactionTypeActionInstrumentEventSchedule.objects.filter(
            transaction_type__id=transaction_type["pk"])

        actions_instrument_event_schedule_action = TransactionTypeActionInstrumentEventScheduleAction.objects.filter(
            transaction_type__id=transaction_type["pk"])

        actions_instrument_factor_schedule = TransactionTypeActionInstrumentFactorSchedule.objects.filter(
            transaction_type__id=transaction_type["pk"])

        actions_instrument_manual_pricing_formula = TransactionTypeActionInstrumentManualPricingFormula.objects.filter(
            transaction_type__id=transaction_type["pk"])

        for order in actions_order:

            result = None

            action = {
                "action_notes": order.action_notes,
                "order": order.order,
                "rebook_reaction": order.rebook_reaction,
                "instrument": None,
                "instrument_accrual_calculation_schedules": None,
                "instrument_event_schedule": None,
                "instrument_event_schedule_action": None,
                "instrument_factor_schedule": None,
                "instrument_manual_pricing_formula": None,
                "transaction": None
            }

            action_key = None

            for item in actions_instrument:
                if item.action_notes == order.action_notes:
                    action_key = 'instrument'
                    result = item

            for item in actions_transaction:
                if item.action_notes == order.action_notes:
                    action_key = 'transaction'
                    result = item

            for item in actions_instrument_accrual_calculation_schedule:
                if item.action_notes == order.action_notes:
                    action_key = 'instrument_accrual_calculation_schedules'
                    result = item

            for item in actions_instrument_event_schedule:
                if item.action_notes == order.action_notes:
                    action_key = 'instrument_event_schedule'
                    result = item

            for item in actions_instrument_event_schedule_action:
                if item.action_notes == order.action_notes:
                    action_key = 'instrument_event_schedule_action'
                    result = item

            for item in actions_instrument_factor_schedule:
                if item.action_notes == order.action_notes:
                    action_key = 'instrument_factor_schedule'
                    result = item

            for item in actions_instrument_manual_pricing_formula:
                if item.action_notes == order.action_notes:
                    action_key = 'instrument_manual_pricing_formula'
                    result = item

            if result:
                result_json = to_json_single(result)["fields"]

                for key in result_json:
                    if key.endswith('_input') and result_json[key]:
                        result_json[key] = TransactionTypeInput.objects.get(pk=result_json[key]).name

                    if key.endswith('_phantom') and result_json[key]:
                        result_json[key] = TransactionTypeAction.objects.get(pk=result_json[key]).order

                self.add_user_code_to_relation(result_json, action_key)

                action[action_key] = result_json

                results.append(action)

        return results

    def get_transaction_types(self):

        qs = TransactionType.objects.filter(master_user=self._master_user, is_deleted=False).exclude(user_code='-')

        qs = permission_filter(qs, self._member)

        transaction_types = to_json_objects(qs)
        results = []

        for transaction_type in transaction_types:
            result_item = transaction_type["fields"]

            result_item["pk"] = transaction_type["pk"]

            result_item.pop("master_user", None)
            result_item.pop("is_deleted", None)
            result_item.pop("instrument_types")

            if result_item["group"]:
                result_item["___group__user_code"] = TransactionTypeGroup.objects.get(
                    pk=result_item["group"]).user_code

                result_item.pop('group')

            result_item["is_valid_for_all_portfolios"] = True
            result_item["is_valid_for_all_instruments"] = True

            result_item["inputs"] = self.get_transaction_type_inputs(transaction_type)
            result_item["actions"] = self.get_transaction_type_actions(transaction_type)
            result_item["recon_fields"] = self.get_transaction_recon_fields(transaction_type)

            result_item["book_transaction_layout"] = TransactionType.objects.get(
                pk=result_item["pk"]).book_transaction_layout

            clear_none_attrs(result_item)
            clear_system_date_attrs(result_item)

            results.append(result_item)

        for transaction_type_model in TransactionType.objects.filter(master_user=self._master_user, is_deleted=False):
            if transaction_type_model.group:
                for transaction_type_json in results:
                    if transaction_type_json["pk"] == transaction_type_model.pk:
                        transaction_type_json["___group__user_code"] = transaction_type_model.group.user_code

        delete_prop(results, 'pk')

        result = {
            "entity": "transactions.transactiontype",
            "count": len(results),
            "content": results
        }

        return result

    def get_transaction_type_groups(self):
        items = to_json_objects(
            TransactionTypeGroup.objects.filter(master_user=self._master_user, is_deleted=False).exclude(user_code='-'))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            result_item.pop("is_deleted", None)

            clear_none_attrs(result_item)
            clear_system_date_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "transactions.transactiontypegroup",
            "count": len(results),
            "content": results
        }

        return result

    def get_account_types(self):

        qs = AccountType.objects.filter(master_user=self._master_user, is_deleted=False).exclude(user_code='-')
        qs = permission_filter(qs, self._member)

        account_types = to_json_objects(qs)
        results = []

        for account_type in account_types:
            result_item = account_type["fields"]

            result_item["pk"] = account_type["pk"]

            result_item.pop("master_user", None)
            result_item.pop("is_deleted", None)

            clear_none_attrs(result_item)
            clear_system_date_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "accounts.accounttype",
            "count": len(results),
            "content": results
        }

        return result

    def get_currency_pricing_policies(self, currency_pk):

        items = CurrencyPricingPolicy.objects.filter(currency=currency_pk)

        results = []

        for item in items:

            result_item = CurrencyPricingPolicySerializer(instance=item).data

            if item.pricing_policy:
                result_item['___pricing_policy__user_code'] = item.pricing_policy.user_code
            if item.pricing_scheme:
                result_item['___pricing_scheme__user_code'] = item.pricing_scheme.user_code

            result_item.pop("id", None)

            result_item.pop("pricing_policy", None)
            result_item.pop("pricing_policy_object", None)

            result_item.pop("pricing_scheme", None)
            result_item.pop("pricing_scheme_object", None)

            results.append(result_item)

        return results

    def get_currencies(self):
        currencies = to_json_objects(
            Currency.objects.filter(master_user=self._master_user, is_deleted=False).exclude(user_code='-'))
        results = []

        for currency in currencies:
            result_item = currency["fields"]

            result_item["pk"] = currency["pk"]

            result_item.pop("master_user", None)
            result_item.pop("is_deleted", None)

            result_item['pricing_policies'] = self.get_currency_pricing_policies(currency["pk"])

            clear_none_attrs(result_item)
            clear_system_date_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "currencies.currency",
            "count": len(results),
            "content": results
        }

        return result

    def get_pricing_policies(self):
        pricing_polices = to_json_objects(
            PricingPolicy.objects.filter(master_user=self._master_user).exclude(user_code='-'))
        results = []

        for pricing_policy in pricing_polices:
            result_item = pricing_policy["fields"]

            result_item["pk"] = pricing_policy["pk"]

            try:
                result_item["__default_instrument_pricing_scheme__user_code"] = InstrumentPricingScheme.objects.get(
                    pk=result_item["default_instrument_pricing_scheme"]).user_code
            except Exception:
                print("Cant find default instrument pricing scheme")

            try:
                result_item["__default_currency_pricing_scheme__user_code"] = CurrencyPricingScheme.objects.get(
                    pk=result_item["default_currency_pricing_scheme"]).user_code
            except Exception:
                print("Cant find default currency pricing scheme")

            result_item.pop("master_user", None)
            result_item.pop("default_currency_pricing_scheme", None)
            result_item.pop("default_instrument_pricing_scheme", None)

            clear_none_attrs(result_item)
            clear_system_date_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "instruments.pricingpolicy",
            "count": len(results),
            "content": results
        }

        return result

    def get_instrument_type_pricing_policies(self, instrument_type_pk):

        items = InstrumentTypePricingPolicy.objects.filter(instrument_type=instrument_type_pk)

        results = []

        for item in items:

            result_item = InstrumentTypePricingPolicySerializer(instance=item).data

            if item.pricing_policy:
                result_item['___pricing_policy__user_code'] = item.pricing_policy.user_code
            if item.pricing_scheme:
                result_item['___pricing_scheme__user_code'] = item.pricing_scheme.user_code

            result_item.pop("id", None)

            result_item.pop("pricing_policy", None)
            result_item.pop("pricing_policy_object", None)

            result_item.pop("pricing_scheme", None)
            result_item.pop("pricing_scheme_object", None)

            results.append(result_item)


        return results

    def get_instrument_types(self):

        qs = InstrumentType.objects.filter(master_user=self._master_user, is_deleted=False).exclude(user_code='-')
        qs = permission_filter(qs, self._member)

        instrument_types = to_json_objects(qs)
        results = []

        for instrument_type in instrument_types:
            result_item = instrument_type["fields"]

            result_item["pk"] = instrument_type["pk"]

            result_item.pop("master_user", None)
            result_item.pop("is_deleted", None)

            if result_item["one_off_event"]:
                result_item["___one_off_event__user_code"] = TransactionType.objects.get(
                    pk=result_item["one_off_event"]).user_code
                result_item.pop("one_off_event", None)

            if result_item["regular_event"]:
                result_item["___regular_event__user_code"] = TransactionType.objects.get(
                    pk=result_item["regular_event"]).user_code
                result_item.pop("regular_event", None)

            if result_item["factor_same"]:
                result_item["___factor_same__user_code"] = TransactionType.objects.get(
                    pk=result_item["factor_same"]).user_code
                result_item.pop("factor_same", None)

            if result_item["factor_up"]:
                result_item["___factor_up__user_code"] = TransactionType.objects.get(
                    pk=result_item["factor_up"]).user_code
                result_item.pop("factor_up", None)

            if result_item["factor_down"]:
                result_item["___factor_down__user_code"] = TransactionType.objects.get(
                    pk=result_item["factor_down"]).user_code
                result_item.pop("factor_down", None)

            result_item['pricing_policies'] = self.get_instrument_type_pricing_policies(instrument_type["pk"])

            clear_none_attrs(result_item)
            clear_system_date_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "instruments.instrumenttype",
            "count": len(results),
            "content": results
        }

        return result

    def get_pricing_automated_schedule(self):
        schedules = to_json_objects(
            PricingAutomatedSchedule.objects.filter(master_user=self._master_user))
        results = []

        for schedule in schedules:
            result_item = schedule["fields"]

            result_item["pk"] = schedule["pk"]

            result_item.pop("master_user", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.pricingautomatedschedule",
            "count": len(results),
            "content": results
        }

        return result

    def get_edit_layouts(self):
        results = to_json_objects(EditLayout.objects.filter(member=self._member))

        for edit_layout_model in EditLayout.objects.filter(member=self._member):
            if edit_layout_model.content_type:
                for edit_layout_json in results:
                    if edit_layout_model.pk == edit_layout_json['pk']:
                        edit_layout_json["fields"]["content_type"] = '%s.%s' % (
                            edit_layout_model.content_type.app_label, edit_layout_model.content_type.model)

        for list_layout_json in results:
            list_layout_json["fields"]["data"] = EditLayout.objects.get(pk=list_layout_json["pk"]).data

        results = unwrap_items(results)

        delete_prop(results, 'json_data')
        delete_prop(results, 'member')

        result = {
            "entity": "ui.editlayout",
            "count": len(results),
            "content": results
        }

        return result

    def get_dashboard_layouts(self):

        results = to_json_objects(DashboardLayout.objects.filter(member=self._member))

        for dashboard_layout_json in results:
            dashboard_layout_json["fields"]["data"] = DashboardLayout.objects.get(pk=dashboard_layout_json["pk"]).data

        results = unwrap_items(results)

        delete_prop(results, 'json_data')

        delete_prop(results, 'member')

        result = {
            "entity": "ui.dashboardlayout",
            "count": len(results),
            "content": results
        }

        return result

    def get_template_layouts(self):

        results = to_json_objects(TemplateLayout.objects.filter(member=self._member))

        for template_layout_json in results:
            template_layout_json["fields"]["data"] = TemplateLayout.objects.get(pk=template_layout_json["pk"]).data

        results = unwrap_items(results)

        delete_prop(results, 'json_data')

        delete_prop(results, 'member')

        result = {
            "entity": "ui.templatelayout",
            "count": len(results),
            "content": results
        }

        return result

    def get_context_menu_layouts(self):

        results = to_json_objects(ContextMenuLayout.objects.filter(member=self._member))

        for template_layout_json in results:
            template_layout_json["fields"]["data"] = ContextMenuLayout.objects.get(pk=template_layout_json["pk"]).data

        results = unwrap_items(results)

        delete_prop(results, 'json_data')

        delete_prop(results, 'member')

        result = {
            "entity": "ui.contextmenulayout",
            "count": len(results),
            "content": results
        }

        return result

    def get_list_layouts(self):

        content_types = ContentType.objects.exclude(app_label='reports')

        results = to_json_objects(ListLayout.objects.filter(member=self._member, content_type__in=content_types))

        for list_layout_model in ListLayout.objects.filter(member=self._member, content_type__in=content_types):

            if list_layout_model.content_type:
                for list_layout_json in results:

                    if list_layout_model.pk == list_layout_json['pk']:
                        list_layout_json["fields"]["content_type"] = '%s.%s' % (
                            list_layout_model.content_type.app_label, list_layout_model.content_type.model)

        for list_layout_json in results:
            list_layout_json["fields"]["data"] = ListLayout.objects.get(pk=list_layout_json["pk"]).data

        results = unwrap_items(results)

        delete_prop(results, 'json_data')

        delete_prop(results, 'member')

        result = {
            "entity": "ui.listlayout",
            "count": len(results),
            "content": results
        }

        return result

    def get_entity_tooltips(self):

        content_types = ContentType.objects.all()

        results = to_json_objects(EntityTooltip.objects.filter(master_user=self._master_user, content_type__in=content_types))

        for item_model in EntityTooltip.objects.filter(master_user=self._master_user, content_type__in=content_types):

            if item_model.content_type:
                for item_json in results:

                    if item_model.pk == item_json['pk']:
                        item_json["fields"]["content_type"] = '%s.%s' % (
                            item_model.content_type.app_label, item_model.content_type.model)

        results = unwrap_items(results)

        result = {
            "entity": "ui.entitytooltip",
            "count": len(results),
            "content": results
        }

        return result

    def get_color_palette_colors(self, color_palette):

        colors = to_json_objects(ColorPaletteColor.objects.filter(color_palette=color_palette["pk"]))

        results = unwrap_items(colors)

        delete_prop(results, 'color_palette')

        return results

    def get_color_palettes(self):

        color_palettes = to_json_objects(ColorPalette.objects.filter(master_user=self._master_user))
        results = []

        for color_palette in color_palettes:
            result_item = color_palette["fields"]

            result_item.pop("master_user", None)

            result_item["colors"] = self.get_color_palette_colors(color_palette)

            results.append(result_item)

        # results = unwrap_items(results)

        result = {
            "entity": "ui.colorpalette",
            "count": len(results),
            "content": results
        }

        return result

    def get_reference_table_rows(self, reference_table):

        rows = to_json_objects(ReferenceTableRow.objects.filter(reference_table=reference_table["pk"]))

        results = unwrap_items(rows)

        delete_prop(results, 'reference_table')

        return results

    def get_reference_tables(self):

        reference_tables = to_json_objects(
            ReferenceTable.objects.filter(master_user=self._master_user))

        results = []

        for reference_table in reference_tables:
            result_item = reference_table["fields"]
            result_item.pop("master_user", None)
            result_item["rows"] = self.get_reference_table_rows(reference_table)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "reference_tables.referencetable",
            "count": len(results),
            "content": results
        }

        return result

    def get_transaction_user_fields(self):

        user_fields = to_json_objects(
            TransactionUserFieldModel.objects.filter(master_user=self._master_user))

        results = []

        for user_field in user_fields:
            result_item = user_field["fields"]
            result_item.pop("master_user", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "ui.transactionuserfieldmodel",
            "count": len(results),
            "content": results
        }

        return result

    def get_instrument_user_fields(self):

        user_fields = to_json_objects(
            InstrumentUserFieldModel.objects.filter(master_user=self._master_user))

        results = []

        for user_field in user_fields:
            result_item = user_field["fields"]
            result_item.pop("master_user", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "ui.instrumentuserfieldmodel",
            "count": len(results),
            "content": results
        }

        return result

    def get_balance_report_custom_fields(self):

        custom_fields = to_json_objects(
            BalanceReportCustomField.objects.filter(master_user=self._master_user))

        results = []

        for custom_field in custom_fields:
            result_item = custom_field["fields"]
            result_item.pop("master_user", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "reports.balancereportcustomfield",
            "count": len(results),
            "content": results
        }

        return result

    def get_pl_report_custom_fields(self):

        custom_fields = to_json_objects(
            PLReportCustomField.objects.filter(master_user=self._master_user))

        results = []

        for custom_field in custom_fields:
            result_item = custom_field["fields"]
            result_item.pop("master_user", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "reports.plreportcustomfield",
            "count": len(results),
            "content": results
        }

        return result

    def get_transaction_report_custom_fields(self):

        custom_fields = to_json_objects(
            TransactionReportCustomField.objects.filter(master_user=self._master_user))

        results = []

        for custom_field in custom_fields:
            result_item = custom_field["fields"]
            result_item.pop("master_user", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "reports.transactionreportcustomfield",
            "count": len(results),
            "content": results
        }

        return result

    def get_report_layouts(self):

        content_types = ContentType.objects.filter(app_label='reports')

        results = to_json_objects(ListLayout.objects.filter(member=self._member, content_type__in=content_types))

        for list_layout_model in ListLayout.objects.filter(member=self._member, content_type__in=content_types):

            if list_layout_model.content_type:
                for list_layout_json in results:

                    if list_layout_model.pk == list_layout_json['pk']:
                        list_layout_json["fields"]["content_type"] = '%s.%s' % (
                            list_layout_model.content_type.app_label, list_layout_model.content_type.model)

        for list_layout_json in results:
            list_layout_json["fields"]["data"] = ListLayout.objects.get(pk=list_layout_json["pk"]).data

        results = unwrap_items(results)

        delete_prop(results, 'json_data')

        delete_prop(results, 'member')

        result = {
            "entity": "ui.reportlayout",
            "count": len(results),
            "content": results
        }

        return result

    def get_bookmarks_children(self, parent_bookmark):

        serializer = BookmarkSerializer([parent_bookmark], many=True,
                                        context={"member": self._member, "request": self._request})

        children = serializer.data[0]["children"]

        if len(children):
            for item in children:
                item_model = Bookmark.objects.get(member=self._member, pk=item["id"])

                item["data"] = item_model.data

                if item_model.list_layout:
                    item["___list_layout__name"] = item_model.list_layout.name
                    item["___list_layout__user_code"] = item_model.list_layout.user_code

                    item["___content_type"] = '%s.%s' % (
                        item_model.list_layout.content_type.app_label,
                        item_model.list_layout.content_type.model)

        delete_prop(children, 'member')
        delete_prop(children, 'id')
        delete_prop(children, 'list_layout')

        return children

    def get_bookmarks(self):

        results = to_json_objects(Bookmark.objects.filter(member=self._member, parent=None))

        for bookmark_model in Bookmark.objects.filter(member=self._member, parent=None):

            for bookmark_json in results:

                if bookmark_model.pk == bookmark_json['pk']:
                    bookmark_json["fields"]["children"] = self.get_bookmarks_children(bookmark_model)

                    bookmark_json["fields"]["data"] = bookmark_model.data
                    if bookmark_model.list_layout:
                        bookmark_json["fields"]["___layout__name"] = bookmark_model.list_layout.name
                        bookmark_json["fields"]["___layout__user_codef"] = bookmark_model.list_layout.user_code
                        bookmark_json["fields"]["___content_type"] = '%s.%s' % (
                            bookmark_model.list_layout.content_type.app_label,
                            bookmark_model.list_layout.content_type.model)

        results = unwrap_items(results)

        delete_prop(results, 'json_data')
        delete_prop(results, 'member')
        delete_prop(results, 'list_layout')

        result = {
            "entity": "ui.bookmark",
            "count": len(results),
            "content": results
        }

        return result

    def get_csv_fields(self, scheme):
        fields = to_json_objects(CsvField.objects.filter(scheme=scheme["pk"]))

        results = unwrap_items(fields)

        delete_prop(results, 'scheme')

        return results

    def get_entity_fields(self, scheme):
        fields = to_json_objects(EntityField.objects.filter(scheme=scheme["pk"]))

        results = unwrap_items(fields)

        for item in results:

            if item["dynamic_attribute_id"]:
                item["___dynamic_attribute_id__user_code"] = GenericAttributeType.objects.get(
                    pk=item["dynamic_attribute_id"]).user_code

        delete_prop(results, 'scheme')

        return results

    def get_csv_import_schemes(self):
        schemes = to_json_objects(CsvImportScheme.objects.filter(master_user=self._master_user))
        results = []

        # print('schemes %s' % len(schemes))
        # print('self._master_user %s' % self._master_user)

        for scheme in schemes:
            result_item = scheme["fields"]
            result_item["pk"] = scheme["pk"]

            result_item.pop("master_user", None)

            result_item["csv_fields"] = self.get_csv_fields(scheme)
            result_item["entity_fields"] = self.get_entity_fields(scheme)

            clear_none_attrs(result_item)

            results.append(result_item)

        for scheme_model in CsvImportScheme.objects.filter(master_user=self._master_user):

            if scheme_model.content_type:
                for scheme_json in results:

                    if scheme_model.pk == scheme_json['pk']:
                        scheme_json["content_type"] = '%s.%s' % (
                            scheme_model.content_type.app_label, scheme_model.content_type.model)

        delete_prop(results, 'pk')

        result = {
            "entity": "csv_import.csvimportscheme",
            "count": len(results),
            "content": results
        }

        return result

    def get_complex_import_scheme_actions(self, scheme):
        results = []

        actions_order = ComplexImportSchemeAction.objects.filter(complex_import_scheme__id=scheme["pk"])

        actions_csv_import = ComplexImportSchemeActionCsvImport.objects.filter(complex_import_scheme__id=scheme["pk"])
        actions_transactionimport = ComplexImportSchemeActionTransactionImport.objects.filter(
            complex_import_scheme__id=scheme["pk"])

        for order in actions_order:

            result = None

            action = {
                "action_notes": order.action_notes,
                "order": order.order,
                "skip": order.skip,
                "csv_import_scheme": None,
                "complex_transaction_import_scheme": None
            }

            action_key = None

            for item in actions_csv_import:
                if item.action_notes == order.action_notes:
                    action_key = 'csv_import_scheme'
                    result = item

            for item in actions_transactionimport:
                if item.action_notes == order.action_notes:
                    action_key = 'complex_transaction_import_scheme'
                    result = item

            if result:

                result_json = to_json_single(result)["fields"]

                if action_key == 'csv_import_scheme':

                    if result_json['csv_import_scheme']:

                        result_json['___csv_import_scheme__scheme_name'] = CsvImportScheme.objects.get(
                            pk=result_json['csv_import_scheme']).scheme_name

                    else:

                        result_json['___csv_import_scheme__scheme_name'] = '-'

                    result_json.pop("csv_import_scheme", None)

                if action_key == 'complex_transaction_import_scheme':

                    if result_json['complex_transaction_import_scheme']:

                        result_json[
                            '___complex_transaction_import_scheme__scheme_name'] = ComplexTransactionImportScheme.objects.get(
                            pk=result_json['complex_transaction_import_scheme']).scheme_name
                    else:
                        result_json[
                            '___complex_transaction_import_scheme__scheme_name'] = '-'

                    result_json.pop("complex_transaction_import_scheme", None)

                action[action_key] = result_json

            results.append(action)

        return results

    def get_complex_import_schemes(self):
        schemes = to_json_objects(ComplexImportScheme.objects.filter(master_user=self._master_user))
        results = []

        print('schemes %s' % len(schemes))
        print('self._master_user %s' % self._master_user)

        for scheme in schemes:
            result_item = scheme["fields"]
            result_item["pk"] = scheme["pk"]

            result_item.pop("master_user", None)

            result_item["actions"] = self.get_complex_import_scheme_actions(scheme)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "complex_import.compleximportscheme",
            "count": len(results),
            "content": results
        }

        return result

    def get_instrument_download_scheme_inputs(self, scheme):
        fields = to_json_objects(InstrumentDownloadSchemeInput.objects.filter(scheme=scheme["pk"]))

        results = unwrap_items(fields)

        delete_prop(results, 'scheme')

        return results

    def get_instrument_download_scheme_attributes(self, scheme):
        fields = to_json_objects(InstrumentDownloadSchemeAttribute.objects.filter(scheme=scheme["pk"]))

        results = unwrap_items(fields)

        delete_prop(results, 'scheme')

        return results

    def get_instrument_download_schemes(self):
        schemes = to_json_objects(InstrumentDownloadScheme.objects.filter(master_user=self._master_user))
        results = []

        for scheme in schemes:
            result_item = scheme["fields"]

            result_item.pop("master_user", None)

            result_item["inputs"] = self.get_instrument_download_scheme_inputs(scheme)
            # result_item["attributes"] = self.get_instrument_download_scheme_attributes(scheme)
            result_item["attributes"] = []

            result_item["___price_download_scheme__scheme_name"] = PriceDownloadScheme.objects.get(
                pk=result_item["price_download_scheme"]).scheme_name

            clear_none_attrs(result_item)

            results.append(result_item)

        result = {
            "entity": "integrations.instrumentdownloadscheme",
            "count": len(results),
            "content": results
        }

        return result

    def get_price_download_schemes(self):
        schemes = to_json_objects(PriceDownloadScheme.objects.filter(master_user=self._master_user))

        results = []

        for scheme in schemes:
            result_item = scheme["fields"]

            clear_none_attrs(result_item)

            result_item.pop("master_user", None)

            results.append(result_item)

        result = {
            "entity": "integrations.pricedownloadscheme",
            "count": len(results),
            "content": results
        }

        return result

    def get_complex_transaction_import_scheme_rule_fields(self, rule_scenario):

        fields = to_json_objects(ComplexTransactionImportSchemeField.objects.filter(rule_scenario=rule_scenario["pk"]))

        results = unwrap_items(fields)

        for item in results:
            item["___input__name"] = TransactionTypeInput.objects.get(pk=item["transaction_type_input"]).name

        delete_prop(results, 'transaction_type_input')
        delete_prop(results, 'rule_scenario')

        return results

    def get_complex_transaction_import_scheme_recon_fields(self, recon_scenario):

        fields = to_json_objects(ComplexTransactionImportSchemeReconField.objects.filter(recon_scenario=recon_scenario["pk"]))

        results = unwrap_items(fields)

        delete_prop(results, 'recon_scenario')

        return results

    def get_complex_transaction_import_scheme_recon_selector_values(self, recon_scenario):

        instance = ComplexTransactionImportSchemeReconScenario.objects.get(id=recon_scenario['pk'])

        result = []

        for item in instance.selector_values.all():
            result.append(item.value)

        return result

    def get_complex_transaction_import_scheme_rule_selector_values(self, rule_scenario):

        instance = ComplexTransactionImportSchemeRuleScenario.objects.get(id=rule_scenario['pk'])

        result = []

        for item in instance.selector_values.all():
            result.append(item.value)

        return result

    def get_complex_transaction_import_scheme_selector_values(self, scheme):

        fields = to_json_objects(ComplexTransactionImportSchemeSelectorValue.objects.filter(scheme=scheme["pk"]))

        results = unwrap_items(fields)

        delete_prop(results, 'scheme')

        return results

    def get_complex_transaction_import_scheme_calculated_inputs(self, scheme):

        fields = to_json_objects(ComplexTransactionImportSchemeCalculatedInput.objects.filter(scheme=scheme["pk"]))

        results = unwrap_items(fields)

        delete_prop(results, 'scheme')

        return results

    def get_complex_transaction_import_scheme_inputs(self, scheme):

        fields = to_json_objects(ComplexTransactionImportSchemeInput.objects.filter(scheme=scheme["pk"]))

        results = unwrap_items(fields)

        delete_prop(results, 'scheme')

        return results

    def get_complex_transaction_import_scheme_rule_scenarios(self, scheme):

        rules = to_json_objects(ComplexTransactionImportSchemeRuleScenario.objects.filter(scheme=scheme["pk"]))

        # results = unwrap_items(rules)

        results = []

        for rule in rules:
            result_item = rule["fields"]

            result_item["fields"] = self.get_complex_transaction_import_scheme_rule_fields(rule)
            result_item["selector_values"] =  self.get_complex_transaction_import_scheme_rule_selector_values(rule)

            result_item["___transaction_type__user_code"] = TransactionType.objects.get(
                pk=rule["fields"]["transaction_type"]).user_code
            result_item.pop("transaction_type", None)

            results.append(result_item)

        delete_prop(results, 'scheme')

        return results

    def get_complex_transaction_import_scheme_recon_scenarios(self, scheme):

        recon_scenarios = to_json_objects(ComplexTransactionImportSchemeReconScenario.objects.filter(scheme=scheme["pk"]))

        # results = unwrap_items(rules)

        results = []

        for recon_scenario in recon_scenarios:
            result_item = recon_scenario["fields"]

            result_item["fields"] = self.get_complex_transaction_import_scheme_recon_fields(recon_scenario)

            result_item["selector_values"] =  self.get_complex_transaction_import_scheme_recon_selector_values(recon_scenario)

            results.append(result_item)

        delete_prop(results, 'scheme')

        return results

    def get_complex_transaction_import_scheme(self):

        schemes = to_json_objects(ComplexTransactionImportScheme.objects.filter(master_user=self._master_user))

        results = []

        for scheme in schemes:
            result_item = scheme["fields"]

            clear_none_attrs(result_item)

            result_item.pop("master_user", None)

            result_item["calculated_inputs"] = self.get_complex_transaction_import_scheme_calculated_inputs(scheme)
            result_item["inputs"] = self.get_complex_transaction_import_scheme_inputs(scheme)
            result_item["selector_values"] = self.get_complex_transaction_import_scheme_selector_values(scheme)
            result_item["rule_scenarios"] = self.get_complex_transaction_import_scheme_rule_scenarios(scheme)
            result_item["recon_scenarios"] = self.get_complex_transaction_import_scheme_recon_scenarios(scheme)

            results.append(result_item)

        result = {
            "entity": "integrations.complextransactionimportscheme",
            "count": len(results),
            "content": results
        }

        return result

    def get_attribute_classifiers(self, attribute_type):

        result = []

        attr = GenericAttributeType.objects.get(pk=attribute_type["pk"])

        serializer = GenericAttributeTypeSerializer([attr], many=True, show_classifiers=True,
                                                    context={"member": self._member, "request": self._request})

        classifiers = serializer.data[0]["classifiers"]

        data = {"children": []}

        for item in classifiers:
            data["children"].append(dict(item))

        def delete_ids(item):
            if "pk" in item:
                del item["pk"]
            if "id" in item:
                del item["id"]

        recursive_callback(data, delete_ids)

        result = data["children"]

        return result

    def get_entity_attribute_types(self, app_label, model):

        content_type = ContentType.objects.get(app_label=app_label, model=model)

        items = to_json_objects(
            GenericAttributeType.objects.filter(master_user=self._master_user, content_type=content_type))

        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            clear_none_attrs(result_item)

            if result_item["value_type"] == 30:
                result_item["classifiers"] = self.get_attribute_classifiers(result_item)

            attr_model = GenericAttributeType.objects.get(pk=result_item["pk"])

            result_item["content_type"] = '%s.%s' % (attr_model.content_type.app_label, attr_model.content_type.model)

            results.append(result_item)

        delete_prop(results, 'pk')
        delete_prop(results, 'master_user')

        result = {
            "entity": "obj_attrs." + model + "attributetype",
            "count": len(results),
            "content": results
        }

        return result


    def get_instrument_pricing_schemes(self):

        schemes = InstrumentPricingScheme.objects.filter(master_user=self._master_user)
        results = []

        for scheme in schemes:

            result_item = InstrumentPricingSchemeSerializer(instance=scheme).data

            result_item.pop("id", None)
            result_item.pop("type_object", None)
            result_item.pop("master_user", None)
            if result_item['type_settings']:
                result_item['type_settings'].pop("instrument_pricing_scheme", None)

            results.append(result_item)

        result = {
            "entity": "pricing.instrumentpricingscheme",
            "count": len(results),
            "content": results
        }

        return result


    def get_currency_pricing_schemes(self):

        schemes = CurrencyPricingScheme.objects.filter(master_user=self._master_user)
        results = []

        for scheme in schemes:

            result_item = CurrencyPricingSchemeSerializer(instance=scheme).data

            result_item.pop("id", None)
            result_item.pop("type_object", None)
            result_item.pop("master_user", None)
            if result_item['type_settings']:
                result_item['type_settings'].pop("currency_pricing_scheme", None)

            results.append(result_item)

        result = {
            "entity": "pricing.currencypricingscheme",
            "count": len(results),
            "content": results
        }

        return result

    def get_pricing_procedures(self):

        schemes = to_json_objects(PricingProcedure.objects.filter(master_user=self._master_user))
        results = []

        for scheme in schemes:
            result_item = scheme["fields"]

            result_item.pop("master_user", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "pricing.pricingprocedure",
            "count": len(results),
            "content": results
        }

        return result

    def get_schedules(self):

        schedules = Schedule.objects.filter(master_user=self._master_user)
        results = []

        for schedule in schedules:

            result_item = ScheduleSerializer(instance=schedule).data

            result_item.pop("id", None)
            result_item.pop("master_user", None)

            # procedures_user_codes = []
            #
            # for procedure in schedule.pricing_procedures.all():
            #     procedures_user_codes.append(procedure.user_code)
            #
            # result_item['pricing_procedures__user_codes'] = procedures_user_codes
            # result_item["pricing_procedures"] = []

            results.append(result_item)

        result = {
            "entity": "schedules.pricingschedule",
            "count": len(results),
            "content": results
        }

        return result


class MappingExportViewSet(AbstractModelViewSet):

    def list(self, request):
        self._master_user = request.user.master_user
        self._member = request.user.member

        self.access_table = get_access_table(self._member)

        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="mapping-%s.json"' % str(datetime.now().date())

        configuration = self.createConfiguration()

        response.write(json.dumps(configuration))

        return response

    def createConfiguration(self):
        configuration = {}
        configuration["head"] = {}
        configuration["head"]["date"] = str(datetime.now().date())
        configuration["body"] = []

        can_export = check_configuration_section(self.access_table)

        print('can_export %s' % can_export)

        if can_export:

            if self.access_table['integrations.mappingtable']:

                portfolio_mapping = self.get_portfolio_mapping()
                currency_mapping = self.get_currency_mapping()
                instrument_type_mapping = self.get_instrument_type_mapping()
                account_mapping = self.get_account_mapping()
                account_type_mapping = self.get_account_type_mapping()
                instrument_mapping = self.get_instrument_mapping()
                counterparty_mapping = self.get_counterparty_mapping()
                responsible_mapping = self.get_responsible_mapping()
                strategy1_mapping = self.get_strategy1_mapping()

                pricing_policy_mapping = self.get_pricing_policy_mapping()
                periodicity_mapping = self.get_periodicity_mapping()
                daily_pricing_model_mapping = self.get_daily_pricing_model_mapping()
                pricing_condition_mapping = self.get_pricing_condition_mapping()
                payment_size_detail_mapping = self.get_payment_size_detail_mapping()
                accrual_calculation_model_mapping = self.get_accrual_calculation_model_mapping()
                price_download_scheme_mapping = self.get_price_download_scheme_mapping()

                configuration["body"].append(account_type_mapping)
                configuration["body"].append(portfolio_mapping)
                configuration["body"].append(currency_mapping)
                configuration["body"].append(instrument_type_mapping)
                configuration["body"].append(account_mapping)
                configuration["body"].append(instrument_mapping)
                configuration["body"].append(counterparty_mapping)
                configuration["body"].append(responsible_mapping)
                configuration["body"].append(strategy1_mapping)

                configuration["body"].append(pricing_policy_mapping)
                configuration["body"].append(periodicity_mapping)
                configuration["body"].append(daily_pricing_model_mapping)
                configuration["body"].append(payment_size_detail_mapping)
                configuration["body"].append(accrual_calculation_model_mapping)
                configuration["body"].append(price_download_scheme_mapping)

        return configuration

    def get_portfolio_mapping(self):
        items = to_json_objects(
            PortfolioMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___user_code"] = Portfolio.objects.get(pk=result_item["content_object"]).user_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.portfoliomapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_currency_mapping(self):
        items = to_json_objects(
            CurrencyMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___user_code"] = Currency.objects.get(pk=result_item["content_object"]).user_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.currencymapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_instrument_type_mapping(self):
        items = to_json_objects(
            InstrumentTypeMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___user_code"] = InstrumentType.objects.get(pk=result_item["content_object"]).user_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.instrumenttypemapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_account_mapping(self):
        items = to_json_objects(
            AccountMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___user_code"] = Account.objects.get(pk=result_item["content_object"]).user_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.accountmapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_account_type_mapping(self):
        items = to_json_objects(
            AccountTypeMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___user_code"] = AccountType.objects.get(pk=result_item["content_object"]).user_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.accounttypemapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_instrument_mapping(self):
        items = to_json_objects(
            InstrumentMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___user_code"] = Instrument.objects.get(pk=result_item["content_object"]).user_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.instrumentmapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_counterparty_mapping(self):
        items = to_json_objects(
            CounterpartyMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___user_code"] = Counterparty.objects.get(pk=result_item["content_object"]).user_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.counterpartymapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_responsible_mapping(self):
        items = to_json_objects(
            ResponsibleMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___user_code"] = Responsible.objects.get(pk=result_item["content_object"]).user_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.responsiblemapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_strategy1_mapping(self):
        items = to_json_objects(
            Strategy1Mapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___user_code"] = Strategy1.objects.get(pk=result_item["content_object"]).user_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.strategy1mapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_strategy2_mapping(self):
        items = to_json_objects(
            Strategy2Mapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___user_code"] = Strategy2.objects.get(pk=result_item["content_object"]).user_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.strategy2mapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_strategy3_mapping(self):
        items = to_json_objects(
            Strategy3Mapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___user_code"] = Strategy3.objects.get(pk=result_item["content_object"]).user_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.strategy3mapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_periodicity_mapping(self):
        items = to_json_objects(
            PeriodicityMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___system_code"] = Periodicity.objects.get(pk=result_item["content_object"]).system_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.periodicitymapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_pricing_policy_mapping(self):
        items = to_json_objects(
            PricingPolicyMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___user_code"] = PricingPolicy.objects.get(pk=result_item["content_object"]).user_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.pricingpolicymapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_daily_pricing_model_mapping(self):
        items = to_json_objects(
            DailyPricingModelMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___system_code"] = DailyPricingModel.objects.get(pk=result_item["content_object"]).system_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.dailypricingmodelmapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_pricing_condition_mapping(self):

        items = to_json_objects(
            PricingConditionMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___system_code"] = PricingCondition.objects.get(pk=result_item["content_object"]).system_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.pricingconditionmapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_payment_size_detail_mapping(self):
        items = to_json_objects(
            PaymentSizeDetailMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___system_code"] = PaymentSizeDetail.objects.get(pk=result_item["content_object"]).system_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.paymentsizedetailmapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_accrual_calculation_model_mapping(self):
        items = to_json_objects(
            AccrualCalculationModelMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___system_code"] = AccrualCalculationModel.objects.get(
                pk=result_item["content_object"]).system_code

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.accrualcalculationmodelmapping",
            "count": len(results),
            "content": results
        }

        return result

    def get_price_download_scheme_mapping(self):
        items = to_json_objects(
            PriceDownloadSchemeMapping.objects.filter(master_user=self._master_user))
        results = []

        for item in items:
            result_item = item["fields"]

            result_item["pk"] = item["pk"]

            result_item.pop("master_user", None)
            # result_item.pop("provider", None)

            result_item["___scheme_name"] = PriceDownloadScheme.objects.get(
                pk=result_item["content_object"]).scheme_name

            result_item.pop("content_object", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "integrations.pricedownloadschememapping",
            "count": len(results),
            "content": results
        }

        return result


class ConfigurationDuplicateCheckViewSet(AbstractModelViewSet):

    def create(self, request, *args, **kwargs):

        if 'file' not in request.data:
            raise ValidationError('File is not set')

        if not request.data['file'].name.endswith('.fcfg'):
            raise ValidationError('File is not fcfg format')

        file_content = json.loads(request.data['file'].read().decode('utf-8-sig'))
        master_user = self.request.user.master_user
        member = self.request.user.member

        head = file_content['head']
        sections = file_content['body']

        results = []

        print(head['date'])

        configuration_section = None

        for section in sections:
            if section['section_name'] == 'configuration':
                configuration_section = section

        if configuration_section:
            for entity in configuration_section['items']:

                result_item = {
                    'entity': entity['entity'],
                    'content': []
                }

                pieces = entity['entity'].split('.')
                app_label = pieces[0]
                model_name = pieces[1]

                if model_name == 'reportlayout':
                    model_name = 'listlayout'

                try:

                    model = apps.get_model(app_label=app_label, model_name=model_name)

                except (LookupError, KeyError):
                    continue

                for item in entity['content']:

                    if entity['entity'] in ['ui.bookmark', 'ui.listlayout', 'ui.reportlayout', 'ui.editlayout',
                                            'ui.dashboardlayout', 'ui.templatelayout', 'ui.contextmenulayout']:

                        if 'user_code' in item:

                            if model.objects.filter(user_code=item['user_code'], member=member).exists():
                                result_item['content'].append({'user_code': item['user_code'], 'is_duplicate': True})
                            else:
                                result_item['content'].append({'user_code': item['user_code'], 'is_duplicate': False})

                        else:

                            # DEPRECATED LOGIC
                            # BEFORE 04.2020 LAYOUT ENTITIES HAD ONLY NAME PROPERTY
                            # SOME OBSOLETE CONFIGURATION FILES CAN HAVE ONLY NAME PROPERTY
                            # IT MEANS user_code WILL BE ALWAYS '' for them

                            if 'name' in item:

                                if model.objects.filter(name=item['name'], member=member).exists():
                                    result_item['content'].append({'name': item['name'], 'is_duplicate': True})
                                else:
                                    result_item['content'].append({'name': item['name'], 'is_duplicate': False})

                    else:

                        # print('item %s' % item)

                        if 'scheme_name' in item:

                            if model.objects.filter(scheme_name=item['scheme_name'], master_user=master_user).exists():
                                result_item['content'].append({'scheme_name': item['scheme_name'], 'is_duplicate': True})
                            else:
                                result_item['content'].append({'scheme_name': item['scheme_name'], 'is_duplicate': False})

                        elif 'user_code' in item:

                            if model.objects.filter(user_code=item['user_code'], master_user=master_user).exists():
                                result_item['content'].append({'user_code': item['user_code'], 'is_duplicate': True})
                            else:
                                result_item['content'].append({'user_code': item['user_code'], 'is_duplicate': False})

                        elif 'name' in item:

                            if entity['entity'] in ['ui.transactionuserfieldmodel', 'ui.instrumentuserfieldmodel']:

                                if model.objects.filter(key=item['key'], master_user=master_user).exists():
                                    result_item['content'].append({'name': item['name'], 'is_duplicate': True})

                            else:

                                if model.objects.filter(name=item['name'], master_user=master_user).exists():
                                    result_item['content'].append({'name': item['name'], 'is_duplicate': True})
                                else:
                                    result_item['content'].append({'name': item['name'], 'is_duplicate': False})

                results.append(result_item)

        return Response({
            "results": results,
        }, status=status.HTTP_202_ACCEPTED)
