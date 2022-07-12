from django.db import models
from django.utils.translation import gettext_lazy

import json
from django.core.serializers.json import DjangoJSONEncoder

from poms.common.models import TimeStampedModel


class CeleryTask(TimeStampedModel):

    STATUS_INIT = 'I'
    STATUS_PENDING = 'P'
    STATUS_DONE = 'D'
    STATUS_ERROR = 'E'
    STATUS_TIMEOUT = 'T'

    STATUS_CHOICES = (
        (STATUS_INIT, 'INIT'),
        (STATUS_PENDING, 'PENDING'),
        (STATUS_DONE, 'DONE'),
        (STATUS_ERROR, 'ERROR'),
        (STATUS_TIMEOUT, 'TIMEOUT'),
    )

    master_user = models.ForeignKey('users.MasterUser', verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    member = models.ForeignKey('users.Member', verbose_name=gettext_lazy('member'), null=True, blank=True, on_delete=models.SET_NULL)

    is_system_task = models.BooleanField(default=False, verbose_name=gettext_lazy("is system task"))

    celery_task_id = models.CharField(null=True, max_length=255)
    status = models.CharField(null=True, max_length=1, default=STATUS_INIT, choices=STATUS_CHOICES,
                              verbose_name='status')
    type = models.CharField(max_length=50, blank=True, null=True)

    parent = models.ForeignKey('self', null=True, blank=True, related_name='children',
                               verbose_name=gettext_lazy('parent'), on_delete=models.SET_NULL)

    options = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('options'))
    result = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('result'))

    file_report = models.ForeignKey('file_reports.FileReport',null=True, blank=True, verbose_name=gettext_lazy('file report'), on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return 'Master_user {0.master_user.id} <Task: {0.pk} ({0.status})>'.format(self)

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