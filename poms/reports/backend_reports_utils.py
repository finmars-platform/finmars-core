def get_nested_attribute(item, attribute_path):
    parts = attribute_path.split(".")
    obj = item
    try:
        for part in parts:
            obj = obj[part]
    except KeyError:
        return None
    return obj

def convert_name_key_to_user_code_key(key):
    result = key

    pieces = key.split('.')

    last_key = None

    if len(pieces) > 1:
        last_key = pieces.pop()

        if last_key in ['short_name', 'name', 'public_name']:
            pieces.append('user_code')

            result = '.'.join(pieces)

    return result


def group_already_exist(group, groups):
    exist = False

    for item in groups:

        if item['___group_identifier'] == group['___group_identifier']:
            exist = True

    return exist


def get_unique_groups(items, group_type):
    result_groups = []

    result_group = None

    for item in items:

        result_group = {
            '___group_name': None,
            '___group_identifier': None,
            '___group_type_key': group_type['key'],
        }


        item_value = item[group_type['key']]
        identifier_key = convert_name_key_to_user_code_key(group_type['key'])
        identifier_value = item[identifier_key]

        if identifier_value != None and identifier_value != '-':

            result_group['___group_identifier'] = str(identifier_value)
            result_group['___group_name'] = str(item_value)

            if group_type['key'] == 'complex_transaction.status':

                if item_value == 1:
                    result_group['___group_name'] = 'Booked'

                if item_value == 2:
                    result_group['___group_name'] = 'Pending'

                if item_value == 3:
                    result_group['___group_name'] = 'Ignored'

        if not group_already_exist(result_group, result_groups):
            result_groups.append(result_group)

    return result_groups

def convert_helper_dict(helper_list):
    helper_dict = {entry['id']: entry for entry in helper_list}
    return helper_dict

def flatten_and_convert_item(item, helper_dicts):
    flattened_item = {}
    for key, value in item.items():
        if key.endswith('_id') and key[:-3] in helper_dicts:
            related_object = helper_dicts[key[:-3]].get(value, {})
            for related_key, related_value in related_object.items():
                new_key = f"{key[:-3]}.{related_key}"
                flattened_item[new_key] = related_value
        else:
            flattened_item[key] = value
    return flattened_item