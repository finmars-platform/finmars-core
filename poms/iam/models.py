import contextlib
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
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
    @staticmethod
    def validate_obj(obj: Any):
        if not hasattr(obj, "resource_groups"):
            raise RuntimeError(
                f"ResourceGroupManager: instance of {obj._meta.model_name} "
                f"does not have 'resource_groups' field"
            )

    def add_object(self, group_user_code: str, obj_instance: Any):
        self.validate_obj(obj_instance)
        rg = self.get_queryset().get(user_code=group_user_code)
        rg.create_assignment(obj_instance)

    def del_object(self, group_user_code: str, obj_instance: Any):
        self.validate_obj(obj_instance)
        rg = self.get_queryset().get(user_code=group_user_code)
        rg.delete_assignment(obj_instance)


class ResourceGroup(models.Model):
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

    @staticmethod
    def get_content_type(obj: Any) -> ContentType:
        return ContentType.objects.get_by_natural_key(
            obj._meta.app_label,
            obj._meta.model_name,
        )

    def create_assignment(self, obj_instance: Any):
        """
        Creates an assignment of an object to this ResourceGroup.
        Args:
            obj_instance: model instance to be assigned to the group.
        """

        with transaction.atomic():
            obj_instance.resource_groups.append(self.user_code)
            obj_instance.resource_groups = list(set(obj_instance.resource_groups))
            obj_instance.save(update_fields=["resource_groups"])
            ResourceGroupAssignment.objects.update_or_create(
                resource_group=self,
                content_type=self.get_content_type(obj_instance),
                object_id=obj_instance.id,
                defaults=dict(object_user_code=obj_instance.user_code),
            )

    def delete_assignment(self, obj_instance: Any):
        """
        Removes an assignment of an object to this ResourceGroup.
        Args:
            obj_instance: model instance to be removed from the group.
        """

        with contextlib.suppress(ValueError):
            obj_instance.resource_groups.remove(self.user_code)

        with transaction.atomic():
            obj_instance.save(update_fields=["resource_groups"])
            assignment = ResourceGroupAssignment.objects.filter(
                resource_group=self,
                content_type=self.get_content_type(obj_instance),
                object_id=obj_instance.id,
            ).first()
            if assignment:
                assignment.delete()

    def destroy_assignments(self):
        group_assignments = ResourceGroupAssignment.objects.filter(resource_group=self)

        for assignment in group_assignments:
            model = assignment.content_type.model_class()
            obj = model.objects.get(id=assignment.object_id)
            if hasattr(obj, "resource_groups"):
                obj.resource_groups.remove(self.user_code)
                obj.save(update_fields=["resource_groups"])

        group_assignments.delete()


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
