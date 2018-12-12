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
from poms.common.utils import delete_keys_from_dict, recursive_callback
from poms.common.views import AbstractModelViewSet
from poms.counterparties.models import Counterparty, Responsible
from poms.csv_import.models import Scheme, CsvField, EntityField
from poms.currencies.models import Currency
from poms.instruments.models import InstrumentType, Instrument, Periodicity, DailyPricingModel, PaymentSizeDetail, \
    AccrualCalculationModel, PricingPolicy
from poms.integrations.models import InstrumentDownloadScheme, InstrumentDownloadSchemeInput, \
    InstrumentDownloadSchemeAttribute, PriceDownloadScheme, ComplexTransactionImportScheme, \
    ComplexTransactionImportSchemeInput, ComplexTransactionImportSchemeRule, ComplexTransactionImportSchemeField, \
    PricingAutomatedSchedule, PortfolioMapping, CurrencyMapping, InstrumentTypeMapping, AccountMapping, \
    InstrumentMapping, CounterpartyMapping, ResponsibleMapping, Strategy1Mapping, Strategy2Mapping, Strategy3Mapping, \
    PeriodicityMapping, DailyPricingModelMapping, PaymentSizeDetailMapping, AccrualCalculationModelMapping
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier
from poms.obj_attrs.serializers import GenericClassifierViewSerializer, GenericClassifierNodeSerializer, \
    GenericAttributeTypeSerializer
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.tags.utils import get_tag_prefetch
from poms.transactions.models import TransactionType, TransactionTypeInput, TransactionTypeAction, \
    TransactionTypeActionInstrument, TransactionTypeActionTransaction, TransactionTypeGroup, \
    TransactionTypeActionInstrumentAccrualCalculationSchedules, TransactionTypeActionInstrumentEventSchedule, \
    TransactionTypeActionInstrumentEventScheduleAction, TransactionTypeActionInstrumentFactorSchedule, \
    TransactionTypeActionInstrumentManualPricingFormula, NotificationClass, EventClass, TransactionClass

from django.core import serializers
import json

from poms.transactions.serializers import TransactionTypeSerializer
from poms.ui.models import EditLayout, ListLayout, Bookmark

from django.forms.models import model_to_dict


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


def unwrap_items(items):
    result = []

    for item in items:
        result.append(item["fields"])

    return result


class ConfigurationExportViewSet(AbstractModelViewSet):

    def list(self, request):

        self._master_user = request.user.master_user
        self._member = request.user.member
        self._request = request

        response = HttpResponse(content_type='application/json')
        # response['Content-Disposition'] = 'attachment; filename="data-%s.json"' % str(datetime.now().date())

        configuration = self.createConfiguration()

        response.write(json.dumps(configuration))

        return response

    def createConfiguration(self):
        configuration = {}
        configuration["head"] = {}
        configuration["head"]["date"] = str(datetime.now().date())
        configuration["body"] = []

        transaction_types = self.get_transaction_types()
        edit_layouts = self.get_edit_layouts()
        list_layouts = self.get_list_layouts()
        report_layouts = self.get_report_layouts()
        csv_import_schemes = self.get_csv_import_schemes()
        instrument_download_schemes = self.get_instrument_download_schemes()
        price_download_schemes = self.get_price_download_schemes()
        complex_transaction_import_scheme = self.get_complex_transaction_import_scheme()
        account_types = self.get_account_types()
        instrument_types = self.get_instrument_types()
        pricing_automated_schedule = self.get_pricing_automated_schedule()

        portfolio_attribute_types = self.get_entity_attribute_types('portfolios', 'portfolio')
        account_attribute_types = self.get_entity_attribute_types('accounts', 'account')
        account_type_attribute_types = self.get_entity_attribute_types('accounts', 'accounttype')

        responsible_attribute_types = self.get_entity_attribute_types('counterparties', 'responsible')
        counterparty_attribute_types = self.get_entity_attribute_types('counterparties', 'counterparty')

        instrument_attribute_types = self.get_entity_attribute_types('instruments', 'instrument')
        instrument_type_attribute_types = self.get_entity_attribute_types('instruments', 'instrumenttype')

        configuration["body"].append(transaction_types)
        configuration["body"].append(edit_layouts)
        configuration["body"].append(list_layouts)
        configuration["body"].append(report_layouts)
        configuration["body"].append(csv_import_schemes)
        configuration["body"].append(price_download_schemes)
        configuration["body"].append(instrument_download_schemes)
        configuration["body"].append(complex_transaction_import_scheme)
        configuration["body"].append(account_types)
        configuration["body"].append(instrument_types)
        configuration["body"].append(pricing_automated_schedule)

        configuration["body"].append(portfolio_attribute_types)
        configuration["body"].append(account_attribute_types)
        configuration["body"].append(account_type_attribute_types)
        configuration["body"].append(responsible_attribute_types)
        configuration["body"].append(counterparty_attribute_types)
        configuration["body"].append(instrument_attribute_types)
        configuration["body"].append(instrument_type_attribute_types)

        return configuration

    def get_transaction_type_inputs(self, transaction_type):

        inputs = to_json_objects(
            TransactionTypeInput.objects.filter(transaction_type__id=transaction_type["pk"]))

        for input_model in TransactionTypeInput.objects.filter(transaction_type__id=transaction_type["pk"]):

            if input_model.content_type:
                for input_json in inputs:

                    if input_model.pk == input_json['pk']:

                        input_json["fields"]["content_type"] = '%s.%s' % (
                            input_model.content_type.app_label, input_model.content_type.model)

                        if input_model.value_type == 100:

                            if input_json["fields"][input_model.content_type.model]:
                                model = apps.get_model(app_label=input_model.content_type.app_label,
                                                       model_name=input_model.content_type.model)

                                input_json["fields"][
                                    '___%s__user_code' % input_model.content_type.model] = model.objects.get(
                                    pk=getattr(input_model, input_model.content_type.model).pk).user_code

        results = unwrap_items(inputs)

        delete_prop(results, 'transaction_type')

        # for item in results:
        #     item.pop('transaction_type', None)

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
                    'model': Response
                }, {
                    'key': 'settlement_currency',
                    'model': Currency
                }, {
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

        if not hasattr(relation_keys, transaction_type_action_key):
            pass

        for attr in relation_keys[transaction_type_action_key]:

            if json_obj[attr['key']] is not None:

                obj = getattr(attr, 'model').objects.get(pk=json_obj[attr['key']])

                if hasattr(obj, 'user_code'):
                    json_obj['___%s__user_code' % attr['key']] = obj.user_code

                if hasattr(obj, 'system_code'):
                    json_obj['___%s__system_code' % attr['key']] = obj.system_code

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

                self.add_user_code_to_relation(result_json, action_key)

                action[action_key] = result_json

                results.append(action)

        return results

    def get_transaction_types(self):
        transaction_types = to_json_objects(
            TransactionType.objects.filter(master_user=self._master_user, is_deleted=False))
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

            result_item["is_valid_for_all_portfolios"] = True
            result_item["is_valid_for_all_instruments"] = True

            result_item["inputs"] = self.get_transaction_type_inputs(transaction_type)
            result_item["actions"] = self.get_transaction_type_actions(transaction_type)

            result_item["book_transaction_layout"] = TransactionType.objects.get(
                pk=result_item["pk"]).book_transaction_layout

            clear_none_attrs(result_item)

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

    def get_account_types(self):
        account_types = to_json_objects(
            AccountType.objects.filter(master_user=self._master_user, is_deleted=False))
        results = []

        for account_type in account_types:
            result_item = account_type["fields"]

            result_item["pk"] = account_type["pk"]

            result_item.pop("master_user", None)
            result_item.pop("is_deleted", None)

            clear_none_attrs(result_item)

            results.append(result_item)

        delete_prop(results, 'pk')

        result = {
            "entity": "accounts.accounttype",
            "count": len(results),
            "content": results
        }

        return result

    def get_instrument_types(self):
        instrument_types = to_json_objects(
            InstrumentType.objects.filter(master_user=self._master_user, is_deleted=False))
        results = []

        for instrument_type in instrument_types:
            result_item = instrument_type["fields"]

            result_item["pk"] = instrument_type["pk"]

            result_item.pop("master_user", None)
            result_item.pop("is_deleted", None)

            if result_item["one_off_event"]:
                result_item["___one_off_event__user_code"] = TransactionType.objects.get(
                    pk=result_item["one_off_event"]).user_code

            if result_item["regular_event"]:
                result_item["___regular_event__user_code"] = TransactionType.objects.get(
                    pk=result_item["regular_event"]).user_code

            if result_item["factor_same"]:
                result_item["___factor_same__user_code"] = TransactionType.objects.get(
                    pk=result_item["factor_same"]).user_code

            if result_item["factor_up"]:
                result_item["___factor_up__user_code"] = TransactionType.objects.get(
                    pk=result_item["factor_up"]).user_code

            if result_item["factor_down"]:
                result_item["___factor_down__user_code"] = TransactionType.objects.get(
                    pk=result_item["factor_down"]).user_code

            clear_none_attrs(result_item)

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
            "entity": "import.pricingautomatedschedule",
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

    def get_csv_fields(self, scheme):
        fields = to_json_objects(CsvField.objects.filter(scheme=scheme["pk"]))

        results = unwrap_items(fields)

        delete_prop(results, 'scheme')

        return results

    def get_entity_fields(self, scheme):
        fields = to_json_objects(EntityField.objects.filter(scheme=scheme["pk"]))

        results = unwrap_items(fields)

        delete_prop(results, 'scheme')

        return results

    def get_csv_import_schemes(self):
        schemes = to_json_objects(Scheme.objects.filter(master_user=self._master_user))
        results = []

        for scheme in schemes:
            result_item = scheme["fields"]
            result_item["pk"] = scheme["pk"]

            result_item.pop("master_user", None)

            result_item["csv_fields"] = self.get_csv_fields(scheme)
            result_item["entity_fields"] = self.get_entity_fields(scheme)

            clear_none_attrs(result_item)

            results.append(result_item)

        for scheme_model in Scheme.objects.filter(master_user=self._master_user):

            if scheme_model.content_type:
                for scheme_json in results:

                    if scheme_model.pk == scheme_json['pk']:
                        scheme_json["content_type"] = '%s.%s' % (
                            scheme_model.content_type.app_label, scheme_model.content_type.model)

        delete_prop(results, 'pk')

        result = {
            "entity": "csv_import.scheme",
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

    def get_complex_transaction_import_scheme_rule_fields(self, rule):

        fields = to_json_objects(ComplexTransactionImportSchemeField.objects.filter(rule=rule["pk"]))

        results = unwrap_items(fields)

        for item in results:
            item["___input__name"] = TransactionTypeInput.objects.get(pk=item["transaction_type_input"]).name

        delete_prop(results, 'rule')

        return results

    def get_complex_transaction_import_scheme_inputs(self, scheme):

        fields = to_json_objects(ComplexTransactionImportSchemeInput.objects.filter(scheme=scheme["pk"]))

        results = unwrap_items(fields)

        delete_prop(results, 'scheme')

        return results

    def get_complex_transaction_import_scheme_rules(self, scheme):

        rules = to_json_objects(ComplexTransactionImportSchemeRule.objects.filter(scheme=scheme["pk"]))

        # results = unwrap_items(rules)

        results = []

        for rule in rules:
            result_item = rule["fields"]

            rule["fields"]["fields"] = self.get_complex_transaction_import_scheme_rule_fields(rule)

            rule["fields"]["___transaction_type__user_code"] = TransactionType.objects.get(
                pk=rule["fields"]["transaction_type"]).user_code

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

            result_item["inputs"] = self.get_complex_transaction_import_scheme_inputs(scheme)
            result_item["rules"] = self.get_complex_transaction_import_scheme_rules(scheme)

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


class MappingExportViewSet(AbstractModelViewSet):

    def list(self, request):
        self._master_user = request.user.master_user
        self._member = request.user.member

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

        portfolio_mapping = self.get_portfolio_mapping()
        currency_mapping = self.get_currency_mapping()
        instrument_type_mapping = self.get_instrument_type_mapping()
        account_mapping = self.get_account_mapping()
        instrument_mapping = self.get_instrument_mapping()
        counterparty_mapping = self.get_counterparty_mapping()
        responsible_mapping = self.get_responsible_mapping()
        strategy1_mapping = self.get_strategy1_mapping()

        periodicity_mapping = self.get_periodicity_mapping()
        daily_pricing_model_mapping = self.get_daily_pricing_model_mapping()
        payment_size_detail_mapping = self.get_payment_size_detail_mapping()
        accrual_calculation_model_mapping = self.get_accrual_calculation_model_mapping()

        configuration["body"].append(portfolio_mapping)
        configuration["body"].append(currency_mapping)
        configuration["body"].append(instrument_type_mapping)
        configuration["body"].append(account_mapping)
        configuration["body"].append(instrument_mapping)
        configuration["body"].append(counterparty_mapping)
        configuration["body"].append(responsible_mapping)
        configuration["body"].append(strategy1_mapping)

        configuration["body"].append(periodicity_mapping)
        configuration["body"].append(daily_pricing_model_mapping)
        configuration["body"].append(payment_size_detail_mapping)
        configuration["body"].append(accrual_calculation_model_mapping)

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
