from django.core.management.commands.shell import Command as OriginalCommand
from django.db import connection


class Command(OriginalCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--space-code", help="Workspace code (DB schema)")

    def handle(self, *args, **options):
        if options["space_code"]:
            with connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {options['space_code']};")
        super().handle(**options)
