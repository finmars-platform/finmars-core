from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy

from poms.users.models import MasterUser


class FileReport(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255, blank=True, default='',)
    content_type = models.ForeignKey(ContentType, verbose_name=ugettext_lazy('content type'), on_delete=models.CASCADE)
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user') , on_delete=models.CASCADE)

    file_url = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('File URL'))
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    def __str__(self):
        return self.name
