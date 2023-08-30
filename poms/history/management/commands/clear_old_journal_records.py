from django.core.management.base import BaseCommand

from poms.history.tasks import clear_old_journal_records


class Command(BaseCommand):
    help = "delete old journal record"

    def handle(self, *args, **options):
        self.stdout.write("command clear_old_journal_records started ...")

        clear_old_journal_records()

        self.stdout.write("command clear_old_journal_records finished")
