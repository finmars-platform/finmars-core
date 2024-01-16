from django.contrib.auth.models import User
from poms.users.models import Member


def _print_all_records(model, arg1, arg2, arg3):
    print("\n")
    for m in model.objects.using("default").all():
        print(f"{arg1}{m.id}{arg2}{m.username}")
    for m in model.objects.using("replica").all():
        print(f"{arg3}{m.id}{arg2}{m.username}")
    print("-" * 60)
    print()


def print_users_and_members():
    _print_all_records(User, "default: u.id=", " u.username=", "replica: u.id=")
    _print_all_records(Member, "default: m.id=", " m.username=", "replica: m.id=")
