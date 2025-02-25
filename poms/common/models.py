import logging

from django.core.cache import cache
from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.middleware import get_request
from poms.currencies.constants import DASH
from poms.expressions_engine import formula

EXPRESSION_FIELD_LENGTH = 4096

_l = logging.getLogger("poms.celery_tasks")


class OwnerModel(models.Model):
    owner = models.ForeignKey(
        "users.Member",
        verbose_name=gettext_lazy("owner"),
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True


class NamedModel(OwnerModel):
    user_code = models.CharField(
        max_length=1024,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("user code"),
        help_text=gettext_lazy(
            "Unique Code for this object. Used in Configuration and Permissions Logic"
        ),
    )
    name = models.CharField(
        max_length=255,
        verbose_name=gettext_lazy("name"),
        help_text="Human Readable Name of the object",
    )
    short_name = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("short name"),
        help_text="Short Name of the object. Used in dropdown menus",
    )
    public_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("public name"),
        help_text=gettext_lazy("Used if user does not have permissions to view object"),
    )
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("notes"),
        help_text="Notes, any useful information about the object",
    )

    is_enabled = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=gettext_lazy("is enabled"),
    )

    class Meta:
        abstract = True
        unique_together = [["master_user", "user_code"]]
        ordering = ["user_code"]

    def __str__(self):
        return self.user_code or ""

    def save(self, *args, **kwargs):
        # cache.clear()

        if not self.user_code:
            self.user_code = self.name
        if not self.short_name:
            self.short_name = self.name

        super(NamedModel, self).save(*args, **kwargs)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        db_index=True,
        verbose_name=gettext_lazy("created at"),
    )
    modified_at = models.DateTimeField(
        auto_now=True,
        editable=False,
        db_index=True,
        verbose_name=gettext_lazy("modified at"),
    )

    class Meta:
        abstract = True
        get_latest_by = "modified_at"
        ordering = [
            "created_at",
        ]


class AbstractClassModel(models.Model):
    id = models.PositiveSmallIntegerField(
        primary_key=True,
        verbose_name=gettext_lazy("ID"),
    )
    user_code = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=gettext_lazy("user code"),
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=gettext_lazy("name"),
    )
    short_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=gettext_lazy("short name"),
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("description"),
    )

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.user_code

    @classmethod
    def get_by_id(cls, pk):
        attr = f"_poms_cache_{pk}"
        try:
            return getattr(cls, attr)
        except AttributeError:
            val = cls.objects.get(pk=pk)
            setattr(cls, attr, val)
            return val


# noinspection PyUnresolvedReferences
class FakeDeletableModel(models.Model):
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=gettext_lazy("is deleted"),
        help_text="Mark object as deleted. Does not actually delete the object.",
    )
    deleted_at = models.DateTimeField(
        null=True,
        editable=False,
        verbose_name=gettext_lazy("deleted at"),
    )
    deleted_user_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("deleted user code"),
        help_text=(
            "Stores original user_code of object. Deleted objects has null "
            "user_code which makes it available again."
        ),
    )

    class Meta:
        abstract = True
        index_together = [["master_user", "is_deleted"]]

    def fake_delete(self):
        from poms.celery_tasks.models import CeleryTask
        from poms.common.celery import get_active_celery_task_id
        from poms.system_messages.handlers import send_system_message

        self.is_deleted = True

        fields_to_update = ["is_deleted", "modified_at"]
        try:
            # fake_delete called by REST API
            member = get_request().user.member
        except Exception:
            # fake_delete called by celery task
            celery_task_id = get_active_celery_task_id()

            celery_task = CeleryTask.objects.get(celery_task_id=celery_task_id)
            member = celery_task.member

        if hasattr(self, "user_code"):
            if self.user_code == DASH:
                return

            self.deleted_user_code = self.user_code
            self.name = f"(del) {self.name}"
            self.short_name = f"(del) {self.short_name}"
            self.user_code = formula.safe_eval(
                'generate_user_code("del", "", 0)',
                context={"master_user": self.master_user},
            )
            # 'del00000000000000001'
            fields_to_update.extend(
                ["deleted_user_code", "name", "short_name", "user_code"]
            )

        if hasattr(self, "is_enabled"):
            self.is_enabled = False
            fields_to_update.append("is_enabled")

        if hasattr(self, "is_active"):  # instrument prop
            self.is_active = False
            fields_to_update.append("is_active")

        entity_name = self._meta.model_name

        send_system_message(
            master_user=self.master_user,
            performed_by=member.username,
            section="data",
            type="warning",
            title=f"Delete {entity_name} (manual)",
            description=f"{entity_name} was deleted (manual) - {self.name}",
        )

        self.save(update_fields=fields_to_update)

    def restore(self):
        from poms.celery_tasks.models import CeleryTask
        from poms.common.celery import get_active_celery_task_id
        from poms.system_messages.handlers import send_system_message

        # if not isinstance(context, dict):
        #     raise TypeError(
        #         f"Invalid value inside argument 'context' for "
        #         f"FakeDeletableModel.restore(). "
        #         f"Expected 'dict' got {type(context)}"
        #     )
        #
        # if "member" not in context:
        #     raise TypeError(
        #         f"Member was not specified inside argument 'context' for "
        #         f"FakeDeletableModel.restore() "
        #     )

        self.is_deleted = False

        fields_to_update = ["is_deleted", "modified_at"]

        try:
            # restore called by REST API
            member = get_request().user.member
        except Exception:
            # restore called by celery task
            celery_task_id = get_active_celery_task_id()

            celery_task = CeleryTask.objects.get(celery_task_id=celery_task_id)
            member = celery_task.member

        if hasattr(self, "user_code"):
            self.name = self.name.replace("(del) ", "")
            self.short_name = self.name.replace("(del) ", "")
            self.user_code = self.deleted_user_code
            self.deleted_user_code = None
            fields_to_update.extend(
                ["deleted_user_code", "name", "short_name", "user_code"]
            )

        if hasattr(self, "is_enabled"):
            self.is_enabled = True
            fields_to_update.append("is_enabled")

        if hasattr(self, "is_active"):  # instrument prop
            self.is_active = True
            fields_to_update.append("is_active")

        entity_name = self._meta.model_name

        send_system_message(
            master_user=self.master_user,
            performed_by=member.username,
            section="data",
            type="warning",
            title=f"Restore {entity_name} (manual)",
            description=f"{entity_name} was restored (manual) - {self.name}",
        )

        self.save(update_fields=fields_to_update)


class ComputedModel(models.Model):
    is_computed = models.BooleanField(
        default=True,
    )
    computed_at = models.DateTimeField(
        editable=False,
        auto_now=True,
        verbose_name=gettext_lazy("computed at"),
    )

    class Meta:
        abstract = True


class ObjectStateModel(models.Model):
    is_active = models.BooleanField(
        default=True,
    )
    actual_at = models.DateTimeField(
        null=True,
        help_text="Show the Date that object is truth for, e.g. price created_at is 2024-07-10 but actually this price is 2024-01-01"
    )
    source_type = models.CharField(
        default="manual",
    )
    source_origin = models.CharField(
        default="manual",
    )
    external_id = models.CharField(
        null=True,
        help_text="how object is referenced in external system"
    )
    is_manual_locked = models.BooleanField(
        default=False,
        help_text="just a flag to disable form on frontend"
    )
    is_locked = models.BooleanField(
        default=True,
        help_text="blocked to any change (only from finmars frontend change is allowed)"
    )

    class Meta:
        abstract = True


# ^_^ Cache ^_^ #
class BaseCacheManager(models.Manager):
    """
    Base cache manager for processing the logic of caching model instances by ID.
    Override `_get_identifier_from_obj` and `_get_obj_from_db` for custom behavior.
    This manager should be used in the `CacheModel`.
    Attention! Global responsibility, not linked to space_code.
    """
    def _get_identifier_from_obj(cls, obj):
        """
        Getting the identificators for the cache. Redefine for non-standard identifiers.
        """
        return obj.pk

    def _get_obj_from_db(self, pk):
        """
        Getting an object from the database. Redefine this method for non-standard identifiers.
        """
        return self.model.objects.get(pk=pk)

    def get_cache_key(self, pk):
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name

        return f"{app_label}_{model_name}_{pk}"

    def get_cache(self, master_user_pk):
        key = self.get_cache_key(master_user_pk)
        try:
            obj = cache.get(key)
            if obj is None:  # Cache miss
                raise ValueError("Cache miss")
        except Exception as e:
            # Log the error if needed
            obj = self._get_obj_from_db(master_user_pk)  # Fetch from DB
            self.set_cache(obj)  # Store in cache again
        return obj

    def set_cache(self, obj):
        identifier = self._get_identifier_from_obj(obj)
        key = self.get_cache_key(identifier)
        cache.set(key, obj, timeout=obj.cache_timeout)

    def delete_cache(self, obj):
        identifier = self._get_identifier_from_obj(obj)
        key = self.get_cache_key(identifier)
        cache.delete(key)


class CacheByMasterUserManager(BaseCacheManager):
    """
    Global cache manager that uses master_user ID as the identifier.
    The model must have a link to `MasterUser`.
    This manager should be used in the `CacheModel`.
    """
    def _get_identifier_from_obj(cls, obj):
        return obj.master_user.pk

    def _get_obj_from_db(self, pk):
        return self.model.objects.get(master_user__pk=pk)

    def get_cache(self, master_user_pk):
        return super().get_cache(pk=master_user_pk)

    def get_cache_key(self, master_user_pk):
        return super().get_cache_key(pk=master_user_pk)


class CacheModel(models.Model):
    """
    Abstract base model for integrating caching logic into Django models.
    This class provides functionality for caching model instances using a  
    custom cache manager `BaseCacheManager` or the managers inherited from it.

    Attrs:
        `cache_timeout`:
            Specifies the default timeout (in seconds) for cached instances.
        `objects`:
            Default Django manager for standard database operations.
        `cache`:
            Custom manager for handling caching logic. Redefine to the required manager.
    """
    cache_timeout = 3600
    objects = models.Manager()
    cache = BaseCacheManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.__class__.cache.delete_cache(self)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.__class__.cache.delete_cache(self)
        super().delete(*args, **kwargs)


# These models need to create custom context, that could be passed to serializers
class ProxyUser(object):
    def __init__(self, member, master_user):
        self.member = member
        self.master_user = master_user


class ProxyRequest(object):
    def __init__(self, user):
        self.user = user
