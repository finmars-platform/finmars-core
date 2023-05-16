from django.core.management import BaseCommand

__author__ = 'szhitenev'

import os


class Command(BaseCommand):
    help = 'Generate super user'

    def handle(self, *args, **options):

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
