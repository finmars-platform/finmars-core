from django.core.management import BaseCommand
from django.db import transaction

__author__ = "ailyukhin"


class Command(BaseCommand):
    help = "Init standalone DB version"

    def handle(self, *args, **options):
        from django.contrib.auth.models import User
        from poms.users.models import MasterUser, Member

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                username="admin", defaults={"is_staff": True, "is_superuser": True}
            )
            if created:
                user.set_password("finmars")
                user.save()

            if MasterUser.objects.count() == 0:
                user, created = User.objects.get_or_create(
                    username="finmars", defaults={}
                )
                if created:
                    user.set_password("finmars")
                    user.save()
                master_user = MasterUser.objects.create_master_user(name="default")
                Member.objects.create(
                    master_user=master_user, user=user, is_owner=True, is_admin=True
                )
