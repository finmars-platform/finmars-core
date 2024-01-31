# May be finish later.
# Needs doing:
# creation of QuerySet with report's items,
# test case for every type of filter
# (text contains, text select, number greater that, date from to etc.),

import unittest
from unittest.mock import Mock
import logging

from poms.common.common_base_test import BaseTestCase
from poms.common.filtering_handlers import handle_filters

_l = logging.getLogger('poms.common.tests')

# region Data for items
data6 = {
    "id": "1,11,2,1,1,1,1",
    "name": "Augusta Gold",
    "short_name": "Augusta Gold",
    "user_code": "Augusta Gold",
    "position_size": -1000,

    "instrument.id": 11,
    "instrument.name": "Augusta Gold",
    "instrument.short_name": "Augusta Gold",
    "instrument.user_code": "Augusta Gold",
    "instrument.public_name": "Augusta Gold",
    "instrument.maturity_date": "2001-01-01",

    "instrument.instrument_type.id": 13,
    "instrument.instrument_type.instrument_class": 1,
    "instrument.instrument_type.instrument_class_object": {
        "id": 1,
        "user_code": "GENERAL",
        "name": "General Class",
        "description": "General Class"
    },
    "instrument.instrument_type.user_code": "stocks",
    "instrument.instrument_type.name": "stocks",
    "instrument.instrument_type.short_name": "stocks",
    "instrument.instrument_type.public_name": "stocks",
    "instrument.instrument_type.notes": None,
    "instrument.instrument_type.deleted_user_code": None,
    "instrument.instrument_type.owner": {
        "id": 1,
        "username": "finmars01",
        "first_name": "",
        "last_name": "",
        "display_name": "finmars01",
        "is_owner": False,
        "is_admin": False,
        "user": 49
    },
    "instrument.instrument_type.meta": {
        "content_type": "instruments.instrumenttype",
        "app_label": "instruments",
        "model_name": "instrumenttype",
        "space_code": "space0fxf3"
    },
    "instrument.instrument_type_object": {
        "id": 13,
        "name": "stocks",
        "user_code": "stocks",
        "short_name": "stocks"
    },

    "instrument.country.id": 41,
    "instrument.country.user_code": "Canada",
    "instrument.country.name": "Canada",
    "instrument.country.short_name": "Canada",
    "instrument.country.meta": {
        "content_type": "instruments.country",
        "app_label": "instruments",
        "model_name": "country",
        "space_code": "space0fxf3"
    },
    "instrument.country_object": {
        "id": 41,
        "name": "Canada",
        "user_code": "Canada",
        "country_code": "124",
        "region": "Americas",
        "region_code": "019",
        "sub_region": "Northern America",
        "sub_region_code": "021"
    },

    "instrument.attributes.country_of_issuer": "Canada - CAN",
    "instrument.attributes.test_number": 12,
    "instrument.attributes.test_date": "9999-12-12",

    "custom_fields": [
        {
            "custom_field": 7,
            "user_code": "com.finmars.standard-layouts:country_of_risk",
            "value": "Invalid expression"
        },
        {
            "custom_field": 8,
            "user_code": "com.finmars.standard-layouts:liquidity",
            "value": "Invalid expression"
        },
        {
            "custom_field": 6,
            "user_code": "com.finmars.standard-layouts:position_nominal",
            "value": 100000
        },
        {
            "custom_field": 5,
            "user_code": "com.finmars.standard-layouts:factor",
            "value": "1"
        },
        {
            "custom_field": 4,
            "user_code": "com.finmars.standard-layouts:price_update_date",
            "value": "2022-08-11"
        },
        {
            "custom_field": 3,
            "user_code": "com.finmars.standard-layouts:asset_types",
            "value": "Invalid expression"
        },
        {
            "custom_field": 2,
            "user_code": "com.finmars.standard-layouts:pricing_ccy",
            "value": "EUR"
        },
        {
            "custom_field": 1,
            "user_code": "com.finmars.standard-layouts:fx_rate_for_asset",
            "value": "Invalid expression"
        },
        {
            "custom_field": 11,
            "user_code": "com.finmars.standard-layouts:liquidity12",
            "value": "Invalid expression"
        },
        {
            "custom_field": 12,
            "user_code": "com.finmars.standard-layouts:custom_column_asset_type",
            "value": "Other"
        }
    ],
    "custom_fields.com.finmars.standard-layouts:country_of_risk": "Invalid expression",
    "custom_fields.com.finmars.standard-layouts:liquidity": "Invalid expression",
    "custom_fields.com.finmars.standard-layouts:position_nominal": 100000,
    "custom_fields.com.finmars.standard-layouts:factor": "1",
    "custom_fields.com.finmars.standard-layouts:price_update_date": "2022-08-11",
    "custom_fields.com.finmars.standard-layouts:asset_types": "Invalid expression",
    "custom_fields.com.finmars.standard-layouts:pricing_ccy": "EUR",
    "custom_fields.com.finmars.standard-layouts:fx_rate_for_asset": "Invalid expression",
    "custom_fields.com.finmars.standard-layouts:liquidity12": "Invalid expression",
    "custom_fields.com.finmars.standard-layouts:custom_column_asset_type": "Other",
}

data7 = {
    "id": "1,42,1,3,1,1,1",
    "name": "FX-Forward: CHF/CAD 23.02.2023 2.0",
    "short_name": "FX-Forward: CHF/CAD 23.02.2023 2.0",
    "user_code": "FX-Forward: CHF/CAD 23.02.2023 2.0",
    "position_size": -20000,

    "instrument.id": 42,
    "instrument.name": "FX-Forward: CHF/CAD 23.02.2023 2.0",
    "instrument.short_name": "FX-Forward: CHF/CAD 23.02.2023 2.0",
    "instrument.user_code": "FX-Forward: CHF/CAD 23.02.2023 2.0",
    "instrument.public_name": "FX-Forward: CHF/CAD 23.02.2023 2.0",
    "instrument.maturity_date": "2023-02-23",

    "instrument.instrument_type.id": 6,
    "instrument.instrument_type.instrument_class": 2,
    "instrument.instrument_type.instrument_class_object": {
        "id": 2,
        "user_code": "EVENT_AT_MATURITY",
        "name": "Event at Maturity",
        "description": "Event at Maturity"
    },
    "instrument.instrument_type.user_code": "FX-Forwards",
    "instrument.instrument_type.name": "FX-Forwards",
    "instrument.instrument_type.short_name": "FX-Forwards",
    "instrument.instrument_type.public_name": "FX-Forwards",
    "instrument.instrument_type.notes": None,
    "instrument.instrument_type.deleted_user_code": None,
    "instrument.instrument_type.owner": {
        "id": 1,
        "username": "finmars01",
        "first_name": "",
        "last_name": "",
        "display_name": "finmars01",
        "is_owner": False,
        "is_admin": False,
        "user": 49
    },
    "instrument.instrument_type.meta": {
        "content_type": "instruments.instrumenttype",
        "app_label": "instruments",
        "model_name": "instrumenttype",
        "space_code": "space0fxf3"
    },
    "instrument.instrument_type_object": {
        "id": 6,
        "name": "FX-Forwards",
        "user_code": "FX-Forwards",
        "short_name": "FX-Forwards"
    },

    "instrument.attributes.country_of_issuer": None,
    "instrument.attributes.test_number": None,
    "instrument.attributes.test_date": None,

    "custom_fields": [
        {
            "custom_field": 7,
            "user_code": "com.finmars.standard-layouts:country_of_risk",
            "value": "Invalid expression"
        },
        {
            "custom_field": 8,
            "user_code": "com.finmars.standard-layouts:liquidity",
            "value": "Invalid expression"
        },
        {
            "custom_field": 6,
            "user_code": "com.finmars.standard-layouts:position_nominal",
            "value": 20000
        },
        {
            "custom_field": 5,
            "user_code": "com.finmars.standard-layouts:factor",
            "value": "1"
        },
        {
            "custom_field": 4,
            "user_code": "com.finmars.standard-layouts:price_update_date",
            "value": None
        },
        {
            "custom_field": 3,
            "user_code": "com.finmars.standard-layouts:asset_types",
            "value": "Invalid expression"
        },
        {
            "custom_field": 2,
            "user_code": "com.finmars.standard-layouts:pricing_ccy",
            "value": "USD"
        },
        {
            "custom_field": 1,
            "user_code": "com.finmars.standard-layouts:fx_rate_for_asset",
            "value": "Invalid expression"
        },
        {
            "custom_field": 11,
            "user_code": "com.finmars.standard-layouts:liquidity12",
            "value": "Invalid expression"
        },
        {
            "custom_field": 12,
            "user_code": "com.finmars.standard-layouts:custom_column_asset_type",
            "value": "Other"
        }
    ],
    "custom_fields.com.finmars.standard-layouts:country_of_risk": "Invalid expression",
    "custom_fields.com.finmars.standard-layouts:liquidity": "Invalid expression",
    "custom_fields.com.finmars.standard-layouts:position_nominal": 20000,
    "custom_fields.com.finmars.standard-layouts:factor": "1",
    "custom_fields.com.finmars.standard-layouts:price_update_date": None,
    "custom_fields.com.finmars.standard-layouts:asset_types": "Invalid expression",
    "custom_fields.com.finmars.standard-layouts:pricing_ccy": "USD",
    "custom_fields.com.finmars.standard-layouts:fx_rate_for_asset": "Invalid expression",
    "custom_fields.com.finmars.standard-layouts:liquidity12": "Invalid expression",
    "custom_fields.com.finmars.standard-layouts:custom_column_asset_type": "Other",
}
# endregion Data for items

list_for_qs = [
    {
        "id": "2,2,2,21,1,1,1",
        "name": "US Dollar (USD)",
        "short_name": "USD",
        "user_code": "USD",
        "instrument": None,
        "position_size": -1221469.22,

        "custom_fields": [
            {
                "custom_field": 7,
                "user_code": "com.finmars.standard-layouts:country_of_risk",
                "value": "Cash"
            },
            {
                "custom_field": 8,
                "user_code": "com.finmars.standard-layouts:liquidity",
                "value": "Cash"
            },
            {
                "custom_field": 6,
                "user_code": "com.finmars.standard-layouts:position_nominal",
                "value": -1221469.22
            },
            {
                "custom_field": 5,
                "user_code": "com.finmars.standard-layouts:factor",
                "value": "1"
            },
            {
                "custom_field": 4,
                "user_code": "com.finmars.standard-layouts:price_update_date",
                "value": None
            },
            {
                "custom_field": 3,
                "user_code": "com.finmars.standard-layouts:asset_types",
                "value": "Cash and equivalents"
            },
            {
                "custom_field": 2,
                "user_code": "com.finmars.standard-layouts:pricing_ccy",
                "value": "USD"
            },
            {
                "custom_field": 1,
                "user_code": "com.finmars.standard-layouts:fx_rate_for_asset",
                "value": "Invalid expression"
            },
            {
                "custom_field": 11,
                "user_code": "com.finmars.standard-layouts:liquidity12",
                "value": "Cash"
            },
            {
                "custom_field": 12,
                "user_code": "com.finmars.standard-layouts:custom_column_asset_type",
                "value": "Cash"
            }
        ],
        "custom_fields.com.finmars.standard-layouts:country_of_risk": "Cash",
        "custom_fields.com.finmars.standard-layouts:liquidity": "Cash",
        "custom_fields.com.finmars.standard-layouts:position_nominal": -1221469.22,
        "custom_fields.com.finmars.standard-layouts:factor": "1",
        "custom_fields.com.finmars.standard-layouts:price_update_date": None,
        "custom_fields.com.finmars.standard-layouts:asset_types": "Cash and equivalents",
        "custom_fields.com.finmars.standard-layouts:pricing_ccy": "USD",
        "custom_fields.com.finmars.standard-layouts:fx_rate_for_asset": "Invalid expression",
        "custom_fields.com.finmars.standard-layouts:liquidity12": "Cash",
        "custom_fields.com.finmars.standard-layouts:custom_column_asset_type": "Cash",

        "instrument.attributes.country_of_issuer": "United States - USA",
        "instrument.attributes.test_number": 12,
        "instrument.attributes.test_date": "9999-12-12",
    },

    {
        "id": "2,2,2,25,1,1,1",
        "name": "US Dollar (USD)",
        "short_name": "USD",
        "user_code": "USD",
        "position_size": 1234238,
        "instrument": None,

        "instrument.attributes.country_of_issuer": "United States - USA",
        "instrument.attributes.test_number": 12,
        "instrument.attributes.test_date": "9999-12-12",

        "custom_fields": [
            {
                "custom_field": 7,
                "user_code": "com.finmars.standard-layouts:country_of_risk",
                "value": "Cash"
            },
            {
                "custom_field": 8,
                "user_code": "com.finmars.standard-layouts:liquidity",
                "value": "Cash"
            },
            {
                "custom_field": 6,
                "user_code": "com.finmars.standard-layouts:position_nominal",
                "value": -678130.36
            },
            {
                "custom_field": 5,
                "user_code": "com.finmars.standard-layouts:factor",
                "value": "1"
            },
            {
                "custom_field": 4,
                "user_code": "com.finmars.standard-layouts:price_update_date",
                "value": None
            },
            {
                "custom_field": 3,
                "user_code": "com.finmars.standard-layouts:asset_types",
                "value": "Cash and equivalents"
            },
            {
                "custom_field": 2,
                "user_code": "com.finmars.standard-layouts:pricing_ccy",
                "value": "USD"
            },
            {
                "custom_field": 1,
                "user_code": "com.finmars.standard-layouts:fx_rate_for_asset",
                "value": "Invalid expression"
            },
            {
                "custom_field": 11,
                "user_code": "com.finmars.standard-layouts:liquidity12",
                "value": "Cash"
            },
            {
                "custom_field": 12,
                "user_code": "com.finmars.standard-layouts:custom_column_asset_type",
                "value": "Cash"
            }
        ],
        "custom_fields.com.finmars.standard-layouts:country_of_risk": "Cash",
        "custom_fields.com.finmars.standard-layouts:liquidity": "Cash",
        "custom_fields.com.finmars.standard-layouts:position_nominal": -678130.36,
        "custom_fields.com.finmars.standard-layouts:factor": "1",
        "custom_fields.com.finmars.standard-layouts:price_update_date": None,
        "custom_fields.com.finmars.standard-layouts:asset_types": "Cash and equivalents",
        "custom_fields.com.finmars.standard-layouts:pricing_ccy": "USD",
        "custom_fields.com.finmars.standard-layouts:fx_rate_for_asset": "Invalid expression",
        "custom_fields.com.finmars.standard-layouts:liquidity12": "Cash",
        "custom_fields.com.finmars.standard-layouts:custom_column_asset_type": "Cash",

    },

    {
        "id": "1,12,2,1,1,1,1",
        "name": "Orange",
        "short_name": "Orange",
        "user_code": "Orange",
        "position_size": 1000,

        "instrument.id": 12,
        "instrument.name": "Orange",
        "instrument.short_name": "Orange",
        "instrument.user_code": "Orange",
        "instrument.public_name": "Orange",
        "instrument.maturity_date": "9999-12-31",

        "instrument.instrument_type.id": 13,
        "instrument.instrument_type.instrument_class": 1,
        "instrument.instrument_type.instrument_class_object": {
            "id": 1,
            "user_code": "GENERAL",
            "name": "General Class",
            "description": "General Class"
        },
        "instrument.instrument_type.user_code": "stocks",
        "instrument.instrument_type.name": "stocks",
        "instrument.instrument_type.short_name": "stocks",
        "instrument.instrument_type.public_name": "stocks",
        "instrument.instrument_type.notes": None,
        "instrument.instrument_type.deleted_user_code": None,
        "instrument.instrument_type.owner": {
            "id": 1,
            "username": "finmars01",
            "first_name": "",
            "last_name": "",
            "display_name": "finmars01",
            "is_owner": False,
            "is_admin": False,
            "user": 49
        },
        "instrument.instrument_type.meta": {
            "content_type": "instruments.instrumenttype",
            "app_label": "instruments",
            "model_name": "instrumenttype",
            "space_code": "space0fxf3"
        },
        "instrument.instrument_type_object": {
            "id": 13,
            "name": "stocks",
            "user_code": "stocks",
            "short_name": "stocks"
        },

        "instrument.country.id": 77,
        "instrument.country.user_code": "France",
        "instrument.country.name": "France",
        "instrument.country.short_name": "France",
        "instrument.country.meta": {
            "content_type": "instruments.country",
            "app_label": "instruments",
            "model_name": "country",
            "space_code": "space0fxf3"
        },
        "instrument.country_object": {
            "id": 77,
            "name": "France",
            "user_code": "France",
            "country_code": "250",
            "region": "Europe",
            "region_code": "150",
            "sub_region": "Western Europe",
            "sub_region_code": "155"
        },
    },

    {
        "id": "1,2,2,1,1,1,1",
        "name": "S&P 500",
        "short_name": "S&P 500",
        "user_code": "sp_500",
        "position_size": 100000,

        "instrument.id": 2,
        "instrument.name": "S&P 500",
        "instrument.short_name": "S&P 500",
        "instrument.user_code": "sp_500",
        "instrument.public_name": "S&P 500",
        "instrument.maturity_date": "9999-12-31",

        "instrument.instrument_type.id": 7,
        "instrument.instrument_type.instrument_class": 1,
        "instrument.instrument_type.instrument_class_object": {
            "id": 1,
            "user_code": "GENERAL",
            "name": "General Class",
            "description": "General Class"
        },
        "instrument.instrument_type.user_code": "Funds/ETFs",
        "instrument.instrument_type.name": "Funds/ETFs",
        "instrument.instrument_type.short_name": "Funds/ETFs",
        "instrument.instrument_type.public_name": "Funds/ETFs",
        "instrument.instrument_type.notes": None,
        "instrument.instrument_type.deleted_user_code": None,
        "instrument.instrument_type.owner": {
            "id": 1,
            "username": "finmars01",
            "first_name": "",
            "last_name": "",
            "display_name": "finmars01",
            "is_owner": False,
            "is_admin": False,
            "user": 49
        },
        "instrument.instrument_type.meta": {
            "content_type": "instruments.instrumenttype",
            "app_label": "instruments",
            "model_name": "instrumenttype",
            "space_code": "space0fxf3"
        },
        "instrument.instrument_type_object": {
            "id": 7,
            "name": "Funds/ETFs",
            "user_code": "Funds/ETFs",
            "short_name": "Funds/ETFs"
        },

        "instrument.country.id": 236,
        "instrument.country.user_code": "United States of America",
        "instrument.country.name": "United States of America",
        "instrument.country.short_name": "United States of America",
        "instrument.country.meta": {
            "content_type": "instruments.country",
            "app_label": "instruments",
            "model_name": "country",
            "space_code": "space0fxf3"
        },
        "instrument.country_object": {
            "id": 236,
            "name": "United States of America",
            "user_code": "United States of America",
            "country_code": "840",
            "region": "Americas",
            "region_code": "019",
            "sub_region": "Northern America",
            "sub_region_code": "021"
        },

        "instrument.attributes.country_of_issuer": "United States - USA",
        "instrument.attributes.test_number": 12,
        "instrument.attributes.test_date": "9999-12-12",

        "custom_fields": [
            {
                "custom_field": 7,
                "user_code": "com.finmars.standard-layouts:country_of_risk",
                "value": "Invalid expression"
            },
            {
                "custom_field": 8,
                "user_code": "com.finmars.standard-layouts:liquidity",
                "value": "Invalid expression"
            },
            {
                "custom_field": 6,
                "user_code": "com.finmars.standard-layouts:position_nominal",
                "value": 10000
            },
            {
                "custom_field": 5,
                "user_code": "com.finmars.standard-layouts:factor",
                "value": "1"
            },
            {
                "custom_field": 4,
                "user_code": "com.finmars.standard-layouts:price_update_date",
                "value": "2022-10-10"
            },
            {
                "custom_field": 3,
                "user_code": "com.finmars.standard-layouts:asset_types",
                "value": "Invalid expression"
            },
            {
                "custom_field": 2,
                "user_code": "com.finmars.standard-layouts:pricing_ccy",
                "value": "EUR"
            },
            {
                "custom_field": 1,
                "user_code": "com.finmars.standard-layouts:fx_rate_for_asset",
                "value": "Invalid expression"
            },
            {
                "custom_field": 11,
                "user_code": "com.finmars.standard-layouts:liquidity12",
                "value": "Invalid expression"
            },
            {
                "custom_field": 12,
                "user_code": "com.finmars.standard-layouts:custom_column_asset_type",
                "value": "Other"
            }
        ],
        "custom_fields.com.finmars.standard-layouts:country_of_risk": "Invalid expression",
        "custom_fields.com.finmars.standard-layouts:liquidity": "Invalid expression",
        "custom_fields.com.finmars.standard-layouts:position_nominal": 10000,
        "custom_fields.com.finmars.standard-layouts:factor": "1",
        "custom_fields.com.finmars.standard-layouts:price_update_date": "2022-10-10",
        "custom_fields.com.finmars.standard-layouts:asset_types": "Invalid expression",
        "custom_fields.com.finmars.standard-layouts:pricing_ccy": "EUR",
        "custom_fields.com.finmars.standard-layouts:fx_rate_for_asset": "Invalid expression",
        "custom_fields.com.finmars.standard-layouts:liquidity12": "Invalid expression",
        "custom_fields.com.finmars.standard-layouts:custom_column_asset_type": "Other",
    },

    {
        "id": "1,10,2,1,1,1,1",
        "name": "Pfizer",
        "short_name": "Pfizer",
        "user_code": "Pfizer",
        "position_size": 100500,

        "instrument.id": 10,
        "instrument.name": "Pfizer",
        "instrument.short_name": "Pfizer",
        "instrument.user_code": "Pfizer",
        "instrument.public_name": "Pfizer",
        "instrument.maturity_date": "9999-12-31",

        "instrument.instrument_type.id": 13,
        "instrument.instrument_type.instrument_class": 1,
        "instrument.instrument_type.instrument_class_object": {
            "id": 1,
            "user_code": "GENERAL",
            "name": "General Class",
            "description": "General Class"
        },
        "instrument.instrument_type.user_code": "stocks",
        "instrument.instrument_type.name": "stocks",
        "instrument.instrument_type.short_name": "stocks",
        "instrument.instrument_type.public_name": "stocks",
        "instrument.instrument_type.notes": None,
        "instrument.instrument_type.deleted_user_code": None,
        "instrument.instrument_type.owner": {
            "id": 1,
            "username": "finmars01",
            "first_name": "",
            "last_name": "",
            "display_name": "finmars01",
            "is_owner": False,
            "is_admin": False,
            "user": 49
        },
        "instrument.instrument_type.meta": {
            "content_type": "instruments.instrumenttype",
            "app_label": "instruments",
            "model_name": "instrumenttype",
            "space_code": "space0fxf3"
        },
        "instrument.instrument_type_object": {
            "id": 13,
            "name": "stocks",
            "user_code": "stocks",
            "short_name": "stocks"
        },

        "instrument.country.id": 236,
        "instrument.country.user_code": "United States of America",
        "instrument.country.name": "United States of America",
        "instrument.country.short_name": "United States of America",
        "instrument.country.meta": {
            "content_type": "instruments.country",
            "app_label": "instruments",
            "model_name": "country",
            "space_code": "space0fxf3"
        },
        "instrument.country_object": {
            "id": 236,
            "name": "United States of America",
            "user_code": "United States of America",
            "country_code": "840",
            "region": "Americas",
            "region_code": "019",
            "sub_region": "Northern America",
            "sub_region_code": "021"
        },

        "instrument.attributes.country_of_issuer": "United States - USA",
        "instrument.attributes.test_number": 12,
        "instrument.attributes.test_date": "9999-12-12",

        "custom_fields": [
            {
                "custom_field": 7,
                "user_code": "com.finmars.standard-layouts:country_of_risk",
                "value": "Invalid expression"
            },
            {
                "custom_field": 8,
                "user_code": "com.finmars.standard-layouts:liquidity",
                "value": "Invalid expression"
            },
            {
                "custom_field": 6,
                "user_code": "com.finmars.standard-layouts:position_nominal",
                "value": 12000
            },
            {
                "custom_field": 5,
                "user_code": "com.finmars.standard-layouts:factor",
                "value": "1"
            },
            {
                "custom_field": 4,
                "user_code": "com.finmars.standard-layouts:price_update_date",
                "value": "2022-09-30"
            },
            {
                "custom_field": 3,
                "user_code": "com.finmars.standard-layouts:asset_types",
                "value": "Invalid expression"
            },
            {
                "custom_field": 2,
                "user_code": "com.finmars.standard-layouts:pricing_ccy",
                "value": "USD"
            },
            {
                "custom_field": 1,
                "user_code": "com.finmars.standard-layouts:fx_rate_for_asset",
                "value": "Invalid expression"
            },
            {
                "custom_field": 11,
                "user_code": "com.finmars.standard-layouts:liquidity12",
                "value": "Invalid expression"
            },
            {
                "custom_field": 12,
                "user_code": "com.finmars.standard-layouts:custom_column_asset_type",
                "value": "Other"
            }
        ],
        "custom_fields.com.finmars.standard-layouts:country_of_risk": "Invalid expression",
        "custom_fields.com.finmars.standard-layouts:liquidity": "Invalid expression",
        "custom_fields.com.finmars.standard-layouts:position_nominal": 12000,
        "custom_fields.com.finmars.standard-layouts:factor": "1",
        "custom_fields.com.finmars.standard-layouts:price_update_date": "2022-09-30",
        "custom_fields.com.finmars.standard-layouts:asset_types": "Invalid expression",
        "custom_fields.com.finmars.standard-layouts:pricing_ccy": "USD",
        "custom_fields.com.finmars.standard-layouts:fx_rate_for_asset": "Invalid expression",
        "custom_fields.com.finmars.standard-layouts:liquidity12": "Invalid expression",
        "custom_fields.com.finmars.standard-layouts:custom_column_asset_type": "Other",
    },

    data6,

    data7
]

er_balance_date_tree = [data6, data7]

filter_settings1 = [
    {
        "key": "instrument.maturity_date",
        "filter_type": "date_tree",
        "exclude_empty_cells": False,
        "value_type": 40,
        "value": [
            "2001-01-01",
            "2023-02-23",
        ]
    }
]

class HandleFilters(BaseTestCase):
    databases = "__all__"
    filter_strings_settings = {

    }

    def setUp(self):
        super().setUp()
        self.init_test_case()

    @BaseTestCase.cases(
        ('balance_date_tree', list_for_qs, filter_settings1, 'reports.balancereport', er_balance_date_tree)
    )
    def test_handle_filters(self, items_list, filter_settings, content_type, expected):

        # mock_queryset = Mock()
        # mock_queryset.all.return_value = mock_queryset
        # mock_queryset.values.return_value = items_list
        #
        # mock_model_manager = Mock()
        # mock_model_manager.all.return_value = mock_queryset
        #
        # qs = mock_model_manager.all().values()
        # TODO emulate QuerySet with items for report and its `filter` method
        qs = []

        result = handle_filters(
            qs,
            filter_settings,
            self.master_user,
            content_type
        )

        self.assertEqual(list(result), expected)
