
import logging
from celery import shared_task

from django.core.management import call_command
from django.db import connection
from io import StringIO

_l = logging.getLogger("poms.common")

@shared_task(bind=True)
def apply_migration_to_space(self, realm_code, space_code):

    with connection.cursor() as cursor:
        cursor.execute(f"SET search_path TO {space_code};")

    # Create StringIO buffers to capture the output
    out_buffer = StringIO()
    err_buffer = StringIO()

    _l.info("RealmMigrateSchemeView.space_code %s" % space_code)

    # Programmatically call the migrate command
    call_command("migrate", stdout=out_buffer, stderr=err_buffer)

    # Log the captured outputs
    _l.info("Migrate command output: %s", out_buffer.getvalue())

    error = err_buffer.getvalue()
    if error:
        _l.error("Migrate command errors: %s", err_buffer.getvalue())

    # Close the buffers
    out_buffer.close()
    err_buffer.close()

    # TODO szhitenev
    # Add callback to AUthorizer to notify authorizer that backend completed migrations
    # if success:
        # send status operational
    # if error
        # send status error