from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, editable=False, db_index=True,
                                   verbose_name=gettext_lazy('created'))
    modified = models.DateTimeField(auto_now=True, editable=False, db_index=True,
                                    verbose_name=gettext_lazy('modified'))

    class Meta:
        abstract = True
        get_latest_by = 'modified'
        ordering = ['created', ]


class Role(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    user_code = models.CharField(max_length=1024, unique=True,
                                 verbose_name=gettext_lazy('User Code'))
    configuration_code = models.CharField(max_length=255,
                                          default='com.finmars.local',
                                          verbose_name=gettext_lazy('Configuration Code'),
                                          help_text="Indicates that entity is part of Configuration and can be imported/exported.")

    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='iam_roles', blank=True)

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


class Group(models.Model):
    '''
    Part of configuration and thus has configuration_code
    '''
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    user_code = models.CharField(max_length=1024, unique=True,
                                 verbose_name=gettext_lazy('User Code'))
    configuration_code = models.CharField(max_length=255,
                                          default='com.finmars.local',
                                          verbose_name=gettext_lazy('Configuration Code'),
                                          help_text="Indicates that entity is part of Configuration and can be imported/exported.")

    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='iam_groups', blank=True)
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


class UserAccessPolicy(TimeStampedModel):
    '''
    Do not part of configuration, can not be exported
    '''
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="iam_user_policies",
        on_delete=models.CASCADE,
        verbose_name="User",
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
