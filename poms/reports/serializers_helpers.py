def serialize_price_checker_item(item):
    result = {
        "type": item["type"]
    }

    if "name" in item:
        result["name"] = item["name"]

    if "user_code" in item:
        result["user_code"] = item["user_code"]

    if "id" in item:
        result["id"] = item["id"]

    if "position_size" in item:
        result["position_size"] = item["position_size"]

    if "accounting_date" in item:
        result["accounting_date"] = item["accounting_date"]

    if "transaction_currency_id" in item:
        result["transaction_currency_id"] = item["transaction_currency_id"]

    if "transaction_currency_name" in item:
        result["transaction_currency_name"] = item["transaction_currency_name"]

    if "transaction_currency_user_code" in item:
        result["transaction_currency_user_code"] = item["transaction_currency_user_code"]

    if "settlement_currency_name" in item:
        result["settlement_currency_name"] = item["settlement_currency_name"]

    if "settlement_currency_user_code" in item:
        result["settlement_currency_user_code"] = item["settlement_currency_user_code"]

    return result


def serialize_price_checker_item_instrument(item):
    # id', 'instrument_type',  'user_code', 'name', 'short_name',
    # 'public_name', 'notes',
    # 'pricing_currency', 'price_multiplier',
    # 'accrued_currency',  'accrued_multiplier',
    # 'default_price', 'default_accrued',
    # 'user_text_1', 'user_text_2', 'user_text_3',
    # 'reference_for_pricing',
    # 'payment_size_detail',
    # 'daily_pricing_model',
    # 'maturity_date', 'maturity_price'

    attributes = []

    for attribute in item.attributes.all():

        attr_result = {
            "id": attribute.id,
            "attribute_type": attribute.attribute_type_id,
            "attribute_type_object": {
                "id": attribute.attribute_type.id,
                "user_code": attribute.attribute_type.user_code,
                "name": attribute.attribute_type.name,
                "short_name": attribute.attribute_type.short_name,
                "value_type": attribute.attribute_type.value_type
            },
            "value_string": attribute.value_string,
            "value_float": attribute.value_float,
            "value_date": attribute.value_date,
            "classifier": attribute.classifier_id
        }

        if attribute.classifier_id:
            attr_result["classifier_object"] = {
                "id": attribute.classifier.id,
                "name": attribute.classifier.name
            }

        attributes.append(attr_result)

    pricing_policies = []

    for policy in item.pricing_policies.all():

        policy_result = {
            "id": policy.id,
            "pricing_policy": policy.pricing_policy_id
        }

        if policy.pricing_scheme_id:
            policy_result["pricing_scheme"] = policy.pricing_scheme_id,
            policy_result["pricing_scheme_object"] = {
                "id": policy.pricing_scheme.id,
                "user_code": policy.pricing_scheme.user_code,
                "name": policy.pricing_scheme.name,
            }

        pricing_policies.append(policy_result)

    instrument_type = {
        "id": item.instrument_type.id,
        "name": item.instrument_type.name,
        "user_code": item.instrument_type.user_code,
        "short_name": item.instrument_type.short_name
    }

    result = {
        "id": item.id,
        "name": item.name,
        "short_name": item.short_name,
        "user_code": item.user_code,
        "public_name": item.public_name,
        "pricing_currency": item.pricing_currency_id,
        "price_multiplier": item.price_multiplier,
        "accrued_currency": item.accrued_currency_id,
        "accrued_multiplier": item.accrued_multiplier,
        "default_accrued": item.default_accrued,
        "default_price": item.price_multiplier,
        "user_text_1": item.user_text_1,
        "user_text_2": item.user_text_2,
        "user_text_3": item.user_text_3,
        "reference_for_pricing": item.reference_for_pricing,
        "payment_size_detail": item.payment_size_detail_id,
        "maturity_date": item.maturity_date,
        "attributes": attributes,
        "pricing_policies": pricing_policies,
        "instrument_type": item.instrument_type.id,
        "instrument_type_object": instrument_type

    }

    return result


def serialize_transaction_report_item(item):
    result = {
        "id": item.get("id", None),

        "is_locked": item.get("is_locked", None),
        "is_canceled": item.get("is_canceled", None),
        "notes": item.get("notes", None),
        "transaction_code": item.get("transaction_code", None),
        "transaction_class": item.get("transaction_class_id", None),
        "complex_transaction": item.get("complex_transaction_id", None),

        "portfolio": item.get("portfolio_id", None),
        "counterparty": item.get("counterparty_id", None),
        "responsible": item.get("responsible_id", None),
        "settlement_currency": item.get("settlement_currency_id", None),
        "transaction_currency": item.get("transaction_currency_id", None),

        "account_cash": item.get("account_cash_id", None),
        "account_interim": item.get("account_interim_id", None),
        "account_position": item.get("account_position_id", None),

        "allocation_balance": item.get("allocation_balance_id", None),
        "allocation_pl": item.get("allocation_pl_id", None),
        "instrument": item.get("instrument_id", None),
        "linked_instrument": item.get("linked_instrument_id", None),

        "cash_consideration": item.get("cash_consideration", None),
        "carry_amount": item.get("carry_amount", None),
        "carry_with_sign": item.get("carry_with_sign", None),
        "overheads_with_sign": item.get("overheads_with_sign", None),
        "factor": item.get("factor", None),
        "position_amount": item.get("position_amount", None),
        "position_size_with_sign": item.get("position_size_with_sign", None),
        "principal_amount": item.get("principal_amount", None),
        "principal_with_sign": item.get("principal_with_sign", None),
        "reference_fx_rate": item.get("reference_fx_rate", None),
        "trade_price": item.get("trade_price", None),

        "cash_date": item.get("cash_date", None),
        "accounting_date": item.get("accounting_date", None),
        "transaction_date": item.get("transaction_date", None),

        "strategy1_cash": item.get("strategy1_cash_id", None),
        "strategy1_position": item.get("strategy1_position_id", None),

        "strategy2_cash": item.get("strategy2_cash_id", None),
        "strategy2_position": item.get("strategy2_position_id", None),

        "strategy3_cash": item.get("strategy3_cash_id", None),
        "strategy3_position": item.get("strategy3_position_id", None),

    }

    result['transaction_item_name'] = item['transaction_item_name']
    result['transaction_item_short_name'] = item['transaction_item_short_name']
    result['transaction_item_user_code'] = item['transaction_item_user_code']

    # Complex Transaction Fields

    # result['complex_transaction.status'] = item['complex_transaction_status']
    result['complex_transaction.code'] = item['complex_transaction_code']
    result['complex_transaction.text'] = item['complex_transaction_text']
    result['complex_transaction.date'] = item['complex_transaction_date']
    result['complex_transaction.transaction_unique_code'] = item['transaction_unique_code']
    result['complex_transaction.is_canceled'] = item['is_canceled']
    result['complex_transaction.is_locked'] = item['is_locked']

    result['complex_transaction.user_text_1'] = item['complex_transaction_user_text_1']
    result['complex_transaction.user_text_2'] = item['complex_transaction_user_text_2']
    result['complex_transaction.user_text_3'] = item['complex_transaction_user_text_3']
    result['complex_transaction.user_text_4'] = item['complex_transaction_user_text_4']
    result['complex_transaction.user_text_5'] = item['complex_transaction_user_text_5']
    result['complex_transaction.user_text_6'] = item['complex_transaction_user_text_6']
    result['complex_transaction.user_text_7'] = item['complex_transaction_user_text_7']
    result['complex_transaction.user_text_8'] = item['complex_transaction_user_text_8']
    result['complex_transaction.user_text_9'] = item['complex_transaction_user_text_9']
    result['complex_transaction.user_text_10'] = item['complex_transaction_user_text_10']
    result['complex_transaction.user_text_11'] = item['complex_transaction_user_text_11']
    result['complex_transaction.user_text_12'] = item['complex_transaction_user_text_12']
    result['complex_transaction.user_text_13'] = item['complex_transaction_user_text_13']
    result['complex_transaction.user_text_14'] = item['complex_transaction_user_text_14']
    result['complex_transaction.user_text_15'] = item['complex_transaction_user_text_15']
    result['complex_transaction.user_text_16'] = item['complex_transaction_user_text_16']
    result['complex_transaction.user_text_17'] = item['complex_transaction_user_text_17']
    result['complex_transaction.user_text_18'] = item['complex_transaction_user_text_18']
    result['complex_transaction.user_text_19'] = item['complex_transaction_user_text_19']
    result['complex_transaction.user_text_20'] = item['complex_transaction_user_text_20']

    result['complex_transaction.user_number_1'] = item['complex_transaction_user_number_1']
    result['complex_transaction.user_number_2'] = item['complex_transaction_user_number_2']
    result['complex_transaction.user_number_3'] = item['complex_transaction_user_number_3']
    result['complex_transaction.user_number_4'] = item['complex_transaction_user_number_4']
    result['complex_transaction.user_number_5'] = item['complex_transaction_user_number_5']
    result['complex_transaction.user_number_6'] = item['complex_transaction_user_number_6']
    result['complex_transaction.user_number_7'] = item['complex_transaction_user_number_7']
    result['complex_transaction.user_number_8'] = item['complex_transaction_user_number_8']
    result['complex_transaction.user_number_9'] = item['complex_transaction_user_number_9']
    result['complex_transaction.user_number_10'] = item['complex_transaction_user_number_10']
    result['complex_transaction.user_number_11'] = item['complex_transaction_user_number_11']
    result['complex_transaction.user_number_12'] = item['complex_transaction_user_number_12']
    result['complex_transaction.user_number_13'] = item['complex_transaction_user_number_13']
    result['complex_transaction.user_number_14'] = item['complex_transaction_user_number_14']
    result['complex_transaction.user_number_15'] = item['complex_transaction_user_number_15']
    result['complex_transaction.user_number_16'] = item['complex_transaction_user_number_16']
    result['complex_transaction.user_number_17'] = item['complex_transaction_user_number_17']
    result['complex_transaction.user_number_18'] = item['complex_transaction_user_number_18']
    result['complex_transaction.user_number_19'] = item['complex_transaction_user_number_19']
    result['complex_transaction.user_number_20'] = item['complex_transaction_user_number_20']

    result['complex_transaction.user_date_1'] = item['complex_transaction_user_date_1']
    result['complex_transaction.user_date_2'] = item['complex_transaction_user_date_2']
    result['complex_transaction.user_date_3'] = item['complex_transaction_user_date_3']
    result['complex_transaction.user_date_4'] = item['complex_transaction_user_date_4']
    result['complex_transaction.user_date_5'] = item['complex_transaction_user_date_5']

    # Complex Transaction Transaction Type Fields

    result['complex_transaction.transaction_type.id'] = item['transaction_type_id']
    result['complex_transaction.transaction_type.user_code'] = item['transaction_type_user_code']
    result['complex_transaction.transaction_type.name'] = item['transaction_type_name']
    result['complex_transaction.transaction_type.short_name'] = item['transaction_type_short_name']
    result['complex_transaction.transaction_type.group'] = item['transaction_type_group_name']

    result['complex_transaction.status.name'] = item['complex_transaction_status_name']

    result['entry_account'] = item['entry_account']
    result['entry_strategy'] = item['entry_strategy']
    result['entry_item_short_name'] = item['entry_item_short_name']
    result['entry_item_user_code'] = item['entry_item_user_code']
    result['entry_item_name'] = item['entry_item_name']
    result['entry_item_public_name'] = item['entry_item_public_name']
    result['entry_currency'] = item['entry_currency']
    result['entry_instrument'] = item['entry_instrument']
    result['entry_amount'] = item['entry_amount']
    result['entry_item_type'] = item['entry_item_type']
    result['entry_item_type_name'] = item['entry_item_type_name']

    return result


def serialize_balance_report_item(item):
    result = {
        # "id": ','.join(str(x) for x in item['pk']),
        "id": '-',
        "name": item["name"],
        "short_name": item["short_name"],
        "user_code": item["user_code"],
        "portfolio": item["portfolio_id"],
        "item_type": item["item_type"],
        "item_type_name": item["item_type_name"],
    }

    if item["instrument_id"] == -1:
        result["instrument"] = None
    else:
        result["instrument"] = item["instrument_id"]

    if item["currency_id"] == -1:
        result["currency"] = None
    else:
        result["currency"] = item["currency_id"]

    if item["pricing_currency_id"] == -1:
        result["pricing_currency"] = None
    else:
        result["pricing_currency"] = item["pricing_currency_id"]

    if item["exposure_currency_id"] == -1:
        result["exposure_currency"] = None
    else:
        result["exposure_currency"] = item["exposure_currency_id"]

    if item["allocation_pl_id"] == -1:
        result["allocation"] = None
    else:
        result["allocation"] = item["allocation_pl_id"]



    # Check if logic is right
    result["instrument_pricing_currency_fx_rate"] = item["instrument_pricing_currency_fx_rate"]
    result["instrument_accrued_currency_fx_rate"] = item["instrument_accrued_currency_fx_rate"]
    result["instrument_principal_price"] = item["instrument_principal_price"]
    result["instrument_accrued_price"] = item["instrument_accrued_price"]
    result["instrument_factor"] = item["instrument_factor"]

    result["account"] = item["account_position_id"]

    result["strategy1"] = item["strategy1_position_id"]
    result["strategy2"] = item["strategy2_position_id"]
    result["strategy3"] = item["strategy3_position_id"]

    ids = []
    ids.append(str(result["item_type"])) # if of item type

    if item['item_type'] == 1:
        ids.append(str(result["instrument"])) # id of instrument

    if item['item_type'] == 2:
        ids.append(str(result["currency"])) # id of currency

    ids.append(str(result["portfolio"]))
    ids.append(str(result["account"]))
    ids.append(str(result["strategy1"]))
    ids.append(str(result["strategy2"]))
    ids.append(str(result["strategy3"]))

    result['id'] = ','.join(ids)

    # result["pricing_currency"] = item["pricing_currency_id"]
    # result["currency"] = None

    result["price"] = item["price"]
    result["fx_rate"] = item["fx_rate"]

    result["position_size"] = item["position_size"]
    result["nominal_position_size"] = item["nominal_position_size"]

    result["market_value"] = item["market_value"]
    result["market_value_loc"] = item["market_value_loc"]
    result["exposure"] = item["exposure"]
    result["exposure_loc"] = item["exposure_loc"]

    result["ytm"] = item["ytm"]
    result["ytm_at_cost"] = item["ytm_at_cost"]
    result["modified_duration"] = item["modified_duration"]
    result["return_annually"] = item["return_annually"]

    result["position_return"] = item["position_return"]
    result["position_return_loc"] = item["position_return_loc"]
    result["net_position_return"] = item["net_position_return"]
    result["net_position_return_loc"] = item["net_position_return_loc"]

    result["net_cost_price"] = item["net_cost_price"]
    result["net_cost_price_loc"] = item["net_cost_price_loc"]
    result["gross_cost_price"] = item["gross_cost_price"]
    result["gross_cost_price_loc"] = item["gross_cost_price_loc"]

    result["principal_invested"] = item["principal_invested"]
    result["principal_invested_loc"] = item["principal_invested_loc"]

    result["amount_invested"] = item["amount_invested"]
    result["amount_invested_loc"] = item["amount_invested_loc"]

    result["time_invested"] = item["time_invested"]
    result["return_annually"] = item["return_annually"]

    # performance

    result["principal"] = item["principal"]
    result["carry"] = item["carry"]
    result["overheads"] = item["overheads"]
    result["total"] = item["total"]

    result["principal_fx"] = item["principal_fx"]
    result["carry_fx"] = item["carry_fx"]
    result["overheads_fx"] = item["overheads_fx"]
    result["total_fx"] = item["total_fx"]

    result["principal_fixed"] = item["principal_fixed"]
    result["carry_fixed"] = item["carry_fixed"]
    result["overheads_fixed"] = item["overheads_fixed"]
    result["total_fixed"] = item["total_fixed"]

    # loc started

    result["principal_loc"] = item["principal_loc"]
    result["carry_loc"] = item["carry_loc"]
    result["overheads_loc"] = item["overheads_loc"]
    result["total_loc"] = item["total_loc"]

    result["principal_fx_loc"] = item["principal_fx_loc"]
    result["carry_fx_loc"] = item["carry_fx_loc"]
    result["overheads_fx_loc"] = item["overheads_fx_loc"]
    result["total_fx_loc"] = item["total_fx_loc"]

    result["principal_fixed_loc"] = item["principal_fixed_loc"]
    result["carry_fixed_loc"] = item["carry_fixed_loc"]
    result["overheads_fixed_loc"] = item["overheads_fixed_loc"]
    result["total_fixed_loc"] = item["total_fixed_loc"]

    return result


def serialize_pl_report_item(item):
    result = {
        # "id": ','.join(str(x) for x in item['pk']),
        "id": '-',
        "name": item["name"],
        "short_name": item["short_name"],
        "user_code": item["user_code"],
        "portfolio": item["portfolio_id"],
        "item_type": item["item_type"],
        "item_type_name": item["item_type_name"],

        "item_group": item["item_group"],
        "item_group_code": item["item_group_code"],
        "item_group_name": item["item_group_name"]
    }

    # if item["item_type"] == 1:  # instrument
    if item["instrument_id"] == -1:
        result["instrument"] = None
    else:
        result["instrument"] = item["instrument_id"]

    if item["pricing_currency_id"] == -1:
        result["pricing_currency"] = None
    else:
        result["pricing_currency"] = item["pricing_currency_id"]

    if item["exposure_currency_id"] == -1:
        result["exposure_currency"] = None
    else:
        result["exposure_currency"] = item["exposure_currency_id"]

    if item["allocation_pl_id"] == -1:
        result["allocation"] = None
    else:
        result["allocation"] = item["allocation_pl_id"]

    result["account"] = item["account_position_id"]

    result["strategy1"] = item["strategy1_position_id"]
    result["strategy2"] = item["strategy2_position_id"]
    result["strategy3"] = item["strategy3_position_id"]

    # result["pricing_currency"] = item["pricing_currency_id"]
    # result["currency"] = None

    ids = []
    ids.append(str(result["item_type"]))
    ids.append(str(result["item_group"]))

    if item['item_type'] == 1:  # instrument
        ids.append(str(result["instrument"]))

    if item['item_type'] == 3:  # FX Variations
        ids.append(str(result["name"]))

    if item['item_type'] == 4:  # FX Trades
        ids.append(str(result["name"]))

    if item['item_type'] == 5:
        ids.append(str(result["name"]))

    if item['item_type'] == 6:  # mismatch
        ids.append(str(result["instrument"]))


    ids.append(str(result["portfolio"]))
    ids.append(str(result["account"]))
    ids.append(str(result["strategy1"]))
    ids.append(str(result["strategy2"]))
    ids.append(str(result["strategy3"]))
    ids.append(str(result["allocation"]))

    result['id'] = ','.join(ids)

    result["instrument_pricing_currency_fx_rate"] = item["instrument_pricing_currency_fx_rate"]
    result["instrument_accrued_currency_fx_rate"] = item["instrument_accrued_currency_fx_rate"]
    result["instrument_principal_price"] = item["instrument_principal_price"]
    result["instrument_accrued_price"] = item["instrument_accrued_price"]
    result["instrument_factor"] = item["instrument_factor"]

    #
    result["position_size"] = item["position_size"]
    result["nominal_position_size"] = item["nominal_position_size"]

    result["position_return"] = item["position_return"]
    result["position_return_loc"] = item["position_return_loc"]
    result["net_position_return"] = item["net_position_return"]
    result["net_position_return_loc"] = item["net_position_return_loc"]

    result["net_cost_price"] = item["net_cost_price"]
    result["net_cost_price_loc"] = item["net_cost_price_loc"]
    result["gross_cost_price"] = item["gross_cost_price"]
    result["gross_cost_price_loc"] = item["gross_cost_price_loc"]

    result["principal_invested"] = item["principal_invested"]
    result["principal_invested_loc"] = item["principal_invested_loc"]

    result["amount_invested"] = item["amount_invested"]
    result["amount_invested_loc"] = item["amount_invested_loc"]

    result["time_invested"] = item["time_invested"]

    result["mismatch"] = item["mismatch"]

    result["ytm"] = item["ytm"]
    result["ytm_at_cost"] = item["ytm_at_cost"]

    result["market_value"] = item["market_value"]
    result["market_value_loc"] = item["market_value_loc"]
    result["exposure"] = item["exposure"]
    result["exposure_loc"] = item["exposure_loc"]

    result["principal"] = item["principal"]
    result["carry"] = item["carry"]
    result["overheads"] = item["overheads"]
    result["total"] = item["total"]

    result["principal_fx"] = item["principal_fx"]
    result["carry_fx"] = item["carry_fx"]
    result["overheads_fx"] = item["overheads_fx"]
    result["total_fx"] = item["total_fx"]

    result["principal_fixed"] = item["principal_fixed"]
    result["carry_fixed"] = item["carry_fixed"]
    result["overheads_fixed"] = item["overheads_fixed"]
    result["total_fixed"] = item["total_fixed"]

    # loc started

    result["principal_loc"] = item["principal_loc"]
    result["carry_loc"] = item["carry_loc"]
    result["overheads_loc"] = item["overheads_loc"]
    result["total_loc"] = item["total_loc"]

    result["principal_fx_loc"] = item["principal_fx_loc"]
    result["carry_fx_loc"] = item["carry_fx_loc"]
    result["overheads_fx_loc"] = item["overheads_fx_loc"]
    result["total_fx_loc"] = item["total_fx_loc"]

    result["principal_fixed_loc"] = item["principal_fixed_loc"]
    result["carry_fixed_loc"] = item["carry_fixed_loc"]
    result["overheads_fixed_loc"] = item["overheads_fixed_loc"]
    result["total_fixed_loc"] = item["total_fixed_loc"]

    return result


def serialize_report_item_instrument(item):
    attributes = []

    for attribute in item.attributes.all():

        attr_result = {
            "id": attribute.id,
            "attribute_type": attribute.attribute_type_id,
            "attribute_type_object": {
                "id": attribute.attribute_type.id,
                "user_code": attribute.attribute_type.user_code,
                "name": attribute.attribute_type.name,
                "short_name": attribute.attribute_type.short_name,
                "value_type": attribute.attribute_type.value_type
            },
            "value_string": attribute.value_string,
            "value_float": attribute.value_float,
            "value_date": attribute.value_date,
            "classifier": attribute.classifier_id
        }

        if attribute.classifier_id:
            attr_result["classifier_object"] = {
                "id": attribute.classifier.id,
                "name": attribute.classifier.name
            }

        attributes.append(attr_result)

    instrument_type = {
        "id": item.instrument_type.id,
        "name": item.instrument_type.name,
        "user_code": item.instrument_type.user_code,
        "short_name": item.instrument_type.short_name
    }

    country = None
    country_id = None

    if item.country:
        country_id = item.country.id
        country = {
            "id": item.country.id,
            "name": item.country.name,
            "user_code": item.country.user_code,
            "country_code": item.country.country_code,
            "region": item.country.region,
            "region_code": item.country.region_code,
            "sub_region": item.country.sub_region,
            "sub_region_code": item.country.sub_region_code,
        }

    result = {
        "id": item.id,
        "name": item.name,
        "short_name": item.short_name,
        "user_code": item.user_code,
        "public_name": item.public_name,
        "pricing_currency": item.pricing_currency_id,
        "price_multiplier": item.price_multiplier,
        "accrued_currency": item.accrued_currency_id,
        "accrued_multiplier": item.accrued_multiplier,
        "default_accrued": item.default_accrued,
        "default_price": item.price_multiplier,
        "user_text_1": item.user_text_1,
        "user_text_2": item.user_text_2,
        "user_text_3": item.user_text_3,
        "reference_for_pricing": item.reference_for_pricing,
        "payment_size_detail": item.payment_size_detail_id,
        "maturity_date": item.maturity_date,
        "maturity_price": item.maturity_price,
        "attributes": attributes,
        "instrument_type": item.instrument_type.id,
        "instrument_type_object": instrument_type,
        "country": country_id,
        "country_object": country
    }

    return result
