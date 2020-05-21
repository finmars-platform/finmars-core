import time

from django.core.management.base import BaseCommand
from django.db.models import Max, Min
from django.db.utils import ProgrammingError
from django_celery_results.models import TaskResult


class Command(BaseCommand):
    help = 'Set Master Users Tokens'

    def handle(self, *args, **options):

        from poms.users.models import MasterUser
        import uuid

        master_users = MasterUser.objects.all()

        count = 0

        for master_user in master_users:

            if not master_user.token:

                try:

                    token = uuid.uuid4().hex

                    master_user.token = token

                    master_user.save()
                    count = count + 1

                except Exception as e:

                    self.stdout.write("Error occurred. master_user id %s" % master_user.id)
                    self.stdout.write("Error occurred. e %s" % e)

        self.stdout.write("Job Done. Master Users Affected %s " % count)
