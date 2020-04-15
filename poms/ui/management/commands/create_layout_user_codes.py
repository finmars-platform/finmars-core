import time

from django.core.management.base import BaseCommand
from django.db.models import Max, Min
from django.db.utils import ProgrammingError
from django_celery_results.models import TaskResult


class Command(BaseCommand):
    help = 'Copy Name To User Code if not exist'

    def handle(self, *args, **options):

        from poms.ui.models import ListLayout
        list_layouts = ListLayout.objects.all()

        count = 0

        for layout in list_layouts:

            if not layout.user_code:

                try:

                    if len(layout.name) > 23:
                        layout.user_code = layout.name[:23]

                    else:
                        layout.user_code = layout.name

                    layout.save()
                    count = count + 1

                except Exception as e:

                    self.stdout.write("Error occurred. Layout id %s" % layout.id)
                    self.stdout.write("Error occurred. e %s" % e)

        self.stdout.write("Job Done. ListLayout Affected %s " % count)

        from poms.ui.models import ContextMenuLayout
        list_layouts = ContextMenuLayout.objects.all()

        count = 0

        for layout in list_layouts:

            if not layout.user_code:

                try:

                    if len(layout.name) > 23:
                        layout.user_code = layout.name[:23]

                    else:
                        layout.user_code = layout.name

                    layout.save()
                    count = count + 1

                except Exception as e:

                    self.stdout.write("Error occurred. Layout id %s" % layout.id)
                    self.stdout.write("Error occurred. e %s" % e)
                    pass

        self.stdout.write("Job Done. ContextMenuLayout Affected %s " % count)

        from poms.ui.models import DashboardLayout
        list_layouts = DashboardLayout.objects.all()

        count = 0

        for layout in list_layouts:

            if not layout.user_code:

                try:

                    if len(layout.name) > 23:
                        layout.user_code = layout.name[:23]

                    else:
                        layout.user_code = layout.name

                    layout.save()
                    count = count + 1

                except Exception as e:

                    self.stdout.write("Error occurred. Layout id %s" % layout.id)
                    self.stdout.write("Error occurred. e %s" % e)

                    pass

        self.stdout.write("Job Done. DashboardLayout Affected %s " % count)

        from poms.ui.models import TemplateLayout
        list_layouts = TemplateLayout.objects.all()

        count = 0

        for layout in list_layouts:

            if not layout.user_code:

                try:

                    if len(layout.name) > 23:
                        layout.user_code = layout.name[:23]

                    else:
                        layout.user_code = layout.name

                    layout.save()
                    count = count + 1

                except Exception as e:

                    self.stdout.write("Error occurred. Layout id %s" % layout.id)
                    self.stdout.write("Error occurred. e %s" % e)
                    pass

        self.stdout.write("Job Done. TemplateLayout Affected %s " % count)

