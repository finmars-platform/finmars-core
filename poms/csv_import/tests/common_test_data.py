SCHEME_20 = {
    # "id": 20,
    # "master_user_id": 1,
    # "owner_id": 1,
    # "created_at": "2023-09-21 10:24:23.151372 +00:00",
    # "modified_at": "2024-01-16 11:59:51.299484 +00:00",
    # "content_type_id": 73,  instruments - pricehistory
    "user_code": "com.finmars.standard-import-from-file:instruments.pricehistory:price_from_file",
    "filter_expr": "",
    "classifier_handler": "skip",
    "delimiter": ",",
    "error_handler": "continue",
    "missing_data_handler": "throw_error",
    "mode": "overwrite",
    "is_enabled": True,
    "name": "STD - Prices (from File)",
    "notes": None,
    "public_name": None,
    "short_name": "STD - Prices (from File)",
    "spreadsheet_start_cell": "A1",
    "spreadsheet_active_tab_name": "",
    "column_matcher": "name",
    "instrument_reference_column": "",
    "item_post_process_script": "",
    "data_preprocess_expression": "",
    "configuration_code": "com.finmars.standard-import-from-file",
    "deleted_user_code": None,
    "is_deleted": False,
}

SCHEME_20_FIELDS = [
    {
        "column": 1,
        "name": "date",
        "column_name": "Date",
        "name_expr": "universal_parse_date(str(date), yearfirst=True, dayfirst=False)",
        "scheme": None,
    },
    {
        "column": 2,
        "name": "instrument",
        "column_name": "Instrument",
        "name_expr": "str(instrument)",
        "scheme": None,
    },
    {
        "column": 3,
        "name": "principal_price",
        "column_name": "Principal Price",
        "name_expr": "float(principal_price)",
        "scheme": None,
    },
    {
        "column": 4,
        "name": "accrued_price",
        "column_name": "Accrued Price",
        "name_expr": "float(accrued_price)",
        "scheme": None,
    },
    {
        "column": 5,
        "name": "factor",
        "column_name": "Factor",
        "name_expr": "float(factor)",
        "scheme": None,
    },
    {
        "column": 6,
        "name": "ytm",
        "name_expr": "float(ytm)",
        "column_name": "YTM",
        "scheme": None,
    },
    {
        "column": 7,
        "name": "short_delta",
        "name_expr": "float(short_delta)",
        "column_name": "Short Delta",
        "scheme": None,
    },
    {
        "column": 8,
        "name": "modified_duration",
        "name_expr": "float(modified_duration)",
        "column_name": "Modified Duration",
        "scheme": None,
    },
    {
        "column": 9,
        "name": "is_temporary_price",
        "name_expr": "float(is_temporary_price)",
        "column_name": "Is Temporary Price",
        "scheme": None,
    },
    {
        "column": 10,
        "name": "long_delta",
        "name_expr": "float(long_delta)",
        "column_name": "Long Delta",
        "scheme": None,
    },
]

SCHEME_20_ENTITIES = [
    {
        "name": "instrument",
        "expression": "instrument",
        "system_property_key": "instrument",
        "scheme": None,
    },
    {
        "name": "pricing policy",
        "expression": "'com.finmars.standard-pricing:standard'",
        "system_property_key": "pricing_policy",
        "scheme": None,
    },
    {
        "name": "date",
        "expression": "date",
        "system_property_key": "date",
        "scheme": None,
    },
    {
        "name": "principal price",
        "expression": "principal_price",
        "system_property_key": "principal_price",
        "scheme": None,
    },
    {
        "name": "accrued price",
        "expression": "accrued_price",
        "system_property_key": "accrued_price",
        "scheme": None,
    },
    {
        "name": "factor",
        "expression": "factor",
        "system_property_key": "factor",
        "scheme": None,
    },
    {
        "name": "ytm",
        "expression": "ytm",
        "system_property_key": "ytm",
        "scheme": None,
    },
    {
        "name": "short_delta",
        "expression": "short_delta",
        "system_property_key": "short_delta",
        "scheme": None,
    },
    {
        "name": "modified_duration",
        "expression": "modified_duration",
        "system_property_key": "modified_duration",
        "scheme": None,
    },
    {
        "name": "is_temporary_price",
        "expression": "is_temporary_price",
        "system_property_key": "is_temporary_price",
        "scheme": None,
    },
    {
        "name": "long_delta",
        "expression": "long_delta",
        "system_property_key": "long_delta",
        "scheme": None,
    },
]


PRICE_HISTORY = [
    {
        "Date": "2024-01-05",
        "Instrument": "USP37341AA50",
        "Principal Price": 109.72,
        "Accrued Price": None,
        "Factor": None,
        "YTM": None,
        "Modified Duration": 1.1,
        "Long Delta": 1.1,
        "Short Delta": 1.1,
        "Is Temporary Price": False,
    }
]

PRICE_HISTORY_ITEM = {
    "date": "2024-01-05",
    "instrument": "USP37341AA50",
    "principal_price": 109.72,
    "accrued_price": None,
    "factor": None,
    "ytm": None,
    "modified_duration": 1.1,
    "long_delta": 1.1,
    "short_delta": 1.1,
    "is_temporary_price": False,
}


EXPECTED_RESULT_PRICE_HISTORY = {
    "conversion_inputs": {
        "accrued_price": None,
        "date": "2024-01-05",
        "factor": None,
        "instrument": "USP37341AA50",
        "principal_price": 109.72,
        "ytm": None,
        "modified_duration": 1.1,
        "long_delta": 1.1,
        "short_delta": 1.1,
        "is_temporary_price": False,
    },
    "error_message": "",
    "file_inputs": {
        "Accrued Price": None,
        "Date": "2024-01-05",
        "Factor": None,
        "Instrument": "USP37341AA50",
        "Principal Price": 109.72,
        "YTM": None,
        "Modified Duration": 1.1,
        "Long Delta": 1.1,
        "Short Delta": 1.1,
        "Is Temporary Price": False,
    },
    "final_inputs": {
        "date": "2024-01-05",
        "instrument": "USP37341AA50",
        "pricing_policy": "com.finmars.standard-pricing:standard",
        "principal_price": 109.72,
        "modified_duration": 1.1,
        "long_delta": 1.1,
        "short_delta": 1.1,
        "is_temporary_price": False,
    },
    "imported_items": None,
    "inputs": {
        "accrued_price": "None",
        "date": "2024-01-05",
        "factor": "None",
        "instrument": "USP37341AA50",
        "principal_price": "109.72",
        "ytm": None,
        "modified_duration": 1.1,
        "long_delta": 1.1,
        "short_delta": 1.1,
        "is_temporary_price": False,
    },
    "message": "",
    "raw_inputs": {
        "accrued_price": None,
        "date": "2024-01-05",
        "factor": None,
        "instrument": "USP37341AA50",
        "principal_price": 109.72,
        "ytm": None,
        "modified_duration": 1.1,
        "long_delta": 1.1,
        "short_delta": 1.1,
        "is_temporary_price": False,
    },
    "row_number": 1,
    "status": "init",
}


INSTRUMENT = {
    "instrument_type": 17,
    "instrument_type_object": {
        "id": 17,
        "instrument_class": 1,
        "instrument_class_object": {
            "id": 1,
            "user_code": "GENERAL",
            "name": "General Class",
            "description": "General Class",
        },
        "user_code": "local.poms.space00000:stock",
        "name": "stock",
        "short_name": "stock",
        "public_name": "stock",
        "instrument_form_layouts": None,
        "deleted_user_code": None,
        "meta": {
            "content_type": "instruments.instrumenttype",
            "app_label": "instruments",
            "model_name": "instrumenttype",
            "space_code": "space00000",
        },
    },
    "user_code": "CSVJGHVZFC",
    "name": "BOXUGKLYWOR",
    "short_name": "BSH",
    "public_name": None,
    "notes": None,
    "is_active": True,
    "is_deleted": False,
    "has_linked_with_portfolio": False,
    "pricing_currency": 28,
    "pricing_currency_object": {
        "id": 28,
        "user_code": "EUR",
        "name": "EUR - Euro",
        "short_name": "EUR",
        "deleted_user_code": None,
        "meta": {
            "content_type": "currencies.currency",
            "app_label": "currencies",
            "model_name": "currency",
            "space_code": "space00000",
        },
    },
    "price_multiplier": 1.0,
    "accrued_currency": 28,
    "accrued_currency_object": {
        "id": 28,
        "user_code": "EUR",
        "name": "EUR - Euro",
        "short_name": "EUR",
        "deleted_user_code": None,
        "meta": {
            "content_type": "currencies.currency",
            "app_label": "currencies",
            "model_name": "currency",
            "space_code": "space00000",
        },
    },
    "accrued_multiplier": 1.0,
    "payment_size_detail": 1,
    "payment_size_detail_object": {
        "id": 1,
        "user_code": "PERCENT",
        "name": "% per annum",
        "description": "% per annum",
    },
    "default_price": 0.0,
    "default_accrued": 0.0,
    "user_text_1": "JBYWDPLZLI",
    "user_text_2": "FHHMHMVRER",
    "user_text_3": "SHASFYKQLJ",
    "reference_for_pricing": "",
    "daily_pricing_model": 6,
    "daily_pricing_model_object": {
        "id": 6,
        "user_code": "-",
        "name": "Use Default Price (no Price History)",
        "description": "Use Default Price (no Price History)",
    },
    "pricing_condition": 1,
    "pricing_condition_object": {
        "id": 1,
        "user_code": "NO_VALUATION",
        "name": "Don't Run Valuation",
        "description": "Don't Run Valuation",
    },
    "maturity_date": None,
    "maturity_price": 0.0,
    "manual_pricing_formulas": [],
    "accrual_calculation_schedules": [
        {
            "id": 4,
            "accrual_start_date": None,
            "accrual_start_date_value_type": 40,
            "first_payment_date": None,
            "first_payment_date_value_type": 40,
            "accrual_size": "0.598345055004762",
            "accrual_size_value_type": 20,
            "periodicity_n": "30",
            "periodicity_n_value_type": 20,
            "accrual_calculation_model": 2,
            "accrual_calculation_model_object": {
                "id": 2,
                "user_code": "ACT_ACT",
                "name": "ACT/ACT",
                "description": "ACT/ACT",
            },
            "periodicity": 1,
            "periodicity_object": {
                "id": 1,
                "user_code": "N_DAY",
                "name": "N Days",
                "description": "N Days",
            },
            "notes": "",
        }
    ],
    "factor_schedules": [
        {
            "effective_date": "2024-05-21",
            "factor_value": 0.2278459186631061,
        }
    ],
    "event_schedules": [],
    "is_enabled": True,
    "pricing_policies": [],
    "exposure_calculation_model": 1,
    "exposure_calculation_model_object": {
        "id": 1,
        "user_code": "MARKET_VALUE",
        "name": "Market value",
        "description": "Market value",
    },
    "co_directional_exposure_currency": 28,
    "counter_directional_exposure_currency": None,
    "co_directional_exposure_currency_object": {
        "id": 28,
        "user_code": "EUR",
        "name": "EUR - Euro",
        "short_name": "EUR",
        "deleted_user_code": None,
        "meta": {
            "content_type": "currencies.currency",
            "app_label": "currencies",
            "model_name": "currency",
            "space_code": "space00000",
        },
    },
    "counter_directional_exposure_currency_object": {
        "id": 28,
        "user_code": "EUR",
        "name": "EUR - Euro",
        "short_name": "EUR",
        "deleted_user_code": None,
        "meta": {
            "content_type": "currencies.currency",
            "app_label": "currencies",
            "model_name": "currency",
            "space_code": "space00000",
        },
    },
    "long_underlying_instrument": None,
    "short_underlying_instrument": None,
    "long_underlying_instrument_object": None,
    "short_underlying_instrument_object": None,
    "underlying_long_multiplier": 1.0,
    "underlying_short_multiplier": 1.0,
    "long_underlying_exposure": 1,
    "short_underlying_exposure": 1,
    "position_reporting": 1,
    "country": 112,
    "country_object": {
        "id": 112,
        "name": "Italy",
        "user_code": "Italy",
        "country_code": "380",
        "region": "Europe",
        "region_code": "150",
        "alpha_2": "IT",
        "alpha_3": "ITA",
        "sub_region": "Southern Europe",
        "sub_region_code": "039",
    },
    "deleted_user_code": None,
    "attributes": [
        {
            "id": 4,
            "attribute_type": 4,
            "value_string": "PGBZBAEROP",
            "value_float": 6897.0,
            "value_date": "2023-07-21",
            "classifier": None,
            "attribute_type_object": {
                "id": 4,
                "user_code": "local.poms.space00000:auth.permission:tbylo",
                "name": "",
                "short_name": "PC",
                "public_name": None,
                "notes": None,
                "can_recalculate": False,
                "value_type": 20,
                "order": 0,
                "is_hidden": False,
                "kind": 1,
            },
            "classifier_object": None,
        }
    ],
    "meta": {
        "content_type": "instruments.instrument",
        "app_label": "instruments",
        "model_name": "instrument",
        "space_code": "space00000",
    },
}


# PORTFOLIO

SCHEME_PORTFOLIO_FIELDS = [
    {
        "column": 1,
        "name": "temp_portfolio",
        "name_expr": "str(temp_portfolio)",
        "column_name": "Portfolio",
        "scheme": None,
    },
    {
        "column": 1,
        "name": "portfolio_type",
        "name_expr": "portfolio_type",
        "column_name": "portfolio_type",
        "scheme": None,
    },
]

SCHEME_PORTFOLIO_ENTITIES = [
    {
        "name": "portfolio type",
        "expression": "portfolio_type",
        "system_property_key": "portfolio_type",
        "scheme": None,
    },
    {
        "name": "user code",
        "expression": "temp_portfolio",
        "system_property_key": "user_code",
        "scheme": None,
    },
    {
        "name": "name",
        "expression": "temp_portfolio",
        "system_property_key": "name",
        "scheme": None,
    },
    {
        "name": "short name",
        "expression": "temp_portfolio",
        "system_property_key": "short_name",
        "scheme": None,
    },
    {
        "name": "public name",
        "expression": "temp_portfolio",
        "system_property_key": "public_name",
        "scheme": None,
    },
    {
        "name": "notes",
        "expression": "'-'",
        "system_property_key": "notes",
        "scheme": None,
    },
]

PORTFOLIO = [
    {
        "Portfolio": "Test",
        "portfolio_type": "com.finmars.test_01",
    },
]

PORTFOLIO_ITEM = {
    "portfolio_type": "com.finmars.test_01",
    "temp_portfolio": "Test",
}

BAD_PORTFOLIO_ITEM = {
    "portfolio_type": None,
    "temp_portfolio": "Test",
}

EXPECTED_RESULT_PORTFOLIO = {
    "conversion_inputs": {"portfolio_type": "1", "temp_portfolio": "Test"},
    "error_message": "",
    "file_inputs": {"Portfolio": "Test", "portfolio_type": "1"},
    "final_inputs": {
        "name": "Test",
        "notes": "-",
        "portfolio_type": "com.finmars.test_01",
        "public_name": "Test",
        "short_name": "Test",
        "user_code": "Test",
    },
    "imported_items": [{"id": 13, "user_code": "Test"}],
    "inputs": {"portfolio_type": "1", "temp_portfolio": "Test"},
    "message": "Item Imported Test",
    "raw_inputs": {"portfolio_type": "1", "temp_portfolio": "Test"},
    "row_number": 1,
    "status": "success",
}

# Accrual Calculation Schedule

SCHEME_ACCRUAL_CALCULATION_FIELDS = [
    {
        "column": 1,
        "name": "instrument",
        "name_expr": "instrument",
        "column_name": "instrument",
        "scheme": None,
    },
    {
        "column": 2,
        "name": "accrual_start_date",
        "name_expr": "accrual_start_date",
        "column_name": "accrual_start_date",
        "scheme": None,
    },
    {
        "column": 3,
        "name": "first_payment_date",
        "name_expr": "first_payment_date",
        "column_name": "first_payment_date",
        "scheme": None,
    },
    {
        "column": 4,
        "name": "accrual_calculation_model",
        "name_expr": "accrual_calculation_model",
        "column_name": "accrual_calculation_model",
        "scheme": None,
    },
    {
        "column": 5,
        "name": "periodicity",
        "name_expr": "periodicity",
        "column_name": "periodicity",
        "scheme": None,
    },
    {
        "column": 6,
        "name": "accrual_size",
        "name_expr": "float(accrual_size)",
        "column_name": "accrual_size",
        "scheme": None,
    },
    {
        "column": 7,
        "name": "periodicity_n",
        "name_expr": "periodicity_n",
        "column_name": "periodicity_n",
        "scheme": None,
    },
    {
        "column": 8,
        "name": "end_of_month",
        "name_expr": "end_of_month",
        "column_name": "end_of_month",
        "scheme": None,
    },
]


SCHEME_ACCRUAL_CALCULATION_ENTITIES = [
    {
        "name": "first payment date",
        "expression": "first_payment_date",
        "system_property_key": "first_payment_date",
        "scheme": None,
    },
    {
        "name": "instrument",
        "expression": "instrument",
        "system_property_key": "instrument",
        "scheme": None,
    },
    {
        "name": "accrual size",
        "expression": "accrual_size",
        "system_property_key": "accrual_size",
        "scheme": None,
    },
    {
        "name": "accrual calculation model",
        "expression": "accrual_calculation_model",
        "system_property_key": "accrual_calculation_model",
        "scheme": None,
    },
    {
        "name": "periodicity",
        "expression": "periodicity",
        "system_property_key": "periodicity",
        "scheme": None,
    },
    {
        "name": "accrual start date",
        "expression": "accrual_start_date",
        "system_property_key": "accrual_start_date",
        "scheme": None,
    },
    {
        "name": "periodicity n",
        "expression": "periodicity_n",
        "system_property_key": "periodicity_n",
        "scheme": None,
    },
    {
        "name": "notes",
        "expression": "",
        "system_property_key": "notes",
        "scheme": None,
    },
    {
        "name": "EOM",
        "expression": "end_of_month",
        "system_property_key": "eom",
        "scheme": None,
    },
]


ACCRUAL_CALCULATION = [
    {
        "instrument": "commitment-startup-2-round-a-debt",
        "accrual_start_date": 20171122,
        "first_payment_date": 20171122,
        "accrual_calculation_model": "DAY_COUNT_30E_360",
        "periodicity": "ANNUALLY",
        "periodicity_n": None,
        "accrual_size": 4.5,
        "end_of_month": False,
    },
]


ACCRUAL_CALCULATION_ITEM = {
    "instrument": "commitment-startup-2-round-a-debt",
    "accrual_start_date": 20171122,
    "first_payment_date": 20171122,
    "accrual_calculation_model": "DAY_COUNT_30E_360",
    "periodicity": "ANNUALLY",
    "periodicity_n": None,
    "accrual_size": 4.5,
    "end_of_month": False,
}


BAD_ACCRUAL_CALCULATION_ITEM = {
    "instrument": "commitment-startup-2-round-a-debt",
    "accrual_start_date": None,
    "first_payment_date": 20171122,
    "accrual_calculation_model": "DAY_COUNT_30E_360",
    "periodicity": "ANNUALLY",
    "periodicity_n": None,
    "accrual_size": 4.5,
    "end_of_month": False,
}


EXPECTED_RESULT_ACCRUAL_CALCULATION = {
    "conversion_inputs": {
        "accrual_calculation_model": "DAY_COUNT_30E_360",
        "accrual_size": 4.5,
        "accrual_start_date": 20171122,
        "end_of_month": False,
        "first_payment_date": 20171122,
        "instrument": "commitment-startup-2-round-a-debt",
        "periodicity": "ANNUALLY",
        "periodicity_n": None,
    },
    "error_message": "",
    "file_inputs": {
        "accrual_calculation_model": "DAY_COUNT_30E_360",
        "accrual_size": 4.5,
        "accrual_start_date": 20171122,
        "end_of_month": False,
        "first_payment_date": 20171122,
        "instrument": "commitment-startup-2-round-a-debt",
        "periodicity": "ANNUALLY",
        "periodicity_n": None,
    },
    "final_inputs": {
        "accrual_calculation_model": "DAY_COUNT_30E_360",
        "accrual_size": 4.5,
        "accrual_start_date": 20171122,
        "eom": False,
        "first_payment_date": 20171122,
        "instrument": "commitment-startup-2-round-a-debt",
        "notes": None,
        "periodicity": "ANNUALLY",
        "periodicity_n": None,
    },
    "imported_items": [
        {
            "id": 99,
            "user_code": "2017-11-22",
        }
    ],
    "inputs": {
        "accrual_calculation_model": "DAY_COUNT_30E_360",
        "accrual_id": "commitment-startup-2-round-a-debt",
        "accrual_size": "4.5",
        "accrual_start_date": "20171122",
        "end_of_month": "False",
        "first_payment_date": "20171122",
        "instrument": "commitment-startup-2-round-a-debt",
        "periodicity": "ANNUALLY",
        "periodicity_n": "None",
    },
    "message": "Item Imported 2017-11-22",
    "raw_inputs": {
        "accrual_calculation_model": "DAY_COUNT_30E_360",
        "accrual_id": "commitment-startup-2-round-a-debt",
        "accrual_size": 4.5,
        "accrual_start_date": 20171122,
        "end_of_month": False,
        "first_payment_date": 20171122,
        "instrument": "commitment-startup-2-round-a-debt",
        "periodicity": "ANNUALLY",
        "periodicity_n": None,
    },
    "row_number": 1,
    "status": "success",
}


# Currency

SCHEME_CURRENCY_FIELDS = [
    {
        "column": 1,
        "name": "user_code",
        "name_expr": "user_code",
        "column_name": "user_code",
        "scheme": None,
    },
    {
        "column": 2,
        "name": "name",
        "name_expr": "name",
        "column_name": "name",
        "scheme": None,
    },
    {
        "column": 3,
        "name": "short_name",
        "name_expr": "short_name",
        "column_name": "short_name",
        "scheme": None,
    },
    {
        "column": 4,
        "name": "public_name",
        "name_expr": "public_name",
        "column_name": "public_name",
        "scheme": None,
    },
    {
        "column": 5,
        "name": "notes",
        "name_expr": "notes",
        "column_name": "notes",
        "scheme": None,
    },
    {
        "column": 6,
        "name": "reference_for_pricing",
        "name_expr": "reference_for_pricing",
        "column_name": "reference_for_pricing",
        "scheme": None,
    },
    {
        "column": 7,
        "name": "pricing_condition",
        "name_expr": "pricing_condition",
        "column_name": "pricing_condition",
        "scheme": None,
    },
    {
        "column": 8,
        "name": "default_fx_rate",
        "name_expr": "default_fx_rate",
        "column_name": "default_fx_rate",
        "scheme": None,
    },
    {
        "column": 9,
        "name": "country",
        "name_expr": "country_obj = universal_parse_country(str(if_null(country,'-')))\nif country_obj:\n    country_obj['user_code']",
        "column_name": "country",
        "scheme": None,
    },
]


SCHEME_CURRENCY_ENTITIES = [
    {
        "name": "Country",
        "expression": "country",
        "system_property_key": "country",
        "scheme": None,
    },
    {
        "name": "user code",
        "expression": "user_code",
        "system_property_key": "user_code",
        "scheme": None,
    },
    {
        "name": "name",
        "expression": "name",
        "system_property_key": "name",
        "scheme": None,
    },
    {
        "name": "short name",
        "expression": "short_name",
        "system_property_key": "short_name",
        "scheme": None,
    },
    {
        "name": "public name",
        "expression": "public_name",
        "system_property_key": "public_name",
        "scheme": None,
    },
    {
        "name": "notes",
        "expression": "notes",
        "system_property_key": "notes",
        "scheme": None,
    },
    {
        "name": "reference for pricing",
        "expression": "reference_for_pricing",
        "system_property_key": "reference_for_pricing",
        "scheme": None,
    },
    {
        "name": "pricing condition",
        "expression": "if pricing_condition:\n    pricing_condition\nelse:\n    'RUN_VALUATION_IF_OPEN'",
        "system_property_key": "pricing_condition",
        "scheme": None,
    },
    {
        "name": "default fx rate",
        "expression": "default_fx_rate",
        "system_property_key": "default_fx_rate",
        "scheme": None,
    },
]


CURRENCY = {
    "country": "ALB",
    "user_code": "ALL",
    "name": "Albanian Lek",
    "short_name": "ALL",
    "public_name": "Public 1",
    "notes": "No notes",
    "reference_for_pricing": "Reference",
    "pricing_condition": "RUN_VALUATION_IF_OPEN",
    "default_fx_rate": "1",
}


CURRENCY_ITEM = {
    "country": "Albania",
    "user_code": "ALL",
    "name": "Albanian Lek",
    "short_name": "ALL",
    "public_name": "Public 1",
    "notes": "No notes",
    "reference_for_pricing": "Reference",
    "pricing_condition": "RUN_VALUATION_IF_OPEN",
    "default_fx_rate": "1",
}


EXPECTED_RESULT_CURRENCY = {
    "conversion_inputs": {
        "country": "Albania",
        "default_fx_rate": "1",
        "name": "Albanian Lek",
        "notes": "No notes",
        "pricing_condition": "RUN_VALUATION_IF_OPEN",
        "public_name": "Public 1",
        "reference_for_pricing": "Reference",
        "short_name": "ALL",
        "user_code": "ALL",
    },
    "error_message": "",
    "file_inputs": {
        "Country": "ALB",
        "Currency ID": "ALL",
        "Default FX Rate": "1",
        "Name": "Albanian Lek",
        "Notes": "No notes",
        "Pricing Condition": "RUN_VALUATION_IF_OPEN",
        "Pricing Reference": "Reference",
        "Public Name": "Public 1",
        "Short Name": "ALL",
    },
    "final_inputs": {
        "country": "Albania",
        "default_fx_rate": "1",
        "name": "Albanian Lek",
        "notes": "No notes",
        "pricing_condition": "RUN_VALUATION_IF_OPEN",
        "public_name": "Public 1",
        "reference_for_pricing": "Reference",
        "short_name": "ALL",
        "user_code": "ALL",
    },
    "imported_items": [{"id": 24, "user_code": "ALL"}],
    "inputs": {
        "country": "Albania",
        "default_fx_rate": "1",
        "name": "Albanian Lek",
        "notes": "No notes",
        "ccy_prc_cond": "RUN_VALUATION_IF_OPEN",
        "reference_for_pricing": "Reference",
        "public_name": "Public 1",
        "short_name": "ALL",
        "user_code": "ALL",
    },
    "message": "Item Imported ALL",
    "raw_inputs": {
        "country": "ALB",
        "default_fx_rate": "1",
        "name": "Albanian Lek",
        "notes": "No notes",
        "ccy_prc_cond": "RUN_VALUATION_IF_OPEN",
        "reference_for_pricing": "Reference",
        "public_name": "Public 1",
        "short_name": "ALL",
        "user_code": "ALL",
    },
    "row_number": 1,
    "status": "success",
}
