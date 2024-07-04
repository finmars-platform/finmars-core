from django.db import models

from poms.common.models import DataTimeStampedModel


class FinmarsFile(DataTimeStampedModel):
    """
    Model representing a file in the Finmars storage (File system, AWS, Azure...).
    """

    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="File name, including extension",
    )
    path = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Path to the file in the storage system",
    )
    extension = models.CharField(
        blank=True,
        default="",
        max_length=255,
        help_text="File name extension",
    )
    size = models.PositiveBigIntegerField(
        help_text="Size of the file in bytes",
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
