from django.core.management import BaseCommand

__author__ = 'szhitenev'

import os


class Command(BaseCommand):
    help = 'Drop Django Migrations'

    def handle(self, *args, **options):

        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute('drop table django_migrations;')