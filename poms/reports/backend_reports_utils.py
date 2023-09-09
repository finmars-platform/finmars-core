import logging

_l = logging.getLogger('poms.reports')


class BackendReportHelperService():

    def get_nested_attribute(self, item, attribute_path):
        parts = attribute_path.split(".")
        obj = item
        try:
            for part in parts:
                obj = obj[part]
        except KeyError:
            return None
        return obj

    def convert_name_key_to_user_code_key(self, key):
        result = key

        pieces = key.split('.')

        last_key = None

        if len(pieces) > 1:
            last_key = pieces.pop()

            if last_key in ['short_name', 'name', 'public_name']:
                pieces.append('user_code')

                result = '.'.join(pieces)

        return result

    def group_already_exist(self, group, groups):
        exist = False

        for item in groups:

            if item['___group_identifier'] == group['___group_identifier']:
                exist = True

        return exist

    def get_unique_groups(self, items, group_type, columns):
        result_groups = []

        result_group = None

        # _l.info('get_unique_groups.item[0] %s' % items[0])
        for item in items:

            result_group = {
                '___group_name': None,
                '___group_identifier': None,
                '___group_type_key': group_type['key'],
            }

            item_value = item[group_type['key']]
            identifier_key = self.convert_name_key_to_user_code_key(group_type['key'])
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

            if not self.group_already_exist(result_group, result_groups):
                result_groups.append(result_group)

        for result_group in result_groups:

            group_items = []

            for item in items:

                if item[result_group['___group_type_key']] == result_group['___group_identifier']:
                    group_items.append(item)

            result_group['subtotal'] = BackendReportSubtotalService.calculate(group_items, columns)

        return result_groups

    def convert_helper_dict(self, helper_list):
        helper_dict = {entry['id']: entry for entry in helper_list}
        return helper_dict

    def flatten_and_convert_item(self, item, helper_dicts):
        flattened_item = {}
        for key, value in item.items():
            if key in helper_dicts:
                related_object = helper_dicts[key].get(value, {})
                for related_key, related_value in related_object.items():
                    new_key = f"{key}.{related_key}"
                    flattened_item[new_key] = related_value
            else:
                flattened_item[key] = value
        return flattened_item

    def convert_report_items_to_full_items(self, data):

        original_items = []  # probably we missing user attributes

        helper_dicts = {
            'pricing_currency': self.convert_helper_dict(data['item_currencies']),
            'portfolio': self.convert_helper_dict(data['item_portfolios']),
            'instrument': self.convert_helper_dict(data['item_instruments']),
            'account': self.convert_helper_dict(data['item_accounts']),
        }

        # _l.info('data helper_dicts %s' %  helper_dicts)
        # _l.info('data items %s' %  data['items'][0])
        for item in data['items']:

            original_item = self.flatten_and_convert_item(item, helper_dicts)

            for custom_field in item['custom_fields']:
                original_item['custom_fields.' + custom_field['user_code']] = custom_field['value']

            original_items.append(original_item)

        return original_items

    def get_filter_match(self, item, key, value):
        item_value = item.get(key)

        if item_value is None:
            if value != '-':
                return False
        else:
            if str(item_value).lower() != value.lower():
                return False

        return True

    def convert_name_key_to_user_code_key(self, key):
        pieces = key.split('.')

        if len(pieces) > 1:
            last_key = pieces[-1]
            if last_key in ['short_name', 'name', 'public_name']:
                pieces.pop()
                pieces.append('user_code')
                return '.'.join(pieces)

        return key


    # Methods for filter_table_rows

    def check_for_empty_regular_filter(self, regular_filter_value, filter_type):
        # Need null's checks for filters of data type number
        if filter_type in ['from_to', 'out_of_range']:
            if (regular_filter_value.get('min_value') is not None) and (regular_filter_value.get('max_value') is not None):
                return True
        elif isinstance(regular_filter_value, list):
            if regular_filter_value[0] is not None:
                return True
        return False


    def does_string_contains_substrings(self, value_to_filter, filter_by_string):
        filter_substrings = filter_by_string.split(' ')
        for substring in filter_substrings:
            if substring not in value_to_filter:
                return False
        return True


    def filter_value_from_table(self, value_to_filter, filter_by, operation_type):
        if operation_type == 'contains':
            if '"' in filter_by:  # if string inside of double quotes
                formatted_filter_by = filter_by.strip('"')
                if formatted_filter_by in value_to_filter:
                    return True
            elif self.does_string_contains_substrings(value_to_filter, filter_by):
                return True

        elif operation_type == 'contains_has_substring':
            if '"' in filter_by:  # if string inside of double quotes
                formatted_filter_by = filter_by.strip('"')
                if formatted_filter_by in value_to_filter:
                    return True
            elif filter_by in value_to_filter:
                return True

        elif operation_type == 'does_not_contains':
            return filter_by not in value_to_filter
        elif operation_type == 'equal' or operation_type == 'selector':
            return value_to_filter == filter_by
        elif operation_type == 'not_equal':
            return value_to_filter != filter_by
        elif operation_type == 'greater':
            return value_to_filter > filter_by
        elif operation_type == 'greater_equal':
            return value_to_filter >= filter_by
        elif operation_type == 'less':
            return value_to_filter < filter_by
        elif operation_type == 'less_equal':
            return value_to_filter <= filter_by
        elif operation_type == 'from_to':
            return filter_by['min_value'] <= value_to_filter <= filter_by['max_value']
        elif operation_type == 'out_of_range':
            return value_to_filter <= filter_by['min_value'] or value_to_filter >= filter_by['max_value']
        elif operation_type == 'multiselector':
            return value_to_filter in filter_by
        elif operation_type == 'date_tree':
            return any(str(value_to_filter.date()) == str(date) for date in filter_by)
        else:
            return False


    def get_regular_filters(self, options):
        result = {}

        if 'filter_settings' in options:
            result = options['filter_settings']
        else:
            excluded_keys = ['groups_order', 'groups_types', 'groups_values', 'page', 'page_size']
            for key, value in options.items():
                if key not in excluded_keys:
                    result[key] = value

        return result



    def filter_table_rows(self, items, options):

        regular_filters = self.get_regular_filters(options)

        def match_item(item):
            for filter_ in regular_filters:
                key_property = filter_['key']
                value_type = filter_['value_type']
                filter_type = filter_['filter_type']
                exclude_empty_cells = filter_['exclude_empty_cells']
                filter_value = filter_['value']

                if key_property != 'ordering':
                    if key_property in item and item[key_property] is not None:
                        if self.check_for_empty_regular_filter(filter_value, filter_type):
                            value_from_table = item[key_property]
                            filter_argument = filter_value

                            if value_type in [10, 30] and filter_type != 'multiselector':
                                value_from_table = value_from_table.lower()
                                filter_argument = filter_argument[0].lower()
                            elif value_type == 40:
                                if filter_type in ['equal', 'not_equal']:
                                    value_from_table = str(value_from_table.date())
                                    filter_argument = str(filter_argument[0].date())
                                elif filter_type in ['from_to', 'out_of_range']:
                                    value_from_table = value_from_table.date()
                                    filter_argument['min_value'] = filter_argument['min_value'].date()
                                    filter_argument['max_value'] = filter_argument['max_value'].date()

                            if not self.filter_value_from_table(value_from_table, filter_argument, filter_type):
                                return False
                    elif exclude_empty_cells or (key_property in ['name', 'instrument'] and item['item_type'] != 1):
                        return False
            return True

        return [item for item in items if match_item(item)]

    # Methods for filter_table_rows

    def filter_by_groups_filters(self, items, options):

        groups_types = options['groups_types']

        # _l.info('filter_by_groups_filters.groups_types %s' % groups_types)
        # _l.info('filter_by_groups_filters.groups_values %s' % options.get("groups_values", []))

        if len(groups_types) > 0 and len(options.get("groups_values", [])) > 0:
            filtered_items = []
            for item in items:
                match = True
                for i in range(len(options["groups_values"])):
                    key = options["groups_types"][i]["key"]
                    value = options["groups_values"][i]
                    converted_key = self.convert_name_key_to_user_code_key(key)

                    # _l.info('filter_by_groups_filters.key %s' % key)
                    # _l.info('filter_by_groups_filters.value %s' % value)

                    match = self.get_filter_match(item, converted_key, value)

                    if not match:
                        break
                if match:
                    filtered_items.append(item)

            # _l.info('filter_by_groups_filters.filtered_items %s' % filtered_items)

            return filtered_items

        return items


    def filter_by_global_table_search(self, items, options):

        query = options.get('globalTableSearch', '')

        if query:

            pieces = [piece.lower() for piece in query.split()]

            def item_matches(item):
                for key, value in item.items():
                    if value is not None:
                        value_str = str(value).lower()
                        if any(piece in value_str for piece in pieces):
                            return True
                return False

            return list(filter(item_matches, items))

        return items

    def filter(self, items, options):

        _l.info("Before filter %s" % len(items))

        items = self.filter_by_global_table_search(items, options)

        _l.info("After filter_by_global_table_search %s" % len(items))

        items = self.filter_table_rows(items, options)

        _l.info("After filter_table_rows %s" % len(items))

        items = self.filter_by_groups_filters(items, options)

        _l.info("After filter_by_groups_filters %s" % len(items))

        return items


class BackendReportSubtotalService:

    @staticmethod
    def get_item_value(item, value_property):
        return item.get(value_property, 0)

    @staticmethod
    def sum(items, column):
        result = 0
        for item in items:
            item_val = BackendReportSubtotalService.get_item_value(item, column["key"])
            if not isinstance(item_val, (int, float)):
                result = "#Error"
                print(f"{column['key']} with not a number", item, item[column["key"]])
                break
            else:
                result += float(item_val)
        return result

    @staticmethod
    def get_weighted_value(items, column_key, weighted_key):
        result = 0
        for item in items:
            value = BackendReportSubtotalService.get_item_value(item, weighted_key)
            if value:
                item_val = BackendReportSubtotalService.get_item_value(item, column_key)
                if item_val:
                    result += float(item_val) * float(value)
        return result

    @staticmethod
    def get_weighted_average_value(items, column_key, weighted_average_key):
        result = 0
        total = 0
        for item in items:
            value = BackendReportSubtotalService.get_item_value(item, weighted_average_key)
            if value:
                total += value
        if total:
            for item in items:
                item_val = BackendReportSubtotalService.get_item_value(item, column_key)
                if not isinstance(item_val, (int, float)):
                    result = "#Error"
                    break
                else:
                    value = BackendReportSubtotalService.get_item_value(item, weighted_average_key)
                    average = float(value) / total
                    result += float(item_val) * average
        else:
            print(f"{weighted_average_key} totals is", total, column_key)
            result = "#Error"
        return result

    @staticmethod
    def resolve_subtotal_function(items, column):
        if "report_settings" in column and "subtotal_formula_id" in column["report_settings"]:
            formula_id = column["report_settings"]["subtotal_formula_id"]
            if formula_id == 1:
                return BackendReportSubtotalService.sum(items, column)
            elif formula_id == 2:
                return BackendReportSubtotalService.get_weighted_value(items, column["key"], "market_value")
            elif formula_id == 3:
                return BackendReportSubtotalService.get_weighted_value(items, column["key"], "market_value_percent")
            elif formula_id == 4:
                return BackendReportSubtotalService.get_weighted_value(items, column["key"], "exposure")
            elif formula_id == 5:
                return BackendReportSubtotalService.get_weighted_value(items, column["key"], "exposure_percent")
            elif formula_id == 6:
                return BackendReportSubtotalService.get_weighted_average_value(items, column["key"], "market_value")
            elif formula_id == 7:
                return BackendReportSubtotalService.get_weighted_average_value(items, column["key"],
                                                                               "market_value_percent")
            elif formula_id == 8:
                return BackendReportSubtotalService.get_weighted_average_value(items, column["key"], "exposure")
            elif formula_id == 9:
                return BackendReportSubtotalService.get_weighted_average_value(items, column["key"], "exposure_percent")

    @staticmethod
    def calculate(items, columns):
        result = {}
        for column in columns:
            if column["value_type"] == 20:
                result[column["key"]] = BackendReportSubtotalService.resolve_subtotal_function(items, column)
        return result

    @staticmethod
    def calculate_column(items, column):
        result = {}
        result[column["key"]] = BackendReportSubtotalService.resolve_subtotal_function(items, column)
        return result
