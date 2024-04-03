from django.core.management import BaseCommand
from django.db import connection

__author__ = 'szhitenev'

import os

def get_all_tenant_schemas():
    # List to hold tenant schemas
    tenant_schemas = []

    # SQL to fetch all non-system schema names
    # ('pg_catalog', 'information_schema', 'public') # do later in 1.9.0. where is not public schemes left
    sql = """
    SELECT schema_name
    FROM information_schema.schemata
    WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
    AND schema_name NOT LIKE 'pg_toast%'
    AND schema_name NOT LIKE 'pg_temp_%'
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        tenant_schemas = [row[0] for row in cursor.fetchall()]

    return tenant_schemas


class Command(BaseCommand):
    help = 'Generate super user'

    def handle(self, *args, **options):

        for schema in get_all_tenant_schemas():

            if 'public' not in schema:

                self.stdout.write(self.style.SUCCESS(f"Applying migrations to {schema}..."))

                # Set the search path to the tenant's schema
                with connection.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {schema};")

                import logging
                _l = logging.getLogger('provision')

                from django.contrib.auth.models import User

                username = os.environ.get('ADMIN_USERNAME', None)
                password = os.environ.get('ADMIN_PASSWORD', None)
                email = os.environ.get('ADMIN_EMAIL', None)

                if username and password:

                    try:

                        superuser = User.objects.get(username=username)

                        _l.info("Skip. Super user '%s' already exists." % superuser.username)

                    except User.DoesNotExist:

                        superuser = User.objects.create_superuser(
                            username=username,
                            email=email,
                            password=password)

                        superuser.save()
                        _l.info("Super user '%s' created." % superuser.username)

                else:
                    _l.info("Skip. Super user username and password are not provided.")

                # Optionally, reset the search path to default after migrating
                with connection.cursor() as cursor:
                    cursor.execute("SET search_path TO public;")
