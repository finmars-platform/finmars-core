from django.db import models
from django.utils.translation import gettext_lazy

from poms.users.models import MasterUser
from poms.common.models import NamedModel, OwnerModel


class Client(NamedModel):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="client",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    first_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="First name of client",
    )
    last_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Last name of client",
    )
    telephone = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Telephone number of client",
    )
    email = models.EmailField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Email address of client",
    )

    class Meta(NamedModel.Meta):
        verbose_name = gettext_lazy("client")
        verbose_name_plural = gettext_lazy("clients")


class ClientSecret(OwnerModel):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="client_secrets",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    user_code = models.CharField(
        max_length=1024,
        verbose_name=gettext_lazy("user code"),
        help_text=gettext_lazy(
            "Unique Code for this object. Used in Configuration and Permissions Logic"
        ),
    )
    client = models.ForeignKey(
        Client,
        related_name="client_secrets",
        verbose_name=gettext_lazy("client"),
        on_delete=models.CASCADE,
    )
    provider = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    portfolio = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    class Meta(NamedModel.Meta):
        verbose_name = gettext_lazy("client secret")
        verbose_name_plural = gettext_lazy("client secrets")
        unique_together = [["master_user", "user_code"]]
        ordering = ["user_code"]

    def __str__(self):
        return self.user_code
