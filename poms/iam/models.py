from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import NamedModel, TimeStampedModel
from poms.configuration.models import ConfigurationModel
from poms.users.models import MasterUser, Member


class AccessPolicy(ConfigurationModel, TimeStampedModel):
    name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("Name"),
    )
    user_code = models.CharField(
        max_length=1024,
        unique=True,
        verbose_name=gettext_lazy("User Code"),
    )
    description = models.TextField(blank=True)
    policy = models.JSONField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("Policy"),
        help_text="Access Policy JSON",
    )
    members = models.ManyToManyField(
        Member,
        related_name="iam_access_policies",
        blank=True,
    )
    resource_group = models.ForeignKey(
        "ResourceGroup",
        related_name="access_policies",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("Resource Group"),
    )

    # objects = AccessPoliceManager()

    class Meta:
        verbose_name = gettext_lazy("Access Policy Template")
        verbose_name_plural = gettext_lazy("Access Policy Templates")

    def __str__(self):
        return str(self.name)


class Role(ConfigurationModel, TimeStampedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    user_code = models.CharField(
        max_length=1024,
        unique=True,
        verbose_name=gettext_lazy("User Code"),
    )

    # Hate that it should be Member instead of User
    members = models.ManyToManyField(
        Member,
        related_name="iam_roles",
        blank=True,
    )
    access_policies = models.ManyToManyField(
        AccessPolicy,
        related_name="iam_roles",
        blank=True,
    )

    def __str__(self):
        return str(self.name)


class Group(ConfigurationModel, TimeStampedModel):
    """
    Part of configuration and thus has configuration_code
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    user_code = models.CharField(
        max_length=1024,
        unique=True,
        verbose_name=gettext_lazy("User Code"),
    )

    # Hate that it should be Member instead of User
    members = models.ManyToManyField(
        Member,
        related_name="iam_groups",
        blank=True,
    )
    roles = models.ManyToManyField(
        Role,
        related_name="iam_groups",
    )
    access_policies = models.ManyToManyField(
        AccessPolicy,
        related_name="iam_groups",
        blank=True,
    )

    def __str__(self):
        return str(self.name)


from django.contrib.auth.models import Group as UserGroup

class ResourceGroup(NamedModel, TimeStampedModel):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="resource_groups",
        verbose_name=gettext_lazy("Master User"),
        on_delete=models.CASCADE,
    )
    user_code = models.CharField(
        max_length=1024,
        unique=True,
        verbose_name=gettext_lazy("User Code"),
        help_text=gettext_lazy("Unique User Code of the Resource Group"),
    )
    group = models.OneToOneField(
        UserGroup,
        related_name="resource_group",
        verbose_name=gettext_lazy("Django User Group"),
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ["user_code"]


# class ResourceAccessPolicy(TimeStampedModel):
#     ACCESS_CHOICES = [
#         ("read", "Read"),
#         ("write", "Write"),
#     ]
#     RESOURCE_TYPES = [
#         ("api", "API"),
#         ("file", "File"),
#         ("db", "DB"),
#     ]
#     resource_group = models.ForeignKey(
#         ResourceGroup,
#         related_name="access_policies",
#         on_delete=models.CASCADE,
#     )
#     resource_type = models.CharField(
#         max_length=5,
#         db_index=True,
#         choices=RESOURCE_TYPES,
#     )
#     resource_name = models.CharField(
#         max_length=255,
#         db_index=True,
#     )
#     allowed_access = models.CharField(
#         max_length=5,
#         choices=ACCESS_CHOICES,
#     )
#
#     def __str__(self):
#         return f"{self.resource_type}:{self.resource_name}:{self.allowed_access}"
#
#     class Meta:
#         unique_together = ["resource_group", "resource_type", "resource_name"]


# Important, needs for cache clearance after Policy Updated
from . import signals
