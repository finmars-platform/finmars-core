from __future__ import unicode_literals, print_function

from django.conf import settings
from django.core.files.storage import get_storage_class
from django.utils.functional import LazyObject


class FileReportsStorage(LazyObject):
    def _setup(self):
        clazz = get_storage_class(settings.FILE_REPORTS_STORAGE['BACKEND'])
        kwargs = settings.FILE_REPORTS_STORAGE['KWARGS'] or {}
        self._wrapped = clazz(**kwargs)

    def deconstruct(self):
        return 'poms.file_reports.storage.FileReportsStorage', [], {}


file_reports_storage = FileReportsStorage()