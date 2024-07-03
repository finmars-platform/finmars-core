from poms.common.models import ProxyUser, ProxyRequest
from poms.common.utils import get_serializer
from poms.configuration.utils import remove_id_key_recursively, save_json_to_file, user_code_to_file_name
from poms.instruments.models import InstrumentType, PricingPolicy
from poms.transactions.models import TransactionType, TransactionTypeGroup


def export_instrument_types(configuration_code, output_directory, master_user, member):

    proxy_user = ProxyUser(member, master_user)
    proxy_request = ProxyRequest(proxy_user)

    context = {
        'master_user': master_user,
        'member': member,
        'request': proxy_request
    }

    filtered_objects = InstrumentType.objects.filter(configuration_code=configuration_code, master_user=master_user, is_deleted=False).exclude(user_code='-')

    SerializerClass = get_serializer('instruments.instrumenttype')

    for item in filtered_objects:
        serializer = SerializerClass(item, context=context)
        serialized_data = remove_id_key_recursively(serializer.data)

        serialized_data.pop("is_enabled", None)
        serialized_data.pop("is_deleted", None)
        serialized_data.pop("pricing_policies", None)
        serialized_data.pop("deleted_user_code", None)

        if serialized_data["one_off_event"]:
            serialized_data["one_off_event"] = TransactionType.objects.get(
                pk=serialized_data["one_off_event"]).user_code
            serialized_data.pop("one_off_event", None)

        serialized_data.pop("one_off_event_object", None)

        if serialized_data["regular_event"]:
            serialized_data["regular_event"] = TransactionType.objects.get(
                pk=serialized_data["regular_event"]).user_code
            serialized_data.pop("regular_event", None)

        serialized_data.pop("regular_event_object", None)

        if serialized_data["factor_same"]:
            serialized_data["factor_same"] = TransactionType.objects.get(
                pk=serialized_data["factor_same"]).user_code
            serialized_data.pop("factor_same", None)

        serialized_data.pop("factor_same_object", None)

        if serialized_data["factor_up"]:
            serialized_data["factor_up"] = TransactionType.objects.get(
                pk=serialized_data["factor_up"]).user_code
            serialized_data.pop("factor_up", None)

        serialized_data.pop("factor_up_object", None)

        if serialized_data["factor_down"]:
            serialized_data["factor_down"] = TransactionType.objects.get(
                pk=serialized_data["factor_down"]).user_code
            serialized_data.pop("factor_down", None)

        serialized_data.pop("factor_down_object", None)


        serialized_data['pricing_policies'] = []

        # TODO think how to implement
        # result_item['pricing_policies'] = self.get_instrument_type_pricing_policies(instrument_type["pk"])

        path = output_directory + '/' + user_code_to_file_name(configuration_code, item.user_code) + '.json'

        save_json_to_file(path, serialized_data)



def export_pricing_policies(configuration_code, output_directory, master_user, member):

    proxy_user = ProxyUser(member, master_user)
    proxy_request = ProxyRequest(proxy_user)

    context = {
        'master_user': master_user,
        'member': member,
        'request': proxy_request
    }

    filtered_objects = PricingPolicy.objects.filter(configuration_code=configuration_code, master_user=master_user)

    SerializerClass = get_serializer('instruments.pricingpolicy')

    for item in filtered_objects:
        serializer = SerializerClass(item, context=context)
        serialized_data = remove_id_key_recursively(serializer.data)

        serialized_data.pop("deleted_user_code", None)
        # serialized_data.pop("default_currency_pricing_scheme", None)
        # serialized_data.pop("default_currency_pricing_scheme_object", None)
        # serialized_data.pop("default_instrument_pricing_scheme", None)
        # serialized_data.pop("default_instrument_pricing_scheme_object", None)

        path = output_directory + '/' + user_code_to_file_name(configuration_code, item.user_code) + '.json'

        save_json_to_file(path, serialized_data)



def export_transaction_types(configuration_code, output_directory, master_user, member):

    proxy_user = ProxyUser(member, master_user)
    proxy_request = ProxyRequest(proxy_user)

    context = {
        'master_user': master_user,
        'member': member,
        'request': proxy_request
    }

    filtered_objects = TransactionType.objects.filter(configuration_code=configuration_code, master_user=master_user, is_deleted=False).exclude(user_code='-')

    SerializerClass = get_serializer('transactions.transactiontype')

    for item in filtered_objects:
        serializer = SerializerClass(item, context=context)
        serialized_data = remove_id_key_recursively(serializer.data)

        serialized_data.pop("is_enabled", None)
        serialized_data.pop("is_deleted", None)

        serialized_data.pop("deleted_user_code", None)

        # No need anymore # TODO remove later # careful maybe needed
        try:
            serialized_data['group'] = TransactionTypeGroup.objects.get(id=serialized_data['group']).user_code
        except Exception as e:
            serialized_data['group'] = None

        path = output_directory + '/' + user_code_to_file_name(configuration_code, item.user_code) + '.json'

        save_json_to_file(path, serialized_data)
