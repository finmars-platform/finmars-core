from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy

from poms.file_reports.storage import file_reports_storage
from poms.users.models import MasterUser

import io


from storages.backends.sftpstorage import SFTPStorage
SFS = SFTPStorage()


from logging import getLogger

_l = getLogger('poms.file_reports')

from tempfile import NamedTemporaryFile


class FileReport(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255, blank=True, default='', )
    master_user = models.ForeignKey('users.MasterUser', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    file_url = models.TextField(blank=True, default='', verbose_name=gettext_lazy('File URL'))
    file_name = models.CharField(max_length=255, blank=True, default='')
    notes = models.TextField(blank=True, default='', verbose_name=gettext_lazy('notes'))
    content_type = models.CharField(max_length=255, blank=True, default='', )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.name

    def upload_file(self, file_name, text, master_user):

        file_url = self._get_path(master_user, file_name)

        try:

            encoded_text = text.encode('utf-8')

            with NamedTemporaryFile() as tmpfile:

                _l.debug('FileReport tmpfile.name %s' % tmpfile.name)

                tmpfile.seek(0)

                tmpfile.write(encoded_text)

                tmpfile.flush()

                _l.debug(tmpfile)

                SFS.save(file_url, tmpfile)

        except Exception as e:
            _l.debug('Exception %s' % e)

        self.file_url = file_url

        return file_url

    def get_file(self):

        result = None

        print('get_file self.file_url %s' % self.file_url)

        try:
            with SFS.open(self.file_url, 'rb') as f:

                result = f.read()

        except Exception as e:
            print("Cant open file Exception: %s" % e)

        return result

    def _get_path(self, master_user, file_name):
        return '%s/file_reports/%s' % (master_user.token, file_name)
