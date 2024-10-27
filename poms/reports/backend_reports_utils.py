import logging
import itertools

from django.contrib.contenttypes.models import ContentType

from poms.instruments.models import Instrument
from poms.obj_attrs.models import GenericAttributeType

_l = logging.getLogger("poms.reports")


class BackendReportHelperService:
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
        pieces = key.split(".")
        # Transform last key to user_code
        if len(pieces) > 1 and pieces[-1] in ["short_name", "name", "public_name"]:
            pieces[-1] = "user_code"
        return ".".join(pieces)

    def get_result_group(self, item, group_type):
        result_group = {
            "___group_name": None,
            "___group_identifier": None,
            "___group_type_key": group_type["key"],
        }
        item_value = item.get(group_type["key"])
        identifier_key = self.convert_name_key_to_user_code_key(group_type["key"])
        identifier_value = item.get(identifier_key)

        # _l.debug('get_result_group.identifier_value %s' % identifier_value)

        if identifier_value not in [None, "-"]:
            result_group["___group_identifier"] = str(identifier_value)
            result_group["___group_name"] = str(item_value)

            if group_type["key"] == "complex_transaction.status":
                status_map = {1: "Booked", 2: "Pending", 3: "Ignored"}
                result_group["___group_name"] = status_map.get(
                    item_value, str(item_value)
                )
        elif identifier_value == "-":
            result_group["___group_identifier"] = "-"
            result_group["___group_name"] = "-"

        elif identifier_value is None:  # Specifically, handle None values
            result_group["___group_identifier"] = None
            result_group["___group_name"] = "No Data"

        return result_group

    def get_unique_groups(self, items, group_type, columns):
        seen_group_identifiers = set()
        result_groups = []

        for item in items:
            result_group = self.get_result_group(item, group_type)
            identifier = result_group["___group_identifier"]

            if identifier not in seen_group_identifiers:
                seen_group_identifiers.add(identifier)
                result_groups.append(result_group)

        # _l.debug('result_groups %s' % result_groups)
        # _l.debug('items %s' % items)

        identifier_key = self.convert_name_key_to_user_code_key(group_type["key"])

        for result_group in result_groups:
            group_items = [
                item
                for item in items
                if item.get(identifier_key) == result_group["___group_identifier"]
            ]

            # _l.debug('group_items %s' % group_items)

            result_group["subtotal"] = BackendReportSubtotalService.calculate(
                group_items, columns
            )

            if result_group["subtotal"].get("market_value"):
                try:
                    total_value = sum(map(lambda item: item["market_value_percent"], group_items)) or None
                    # None is to raise an exception if sum is 0
                    result_group["subtotal"]["market_value_percent"] = total_value
                except Exception as e:
                    result_group["subtotal"]["market_value_percent"] = "No Data"

            if result_group["subtotal"].get("exposure"):
                try:
                    total_value = sum(map(lambda item: item["exposure_percent"], group_items)) or None
                    result_group["subtotal"]["exposure_percent"] = total_value
                except Exception as e:
                    result_group["subtotal"]["exposure_percent"] = "No Data"

        return result_groups

    def convert_helper_dict(self, helper_list):
        return {entry["id"]: entry for entry in helper_list}

    def _get_attribute_value(self, attribute):
        value_type = attribute.get("attribute_type_object", {}).get("value_type")
        if value_type == 30:
            if "classifier_object" in attribute and attribute["classifier_object"]:
                return attribute["classifier_object"]["name"]

        elif value_type == 10:  # example value types for float and string
            return attribute.get("value_string")
        elif value_type == 20:  # example value types for float and string
            return attribute.get("value_float")
        elif value_type == 40:  # example value types for float and string
            return attribute.get("value_date")

        return None

    # def flatten_and_convert_item(self, item, helper_dicts):
    #     def recursively_flatten(prefix, item):
    #         flattened = {}
    #
    #         for key, value in item.items():
    #
    #             current_key = f"{prefix}.{key}" if prefix else key
    #
    #             if key in helper_dicts:
    #                 related_object = helper_dicts[key].get(value, {})
    #
    #                 if related_object:
    #                     flattened.update(
    #                         recursively_flatten(current_key, related_object)
    #                     )
    #                 else:
    #                     flattened[current_key] = value
    #
    #             elif key == "attributes" and isinstance(value, list):
    #                 for attribute in value:
    #                     user_code = attribute.get("attribute_type_object", {}).get(
    #                         "user_code"
    #                     )
    #                     if user_code:
    #                         attr_value = self._get_attribute_value(attribute)
    #                         flattened[f"{current_key}.{user_code}"] = attr_value
    #             else:
    #                 flattened[current_key] = value
    #
    #         return flattened
    #
    #     return recursively_flatten("", item)

    def flatten_and_convert_item(self, item, helper_dicts, instrument_attribute_types):
        # Complicated function, but no need recursion here
        # perforamnce matter
        # basicaly code below doing

        # {
        #     'a': '1',
        #     'b': {
        #         'c': '2',
        #         'd': {
        #             'e': '4'
        #         }
        #     }
        # }

        # to

        # 'a': 1',
        # 'b.c': '2',
        # 'b.d.e': '4'
        # Maximum 2 levels of nesting, last level has no attributes

        # I beg my pardon for what your eyes will see below

        flattened_item = {}

        for root_key, value in item.items():
            if root_key in helper_dicts:
                related_object = helper_dicts[root_key].get(value, {})

                if related_object:
                    for first_level_key, related_value in related_object.items():
                        related_prefixed_key = f"{root_key}.{first_level_key}"

                        if first_level_key == "attributes" and isinstance(
                            related_value, list
                        ):
                            for attribute in related_value:
                                user_code = attribute.get(
                                    "attribute_type_object", {}
                                ).get("user_code")
                                if user_code:
                                    attr_value = self._get_attribute_value(attribute)
                                    flattened_item[
                                        f"{related_prefixed_key}.{user_code}"
                                    ] = attr_value
                        elif first_level_key in helper_dicts:
                            related_related_object = helper_dicts[first_level_key].get(
                                related_value, {}
                            )

                            if related_related_object:
                                for (
                                    second_level_key,
                                    related_related_value,
                                ) in related_related_object.items():
                                    _prefixed_key = f"{root_key}.{first_level_key}.{second_level_key}"

                                    flattened_item[
                                        _prefixed_key
                                    ] = related_related_value

                            else:
                                flattened_item[
                                    f"{root_key}.{first_level_key}"
                                ] = related_value

                        else:
                            flattened_item[
                                f"{root_key}.{first_level_key}"
                            ] = related_value

                else:
                    flattened_item[root_key] = value
            else:
                flattened_item[root_key] = value

        if "item_type" in item:
            if item["item_type"] == 2:
                for attribute_type in instrument_attribute_types:
                    flattened_item[
                        f"instrument.attributes.{attribute_type.user_code}"
                    ] = "Cash & Equivalents"

                if "currency.country.name" in flattened_item:
                    flattened_item["instrument.country.name"] = flattened_item[
                        "currency.country.name"
                    ]
                    flattened_item["instrument.country.user_code"] = flattened_item[
                        "currency.country.user_code"
                    ]
                    flattened_item["instrument.country.short_name"] = flattened_item[
                        "currency.country.short_name"
                    ]

                flattened_item['instrument.instrument_type.name'] = 'Cash & Equivalents'
                flattened_item['instrument.instrument_type.user_code'] = 'Cash & Equivalents'
                flattened_item['instrument.instrument_type.short_name'] = 'Cash & Equivalents'

            if item["item_type"] == 1 and "instrument.country.name" in flattened_item:
                flattened_item["currency.country.name"] = flattened_item[
                    "instrument.country.name"
                ]
                flattened_item["currency.country.user_code"] = flattened_item[
                    "instrument.country.user_code"
                ]
                flattened_item["currency.country.short_name"] = flattened_item[
                    "instrument.country.short_name"
                ]

            if item["item_type"] == 3:
                for attribute_type in instrument_attribute_types:
                    flattened_item[
                        f"instrument.attributes.{attribute_type.user_code}"
                    ] = "FX Variations"


                flattened_item["instrument.country.name"] = 'FX Variations'
                flattened_item["instrument.country.user_code"] = 'FX Variations'
                flattened_item["instrument.country.short_name"] = 'FX Variations'

                flattened_item['instrument.instrument_type.name'] = 'FX Variations'
                flattened_item['instrument.instrument_type.user_code'] = 'FX Variations'
                flattened_item['instrument.instrument_type.short_name'] = 'FX Variations'

                flattened_item["currency.country.name"] = 'FX Variations'
                flattened_item["currency.country.user_code"] = 'FX Variations'
                flattened_item["currency.country.short_name"] = 'FX Variations'


            if item["item_type"] == 4:
                for attribute_type in instrument_attribute_types:
                    flattened_item[
                        f"instrument.attributes.{attribute_type.user_code}"
                    ] = "FX Trades"

                flattened_item["instrument.country.name"] = 'FX Trades'
                flattened_item["instrument.country.user_code"] = 'FX Trades'
                flattened_item["instrument.country.short_name"] = 'FX Trades'

                flattened_item['instrument.instrument_type.name'] = 'FX Trades'
                flattened_item['instrument.instrument_type.user_code'] = 'FX Trades'
                flattened_item['instrument.instrument_type.short_name'] = 'FX Trades'

                flattened_item["currency.country.name"] = 'FX Trades'
                flattened_item["currency.country.user_code"] = 'FX Trades'
                flattened_item["currency.country.short_name"] = 'FX Trades'

            if item["item_type"] == 5:
                for attribute_type in instrument_attribute_types:
                    flattened_item[
                        f"instrument.attributes.{attribute_type.user_code}"
                    ] = "Other"

                flattened_item["instrument.country.name"] = 'Other'
                flattened_item["instrument.country.user_code"] = 'Other'
                flattened_item["instrument.country.short_name"] = 'Other'

                flattened_item['instrument.instrument_type.name'] = 'Other'
                flattened_item['instrument.instrument_type.user_code'] = 'Other'
                flattened_item['instrument.instrument_type.short_name'] = 'Other'

                flattened_item["currency.country.name"] = 'Other'
                flattened_item["currency.country.user_code"] = 'Other'
                flattened_item["currency.country.short_name"] = 'Other'

            if item["item_type"] == 6:
                for attribute_type in instrument_attribute_types:
                    flattened_item[
                        f"instrument.attributes.{attribute_type.user_code}"
                    ] = "Mismatch"

                flattened_item["instrument.country.name"] = 'Mismatch'
                flattened_item["instrument.country.user_code"] = 'Mismatch'
                flattened_item["instrument.country.short_name"] = 'Mismatch'

                flattened_item['instrument.instrument_type.name'] = 'Mismatch'
                flattened_item['instrument.instrument_type.user_code'] = 'Mismatch'
                flattened_item['instrument.instrument_type.short_name'] = 'Mismatch'

                flattened_item["currency.country.name"] = 'Mismatch'
                flattened_item["currency.country.user_code"] = 'Mismatch'
                flattened_item["currency.country.short_name"] = 'Mismatch'

        return flattened_item

    def convert_report_items_to_full_items(self, data):
        original_items = []  # probably we missing user attributes

        helper_dicts = {
            "accrued_currency": self.convert_helper_dict(data["item_currencies"]),
            "pricing_currency": self.convert_helper_dict(data["item_currencies"]),
            "settlement_currency": self.convert_helper_dict(data["item_currencies"]),
            "transaction_currency": self.convert_helper_dict(data["item_currencies"]),
            "exposure_currency": self.convert_helper_dict(data["item_currencies"]),
            "entry_currency": self.convert_helper_dict(data["item_currencies"]),
            "currency": self.convert_helper_dict(data["item_currencies"]),
            "portfolio": self.convert_helper_dict(data["item_portfolios"]),
            "instrument": self.convert_helper_dict(data["item_instruments"]),
            "instrument_type": self.convert_helper_dict(data["item_instrument_types"]),
            "country": self.convert_helper_dict(data["item_countries"]),
            "entry_instrument": self.convert_helper_dict(data["item_instruments"]),
            "allocation": self.convert_helper_dict(data["item_instruments"]),
            "allocation_balance": self.convert_helper_dict(data["item_instruments"]),
            "allocation_pl": self.convert_helper_dict(data["item_instruments"]),
            "account": self.convert_helper_dict(data["item_accounts"]),
            "type": self.convert_helper_dict(data["item_account_types"]),
            "account_cash": self.convert_helper_dict(data["item_accounts"]),
            "account_interim": self.convert_helper_dict(data["item_accounts"]),
            "account_position": self.convert_helper_dict(data["item_accounts"]),
            "entry_account": self.convert_helper_dict(data["item_accounts"]),
            "strategy1_position": self.convert_helper_dict(data["item_strategies1"]),
            "strategy1_cash": self.convert_helper_dict(data["item_strategies1"]),
            "strategy2_position": self.convert_helper_dict(data["item_strategies2"]),
            "strategy2_cash": self.convert_helper_dict(data["item_strategies2"]),
            "strategy3_position": self.convert_helper_dict(data["item_strategies3"]),
            "strategy3_cash": self.convert_helper_dict(data["item_strategies3"]),
        }

        if "item_counterparties" in data:
            helper_dicts["counterparty"] = self.convert_helper_dict(
                data["item_counterparties"]
            )

        if "item_responsibles" in data:
            helper_dicts["responsible"] = self.convert_helper_dict(
                data["item_responsibles"]
            )

        if "item_transaction_classes" in data:
            helper_dicts["transaction_class"] = self.convert_helper_dict(
                data["item_transaction_classes"]
            )

        content_type = ContentType.objects.get(app_label='instruments', model='instrument')
        instrument_attribute_types = GenericAttributeType.objects.filter(
            content_type=content_type
        )

        # _l.debug('data helper_dicts %s' %  helper_dicts)
        # _l.debug('data items %s' % data['items'][0])
        for item in data["items"]:
            original_item = self.flatten_and_convert_item(
                item, helper_dicts, instrument_attribute_types
            )

            if "custom_fields" in item:
                for custom_field in item["custom_fields"]:
                    original_item[
                        "custom_fields." + custom_field["user_code"]
                    ] = custom_field["value"]

            original_items.append(original_item)

        return original_items

    def get_filter_match(self, item, key, value):
        item_value = item.get(key)

        result_value = value

        if isinstance(result_value, str):
            result_value = result_value.lower()

        # _l.debug('get_filter_match.item_value %s' % item_value)
        # _l.debug('get_filter_match.result_value %s' % result_value)

        # Refactor someday this shitty logic
        if item_value is None:
            if result_value not in ("-", None):
                # TODO this one is important, we need to split - and None in future
                return False
        elif str(item_value).lower() != result_value:
            return False

        return True

    # Methods for filter_table_rows

    def check_for_empty_regular_filter(self, regular_filter_value, filter_type):
        # Need null's checks for filters of data type number
        if filter_type in ["from_to", "out_of_range"]:
            if (regular_filter_value.get("min_value") is not None) and (
                regular_filter_value.get("max_value") is not None
            ):
                return True
        elif isinstance(regular_filter_value, list):
            if regular_filter_value and regular_filter_value[0]:
                return True
        return False

    def does_string_contains_substrings(self, value_to_filter, filter_by_string):
        filter_substrings = filter_by_string.split(" ")
        return all(substring in value_to_filter for substring in filter_substrings)

    def filter_value_from_table(self, value_to_filter, filter_by, operation_type):

        if operation_type == "contains":
            if '"' in filter_by:  # if string inside of double quotes
                formatted_filter_by = filter_by.strip('"')
                if formatted_filter_by in value_to_filter:
                    return True
            elif self.does_string_contains_substrings(value_to_filter, filter_by):
                return True

        elif operation_type == "contains_has_substring":
            if '"' in filter_by:  # if string inside of double quotes
                formatted_filter_by = filter_by.strip('"')
                if formatted_filter_by in value_to_filter:
                    return True
            elif filter_by in value_to_filter:
                return True

        elif operation_type == "does_not_contains":
            return filter_by not in value_to_filter
        elif operation_type in ("equal", "selector"):
            return value_to_filter == filter_by
        elif operation_type == "not_equal":
            return value_to_filter != filter_by
        elif operation_type == "greater":
            return value_to_filter > filter_by
        elif operation_type == "greater_equal":
            return value_to_filter >= filter_by
        elif operation_type == "less":
            return value_to_filter < filter_by
        elif operation_type == "less_equal":
            return value_to_filter <= filter_by
        elif operation_type == "from_to":
            return filter_by["min_value"] <= value_to_filter <= filter_by["max_value"]
        elif operation_type == "out_of_range":
            return (
                value_to_filter <= filter_by["min_value"]
                or value_to_filter >= filter_by["max_value"]
            )
        elif operation_type == "multiselector":
            return value_to_filter in filter_by

        elif operation_type == "date_tree":
            return any(value_to_filter == str(date) for date in filter_by)

        else:
            return False

    def get_regular_filters(self, options):
        result = {}

        if "filter_settings" in options:
            result = options["filter_settings"]
        else:
            excluded_keys = [
                "groups_order",
                "groups_types",
                "groups_values",
                "page",
                "page_size",
            ]
            for key, value in options.items():
                if key not in excluded_keys:
                    result[key] = value

        return result

    def filter_table_rows(self, items, options):
        regular_filters = self.get_regular_filters(options)

        def match_item(item):
            for filter_ in regular_filters:

                key_property = filter_["key"]
                value_type = filter_["value_type"]
                filter_type = filter_["filter_type"]
                filter_value = filter_["value"]
                filter_value_not_empty = self.check_for_empty_regular_filter(filter_value, filter_type)

                if key_property != "ordering":
                    if item.get(key_property) or item.get(key_property) == 0:

                        if filter_type == 'empty':
                            return False

                        if filter_value_not_empty:

                            value_from_table = item[key_property]
                            filter_argument = filter_value

                            if (
                                value_type in (10, 30)
                                and filter_type != "multiselector"
                            ):
                                value_from_table = value_from_table.lower()
                                filter_argument = filter_argument[0].lower()

                            elif value_type == 20:

                                if filter_type not in ('from_to', 'out_of_range'):
                                    filter_argument = filter_argument[0]

                            elif value_type == 40:
                                _l.debug(
                                    "BackendReportHelperService.filter_table_rows"
                                    f".match_item value_type=40 "
                                    f"value_from_table={value_from_table} "
                                    f"filter_argument={filter_argument}"
                                )

                                if filter_type not in {"from_to", "out_of_range", "date_tree"}:
                                    filter_argument = filter_argument[0]

                            if not self.filter_value_from_table(
                                value_from_table, filter_argument, filter_type
                            ):
                                return False

                    # Strange logic migrated from front end. May be not needed.
                    #
                    # item_type 1 == "instrument"
                    # elif exclude_empty_cells or (
                    #         key_property in ["name", "instrument"]
                    #         and item["item_type"] != 1
                    # ):

                    elif filter_type != "empty" and filter_value_not_empty:
                        return False
            return True

        return [item for item in items if match_item(item)]

    # Methods for filter_table_rows

    def filter_by_groups_filters(self, items, options):
        # Retrieve the group types and values from the options dictionary
        groups_types = options.get("groups_types", [])
        groups_values = options.get("groups_values", [])

        # Early exit: If there are no group types or values, return the original list without filtering
        if not groups_types or not groups_values:
            _l.debug(f"filter_by_groups_filters after len {len(items)}")
            return items

        # Filter the items based on group types and values
        # We use a list comprehension for efficiency and readability
        filtered_items = [
            item  # Include item in the filtered list if it matches all criteria
            for item in items
            if all(  # `all` checks that every condition in the inner loop is True
                self.get_filter_match(
                    item,
                    self.convert_name_key_to_user_code_key(groups_types[i]["key"]),
                    groups_values[i]
                )
                for i in range(len(groups_types))  # Iterate over each index in group types
            )
        ]

        # Log the final count of filtered items
        _l.debug(f"filter_by_groups_filters after len {len(filtered_items)}")

        # Return the filtered list
        return filtered_items


    def filter_by_global_table_search(self, items, options):
        query = options.get("globalTableSearch", "")

        if not query:
            return items

        pieces = {piece.lower() for piece in query.split()}

        def item_matches(item):
            for value in item.values():
                if value is not None:
                    # Let's only convert to str if it's not already a str
                    value_str = value if isinstance(value, str) else str(value)
                    value_str = value_str.lower()

                    # Check if any piece is in value_str
                    if any(piece in value_str for piece in pieces):
                        return True

            return False

        return list(filter(item_matches, items))

    def filter(self, items, options):
        _l.debug(f"Before filter {len(items)}")

        items = self.filter_by_global_table_search(items, options)

        _l.debug(f"After filter_by_global_table_search {len(items)}")

        items = self.filter_table_rows(items, options)

        _l.debug(f"After filter_table_rows {len(items)}")

        # items = self.filter_by_groups_filters(items, options)

        _l.debug(f"After filter_by_groups_filters {len(items)}")

        return items

    def reduce_columns(self, items, options):
        columns = options["columns"]

        user_columns = [column["key"] for column in columns]

        result_items = []
        for item in items:
            result_item = {"id": item["id"]}

            for key in user_columns:
                if key in item:
                    result_item[key] = item[key]

            for key in item.keys():
                if ".id" in key:
                    result_item[key] = item[key]

            result_items.append(result_item)

        return result_items

    # Probably Deprecated
    def order_sort(self, property, sort_order):
        def comparator(a, b):
            if a.get(property) is None:
                return 1 * sort_order
            if b.get(property) is None:
                return -1 * sort_order

            if a[property] < b[property]:
                return -1 * sort_order

            return 1 * sort_order if a[property] > b[property] else 0

        return comparator

    def sort_items_by_property(self, items, property):
        # Determine sort direction
        if property.startswith("-"):
            reverse = True
            property = property[1:]
        else:
            reverse = False

        # Adjusted sort key to handle None values
        sort_key = lambda x: (x.get(property) is None, x.get(property))

        # Use sorted() to sort items
        return sorted(items, key=sort_key, reverse=reverse)

    def sort_groups(self, items, options):
        if "groups_order" in options:
            property = "___group_name"  # TODO consider refactor someday

            if options["groups_order"] == "desc":
                property = f"-{property}"

            return self.sort_items_by_property(items, property)

        return items

    def sort_items(self, items, options):
        if "ordering" in options and "items_order" in options:
            property = options["ordering"]

            if options["items_order"] == "desc":
                property = f"-{property}"

            return self.sort_items_by_property(items, property)

        return items

    def calculate_value_percent(self, items, group_field, data_field):
        if not items:
            return items
        if group_field == 'no_grouping':
            item_groups = [items]
        else:
            sorted_items = sorted(items, key=lambda item: item[group_field])
            item_groups = [list(items_group) for _, items_group in itertools.groupby(
                sorted_items,
                lambda item: item[group_field]
            )]
        for items_group in item_groups:
            try:
                group_value = sum(item[data_field] for item in items_group)
                for item in items_group:
                    item[f"{data_field}_percent"] = item[data_field] / group_value
            except Exception as e:
                for item in items_group:
                    item[f"{data_field}_percent"] = None

        return items

    def paginate_items(self, items, options):
        page_size = options.get("page_size", 40)

        page = options.get("page", 1)

        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        return items[start_index:end_index]


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
                result = "No Data"
                # print(f"{column['key']} with not a number", item, item[column["key"]])
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
            value = BackendReportSubtotalService.get_item_value(
                item, weighted_average_key
            )
            if value:
                total += value
        if total:
            for item in items:
                item_val = BackendReportSubtotalService.get_item_value(item, column_key)
                if not isinstance(item_val, (int, float)):
                    result = "No Data"
                    break
                else:
                    value = BackendReportSubtotalService.get_item_value(
                        item, weighted_average_key
                    )
                    if isinstance(value, (int, float)):
                        average = float(value) / total
                        result += float(item_val) * average
        else:
            print(f"{weighted_average_key} totals is", total, column_key)
            result = "No Data"
        return result

    @staticmethod
    def resolve_subtotal_function(items, column):
        # szhitenev 2023-12-21
        # implement other formulas
        if (
            "report_settings" in column
            and "subtotal_formula_id" in column["report_settings"]
        ):

            formula_id = column["report_settings"]["subtotal_formula_id"]
            if formula_id == 1:
                return BackendReportSubtotalService.sum(items, column)
            elif formula_id == 2:
                return BackendReportSubtotalService.get_weighted_value(
                    items, column["key"], "market_value"
                )
            elif formula_id == 3:
                return BackendReportSubtotalService.get_weighted_value(
                    items, column["key"], "market_value_percent"
                )
            elif formula_id == 4:
                return BackendReportSubtotalService.get_weighted_value(
                    items, column["key"], "exposure"
                )
            elif formula_id == 5:
                return BackendReportSubtotalService.get_weighted_value(
                    items, column["key"], "exposure_percent"
                )
            elif formula_id == 6:
                return BackendReportSubtotalService.get_weighted_average_value(
                    items, column["key"], "market_value"
                )
            elif formula_id == 7:
                return BackendReportSubtotalService.get_weighted_average_value(
                    items, column["key"], "market_value_percent"
                )
            elif formula_id == 8:
                return BackendReportSubtotalService.get_weighted_average_value(
                    items, column["key"], "exposure"
                )
            elif formula_id == 9:
                return BackendReportSubtotalService.get_weighted_average_value(
                    items, column["key"], "exposure_percent"
                )

    @staticmethod
    def calculate(items, columns):
        return {
            column["key"]: BackendReportSubtotalService.resolve_subtotal_function(
                items, column
            )
            for column in columns
            if column["value_type"] == 20
        }

    @staticmethod
    def calculate_column(items, column):
        return {
            column["key"]: BackendReportSubtotalService.resolve_subtotal_function(
                items, column
            )
        }
