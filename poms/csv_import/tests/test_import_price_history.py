import json
from unittest import mock

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.csv_import.models import CsvImportScheme
from poms.csv_import.tests.common_test_data import PRICE_HISTORY, SCHEMA_20

API_URL = f"/{settings.BASE_API_URL}/api/v1/import/csv"
FILE_CONTENT = json.dumps(PRICE_HISTORY).encode("utf-8")
FILE_NAME = "price_history.json"


class DummyStorage:
    def save(self):
        return


class ImportPriceHistoryTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = API_URL
        content_type = ContentType.objects.get(
            app_label="instruments",
            model="pricehistory",
        )
        schema_data = SCHEMA_20
        schema_data.update(
            {
                "content_type_id": content_type.id,
                "master_user_id": self.master_user.id,
                "owner_id": self.member.id,
            }
        )
        print(schema_data)
        self.scheme_20 = CsvImportScheme.objects.create(**schema_data)


    def test(self):
        pass
