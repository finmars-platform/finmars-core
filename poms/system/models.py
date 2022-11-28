import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy


class EcosystemConfiguration(models.Model):
    name = models.CharField(max_length=255, blank=True, default="", db_index=True, verbose_name=gettext_lazy('name'))

    description = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('description'))

    json_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('json data'))

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

    class Meta:
        unique_together = [
            ['name'],
        ]
        ordering = ['name']

    def __str__(self):
        return self.name
