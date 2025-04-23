from django.core.management.commands.migrate import Command as OriginalMigrateCommand
from django.db import connection


class Command(OriginalMigrateCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--space-code", help="Workspace code (DB schema)")

    def handle(self, *args, **options):
        if space_code := options.get("space_code"):
            with connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {space_code};")
        super().handle(*args, **options)
