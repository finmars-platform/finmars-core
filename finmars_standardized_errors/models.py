import json

from django.db import models
from django.utils.translation import gettext_lazy

class ErrorRecord(models.Model):

    url = models.CharField(max_length=255, null=True, blank=True,
                           verbose_name=gettext_lazy('url'))

    username = models.CharField(max_length=255, null=True, blank=True,
                           verbose_name=gettext_lazy('username'))

    message = models.TextField(blank=True, default='', verbose_name=gettext_lazy('message'))
    status_code = models.IntegerField(verbose_name=gettext_lazy('integer'))

    notes = models.TextField(blank=True, default='', verbose_name=gettext_lazy('notes'))

    details_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('details data'))

    created = models.DateTimeField(auto_now_add=True)

    class Meta:

        ordering = ['-created']


    @property
    def details(self):
        if self.details_data:
            try:
                return json.loads(self.details_data)
            except (ValueError, TypeError):
                return None
        else:
            return None

    @details.setter
    def details(self, val):
        if val:
            self.details_data = json.dumps(val, default=str, sort_keys=True)
        else:
            self.details_data = None