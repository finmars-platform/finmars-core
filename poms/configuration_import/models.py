from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy

import json
from django.core.serializers.json import DjangoJSONEncoder

from poms.users.models import MasterUser


class ConfigurationEntityArchetype(models.Model):
    name = models.CharField(max_length=255, blank=True, default="", db_index=True, verbose_name=ugettext_lazy('name'))
    json_data = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('json data'))
    master_user = models.ForeignKey(MasterUser, verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, verbose_name=ugettext_lazy('content type'), on_delete=models.CASCADE)

    class Meta:
        unique_together = (
            ('name', 'master_user', 'content_type')
        )

    @property
    def data(self):
        if self.json_data:
            try:
                return json.loads(self.json_data)
            except (ValueError, TypeError):
                return None
        else:
            return None

    @data.setter
    def data(self, val):
        if val:
            self.json_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.json_data = None
