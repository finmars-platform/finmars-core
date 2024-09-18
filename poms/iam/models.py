from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
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


class ResourceGroup(models.Model):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="resource_groups",
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        max_length=255,
        unique=True,
    )
    user_code = models.CharField(
        max_length=1024,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("user code"),
        help_text=gettext_lazy(
            "Unique Code for this object. Used in Configuration and Permissions Logic"
        ),
    )
    description = models.TextField(
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
    )
    modified_at = models.DateTimeField(
        auto_now=True,
        editable=False,
    )

    class Meta:
        ordering = ["user_code"]

    def __str__(self):
        return self.name


class ResourceGroupAssignment(models.Model):
    resource_group = models.ForeignKey(
        ResourceGroup,
        related_name="assignments",
        on_delete=models.CASCADE,
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")  # virtual field
    object_user_code = models.CharField(
        max_length=1024,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("user code"),
        help_text=gettext_lazy("Unique Code for referenced object."),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
    )
    modified_at = models.DateTimeField(
        auto_now=True,
        editable=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["resource_group", "content_type", "object_id"],
                name="resource_group_object_assignment",
            )
        ]

    def __str__(self) -> str:
        return (
            f"{self.resource_group.name} assigned to "
            f"{self.content_object}:{self.object_user_code}"
        )


# Important, needs for cache clearance after Policy Updated !!!
from . import signals
