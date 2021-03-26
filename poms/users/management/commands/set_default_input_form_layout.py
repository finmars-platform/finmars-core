import time

from django.core.management.base import BaseCommand
from django.db.models import Max, Min
from django.db.utils import ProgrammingError
from django_celery_results.models import TaskResult


class Command(BaseCommand):
    help = 'Move input settings'

    def handle(self, *args, **options):

        from poms.ui.models import EditLayout
        from poms.users.models import Member

        from django.contrib.contenttypes.models import ContentType

        content_types = ContentType.objects.all()


        members = Member.objects.all()

        count = 0

        for member in members:

            for content_type in content_types:

                layouts = EditLayout.objects.filter(member=member, content_type=content_type, is_default=True)

                if len(layouts) == 0:
                    layouts = EditLayout.objects.filter(member=member, content_type=content_type)

                    if len(layouts):
                        layout = layouts[0]
                        layout.is_default = True
                        layout.save()
                        count = count + 1


        self.stdout.write("Job Done. Layouts Affected %s " % count)
