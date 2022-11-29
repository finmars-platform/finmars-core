from __future__ import unicode_literals

import csv
import os

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy

from poms_app import settings


def load_countries():
    ccy_path = os.path.join(settings.BASE_DIR, 'data', 'countries.csv')
    results = []
    with open(ccy_path) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        for row in reader:
            results.append(row)
    return results


class InstrumentsConfig(AppConfig):
    name = 'poms.instruments'
    # label = 'poms'
    verbose_name = gettext_lazy('Instruments')

    def ready(self):
        post_migrate.connect(self.update_transaction_classes, sender=self)
        post_migrate.connect(self.fill_with_countries, sender=self)

    def fill_with_countries(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):
        countries = load_countries()

        from .models import Country

        for country in countries:
            item, created = Country.objects.get_or_create(name=country['name'])

            item.name = country['name']
            item.user_code = country['name']
            item.short_name = country['name']
            item.description = country['name']

            item.alpha_2 = country['alpha-2']
            item.alpha_3 = country['alpha-3']
            item.country_code = country['country-code']
            item.iso_3166_2 = country['iso_3166-2']
            item.region = country['region']
            item.sub_region = country['sub-region']
            item.intermediate_region = country['intermediate-region']
            item.region_code = country['region-code']
            item.sub_region_code = country['sub-region-code']
            item.intermediate_region_code = country['intermediate-region-code']

            item.save()

    def update_transaction_classes(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):
        from poms.common.utils import db_class_check_data
        from .models import InstrumentClass, DailyPricingModel, AccrualCalculationModel, Periodicity, \
            CostMethod, PaymentSizeDetail, PricingCondition, ExposureCalculationModel, LongUnderlyingExposure, \
            ShortUnderlyingExposure

        db_class_check_data(InstrumentClass, verbosity, using)
        db_class_check_data(DailyPricingModel, verbosity, using)
        db_class_check_data(AccrualCalculationModel, verbosity, using)
        db_class_check_data(Periodicity, verbosity, using)
        db_class_check_data(CostMethod, verbosity, using)
        db_class_check_data(PaymentSizeDetail, verbosity, using)
        db_class_check_data(PricingCondition, verbosity, using)
        db_class_check_data(ExposureCalculationModel, verbosity, using)
        db_class_check_data(LongUnderlyingExposure, verbosity, using)
        db_class_check_data(ShortUnderlyingExposure, verbosity, using)
