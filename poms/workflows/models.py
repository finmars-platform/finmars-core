from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import DataTimeStampedModel
from poms.users.models import MasterUser, Member


class Workflow(DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser,
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    member = models.ForeignKey(Member, null=True, blank=True, verbose_name=gettext_lazy('member'),
                               on_delete=models.SET_NULL)

    name = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('name'))

    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'))

    current_step = models.IntegerField(default=0, verbose_name=gettext_lazy('current step'))


class WorkflowStep(DataTimeStampedModel):
    STATUS_INIT = 'I'
    STATUS_PENDING = 'P'
    STATUS_DONE = 'D'
    STATUS_ERROR = 'E'
    STATUS_TIMEOUT = 'T'
    STATUS_CANCELED = 'C'

    STATUS_CHOICES = (
        (STATUS_INIT, 'INIT'),
        (STATUS_PENDING, 'PENDING'),
        (STATUS_DONE, 'DONE'),
        (STATUS_ERROR, 'ERROR'),
        (STATUS_TIMEOUT, 'TIMEOUT'),
        (STATUS_CANCELED, 'CANCELED')
    )

    workflow = models.ForeignKey(Workflow, related_name="steps",
                                 verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    name = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('name'))

    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'))

    status = models.CharField(null=True, max_length=1, default=STATUS_INIT, choices=STATUS_CHOICES,
                              verbose_name='status')

    log = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('log'))
    result = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('result'))

    error_message = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('error message'))

    code = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('code'))

    order = models.IntegerField(default=0, verbose_name=gettext_lazy('order'))
