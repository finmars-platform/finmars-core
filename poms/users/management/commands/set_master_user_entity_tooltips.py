import time

from django.core.management.base import BaseCommand
from django.db.models import Max, Min
from django.db.utils import ProgrammingError
from django_celery_results.models import TaskResult


class Command(BaseCommand):
    help = 'Set Master Users Entity Tooltips'

    def handle(self, *args, **options):

        from poms.users.models import MasterUser

        master_users = MasterUser.objects.all()

        for master_user in master_users:

            master_user.create_entity_tooltips()

        self.stdout.write("Job Done. Tooltips created")
