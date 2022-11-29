import json
import logging
from datetime import datetime

from croniter import croniter
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy

from poms.common.models import NamedModel, DataTimeStampedModel
from poms.system_messages.handlers import send_system_message
from poms.users.models import MasterUser

_l = logging.getLogger('poms.schedules')


def validate_crontab(value):
    try:
        # to_crontab(value)
        croniter(value, timezone.now())
    except (ValueError, KeyError, TypeError):
        raise ValidationError(gettext_lazy('A valid cron string is required.'))


class Schedule(NamedModel):
    ERROR_HANDLER_CHOICES = [
        ['break', 'Break'],
        ['continue', 'Continue'],
    ]

    master_user = models.ForeignKey(MasterUser, verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    cron_expr = models.CharField(max_length=255, blank=True, default='', validators=[validate_crontab],
                                 verbose_name=gettext_lazy('cron expr'),
                                 help_text=gettext_lazy(
                                     'Format is "* * * * *" (minute / hour / day_month / month / day_week)'))

    last_run_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True,
                                       verbose_name=gettext_lazy('last run at'))

    next_run_at = models.DateTimeField(default=timezone.now, editable=True, db_index=True,
                                       verbose_name=gettext_lazy('next run at'))

    error_handler = models.CharField(max_length=255, choices=ERROR_HANDLER_CHOICES, default='break')

    json_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('json data'))

    @property
    def data(self):
        if self.json_data:
            try:
                return json.loads(self.json_data)
            except (ValueError, TypeError):
                return None
        else:
            return None

    @data.setter
    def data(self, val):
        if val:
            self.json_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.json_data = None

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.is_enabled:
            self.schedule(save=False)
        super(Schedule, self).save(force_insert=force_insert, force_update=force_update, using=using,
                                   update_fields=update_fields)

        from poms.schedules.utils import sync_schedules
        sync_schedules()

    def schedule(self, save=False):
        start_time = timezone.localtime(timezone.now())
        cron = croniter(self.cron_expr, start_time)

        _l.info('schedule cron_expr %s ' % self.cron_expr)
        _l.info('schedule start_time %s ' % start_time)

        next_run_at = cron.get_next(datetime)

        _l.info('schedule next_run_at %s ' % next_run_at)

        # next_run_at = cron.get_next(datetime)
        #
        # _l.info('schedule next_run_at after %s ' % next_run_at)

        self.next_run_at = next_run_at

        if save:
            self.save(update_fields=['last_run_at', 'next_run_at', ])

    class Meta(NamedModel.Meta):
        unique_together = (
            ('user_code', 'master_user')
        )

    def __str__(self):
        return self.user_code


class ScheduleProcedure(models.Model):
    schedule = models.ForeignKey(Schedule, verbose_name=gettext_lazy('schedule'), related_name="procedures",
                                 on_delete=models.CASCADE)
    type = models.CharField(max_length=25, null=True, blank=True, verbose_name=gettext_lazy('type'))
    user_code = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('user code'))
    order = models.IntegerField(default=0, verbose_name=gettext_lazy('order'))

    class Meta:
        unique_together = [
            ['schedule', 'order'],
        ]


class ScheduleInstance(DataTimeStampedModel):
    STATUS_INIT = 'I'
    STATUS_PENDING = 'P'
    STATUS_DONE = 'D'
    STATUS_ERROR = 'E'

    STATUS_CHOICES = (
        (STATUS_INIT, gettext_lazy('Init')),
        (STATUS_PENDING, gettext_lazy('Pending')),
        (STATUS_DONE, gettext_lazy('Done')),
        (STATUS_ERROR, gettext_lazy('Error')),
    )

    master_user = models.ForeignKey(MasterUser, verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    schedule = models.ForeignKey(Schedule, verbose_name=gettext_lazy('schedule'), related_name="instances",
                                 on_delete=models.CASCADE)
    current_processing_procedure_number = models.IntegerField(default=0, verbose_name=gettext_lazy(
        'current processing procedure number'))

    status = models.CharField(max_length=1, default=STATUS_INIT, choices=STATUS_CHOICES,
                              verbose_name=gettext_lazy('status'))

    def run_next_procedure(self):

        from poms.schedules.tasks import process_procedure_async

        total_procedures = len(self.schedule.procedures.all())

        send_system_message(master_user=self.master_user,
                            performed_by='system',
                            section='schedules',
                            description="Schedule %s. Step  %s/%s finished" % (
                            self.schedule.name, self.current_processing_procedure_number, total_procedures))

        self.current_processing_procedure_number = self.current_processing_procedure_number + 1

        _l.debug('run_next_procedure schedule %s procedure number %s' % (
        self.schedule, self.current_processing_procedure_number))

        for procedure in self.schedule.procedures.all():

            try:

                if self.status != ScheduleInstance.STATUS_ERROR or self.schedule.error_handler == 'continue':

                    if procedure.order == self.current_processing_procedure_number:
                        self.save()

                        send_system_message(master_user=self.master_user,
                                            performed_by='system',
                                            section='schedules',
                                            description="Schedule %s. Start processing step %s/%s " % (
                                            self.schedule.name, self.current_processing_procedure_number,
                                            total_procedures))

                        process_procedure_async.apply_async(
                            kwargs={'procedure_id': procedure.id, 'master_user_id': self.master_user.id,
                                    'schedule_instance_id': self.id})

            except Exception as e:

                self.status = ScheduleInstance.STATUS_ERROR
                self.save()

                send_system_message(master_user=self.master_user,
                                    performed_by='system',
                                    section='schedules',
                                    description="Schedule %s. Error occurred at step %s/%s" % (
                                    self.schedule.name, self.current_processing_procedure_number, total_procedures))
