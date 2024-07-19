from django.db import models
from django.utils.translation import gettext_lazy
from poms.common.encrypted_field import EncryptedTextField
from poms.common.models import DataTimeStampedModel, NamedModel
from poms.users.models import MasterUser


class VaultRecord(NamedModel, DataTimeStampedModel):
    master_user = models.ForeignKey(
        MasterUser,
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )

    data = EncryptedTextField()

    class Meta(NamedModel.Meta):
        unique_together = [["master_user", "user_code"]]
        ordering = ["user_code"]
