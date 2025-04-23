from django.core.management import BaseCommand

__author__ = "szhitenev"


class Command(BaseCommand):
    help = "Add prefix to context property in ttype inputs"

    def handle(self, *args, **options):
        from poms.transactions.models import TransactionTypeInput

        processed = 0

        for item in TransactionTypeInput.objects.all().iterator():
            if item.context_property is not None:
                if "context" not in item.context_property:
                    item.context_property = "context_" + str(item.context_property)
                    item.save()
                    processed = processed + 1

        print("Inputs processed: %s" % processed)
