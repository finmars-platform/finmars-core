VERSION = "1.0.1"
CONFIGURATION_CODE = "com.finmars.initial"
TOKEN = "test_token"
POST_PAYLOAD = {
    "configuration_code": "com.finmars.initial",
    "version": VERSION,
    "is_package": True,
}
OPTIONS = {
    "access_token": TOKEN,
    "configuration_code": "com.finmars.initial",
    "is_package": True,
    "version": VERSION,
}
JOURNAL_RECORD = {
    "id": 2,
    "configuration_code": CONFIGURATION_CODE,
    "name": "Finmars Initial",
    "short_name": None,
    "description": "",
    "version": VERSION,
    "is_from_marketplace": True,
    "is_package": True,
    "manifest_data": {
        "configuration_code": CONFIGURATION_CODE,
        "date": "2023-04-22",
        "dependencies": [
            {
                "configuration_code": "com.finmars.initial-instrument-type",
                "version": "1.0.0",
            },
            {
                "configuration_code": "com.finmars.initial-system-procedure",
                "version": "2.0.0",
            },
        ],
        "name": "Initial",
        "version": VERSION,
    },
    "is_primary": False,
}
PACKAGE_RESPONSE_JSON = {
    "id": 117,
    "configuration": 7,
    "configuration_object": {
        "id": 7,
        "configuration_code": "com.finmars.initial",
        "organization": 1,
        "organization_object": {
            "id": 1,
            "name": "Finmars",
            "description": "",
            "created": "2023-04-15T11:07:33.656722Z",
            "modified": "2023-04-15T11:07:33.656742Z",
            "members": [
                {
                    "id": 1,
                    "user": 3
                }
            ]
        },
        "thumbnail": "https://finmars-marketplace.s3.amazonaws.com/thumbnails/logo_sphere.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAZFI7MO4TUOBKIT7O%2F20230827%2Feu-central-1%2Fs3%2Faws4_request&X-Amz-Date=20230827T131514Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=dbfba851067a4a97063f7a6679d0d914d0abc8ff3f8bb127e09f1846e5c1f2a9",
        "download_count": 0,
        "latest_release_object": {
            "id": 117,
            "version": "1.0.1",
            "changelog": ""
        },
        "is_package": True,
        "name": "Finmars Initial",
        "description": "",
        "created": "2023-04-22T19:52:13.178250Z",
        "modified": "2023-06-01T18:23:13.364081Z"
    },
    "manifest": {
        "configuration_code": "com.finmars.initial",
        "date": "2023-04-22",
        "dependencies": [
            {
                "configuration_code": "com.finmars.initial-instrument-type",
                "version": "1.0.0"
            },
            {
                "configuration_code": "com.finmars.initial-system-procedure",
                "version": "1.0.0"
            }
        ],
        "name": "Initial",
        "version": VERSION
    },
    "version": VERSION,
    "is_latest": True,
    "changelog": "",
    "created": "2023-06-18T22:45:58.393808Z",
    "modified": "2023-06-22T12:35:28.782104Z",
    "file_name": "tmp_vu63hqf.zip",
    "file_path": "marketplace/com.finmars.initial/1.0.1/tmp_vu63hqf.zip"
}
EXPECTED_PROGRESS_OBJECT = {
    "current": len(PACKAGE_RESPONSE_JSON["manifest"]["dependencies"]),
    "total": len(PACKAGE_RESPONSE_JSON["manifest"]["dependencies"]),
    "percent": 100,
    "description": "Installation complete",
}

MODULE_1_RESPONSE_JSON = {
    "id": 23,
    "configuration": 6,
    "configuration_object": {
        "id": 6,
        "configuration_code": "com.finmars.initial-instrument-type",
        "organization": 1,
        "organization_object": {
            "id": 1,
            "name": "Finmars",
            "description": "",
            "created": "2023-04-15T11:07:33.656722Z",
            "modified": "2023-04-15T11:07:33.656742Z",
            "members": [
                {
                    "id": 1,
                    "user": 3
                }
            ]
        },
        "thumbnail": "https://finmars-marketplace.s3.amazonaws.com/thumbnails/logo_sphere.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAZFI7MO4TUOBKIT7O%2F20230827%2Feu-central-1%2Fs3%2Faws4_request&X-Amz-Date=20230827T132044Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=4eccf33cd1502011eed5cb51084b1becde083c7ec53b9f56dd34910bc34e647c",
        "download_count": 639,
        "latest_release_object": {
            "id": 23,
            "version": "1.0.0",
            "changelog": ""
        },
        "is_package": False,
        "name": "Initial Instrument Types",
        "description": "",
        "created": "2023-04-22T19:51:58.023435Z",
        "modified": "2023-08-26T10:42:05.134667Z"
    },
    "manifest": {
        "configuration_code": "com.finmars.initial-instrument-type",
        "date": "2023-04-22",
        "dependencies": {},
        "name": "Initial Instrument Types",
        "version": "1.0.0"
    },
    "version": "1.0.0",
    "is_latest": True,
    "changelog": "",
    "created": "2023-04-27T20:39:56.668764Z",
    "modified": "2023-04-27T20:39:56.668783Z",
    "file_name": "tmpzih_d8no.zip",
    "file_path": "marketplace/com.finmars.initial-instrument-type/1.0.0/tmpzih_d8no.zip"
}

MODULE_2_RESPONSE_JSON = {
    "id": 17,
    "configuration": 8,
    "configuration_object": {
        "id": 8,
        "configuration_code": "com.finmars.initial-system-procedure",
        "organization": 1,
        "organization_object": {
            "id": 1,
            "name": "Finmars",
            "description": "",
            "created": "2023-04-15T11:07:33.656722Z",
            "modified": "2023-04-15T11:07:33.656742Z",
            "members": [
                {
                    "id": 1,
                    "user": 3
                }
            ]
        },
        "thumbnail": "https://finmars-marketplace.s3.amazonaws.com/thumbnails/logo_sphere.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAZFI7MO4TUOBKIT7O%2F20230827%2Feu-central-1%2Fs3%2Faws4_request&X-Amz-Date=20230827T132456Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=6a1f3b84328b7a535501bfcbddd36da1559d87e17d87eb652e4f6c4ea4b5b384",
        "download_count": 619,
        "latest_release_object": {
            "id": 17,
            "version": "1.0.0",
            "changelog": ""
        },
        "is_package": False,
        "name": "Initial System Procedures",
        "description": "",
        "created": "2023-04-22T20:11:08.843746Z",
        "modified": "2023-08-26T10:42:09.504979Z"
    },
    "manifest": {
        "configuration_code": "com.finmars.initial-system-procedure",
        "date": "2023-04-22",
        "dependencies": {},
        "name": "Initial System Procedure",
        "version": "1.0.0"
    },
    "version": "1.0.0",
    "is_latest": True,
    "changelog": "",
    "created": "2023-04-22T21:09:30.406945Z",
    "modified": "2023-04-24T13:31:53.656277Z",
    "file_name": "tmp8mxrbpak.zip",
    "file_path": "marketplace/com.finmars.initial-system-procedure/1.0.0/tmp8mxrbpak.zip"
}

CONFIGURATION_RESPONSE_12 = "configuration in special format"
