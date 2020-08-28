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


def validate_crontab(value):
    try:
        # to_crontab(value)
        croniter(value, timezone.now())
    except (ValueError, KeyError, TypeError):
        raise ValidationError(ugettext_lazy('A valid cron string is required.'))


class BaseSchedule(NamedModel):
    master_user = models.ForeignKey(MasterUser,  verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    cron_expr = models.CharField(max_length=255, blank=True, default='', validators=[validate_crontab],
                                 verbose_name=ugettext_lazy('cron expr'),
                                 help_text=ugettext_lazy(
                                     'Format is "* * * * *" (minute / hour / day_month / month / day_week)'))

    last_run_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True,
                                       verbose_name=ugettext_lazy('last run at'))

    next_run_at = models.DateTimeField(default=timezone.now, editable=True, db_index=True,
                                       verbose_name=ugettext_lazy('next run at'))

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.is_enabled:
            self.schedule(save=False)
        super(BaseSchedule, self).save(force_insert=force_insert, force_update=force_update, using=using,
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
        abstract = True
        unique_together = (
            ('user_code',  'master_user')
        )

    def __str__(self):
        return self.user_code


class PricingSchedule(BaseSchedule, DataTimeStampedModel):

    pricing_procedures = models.ManyToManyField('pricing.PricingProcedure', blank=True, verbose_name=ugettext_lazy('pricing procedures'))


    class Meta(BaseSchedule.Meta):
        unique_together = (
            ('user_code',  'master_user')
        )


class Schedule(NamedModel):
    master_user = models.ForeignKey(MasterUser,  verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    cron_expr = models.CharField(max_length=255, blank=True, default='', validators=[validate_crontab],
                                 verbose_name=ugettext_lazy('cron expr'),
                                 help_text=ugettext_lazy(
                                     'Format is "* * * * *" (minute / hour / day_month / month / day_week)'))

    last_run_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True,
                                       verbose_name=ugettext_lazy('last run at'))

    next_run_at = models.DateTimeField(default=timezone.now, editable=True, db_index=True,
                                       verbose_name=ugettext_lazy('next run at'))

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
