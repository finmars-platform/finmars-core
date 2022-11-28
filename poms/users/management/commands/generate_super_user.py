from django.core.management import BaseCommand

__author__ = 'szhitenev'

import os


class Command(BaseCommand):
    help = 'Generate super user'

    def handle(self, *args, **options):

        from django.contrib.auth.models import User

        username = os.environ.get('ADMIN_USERNAME', None)
        password = os.environ.get('ADMIN_PASSWORD', None)
        email = os.environ.get('ADMIN_EMAIL', None)

        if username and password:

            try:

                superuser = User.objects.get(username=username)

                self.stdout.write("Skip. Super user '%s' already exists." % superuser.username)

            except User.DoesNotExist:

                superuser = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password)

                superuser.save()
                self.stdout.write("Super user '%s' created." % superuser.username)

        else:
            self.stdout.write("Skip. Super user username and password are not provided.")
