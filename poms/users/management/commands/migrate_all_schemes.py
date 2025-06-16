from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

from poms.common.db import get_all_tenant_schemas


class Command(BaseCommand):
    help = "Apply database migrations to all tenant schemas."

    def handle(self, *args, **options):
        for schema in get_all_tenant_schemas():
            self.stdout.write(self.style.SUCCESS(f"Applying migrations to {schema}..."))

            # Set the search path to the tenant's schema
            with connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {schema};")

            # Programmatically call the migrate command
            call_command("migrate", *args, **options)

            # Optionally, reset the search path to default after migrating
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO public;")
