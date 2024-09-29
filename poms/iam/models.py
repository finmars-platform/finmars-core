from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import NamedModel, TimeStampedModel
from poms.configuration.models import ConfigurationModel
from poms.users.models import MasterUser, Member


def default_list():
    return []


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
    resource_groups = ArrayField(
        base_field=models.CharField(max_length=1024),
        default=default_list,
        verbose_name=gettext_lazy("List of ResourceGroup user_codes"),
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


class ResourceGroupManager(models.Manager):
    def add_object(
        self,
        group_user_code: str,
        app_name: str,
        model_name: str,
        object_id: int,
        object_user_code: str,
    ):
        rg = self.get_queryset().get(user_code=group_user_code)
        rg.create_assignment(
            app_name.lower(), model_name.lower(), object_id, object_user_code
        )

    def remove_object(
        self, group_user_code: str, app_name: str, model_name: str, object_id: int
    ):
        rg = self.get_queryset().get(user_code=group_user_code)
        rg.remove_assignment(app_name.lower(), model_name.lower(), object_id)


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
        unique=True,
        help_text=gettext_lazy(
            "Unique code of the ResourceGroup. Used in Configuration and Permissions Logic"
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

    objects = ResourceGroupManager()

    class Meta:
        ordering = ["user_code"]

    def __str__(self):
        return self.name

    def create_assignment(
        self,
        app_name: str,
        model_name: str,
        object_id: int,
        object_user_code: str,
    ):
        """
        Creates an assignment of an object to this ResourceGroup.

        Args:
            app_name: The app name of the model.
            model_name: The name of the model.
            object_id: The ID of the object to be assigned.
            object_user_code: The user_code of the object to be assigned.

        Raises:
            ValueError: If object_id does not exist.
            ValueError: If object_user_code does not match the object's user_code.
        """

        # Validate that content_type is available
        content_type = ContentType.objects.get_by_natural_key(app_name, model_name)

        # Validate that object_id is available
        model = content_type.model_class()
        obj = model.objects.get(id=object_id)

        # Validate that object_user_code is available
        if obj.user_code != object_user_code:
            raise ValueError(
                "create_assignment: object_user_code does not match object's user_code"
            )

        ResourceGroupAssignment.objects.update_or_create(
            resource_group=self,
            content_type=content_type,
            object_id=object_id,
            defaults=dict(object_user_code=object_user_code),
        )

    def remove_assignment(self, app_name: str, model_name: str, object_id: int):
        """
        Removes an assignment of an object to this ResourceGroup.

        Args:
            app_name: The app name of the model.
            model_name: The name of the model.
            object_id: The ID of the object to be removed.

        Raises:
            ValueError: If the object_id does not exist.
        """

        # Validate that content_type is available
        content_type = ContentType.objects.get_by_natural_key(app_name, model_name)

        # Validate that object_id is available
        model = content_type.model_class()
        _ = model.objects.get(id=object_id)

        obj = ResourceGroupAssignment.objects.get(
            resource_group=self,
            content_type=content_type,
            object_id=object_id,
        )
        obj.delete()


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
