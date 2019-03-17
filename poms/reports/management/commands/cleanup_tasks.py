import time

from django.core.management.base import BaseCommand
from django.db.models import Max, Min
from django.db.utils import ProgrammingError
from django_celery_results.models import TaskResult


class Command(BaseCommand):
    help = 'Delete old celery tasks'

    def handle(self, *args, **options):
        result = TaskResult.objects.aggregate(Max('id'), Min('id'))
        id_min, id_max = result['id__min'], result['id__max']
        self.stdout.write(
            "Total: %r, ranging from %r to %r"
            % (TaskResult.objects.count(), id_min, id_max)
        )
        if id_min is None or id_max is None:
            self.stdout.write("Nothing to do, exiting")
            return
        id_max -= 100
        self.stdout.write("Decreased finish down to %d" % id_max)
        step = 100
        start = id_min
        while start < id_max:
            finish = start + step
            try:
                deleted, _ = TaskResult.objects.filter(id__gte=start, id__lt=finish).delete()
                self.stdout.write(
                    "For range %d-%d deleted %d objects"
                    % (start, finish, deleted)
                )
                step = int(step * 1.05)
                start = finish
            except ProgrammingError as exc:
                self.stderr.write(str(exc))
                time.sleep(60)
                step = max(10, step / 2)
        return