from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy

from poms.common.models import NamedModel, DataTimeStampedModel
from poms.integrations.models import DataProvider
from poms.users.models import MasterUser

from croniter import croniter
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, datetime, timedelta
from django.conf import settings





import logging

_l = logging.getLogger('poms.schedules')


def validate_crontab(value):
    try:
        # to_crontab(value)
        croniter(value, timezone.now())
    except (ValueError, KeyError, TypeError):
        raise ValidationError(ugettext_lazy('A valid cron string is required.'))


class Schedule(NamedModel):

    ERROR_HANDLER_CHOICES = [
        ['break', 'Break'],
        ['continue', 'Continue'],
    ]

    master_user = models.ForeignKey(MasterUser,  verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    cron_expr = models.CharField(max_length=255, blank=True, default='', validators=[validate_crontab],
                                 verbose_name=ugettext_lazy('cron expr'),
                                 help_text=ugettext_lazy(
                                     'Format is "* * * * *" (minute / hour / day_month / month / day_week)'))

    last_run_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True,
                                       verbose_name=ugettext_lazy('last run at'))

    next_run_at = models.DateTimeField(default=timezone.now, editable=True, db_index=True,
                                       verbose_name=ugettext_lazy('next run at'))

    error_handler = models.CharField(max_length=255, choices=ERROR_HANDLER_CHOICES, default='break')

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.is_enabled:
            self.schedule(save=False)
        super(Schedule, self).save(force_insert=force_insert, force_update=force_update, using=using,
                                       update_fields=update_fields)

    def schedule(self, save=False):
        start_time = timezone.localtime(timezone.now())
        cron = croniter(self.cron_expr, start_time)

        next_run_at = cron.get_next(datetime)

        min_timedelta = settings.PRICING_AUTO_DOWNLOAD_MIN_TIMEDELTA
        if min_timedelta is not None:
            if not isinstance(min_timedelta, timedelta):
                min_timedelta = timedelta(minutes=min_timedelta)
            for i in range(100):
                if (next_run_at - start_time) >= min_timedelta:
                    break
                next_run_at = cron.get_next(datetime)

        self.next_run_at = next_run_at

        if save:
            self.save(update_fields=['last_run_at', 'next_run_at', ])

    class Meta(NamedModel.Meta):
        unique_together = (
            ('user_code',  'master_user')
        )

    def __str__(self):
        return self.user_code


class ScheduleProcedure(models.Model):

    schedule = models.ForeignKey(Schedule,  verbose_name=ugettext_lazy('schedule'), related_name="procedures", on_delete=models.CASCADE)
    type = models.CharField(max_length=25, null=True, blank=True, verbose_name=ugettext_lazy('type'))
    user_code = models.CharField(max_length=25, null=True, blank=True, verbose_name=ugettext_lazy('user code'))
    order = models.IntegerField(default=0, verbose_name=ugettext_lazy('order'))

    class Meta:
        unique_together = [
            ['user_code', 'order', 'type'],
        ]


class ScheduleInstance(DataTimeStampedModel):

    STATUS_INIT = 'I'
    STATUS_PENDING = 'P'
    STATUS_DONE = 'D'
    STATUS_ERROR = 'E'

    STATUS_CHOICES = (
        (STATUS_INIT, ugettext_lazy('Init')),
        (STATUS_PENDING, ugettext_lazy('Pending')),
        (STATUS_DONE, ugettext_lazy('Done')),
        (STATUS_ERROR, ugettext_lazy('Error')),
    )

    master_user = models.ForeignKey(MasterUser,  verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    schedule = models.ForeignKey(Schedule,  verbose_name=ugettext_lazy('schedule'), related_name="instances", on_delete=models.CASCADE)
    current_processing_procedure_number = models.IntegerField(default=0, verbose_name=ugettext_lazy('current processing procedure number'))

    status = models.CharField(max_length=1, default=STATUS_INIT, choices=STATUS_CHOICES,
                              verbose_name=ugettext_lazy('status'))

    def run_next_procedure(self):

        from poms.schedules.tasks import process_procedure_async

        self.current_processing_procedure_number = self.current_processing_procedure_number + 1

        _l.info('run_next_procedure schedule %s procedure number %s' % (self.schedule, self.current_processing_procedure_number))

        for procedure in self.schedule.procedures.all():

            try:

                if self.status != ScheduleInstance.STATUS_ERROR or self.schedule.error_handler == 'continue':

                    if procedure.order == self.current_processing_procedure_number:

                        self.save()

                        process_procedure_async.apply_async(kwargs={'procedure':procedure, 'master_user':self.master_user, 'schedule_instance': self})

            except Exception as e:

                self.status = ScheduleInstance.STATUS_ERROR
                self.save()
