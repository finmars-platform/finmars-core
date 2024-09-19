import copy
import json
from unittest import mock

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from poms.instruments.models import PricingPolicy, PriceHistory
from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.csv_import.handlers import SimpleImportProcess
from poms.csv_import.models import CsvField, CsvImportScheme, EntityField
from poms.csv_import.tasks import simple_import
from poms.csv_import.tests.common_test_data import (
    PRICE_HISTORY,
    PRICE_HISTORY_ITEM,
    SCHEME_20,
    SCHEME_20_ENTITIES,
    SCHEME_20_FIELDS,
)
from poms.instruments.models import Instrument

FILE_CONTENT = json.dumps(PRICE_HISTORY).encode()
FILE_NAME = "test_file.json"


class MaxItemsImportTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/import/csv/"
        self.scheme_20 = self.create_scheme_20()
        self.storage = mock.Mock()
        self.storage.save.return_value = None
        self.instrument = self.create_instrument_for_price_history(
            isin=PRICE_HISTORY[0]["Instrument"]
        )
        self.pricing_policy = PricingPolicy.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code="com.finmars.standard-pricing:standard",
            configuration_code="com.finmars.standard-pricing",
            name="Standard",
            short_name="Standard",
            is_enabled=True,
        )

    def create_scheme_20(self):
        content_type = ContentType.objects.using(settings.DB_DEFAULT).get(
            app_label="instruments",
            model="pricehistory",
        )
        scheme_data = SCHEME_20.copy()
        scheme_data.update(
            {
                "content_type_id": content_type.id,
                "master_user_id": self.master_user.id,
                "owner_id": self.member.id,
            }
        )
        scheme = CsvImportScheme.objects.using(settings.DB_DEFAULT).create(
            **scheme_data
        )

        for field_data in SCHEME_20_FIELDS:
            field_data["scheme"] = scheme
            CsvField.objects.create(**field_data)

        for entity_data in SCHEME_20_ENTITIES:
            entity_data["scheme"] = scheme
            EntityField.objects.using(settings.DB_DEFAULT).create(**entity_data)

        return scheme

    def create_task(self, remove_accrued_and_factor=False):
        items = copy.deepcopy(PRICE_HISTORY)
        if remove_accrued_and_factor:
            for item in items:
                item.pop("Accrued Price", None)
                item.pop("Factor", None)

        options_object = {
            "file_path": FILE_NAME,
            "filename": FILE_NAME,
            "scheme_id": self.scheme_20.id,
            "execution_context": None,
            "items": items,
        }
        return CeleryTask.objects.using(settings.DB_DEFAULT).create(
            master_user=self.master_user,
            member=self.member,
            options_object=options_object,
            verbose_name="Simple Import",
            type="simple_import",
        )

    def create_instrument_for_price_history(self, isin: str) -> Instrument:
        instrument = self.create_instrument()
        instrument.user_code = isin
        instrument.short_name = isin
        instrument.save()
        self.create_accrual(instrument)
        return instrument

    def test__error_stage(self):
        pass
