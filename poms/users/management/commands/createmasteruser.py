from django.core.management import BaseCommand
from django.db import transaction

__author__ = "ailyukhin"


class Command(BaseCommand):
    help = "Create empty master user"

    def add_arguments(self, parser):
        parser.add_argument("name", nargs="+", type=str)

    def handle(self, *args, **options):
        from poms.users.models import MasterUser

        name = options["name"]
        if not isinstance(name, (list, tuple, set)):
            name = [name]
        for n in name:
            with transaction.atomic():
                MasterUser.objects.create_master_user(name=n)
            self.stdout.write("Master user '%s' created." % n)
