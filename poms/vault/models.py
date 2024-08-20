import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy
from poms.common.encrypted_field import EncryptedTextField
from poms.common.models import TimeStampedModel, NamedModel
from poms.users.models import MasterUser


class VaultRecord(NamedModel, TimeStampedModel):
    master_user = models.ForeignKey(
        MasterUser,
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )

    json_data = EncryptedTextField()

    @property
    def data(self):
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

    class Meta(NamedModel.Meta):
        unique_together = [["master_user", "user_code"]]
        ordering = ["user_code"]
