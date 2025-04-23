import json
import logging
from datetime import datetime
from typing import Optional

from croniter import croniter

from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy

from poms.common.models import NamedModel, TimeStampedModel
from poms.configuration.models import ConfigurationModel
from poms.system_messages.handlers import send_system_message
from poms.users.models import MasterUser

_l = logging.getLogger("poms.schedules")


def validate_crontab(value: str) -> None:
    try:
        croniter(value, timezone.now())

    except Exception as e:
        raise ValidationError(
            gettext_lazy(f"Invalid cron string {value} resulted in {repr(e)}")
        ) from e


class Schedule(NamedModel, ConfigurationModel):
    """
    Simply schedules, User Defined

    User chooses time (server UTC) and setting up Actions and their order
    When its time, actions just executes one after another (Thanks to Celery Beat)

    Possibly be deprecated soon. Everything background-task related will
    move to Workflow/Olap

    ==== Important ====
    Part of Finmars Configuration
    Part of Finmars Marketplace

    """

    ERROR_HANDLER_CHOICES = [
        ["break", "Break"],
        ["continue", "Continue"],
    ]

    master_user = models.ForeignKey(
        MasterUser,
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    cron_expr = models.CharField(
        max_length=255,
        blank=True,
        default="",
        validators=[validate_crontab],
        verbose_name=gettext_lazy("cron expr"),
        help_text=gettext_lazy(
            'Format is "* * * * *" (minute / hour / day_month / month / day_week)'
        ),
    )
    last_run_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        db_index=True,
        verbose_name=gettext_lazy("last run at"),
    )
    next_run_at = models.DateTimeField(
        default=timezone.now,
        editable=True,
        db_index=True,
        verbose_name=gettext_lazy("next run at"),
    )
    error_handler = models.CharField(
        max_length=255,
        choices=ERROR_HANDLER_CHOICES,
        default="break",
    )
    json_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("json data"),
    )

    @property
    def data(self):
        if not self.json_data:
            return None

        try:
            return json.loads(self.json_data)
        except (ValueError, TypeError):
            return None

    @data.setter
    def data(self, val):
        if val:
            self.json_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.json_data = None

    class Meta(NamedModel.Meta):
        unique_together = ("user_code", "master_user")

    def __str__(self):
        return self.user_code

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        from poms.schedules.utils import sync_schedules

        if self.is_enabled:
            self.schedule()

        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

        sync_schedules()

    def schedule(self, save=False) -> Optional[datetime]:
        """Schedule the next run of the schedule based on the cron expression."""
        start_time = timezone.now()
        try:
            next_run_time = croniter(self.cron_expr, start_time).get_next()
            self.next_run_at = datetime.fromtimestamp(next_run_time, tz=timezone.utc)
            if save:
                self.save(update_fields=["next_run_at"])

            _l.info(f"schedule next_run_time {self.next_run_at}")

            return self.next_run_at

        except Exception as e:
            _l.error(f"Error scheduling next run for {self.name}: {e}")
            return None


class ScheduleProcedure(models.Model):
    """
    Schedule Action itself, for now we support 3 types
    1 - Data Procedure (which executes transaction import/simple import ->
    generates Instruments and Transactions)
    2 - Pricing Procedure (runs pricing and fetching PriceHistory and CurrencyHistory)
    3 - Expression Procedure (user defined scripts, executes rolling of prices,
    or other finmars tasks)
    """

    schedule = models.ForeignKey(
        Schedule,
        verbose_name=gettext_lazy("schedule"),
        related_name="procedures",
        on_delete=models.CASCADE,
    )
    type = models.CharField(
        max_length=25,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("type"),
    )
    user_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("user code"),
    )
    order = models.IntegerField(
        default=0,
        verbose_name=gettext_lazy("order"),
    )

    class Meta:
        unique_together = [
            ["schedule", "order"],
        ]


class ScheduleInstance(TimeStampedModel):
    """
    Actual Instance of schedule
    Needs just to be control of Schedule Status
    It's really important to keep track of Pricing Procedures/Data Procedures daily
    External data feeds keeps our Reports in latest state. And we should be sure
    that schedules processed correctly
    """

    STATUS_INIT = "I"
    STATUS_PENDING = "P"
    STATUS_DONE = "D"
    STATUS_ERROR = "E"

    STATUS_CHOICES = (
        (STATUS_INIT, gettext_lazy("Init")),
        (STATUS_PENDING, gettext_lazy("Pending")),
        (STATUS_DONE, gettext_lazy("Done")),
        (STATUS_ERROR, gettext_lazy("Error")),
    )

    master_user = models.ForeignKey(
        MasterUser,
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    schedule = models.ForeignKey(
        Schedule,
        verbose_name=gettext_lazy("schedule"),
        related_name="instances",
        on_delete=models.CASCADE,
    )
    current_processing_procedure_number = models.IntegerField(
        default=0,
        verbose_name=gettext_lazy("current processing procedure number"),
    )
    status = models.CharField(
        max_length=1,
        default=STATUS_INIT,
        choices=STATUS_CHOICES,
        verbose_name=gettext_lazy("status"),
    )

    def run_next_procedure(self):
        from poms.schedules.tasks import process_procedure_async

        total_procedures = len(self.schedule.procedures.all())

        send_system_message(
            master_user=self.master_user,
            performed_by="system",
            section="schedules",
            description=(
                f"Schedule {self.schedule.name}. "
                f"Step {self.current_processing_procedure_number}/{total_procedures} "
                f"finished"
            ),
        )

        self.current_processing_procedure_number += 1

        _l.debug(
            f"run_next_procedure schedule {self.schedule} "
            f"procedure number {self.current_processing_procedure_number}"
        )

        for procedure in self.schedule.procedures.all():
            try:
                if (
                    self.status != ScheduleInstance.STATUS_ERROR
                    or self.schedule.error_handler == "continue"
                ) and procedure.order == self.current_processing_procedure_number:
                    self.save()

                    send_system_message(
                        master_user=self.master_user,
                        performed_by="system",
                        section="schedules",
                        description=(
                            f"Schedule {self.schedule.name}. Start processing step"
                            f" {self.current_processing_procedure_number}"
                            f"/{total_procedures} "
                        ),
                    )

                    process_procedure_async.apply_async(
                        kwargs={
                            "procedure_id": procedure.id,
                            "master_user_id": self.master_user.id,
                            "schedule_instance_id": self.id,
                            "context": {
                                "space_code": self.master_user.space_code,
                                "realm_code": self.master_user.realm_code,
                            },
                        }
                    )

            except Exception as e:
                self.status = ScheduleInstance.STATUS_ERROR
                self.save()

                send_system_message(
                    master_user=self.master_user,
                    performed_by="system",
                    section="schedules",
                    description=(
                        f"Schedule {self.schedule.name}. Error {repr(e)} occurred at step "
                        f"{self.current_processing_procedure_number}/{total_procedures}"
                    ),
                )
