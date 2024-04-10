import logging
import time

from django.core.management.base import BaseCommand
from django.db import connection

_l = logging.getLogger('provision')

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
    help = 'Clear celery tasks and procedures'

    def handle(self, *args, **options):
        from poms_app.celery import app as celery_app

        _l.info("Clearing celery tasks and procedures")

        # Need to wait to ensure celery workers are available
        i = celery_app.control.inspect()

        max_wait = 60
        interval_wait = 5
        current_wait = 0

        while not i.stats() and current_wait < max_wait:
            _l.info('Waiting for Celery worker(s)...')
            time.sleep(interval_wait)
            current_wait = current_wait + interval_wait

        _l.info('Celery worker(s) are now available.')

        # WARNING Do not delete
        # important, its inits celery listeners for global state
        # it uses for record history in post_save post_delete signals for proper context
        from poms_app import celery_app

        from poms.common.celery import cancel_existing_tasks
        from poms.common.celery import cancel_existing_procedures

        for schema in get_all_tenant_schemas():

            with connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {schema};")

            cancel_existing_tasks(celery_app)
            cancel_existing_procedures(celery_app)

            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO public;")
