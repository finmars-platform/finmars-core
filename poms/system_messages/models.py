from django.db import models
from django.utils.translation import gettext_lazy

from poms.file_reports.models import FileReport
from poms.users.models import Member


class SystemMessage(models.Model):

    SECTION_GENERAL = 0
    SECTION_EVENTS = 1
    SECTION_TRANSACTIONS = 2
    SECTION_INSTRUMENTS = 3
    SECTION_DATA = 4
    SECTION_PRICES = 5
    SECTION_REPORT = 6
    SECTION_IMPORT = 7
    SECTION_ACTIVITY_LOG = 8
    SECTION_SCHEDULES = 9

    SECTION_CHOICES = (
        (SECTION_EVENTS, gettext_lazy('Events')),
        (SECTION_TRANSACTIONS, gettext_lazy('Transactions')),
        (SECTION_INSTRUMENTS, gettext_lazy('Instruments')),
        (SECTION_DATA, gettext_lazy('Data')),
        (SECTION_PRICES, gettext_lazy('Prices')),
        (SECTION_REPORT, gettext_lazy('Report')),
        (SECTION_IMPORT, gettext_lazy('Import')),
        (SECTION_ACTIVITY_LOG, gettext_lazy('Activity Log')),
        (SECTION_SCHEDULES, gettext_lazy('Schedules')),
    )

    TYPE_INFORMATION = 1
    TYPE_WARNING = 2
    TYPE_ERROR = 3
    TYPE_SUCCESS = 4

    TYPE_CHOICES = (
        (TYPE_INFORMATION, gettext_lazy('Information')),
        (TYPE_WARNING, gettext_lazy('Warning')),
        (TYPE_ERROR, gettext_lazy('Error')),
        (TYPE_SUCCESS, gettext_lazy('Success'))
    )

    master_user = models.ForeignKey('users.MasterUser', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    section = models.PositiveSmallIntegerField(default=SECTION_GENERAL, choices=SECTION_CHOICES,
                                            verbose_name=gettext_lazy('section'))

    type = models.PositiveSmallIntegerField(default=TYPE_INFORMATION, choices=TYPE_CHOICES,
                                            verbose_name=gettext_lazy('status'))

    title = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('title'))

    description = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('text'))

    created = models.DateTimeField(auto_now_add=True, editable=False, db_index=True,
                                   verbose_name=gettext_lazy('created'))

    performed_by = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('performed by'))
    target = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('target'))

    linked_event = models.ForeignKey('instruments.GeneratedEvent', null=True, blank=True,
                                     verbose_name=gettext_lazy('linked event'), on_delete=models.SET_NULL)

    def __str__(self):
        return self.title

class SystemMessageAttachment(models.Model):
    system_message = models.ForeignKey(SystemMessage, verbose_name=gettext_lazy('system message'),
                                       on_delete=models.CASCADE, related_name="attachments")

    file_url = models.TextField(null=True, blank=True, default='', verbose_name=gettext_lazy('File URL'))
    file_name = models.CharField(null=True, max_length=255, blank=True, default='')
    notes = models.TextField(null=True, blank=True, default='', verbose_name=gettext_lazy('notes'))

    file_report = models.ForeignKey(FileReport, null=True, verbose_name=gettext_lazy('file report'),
                                    on_delete=models.SET_NULL)


class SystemMessageMember(models.Model):

    # read, new, solved

    STATUS_NEW = 1
    STATUS_READ = 2
    STATUS_SOLVED = 3

    STATUS_CHOICES = (
        (STATUS_NEW, gettext_lazy('New')),
        (STATUS_READ, gettext_lazy('Read')),
        (STATUS_SOLVED, gettext_lazy('Solved'))
    )

    system_message = models.ForeignKey(SystemMessage, verbose_name=gettext_lazy('system message'),
                                       on_delete=models.CASCADE, related_name="members")

    member = models.ForeignKey(Member, related_name='system_messages',
                               verbose_name=gettext_lazy('member'), on_delete=models.CASCADE)

    status = models.PositiveSmallIntegerField(default=STATUS_NEW, choices=STATUS_CHOICES,
                                              verbose_name=gettext_lazy('status'))

    is_pinned = models.BooleanField(default=False, verbose_name=gettext_lazy('is pinned'))