from django.core.management import BaseCommand
from django.db import transaction


__author__ = 'szhitenev'


class Command(BaseCommand):
    help = 'Set is Enabled to True'

    def handle(self, *args, **options):
        from poms.common.models import NamedModel

        print(NamedModel.__subclasses__())

        models = NamedModel.__subclasses__()

        for model in models:

            if hasattr(model, 'objects'):
                items = model.objects.all()
                for item in items:
                    item.is_enabled = True
                    item.save()
            else:
                submodels = model.__subclasses__()
                print(submodels)

                for submodel in submodels:
                    items = submodel.objects.all()
                    for item in items:
                        item.is_enabled = True
                        item.save()

        self.stdout.write("Enabled is set to True.")

