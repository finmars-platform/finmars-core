from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy

from poms.configuration.models import ConfigurationModel
from poms.users.models import Member


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, editable=False, db_index=True,
                                   verbose_name=gettext_lazy('created'))
    modified = models.DateTimeField(auto_now=True, editable=False, db_index=True,
                                    verbose_name=gettext_lazy('modified'))

    class Meta:
        abstract = True
        get_latest_by = 'modified'
        ordering = ['created', ]


class Role(ConfigurationModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    user_code = models.CharField(max_length=1024, unique=True,
                                 verbose_name=gettext_lazy('User Code'))

    # Hate that it should be Member instead of User
    members = models.ManyToManyField(Member, related_name='iam_roles', blank=True)

    def __str__(self):
        return self.name


class RoleAccessPolicy(TimeStampedModel):
    '''
    Do not part of configuration, can not be exported
    '''
    role = models.ForeignKey(Role, related_name="access_policies",
                             on_delete=models.CASCADE, verbose_name="Role")

    name = models.CharField(max_length=255, null=True, blank=True,
                            verbose_name=gettext_lazy('Name'))

    user_code = models.CharField(max_length=1024, unique=True,
                                 verbose_name=gettext_lazy('User Code'))

    policy = models.JSONField(null=True, blank=True, verbose_name=gettext_lazy('Policy'),
                              help_text="Access Policy JSON")

    class Meta:
        verbose_name = gettext_lazy("User Access Policy")
        verbose_name_plural = gettext_lazy("User Access Policies")

    def __str__(self):
        return 'Access Policy for %s' % self.role


class Group(ConfigurationModel):
    '''
    Part of configuration and thus has configuration_code
    '''
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    user_code = models.CharField(max_length=1024, unique=True,
                                 verbose_name=gettext_lazy('User Code'))

    # Hate that it should be Member instead of User
    members = models.ManyToManyField(Member, related_name='iam_groups', blank=True)
    roles = models.ManyToManyField(Role, related_name='iam_groups')

    def __str__(self):
        return self.name


class GroupAccessPolicy(TimeStampedModel):
    '''
    Do not part of configuration, can not be exported
    '''
    group = models.ForeignKey(Group, related_name="access_policies",
                              on_delete=models.CASCADE, verbose_name="Role")

    name = models.CharField(max_length=255, null=True, blank=True,
                            verbose_name=gettext_lazy('Name'))

    user_code = models.CharField(max_length=1024, unique=True,
                                 verbose_name=gettext_lazy('User Code'))

    policy = models.JSONField(null=True, blank=True, verbose_name=gettext_lazy('Policy'),
                              help_text="Access Policy JSON")

    class Meta:
        verbose_name = gettext_lazy("User Access Policy")
        verbose_name_plural = gettext_lazy("User Access Policies")

    def __str__(self):
        return 'Access Policy for %s' % self.group


class MemberAccessPolicy(TimeStampedModel):
    '''
    Do not part of configuration, can not be exported
    '''
    # Hate that it should be Member instead of User
    member = models.ForeignKey(
        Member,
        related_name="iam_member_policies",
        on_delete=models.CASCADE,
        verbose_name="Member",
    )

    name = models.CharField(max_length=255, null=True, blank=True,
                            verbose_name=gettext_lazy('Name'))

    user_code = models.CharField(max_length=1024, unique=True,
                                 verbose_name=gettext_lazy('User Code'))

    policy = models.JSONField(null=True, blank=True, verbose_name=gettext_lazy('Policy'),
                              help_text="Access Policy JSON")

    class Meta:
        verbose_name = gettext_lazy("User Access Policy")
        verbose_name_plural = gettext_lazy("User Access Policies")

    def __str__(self):
        return 'Access Policy for %s' % self.user


class AccessPolicyTemplate(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True,
                            verbose_name=gettext_lazy('Name'))

    user_code = models.CharField(max_length=1024, unique=True,
                                 verbose_name=gettext_lazy('User Code'))

    policy = models.JSONField(null=True, blank=True, verbose_name=gettext_lazy('Policy'),
                              help_text="Access Policy JSON")

    configuration_code = models.CharField(max_length=255,
                                          default='com.finmars.local',
                                          verbose_name=gettext_lazy('Configuration Code'))

    class Meta:
        verbose_name = gettext_lazy("Access Policy Template")
        verbose_name_plural = gettext_lazy("Access Policy Templates")

    def __str__(self):
        return self.name
