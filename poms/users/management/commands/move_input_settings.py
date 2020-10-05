import time

from django.core.management.base import BaseCommand
from django.db.models import Max, Min
from django.db.utils import ProgrammingError
from django_celery_results.models import TaskResult


class Command(BaseCommand):
    help = 'Move input settings'

    def handle(self, *args, **options):

        from poms.transactions.models import TransactionTypeInput
        import uuid

        inputs = TransactionTypeInput.objects.all()

        count = 0

        for input in inputs:

            old_settings = input.settings_old.last()

            if old_settings:

                input.settings = old_settings

                count = count + 1

                input.save()


        self.stdout.write("Job Done. Inputs Affected %s " % count)
