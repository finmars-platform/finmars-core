import os
import os.path
from datetime import datetime

from django.core.management import BaseCommand

from poms_app import settings

__author__ = 'szhitenev'


class Command(BaseCommand):
    help = 'Get Fancy Name'
    def handle(self, *args, **options):

        from haikunator import Haikunator
        import sys

        haikunator = Haikunator()
        worker_name = haikunator.haikunate(delimiter='-', token_length=0)

        return worker_name