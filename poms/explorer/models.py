from django.db import models
from django.utils.crypto import get_random_string

from poms.common.models import DataTimeStampedModel
from poms.iam.models import AccessPolicy, Group
from poms.users.models import Member

MAX_PATH_LENGTH = 2048
MAX_NAME_LENGTH = 255


class FinmarsDirectory(DataTimeStampedModel):
    """
    Model representing a directory in the Finmars storage (File system, AWS, Azure...).
    """

    name = models.CharField(
        max_length=MAX_NAME_LENGTH,
        db_index=True,
        help_text="Directory name",
    )
    path = models.CharField(
        max_length=MAX_PATH_LENGTH,
        db_index=True,
        help_text="Path to the directory in the storage system",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["path", "name"],
                name="unique_directory_path",
            )
        ]
        ordering = ["path", "name"]

    def __str__(self):
        return self.name


class FinmarsFile(DataTimeStampedModel):
    """
    Model representing a file in the Finmars storage (File system, AWS, Azure...).
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
        return self.name

    def _extract_extension(self) -> str:
        parts = self.name.rsplit(".", 1)
        return parts[1] if len(parts) > 1 else ""

    def save(self, *args, **kwargs):
        self.extension = self._extract_extension()
        super().save(*args, **kwargs)

    @property
    def filepath(self):
        return f"{self.path.rstrip('/')}/{self.name}"


class ShareAccessRecord(models.Model):
    owner = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
    )
    path = models.CharField(
        db_index=True,
        max_length=MAX_PATH_LENGTH,
        help_text="Path to the file/directory in the storage system",
    )
    shared_with_users = models.ManyToManyField(
        Member,
        through="MemberShare",
        related_name="shared_files",
    )
    shared_with_groups = models.ManyToManyField(
        Group,
        through="GroupShare",
        related_name="shared_files",
    )
    public_link_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    public_link_expires = models.DateTimeField(
        blank=True,
        null=True,
    )
    public_link_policy = models.ForeignKey(
        AccessPolicy,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    def generate_public_link(self):
        self.public_link_token = get_random_string(32)
        self.save()


class MemberShare(models.Model):
    share_access_record = models.ForeignKey(
        ShareAccessRecord,
        on_delete=models.CASCADE,
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
    )
    policy = models.ForeignKey(
        AccessPolicy,
        on_delete=models.CASCADE,
    )


class GroupShare(models.Model):
    share_access_record = models.ForeignKey(
        ShareAccessRecord,
        on_delete=models.CASCADE,
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
    )
    policy = models.ForeignKey(
        AccessPolicy,
        on_delete=models.CASCADE,
    )
