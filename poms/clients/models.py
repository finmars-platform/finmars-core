from django.db import models
from django.utils.translation import gettext_lazy
from poms.users.models import MasterUser
from poms.common.models import NamedModel


class Client(NamedModel):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="client",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )

    class Meta(NamedModel.Meta):
        verbose_name = gettext_lazy("client")
        verbose_name_plural = gettext_lazy("clients")