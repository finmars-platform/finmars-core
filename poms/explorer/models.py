from pathlib import Path

from django.conf import settings
from django.db import models

from mptt.models import MPTTModel, TreeForeignKey

from poms.common.fields import ResourceGroupsField
from poms.common.models import TimeStampedModel
from poms.configuration.utils import get_default_configuration_code
from poms.iam.models import AccessPolicy, Group
from poms.users.models import Member

MAX_PATH_LENGTH = 2048
MAX_NAME_LENGTH = 255
MAX_TOKEN_LENGTH = 32

DIR_SUFFIX = "/"


def get_root_path():
    from poms.users.models import MasterUser

    space_code = MasterUser.objects.first().space_code or "space00000"
    return f"{space_code}{DIR_SUFFIX}"


class AccessLevel:
    READ = "read"
    WRITE = "write"

    @classmethod
    def validate_level(cls, access: str):
        if access not in {cls.READ, cls.WRITE}:
            raise ValueError(f"AccessLevel can be '{cls.READ}' or '{cls.WRITE}'")


class StorageObject(MPTTModel, TimeStampedModel):
    """
    Model represents an object (directory or file)
    in the Finmars storage (Filesystem, AWS, Azure...).
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
    size = models.PositiveBigIntegerField(
        default=0,
        help_text="Size of the file in bytes",
    )
    is_file = models.BooleanField(
        default=False,
        help_text="Is this directory a file",
    )
    resource_groups = ResourceGroupsField()

    class Meta:
        ordering = ["path"]

    class MPTTMeta:
        level_attr = "mptt_level"
        order_insertion_by = ["path"]

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
