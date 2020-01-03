from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy

from poms.file_reports.storage import file_reports_storage
from poms.users.models import MasterUser

import io

from logging import getLogger


_l = getLogger('poms.file_reports')



class FileReport(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255, blank=True, default='', )
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    file_url = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('File URL'))
    file_name = models.CharField(max_length=255, blank=True, default='')
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.name

    def upload_file(self, file_name, text, master_user):

        file_url = self._get_path(master_user, file_name)

        file = io.StringIO(text)

        try:
            file_reports_storage.save(file_url, file)
        except Exception as e:
            _l.debug('Exception %s' % e)

        self.file_url = file_url

        return file_url

    def get_file(self):

        result = None

        print('get_file self.file_url %s' % self.file_url)

        try:
            with file_reports_storage.open(self.file_url, 'rb') as f:

                result = f.read()

        except Exception as e:
            print("Cant open file Exception: %s" % e)

        return result

    def _get_path(self, owner, file_name):
        return '%s/%s' % (owner.pk, file_name)
