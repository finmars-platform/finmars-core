from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Set Master Users Tokens'

    def handle(self, *args, **options):

        from poms.users.models import EcosystemDefault
        from poms.instruments.models import PricingCondition

        items = EcosystemDefault.objects.all()

        count = 0

        for item in items:

            if not item.pricing_condition:
                item.pricing_condition = PricingCondition.objects.get(id=PricingCondition.NO_VALUATION)

                count = count + 1

                item.save()

        self.stdout.write("Job Done. Ecosystems Affected %s " % count)
