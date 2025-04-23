from django.core.management import BaseCommand

__author__ = "szhitenev"


class Command(BaseCommand):
    help = "Delete old zero currency histories"

    def handle(self, *args, **options):
        from poms.currencies.models import CurrencyHistory

        count = CurrencyHistory.objects.filter(fx_rate=0).count()

        print("%s items will be deleted " % count)

        CurrencyHistory.objects.filter(fx_rate=0).delete()
