import time

from django.core.management.base import BaseCommand
from django.db.models import Max, Min
from django.db.utils import ProgrammingError
from django_celery_results.models import TaskResult


class Command(BaseCommand):
    help = 'Set Default Pricing Condition'

    def handle(self, *args, **options):

        from poms.instruments.models import Instrument
        from poms.instruments.models import PricingCondition
        instruments = Instrument.objects.all()

        count = 0

        for instrument in instruments:

            if not instrument.pricing_condition_id:

                try:

                    instrument.pricing_condition_id = PricingCondition.NO_VALUATION

                    instrument.save()
                    count = count + 1

                except Exception as e:

                    self.stdout.write("Error occurred. Instrument id %s" % instrument.id)
                    self.stdout.write("Error occurred. e %s" % e)

        self.stdout.write("Job Done. Instruments Affected %s " % count)

        from poms.currencies.models import Currency
        currencies = Currency.objects.all()

        count = 0

        for currency in currencies:

            if not currency.pricing_condition_id:

                try:

                    currency.pricing_condition_id = PricingCondition.NO_VALUATION

                    currency.save()
                    count = count + 1

                except Exception as e:

                    self.stdout.write("Error occurred. Currency id %s" % currency.id)
                    self.stdout.write("Error occurred. e %s" % e)

        self.stdout.write("Job Done. Currencies Affected %s " % count)

