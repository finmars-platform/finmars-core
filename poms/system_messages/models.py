from django.db import models
from django.utils.translation import gettext_lazy

from poms.file_reports.models import FileReport


class SystemMessage(models.Model):

    LEVEL_INFO = 'info'
    LEVEL_WARNING = 'warn'
    LEVEL_ERROR = 'error'

    LEVELS_CHOICES = (
        (LEVEL_INFO, gettext_lazy('Info')),
        (LEVEL_WARNING, gettext_lazy('Warning')),
        (LEVEL_ERROR, gettext_lazy('Error')),
    )

    STATUS_NEW = 1
    STATUS_SOLVED = 2
    STATUS_VIEWED = 3
    STATUS_MARKED = 4
    STATUS_ABANDONED = 5

    STATUS_CHOICES = (
        (STATUS_NEW, gettext_lazy('New')),
        (STATUS_SOLVED, gettext_lazy('Solved')),
        (STATUS_VIEWED, gettext_lazy('Viewed')),
        (STATUS_MARKED, gettext_lazy('Marked')),
        (STATUS_ABANDONED, gettext_lazy('Abandoned')),
    )

    master_user = models.ForeignKey('users.MasterUser', verbose_name=gettext_lazy('master user') , on_delete=models.CASCADE)

    level = models.CharField(max_length=255, default=LEVEL_INFO,  choices=LEVELS_CHOICES,
                                             verbose_name=gettext_lazy('level'))
    status = models.PositiveSmallIntegerField(default=STATUS_NEW, choices=STATUS_CHOICES,
                                              verbose_name=gettext_lazy('status'))
    text = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('text'))

    created = models.DateTimeField(auto_now_add=True, editable=False, db_index=True,
                                   verbose_name=gettext_lazy('created'))

    source = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('source'))

    # TODO channels
    # TODO actions


class SystemMessageAttachment(models.Model):

    system_message = models.ForeignKey(SystemMessage, verbose_name=gettext_lazy('system message') , on_delete=models.CASCADE, related_name="attachments")

    file_url = models.TextField(null=True, blank=True, default='', verbose_name=gettext_lazy('File URL'))
    file_name = models.CharField(null=True, max_length=255, blank=True, default='')
    notes = models.TextField(null=True, blank=True, default='', verbose_name=gettext_lazy('notes'))

    file_report = models.ForeignKey(FileReport, null=True, verbose_name=gettext_lazy('file report') , on_delete=models.SET_NULL)
