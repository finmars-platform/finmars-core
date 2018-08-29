import csv

from django.db.models import Prefetch
from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
from django.utils.datetime_safe import datetime
from rest_framework.renderers import JSONRenderer

from poms.common.views import AbstractModelViewSet
from poms.csv_import.models import Scheme, CsvField, EntityField
from poms.instruments.models import InstrumentType
from poms.integrations.models import InstrumentDownloadScheme, InstrumentDownloadSchemeInput, \
    InstrumentDownloadSchemeAttribute, PriceDownloadScheme, ComplexTransactionImportScheme, \
    ComplexTransactionImportSchemeInput, ComplexTransactionImportSchemeRule, ComplexTransactionImportSchemeField
from poms.tags.utils import get_tag_prefetch
from poms.transactions.models import TransactionType, TransactionTypeInput, TransactionTypeAction, \
    TransactionTypeActionInstrument, TransactionTypeActionTransaction, TransactionTypeGroup

from django.core import serializers
import json

from poms.transactions.serializers import TransactionTypeSerializer
from poms.ui.models import EditLayout, ListLayout, Bookmark


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

        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="data-%s.json"' % str(datetime.now().date())

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
        csv_import_schemes = self.get_csv_import_schemes()
        instrument_download_schemes = self.get_instrument_download_schemes()
        price_download_schemes = self.get_price_download_schemes()
        complex_transaction_import_scheme = self.get_complex_transaction_import_scheme()

        configuration["body"].append(transaction_types)
        configuration["body"].append(edit_layouts)
        configuration["body"].append(list_layouts)
        configuration["body"].append(csv_import_schemes)
        configuration["body"].append(price_download_schemes)
        configuration["body"].append(instrument_download_schemes)
        configuration["body"].append(complex_transaction_import_scheme)

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

        results = unwrap_items(inputs)

        for item in results:

            if item.value_type == 100:
                item.pop("account")
                item.pop("counterparty")
                item.pop("currency")
                item.pop("instrument")
                item.pop("instrument_type")
                item.pop("portfolio")
                item.pop("responsible")
                item.pop("strategy1")
                item.pop("strategy2")
                item.pop("strategy3")
                item.pop("price_download_scheme")
                item.pop("payment_size_detail")
                item.pop("daily_pricing_model")

        delete_prop(results, 'transaction_type')

        # for item in results:
        #     item.pop('transaction_type', None)

        return results

    def get_transaction_type_actions(self, transaction_type):
        results = []

        actions_order = TransactionTypeAction.objects.filter(transaction_type__id=transaction_type["pk"])
        actions_instrument = TransactionTypeActionInstrument.objects.filter(transaction_type__id=transaction_type["pk"])
        actions_transaction = TransactionTypeActionTransaction.objects.filter(
            transaction_type__id=transaction_type["pk"])

        for order in actions_order:

            result = None

            action = {
                "action_notes": order.action_notes,
                "order": order.order,
                "instrument": None,
                "transaction": None
            }

            for instrument in actions_instrument:
                if instrument.action_notes == order.action_notes:
                    result = instrument

            for transaction in actions_transaction:
                if transaction.action_notes == order.action_notes:
                    result = transaction

            result_json = to_json_single(result)["fields"]

            for key in result_json:
                if key.endswith('_input') and result_json[key]:
                    result_json[key] = TransactionTypeInput.objects.get(pk=result_json[key]).name

            if hasattr(result, "transaction_class"):
                action["transaction"] = result_json
            else:
                action["instrument"] = result_json

            results.append(action)

        return results

    def get_transaction_types_groups(self):

        transaction_types_groups = to_json_objects(
            TransactionTypeGroup.objects.filter(master_user=self._master_user, is_deleted=False))

        results = []

        for transaction_type_group in transaction_types_groups:
            result_item = transaction_type_group["fields"]

            result_item.pop("master_user", None)
            result_item.pop("is_deleted", None)

            results.append(result_item)

        return {
            "entity": "transactions.transactiontypegroup",
            "count": len(results),
            "content": results,
        }

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
            result_item.pop("portfolios")

            result_item["inputs"] = self.get_transaction_type_inputs(transaction_type)
            result_item["actions"] = self.get_transaction_type_actions(transaction_type)

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
            "content": results,
            "dependencies": []
        }

        groups_dependencies = self.get_transaction_types_groups()

        if groups_dependencies["count"]:
            result["dependencies"].append(groups_dependencies)

        return result

    def get_edit_layouts(self):
        results = to_json_objects(EditLayout.objects.filter(member=self._member))

        for edit_layout_model in EditLayout.objects.filter(member=self._member):
            if edit_layout_model.content_type:
                for edit_layout_json in results:
                    if edit_layout_model.pk == edit_layout_json['pk']:
                        edit_layout_json["fields"]["content_type"] = '%s.%s' % (
                            edit_layout_model.content_type.app_label, edit_layout_model.content_type.model)

        results = unwrap_items(results)

        for edit_layout_json in results:
            edit_layout_json["data"] = json.dumps(edit_layout_json["json_data"])

        delete_prop(results, 'json_data')
        delete_prop(results, 'member')

        result = {
            "entity": "ui.editlayout",
            "count": len(results),
            "content": results
        }

        return result

    def get_list_layouts(self):
        results = to_json_objects(ListLayout.objects.filter(member=self._member))

        for list_layout_model in ListLayout.objects.filter(member=self._member):

            if list_layout_model.content_type:
                for list_layout_json in results:

                    if list_layout_model.pk == list_layout_json['pk']:
                        list_layout_json["fields"]["content_type"] = '%s.%s' % (
                            list_layout_model.content_type.app_label, list_layout_model.content_type.model)

        results = unwrap_items(results)

        for list_layout_json in results:
            list_layout_json["data"] = json.dumps(list_layout_json["json_data"])

        delete_prop(results, 'json_data')

        delete_prop(results, 'member')

        result = {
            "entity": "ui.listlayout",
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
            "content": results,
            "dependencies": []
        }

        price_download_scheme_dependencies = self.get_price_download_schemes()

        if price_download_scheme_dependencies["count"]:
            result["dependencies"].append(price_download_scheme_dependencies)

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
            "content": results,
            "dependencies": []
        }

        transaction_type_dependencies = self.get_transaction_types()

        if transaction_type_dependencies["count"]:
            result["dependencies"].append(transaction_type_dependencies)

        return result
