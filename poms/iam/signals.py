from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from poms.iam.models import AccessPolicy, Role, Group

import logging

_l = logging.getLogger('poms.iam')


'''
Performance improvement, save member access policies in cache,
code below just clears the cache when access policy is updated 
'''
def clear_member_access_policies_cache(member):
    cache_key = f'member_access_policies_{member.id}'
    _l.info("clear_member_access_policies_cache.going to clear cache for %s" % member)
    cache.delete(cache_key)

@receiver(post_save, sender=AccessPolicy)
@receiver(post_delete, sender=AccessPolicy)
def clear_access_policy_cache(sender, instance, **kwargs):
    # Clear cache for all related users
    for member in instance.members.all():
        clear_member_access_policies_cache(member)
    for member in instance.iam_roles.all().values_list('members', flat=True):
        clear_member_access_policies_cache(member)
    for member in instance.iam_groups.all().values_list('members', flat=True):
        clear_member_access_policies_cache(member)

@receiver(post_save, sender=Role)
@receiver(post_delete, sender=Role)
def clear_role_cache(sender, instance, **kwargs):
    # Clear cache for all related users
    for member in instance.members.all():
        clear_member_access_policies_cache(member)

@receiver(post_save, sender=Group)
@receiver(post_delete, sender=Group)
def clear_group_cache(sender, instance, **kwargs):
    # Clear cache for all related users
    for member in instance.members.all():
        clear_member_access_policies_cache(member)