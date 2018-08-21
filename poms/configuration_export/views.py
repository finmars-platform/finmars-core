import csv

from django.db.models import Prefetch
from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
from django.utils.datetime_safe import datetime
from rest_framework.renderers import JSONRenderer

from poms.common.views import AbstractModelViewSet
from poms.instruments.models import InstrumentType
from poms.tags.utils import get_tag_prefetch
from poms.transactions.models import TransactionType, TransactionTypeInput, TransactionTypeAction, \
    TransactionTypeActionInstrument, TransactionTypeActionTransaction

from django.core import serializers
import json

from poms.transactions.serializers import TransactionTypeSerializer


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


def get_transaction_type_inputs(transaction_type):
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
        item.pop('transaction_type', None)

    return results


def get_transaction_type_actions(transaction_type):
    results = []

    actions_order = TransactionTypeAction.objects.filter(transaction_type__id=transaction_type["pk"])
    actions_instrument = TransactionTypeActionInstrument.objects.filter(transaction_type__id=transaction_type["pk"])
    actions_transaction = TransactionTypeActionTransaction.objects.filter(transaction_type__id=transaction_type["pk"])

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
                print(key)

                result_json[key] = TransactionTypeInput.objects.get(pk=result_json[key]).name

        if hasattr(result, "transaction_class"):
            action["transaction"] = result_json
        else:
            action["instrument"] = result_json

        results.append(action)

    return results


def get_transaction_types():
    transaction_types = to_json_objects(TransactionType.objects.filter(is_deleted=False))
    results = []

    for transaction_type in transaction_types:
        result_item = transaction_type["fields"]

        result_item["inputs"] = get_transaction_type_inputs(transaction_type)
        result_item["actions"] = get_transaction_type_actions(transaction_type)

        clear_none_attrs(result_item)

        results.append(result_item)

    # transaction_types = to_json_objects(TransactionType.objects.filter(is_deleted=False))
    #
    # for transaction_type in transaction_types:
    #
    #     transaction_type["inputs"] = to_json_objects(
    #         TransactionTypeInput.objects.filter(transaction_type__id=transaction_type["pk"]))
    #     transaction_type["actions_order"] = to_json_objects(
    #         TransactionTypeAction.objects.filter(transaction_type__id=transaction_type["pk"]))
    #     transaction_type["actions_instrument"] = to_json_objects(
    #         TransactionTypeActionInstrument.objects.filter(transaction_type__id=transaction_type["pk"]))
    #     transaction_type["actions_transaction"] = to_json_objects(
    #         TransactionTypeActionTransaction.objects.filter(transaction_type__id=transaction_type["pk"]))
    #
    #     for input in TransactionTypeInput.objects.filter(transaction_type__id=transaction_type["pk"]):
    #         if input.content_type:
    #             for input_json in transaction_type['inputs']:
    #
    #                 input_json["fields"].pop('transaction_type', None)
    #
    #                 if input.pk == input_json['pk']:
    #                     input_json["fields"]["content_type"] = '%s.%s' % (
    #                         input.content_type.app_label, input.content_type.model)
    #
    #     for transaction in TransactionTypeActionTransaction.objects.filter(transaction_type__id=transaction_type["pk"]):
    #         for transaction_json in transaction_type["actions_transaction"]:
    #             if transaction.pk == transaction_json["pk"]:
    #                 transaction_json["fields"]["action_notes"] = transaction.action_notes
    #
    #     for instrument in TransactionTypeActionInstrument.objects.filter(transaction_type__id=transaction_type["pk"]):
    #         for instrument_json in transaction_type["actions_instrument"]:
    #             if instrument.pk == instrument_json["pk"]:
    #                 instrument_json["fields"]["action_notes"] = instrument.action_notes
    #
    #
    #     delete_prop(transaction_type["inputs"], 'pk')
    #     delete_prop(transaction_type["actions_order"], 'pk')
    #     delete_prop(transaction_type["actions_instrument"], 'pk')
    #     delete_prop(transaction_type["actions_transaction"], 'pk')
    #
    #     transaction_type["fields"].pop('master_user', None)
    #
    # delete_prop(transaction_types, 'pk')

    result = {
        "entity": "transactions.transactiontype",
        "count": len(results),
        "content": results
    }

    return result


def createConfiguration():
    configuration = {}
    configuration["head"] = {}
    configuration["head"]["date"] = str(datetime.now().date())
    configuration["body"] = []

    transaction_types = get_transaction_types()

    configuration["body"].append(transaction_types)

    return configuration


class ConfigurationExportViewSet(AbstractModelViewSet):

    def list(self, request):
        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="configuration.json"'

        configuration = createConfiguration()

        response.write(json.dumps(configuration))

        return response
