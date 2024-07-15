from django.conf import settings
from django.db import models

# from django.utils.crypto import get_random_string

from mptt.models import MPTTModel, TreeForeignKey

from poms.common.models import DataTimeStampedModel
from poms.configuration.utils import get_default_configuration_code
from poms.iam.models import AccessPolicy, Group
from poms.users.models import Member

MAX_PATH_LENGTH = 2048
MAX_NAME_LENGTH = 255
MAX_TOKEN_LENGTH = 32

READ = "read"
FULL = "full"
DIR = "dir"
FILE = "file"


class ObjMixin:
    @property
    def resource(self):
        return self.__str__()

    def policy_user_code(self):
        return (
            f"{get_default_configuration_code()}:{settings.SERVICE_NAME}"
            f":explorer:{self.resource}"
        )

    def _fix_path(self):
        """
        Ensures the path starts with a slash and does not end with a slash.
        If the path is empty, sets it to "/".
        """
        if self.path and self.path[0] != "/":
            self.path = "/" + self.path
        if self.path and self.path[-1] == "/":
            self.path = self.path.rstrip("/")
        if not self.path:
            self.path = "/"


class FinmarsDirectory(MPTTModel, ObjMixin, DataTimeStampedModel):
    """
    Model represents a directory in the Finmars storage (File system, AWS, Azure...).
    """

    path = models.CharField(
        max_length=MAX_PATH_LENGTH,
        unique=True,
        blank=False,
        help_text="Path to the directory in the storage system",
    )
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    __size = 0

    class Meta:
        ordering = ["path"]

    class MPTTMeta:
        level_attr = "mptt_level"
        order_insertion_by = ["path"]

    def __str__(self):
        return f"{DIR}:{self.path}"

    @property
    def size(self):
        return self.__size

    @property
    def name(self):
        return self.path

    @property
    def fullpath(self):
        return self.path

    def save(self, *args, **kwargs):
        """
        This method overrides the default save method. It removes any trailing slashes
        from the `path` attribute and sets the `name` attribute to the
        last part of the `path`.
        """
        self._fix_path()
        super().save(*args, **kwargs)


class FinmarsFile(ObjMixin, DataTimeStampedModel):
    """
    Model represents a file in the Finmars storage (File system, AWS, Azure...).
    """

    name = models.CharField(
        max_length=MAX_NAME_LENGTH,
        db_index=True,
        help_text="File name, including extension",
    )
    path = models.CharField(
        max_length=MAX_PATH_LENGTH,
        db_index=True,
        help_text="Path to the file in the storage system",
    )
    extension = models.CharField(
        blank=True,
        default="",
        max_length=MAX_NAME_LENGTH,
        help_text="File name extension",
    )
    size = models.PositiveBigIntegerField(
        help_text="Size of the file in bytes",
    )
    directory = models.ForeignKey(
        FinmarsDirectory,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="files",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["path", "name"],
                name="unique_file_path",
            )
        ]
        ordering = ["path", "name"]

    def __str__(self):
        return f"{FILE}:{self.fullpath}"

    @property
    def fullpath(self):
        return f"{self.path}/{self.name}"

    def _extract_extension(self) -> str:
        parts = self.name.rsplit(".", 1)
        return parts[1] if len(parts) > 1 else ""

    def save(self, *args, **kwargs):
        self._fix_path()
        self.extension = self._extract_extension()
        super().save(*args, **kwargs)


# class ShareAccessRecord(models.Model):
#     owner = models.ForeignKey(
#         Member,
#         on_delete=models.CASCADE,
#     )
#     path = models.CharField(
#         db_index=True,
#         max_length=MAX_PATH_LENGTH,
#         help_text="Path to the file/directory in the storage system",
#     )
#     shared_with_users = models.ManyToManyField(
#         Member,
#         through="MemberShare",
#         related_name="shared_files",
#     )
#     shared_with_groups = models.ManyToManyField(
#         Group,
#         through="GroupShare",
#         related_name="shared_files",
#     )
#     public_link_token = models.CharField(
#         max_length=MAX_TOKEN_LENGTH,
#         blank=True,
#         null=True,
#     )
#     public_link_expires = models.DateTimeField(
#         blank=True,
#         null=True,
#     )
#     public_link_policy = models.ForeignKey(
#         AccessPolicy,
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#     )
#
#     def generate_public_link(self):
#         self.public_link_token = get_random_string(MAX_TOKEN_LENGTH)
#         self.save()
#
#
# class MemberShare(models.Model):
#     share_access_record = models.ForeignKey(
#         ShareAccessRecord,
#         on_delete=models.CASCADE,
#     )
#     member = models.ForeignKey(
#         Member,
#         on_delete=models.CASCADE,
#     )
#     policy = models.ForeignKey(
#         AccessPolicy,
#         on_delete=models.CASCADE,
#     )
#
#
# class GroupShare(models.Model):
#     share_access_record = models.ForeignKey(
#         ShareAccessRecord,
#         on_delete=models.CASCADE,
#     )
#     group = models.ForeignKey(
#         Group,
#         on_delete=models.CASCADE,
#     )
#     policy = models.ForeignKey(
#         AccessPolicy,
#         on_delete=models.CASCADE,
#     )
