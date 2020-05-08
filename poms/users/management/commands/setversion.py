from datetime import datetime
import os
import os.path

from django.core.management import BaseCommand
from django.db import transaction

from poms_app import settings

__author__ = 'szhitenev'


class Command(BaseCommand):
    help = 'Set Version of Configuration Files'

    current_major = 0
    current_minor = 0
    current_revision = 0

    def add_arguments(self, parser):
        parser.add_argument('--major', type=int)
        parser.add_argument('--minor', type=int)
        parser.add_argument('--revision', type=int)
        parser.add_argument('--increment', type=str)


    def handle(self, *args, **options):

        version_date = datetime.today().strftime('%Y-%m-%d-%H-%M')

        version_path = os.path.join(settings.BASE_DIR, 'data', 'version.txt')

        print('version_path %s' % version_path)
        print('options %s' % options)


        if os.path.isfile(version_path):

            with open(version_path, 'r') as f:

                try:
                    line = f.read()

                    version = line.split(' ')[0]
                    parts = version.split('.')

                    self.current_major = int(parts[0])
                    self.current_minor = int(parts[1])
                    self.current_revision = int(parts[2])

                except Exception as e:

                    print('Can\'t parse version file. Error:  %s' % e)

            with open(version_path, 'w') as f:

                version = self.get_version_str(options, version_date)

                f.write(version)

        else:

            with open(version_path, 'w') as f:

                version = self.get_version_str(options, version_date)

                f.write(version)


    def get_version_str(self, options, version_date):

        if options['major']:
            self.current_major = options['major']

        if options['minor']:
            self.current_minor = options['minor']

        if options['revision']:
            self.current_revision = options['revision']

        if options['increment']:

            if options['increment'] == 'major':
                self.current_major = self.current_major + 1

            if options['increment'] == 'minor':
                self.current_minor = self.current_minor + 1

            if options['increment'] == 'revision':
                self.current_revision = self.current_revision + 1

        result_version = str(self.current_major) + "." + str(self.current_minor) + "." + str(self.current_revision) + " " + version_date

        print('New version: %s' % result_version)

        return result_version
