from pathlib import Path

from django.conf import settings
from django.db import models

from mptt.models import MPTTModel, TreeForeignKey

from poms.common.models import DataTimeStampedModel
from poms.configuration.utils import get_default_configuration_code
from poms.iam.models import AccessPolicy, Group
from poms.users.models import Member


MAX_PATH_LENGTH = 2048
MAX_NAME_LENGTH = 255
MAX_TOKEN_LENGTH = 32

DIR_SUFFIX = "/*"
ROOT_PATH = DIR_SUFFIX


class AccessLevel:
    READ = "read"
    WRITE = "write"

    @classmethod
    def validate_level(cls, access: str):
        if access not in {cls.READ, cls.WRITE}:
            raise ValueError(f"AccessLevel must be either '{cls.READ}' or '{cls.WRITE}'")


class ObjMixin:
    def __str__(self):
        return self.path

    def policy_user_code(self, access: str = AccessLevel.READ) -> str:
        AccessLevel.validate_level(access)
        return (
            f"{get_default_configuration_code()}:{settings.SERVICE_NAME}"
            f":explorer:{self.path}-{access}"
        )

    @property
    def name(self) -> str:
        path = Path(self.path)
        return path.name

    @property
    def extension(self) -> str:
        path = Path(self.path)
        return path.suffix


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

    class Meta:
        ordering = ["path"]

    class MPTTMeta:
        level_attr = "mptt_level"
        order_insertion_by = ["path"]

    @property
    def size(self):
        return 0


class FinmarsFile(ObjMixin, DataTimeStampedModel):
    """
    Model represents a file in the Finmars storage (File system, AWS, Azure...).
    """

    path = models.CharField(
        max_length=MAX_PATH_LENGTH,
        unique=True,
        help_text="Path to the file in the storage system with name and extension",
    )
    parent = models.ForeignKey(
        FinmarsDirectory,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="files",
    )
    size = models.PositiveBigIntegerField(
        help_text="Size of the file in bytes",
    )

    class Meta:
        ordering = ["path"]
