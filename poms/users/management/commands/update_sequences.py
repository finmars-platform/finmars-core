from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection
from django.db.models import AutoField


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
    help = "Repair autoincrement primary keys sequence to be greater than max id"

    def handle(self, *args, **options):
        models = apps.get_models()

        for schema in get_all_tenant_schemas():
            self.stdout.write(f"Checking schema {schema}")
            with connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {schema};")

                for model in models:
                    if not model._meta.managed:
                        continue

                    table_name = model._meta.db_table
                    primary_key_field = model._meta.pk
                    if not isinstance(primary_key_field, AutoField):
                        continue

                    primary_key_column = primary_key_field.column
                    cursor.execute(
                        f"SELECT MAX({primary_key_column}) FROM {table_name}"
                    )
                    max_id = cursor.fetchone()[0] or 0

                    cursor.execute(f"""SELECT seq.relname AS sequence_name
                                        FROM pg_class AS seq
                                        JOIN pg_depend AS dep ON seq.oid = dep.objid
                                        JOIN pg_class AS tab ON dep.refobjid = tab.oid
                                        JOIN pg_namespace AS ns ON tab.relnamespace = ns.oid
                                        WHERE seq.relkind = 'S'
                                          AND tab.relname = '{table_name}' and ns.nspname = '{schema}'""")
                    sequence_exists = cursor.fetchone()
                    if not sequence_exists:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Sequence {sequence_name} does not exist for {schema}.{table_name}"
                            )
                        )
                        continue
                    sequence_name = sequence_exists[0]

                    cursor.execute(f"SELECT last_value FROM {sequence_name}")
                    last_id = cursor.fetchone()[0]

                    if max_id > last_id:
                        cursor.execute(
                            f"SELECT setval('{sequence_name}', {max_id + 1}, false)"
                        )
                        self.stdout.write(
                            f"Updated sequence {schema}.{sequence_name} from {last_id} to {max_id + 1}"
                        )

        self.stdout.write(
            self.style.SUCCESS("Successfully updated sequences where necessary")
        )
