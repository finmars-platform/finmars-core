import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy

MAX_NAME_LENGTH = 255
MAX_URL_LENGTH = 512


class EcosystemConfiguration(models.Model):
    name = models.CharField(
        max_length=MAX_NAME_LENGTH,
        blank=True,
        default="",
        db_index=True,
        verbose_name=gettext_lazy("name"),
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("description"),
    )
    json_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("json data"),
    )

    @property
    def data(self):
        if not self.json_data:
            return None

        try:
            return json.loads(self.json_data)
        except (ValueError, TypeError):
            return None

    @data.setter
    def data(self, val):
        if val:
            self.json_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.json_data = None

    class Meta:
        unique_together = [
            ["name"],
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class WhitelabelModel(models.Model):
    company_name = models.CharField(
        max_length=MAX_NAME_LENGTH,
        verbose_name="Company Name",
    )
    theme_code = models.CharField(
        max_length=MAX_NAME_LENGTH,
        verbose_name="Theme Code",
        blank=True,
        null=True,
        help_text="com.finmars.client-a",
    )
    theme_css_url = models.URLField(
        max_length=MAX_URL_LENGTH,
        verbose_name="Theme CSS URL",
        blank=True,
        null=True,
        help_text="URI to theme.css file in Storage",
    )
    logo_dark_url = models.URLField(
        max_length=MAX_URL_LENGTH,
        verbose_name="Dark Logo URL",
        blank=True,
        null=True,
        help_text="URI to logo_dark image in Storage",
    )
    logo_light_url = models.URLField(
        max_length=MAX_URL_LENGTH,
        verbose_name="Light Logo URL",
        blank=True,
        null=True,
        help_text="URI to logo_light image in Storage",
    )
    favicon_url = models.URLField(
        max_length=MAX_URL_LENGTH,
        verbose_name="Favicon URL",
        blank=True,
        null=True,
        help_text="URI to favicon image in Storage",
    )
    custom_css = models.TextField(
        verbose_name="Custom CSS",
        blank=True,
        null=True,
        help_text="Custom CSS parameters for theme",
    )
    is_default = models.BooleanField(
        verbose_name="Is Default Logo/Schema",
        default=False,
    )

    # Add other potential fields for white-label customization

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Whitelabel settings for {self.company_name}"
