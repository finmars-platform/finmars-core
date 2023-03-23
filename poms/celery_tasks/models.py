import json
import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import TimeStampedModel
from poms.file_reports.models import FileReport
from django.utils.timezone import now
import datetime
from poms_app import settings

_l = logging.getLogger('poms.celery_tasks')


class CeleryTask(TimeStampedModel):
    '''

    Maybe should be rename just to Task (like in Workflow)
    Kinda legacy functionality (everything to background processes should be moved to Workflow/Olap microservices)
    But still its in use
    Most important tasks are:
        Transaction Import (transactions itself, sometimes instruments)
        Simple Import (Portfolios, Accounts, Instruments, Prices, FXrates)
        Configuration Import (Account Type, Instrument Types, Transaction Types, UI layouts)
        Portfolio Records and Portfolio Prices

    Also we have poms.procedures, and poms.pricings and somehow it different entities but they do the same thing as CeleryTask
    Maybe in future procedures/pricing will be refactored and one day they will be just CeleryTask
    And in far future even that will be moved to Workflow/Olap

    '''
    STATUS_INIT = 'I'
    STATUS_PENDING = 'P'
    STATUS_DONE = 'D'
    STATUS_ERROR = 'E'
    STATUS_TIMEOUT = 'T'
    STATUS_CANCELED = 'C'
    STATUS_TRANSACTIONS_ABORTED = 'X'
    STATUS_REQUEST_SENT = 'S'
    STATUS_WAIT_RESPONSE = 'W'


    STATUS_CHOICES = (
        (STATUS_INIT, 'INIT'),
        (STATUS_PENDING, 'PENDING'),
        (STATUS_DONE, 'DONE'),
        (STATUS_ERROR, 'ERROR'),
        (STATUS_TIMEOUT, 'TIMEOUT'),
        (STATUS_CANCELED, 'CANCELED'),
        (STATUS_TRANSACTIONS_ABORTED, 'TRANSACTIONS_ABORTED'),
        (STATUS_REQUEST_SENT, 'REQUEST_SENT'),
        (STATUS_WAIT_RESPONSE, 'WAIT_RESPONSE'),
    )

    master_user = models.ForeignKey('users.MasterUser', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    member = models.ForeignKey('users.Member', verbose_name=gettext_lazy('member'), null=True, blank=True,
                               on_delete=models.SET_NULL)

    is_system_task = models.BooleanField(default=False, verbose_name=gettext_lazy("is system task"))

    celery_task_id = models.CharField(null=True, max_length=255)
    function_name = models.CharField(null=True, max_length=255)
    status = models.CharField(null=True, max_length=1, default=STATUS_INIT, choices=STATUS_CHOICES,
                              verbose_name='status')
    type = models.CharField(max_length=255, blank=True, null=True)

    parent = models.ForeignKey('self', null=True, blank=True, related_name='children',
                               verbose_name=gettext_lazy('parent'), on_delete=models.SET_NULL)

    options = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('options'))
    result = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('result'))
    progress = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('progress'))

    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'))
    error_message = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('error message'))

    file_report = models.ForeignKey('file_reports.FileReport', null=True, blank=True,
                                    verbose_name=gettext_lazy('file report'), on_delete=models.SET_NULL)

    verbose_name = models.CharField(null=True, max_length=255)
    verbose_result = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('verbose result'))

    finished_at = models.DateTimeField(null=True, db_index=True,
                                       verbose_name=gettext_lazy('finished at'))

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return '{0.verbose_name} [{0.pk}] ({0.status})>'.format(self)

    @property
    def options_object(self):
        if self.options is None:
            return None
        return json.loads(self.options)

    @options_object.setter
    def options_object(self, value):
        if value is None:
            self.options = None
        else:
            self.options = json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, indent=1)

    @property
    def result_object(self):
        if self.result is None:
            return None
        return json.loads(self.result)

    @result_object.setter
    def result_object(self, value):
        if value is None:
            self.result = None
        else:
            self.result = json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, indent=1)

    @property
    def progress_object(self):
        if self.progress is None:
            return None
        return json.loads(self.progress)

    @progress_object.setter
    def progress_object(self, value):
        if value is None:
            self.progress = None
        else:
            self.progress = json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, indent=1)

    def add_attachment(self, file_report_id):

        CeleryTaskAttachment.objects.create(celery_task=self,
                                            file_report_id=file_report_id)

    def mark_task_as_finished(self):

        self.finished_at = now()

    def update_progress(self, progress):

        # {
        #   current: 20,
        #   total: 100,
        #   percent: 20
        #   description
        # }

        _l.info('update_progress %s' % progress)

        self.progress_object = progress

        self.save()


class CeleryTaskAttachment(models.Model):
    celery_task = models.ForeignKey(CeleryTask, verbose_name=gettext_lazy('celery task'),
                                    on_delete=models.CASCADE, related_name="attachments")

    file_url = models.TextField(null=True, blank=True, default='', verbose_name=gettext_lazy('File URL'))
    file_name = models.CharField(null=True, max_length=255, blank=True, default='')
    notes = models.TextField(null=True, blank=True, default='', verbose_name=gettext_lazy('notes'))

    file_report = models.ForeignKey(FileReport, null=True, verbose_name=gettext_lazy('file report'),
                                    on_delete=models.SET_NULL)
