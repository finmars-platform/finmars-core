EXPECTED_CURRENCY_HISTORY = {
    "id": 1,
    "currency": 7,
    "currency_object": {
        "id": 7,
        "user_code": "USD",
        "name": "USD - United States Dollar",
        "short_name": "USD",
        "deleted_user_code": None,
        "meta": {
            "content_type": "currencies.currency",
            "app_label": "currencies",
            "model_name": "currency",
            "space_code": "space00000",
        },
    },
    "pricing_policy": 5,
    "pricing_policy_object": {
        "id": 5,
        "user_code": "local.poms.space00000:ytqvh",
        "name": "OHGYTISTWFL",
        "short_name": "BI",
        "notes": None,
        "expr": "",
        "deleted_user_code": None,
        "meta": {
            "content_type": "instruments.pricingpolicy",
            "app_label": "instruments",
            "model_name": "pricingpolicy",
            "space_code": "space00000",
        },
    },
    "date": "2023-07-19",
    "fx_rate": 426.0,
    "procedure_modified_datetime": "2023-07-19T00:00:00Z",
    "modified_at": "2023-07-19T17:31:35.274932Z",
    "meta": {
        "content_type": "currencies.currencyhistory",
        "app_label": "currencies",
        "model_name": "currencyhistory",
        "space_code": "space00000",
    },
    "created_at": "20240823T16:41:00.0Z",
}

CREATE_DATA = {
    "currency": 7,
    "pricing_policy": 5,
    "fx_rate": 426.0,
    "date": "2023-07-19",
}
