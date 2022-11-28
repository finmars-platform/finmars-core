from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, dispatch_uid='create_user_profile', sender=User)
def create_user_profile(instance=None, created=None, using=None, **kwargs):
    # if created:
    #     UserProfile.objects.using(using).create(user=instance)
    pass
