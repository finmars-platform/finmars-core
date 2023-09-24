from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import TimeStampedModel
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
    SECTION_OTHER = 10

    SECTION_CHOICES = (
        (SECTION_GENERAL, gettext_lazy("General")),
        (SECTION_EVENTS, gettext_lazy("Events")),
        (SECTION_TRANSACTIONS, gettext_lazy("Transactions")),
        (SECTION_INSTRUMENTS, gettext_lazy("Instruments")),
        (SECTION_DATA, gettext_lazy("Data")),
        (SECTION_PRICES, gettext_lazy("Prices")),
        (SECTION_REPORT, gettext_lazy("Report")),
        (SECTION_IMPORT, gettext_lazy("Import")),
        (SECTION_ACTIVITY_LOG, gettext_lazy("Activity Log")),
        (SECTION_SCHEDULES, gettext_lazy("Schedules")),
        (SECTION_OTHER, gettext_lazy("Other")),
    )

    TYPE_INFORMATION = 1
    TYPE_WARNING = 2
    TYPE_ERROR = 3
    TYPE_SUCCESS = 4

    TYPE_CHOICES = (
        (TYPE_INFORMATION, gettext_lazy("Information")),
        (TYPE_WARNING, gettext_lazy("Warning")),
        (TYPE_ERROR, gettext_lazy("Error")),
        (TYPE_SUCCESS, gettext_lazy("Success")),
    )

    ACTION_STATUS_NOT_REQUIRED = 1
    ACTION_STATUS_REQUIRED = 2
    ACTION_STATUS_SOLVED = 3

    ACTION_STATUS_CHOICES = (
        (ACTION_STATUS_NOT_REQUIRED, gettext_lazy("Not Required")),
        (ACTION_STATUS_REQUIRED, gettext_lazy("Required")),
        (ACTION_STATUS_SOLVED, gettext_lazy("Solved")),
    )

    master_user = models.ForeignKey(
        "users.MasterUser",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    section = models.PositiveSmallIntegerField(
        default=SECTION_GENERAL,
        choices=SECTION_CHOICES,
        verbose_name=gettext_lazy("section"),
    )
    type = models.PositiveSmallIntegerField(
        default=TYPE_INFORMATION,
        choices=TYPE_CHOICES,
        verbose_name=gettext_lazy("type"),
    )
    action_status = models.PositiveSmallIntegerField(
        default=ACTION_STATUS_NOT_REQUIRED,
        choices=ACTION_STATUS_CHOICES,
        verbose_name=gettext_lazy("action status"),
    )
    title = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("title"),
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("text"),
    )
    created = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        db_index=True,
        verbose_name=gettext_lazy("created"),
    )
    performed_by = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("performed by"),
    )
    target = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("target"),
    )
    linked_event = models.ForeignKey(
        "instruments.GeneratedEvent",
        null=True,
        blank=True,
        verbose_name=gettext_lazy("linked event"),
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        pieces = []

        if self.created:
            pieces.append(self.created.strftime("%Y-%m-%d %H:%M:%S"))

        if self.title:
            pieces.append(self.title)

        if self.description:
            pieces.append(f"{self.description[:30]}...")

        return " ".join(pieces)


class SystemMessageAttachment(models.Model):
    system_message = models.ForeignKey(
        SystemMessage,
        verbose_name=gettext_lazy("system message"),
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file_url = models.TextField(
        null=True,
        blank=True,
        default="",
        verbose_name=gettext_lazy("File URL"),
    )
    file_name = models.CharField(
        null=True,
        max_length=255,
        blank=True,
        default="",
    )
    notes = models.TextField(
        null=True,
        blank=True,
        default="",
        verbose_name=gettext_lazy("notes"),
    )
    file_report = models.ForeignKey(
        FileReport,
        null=True,
        verbose_name=gettext_lazy("file report"),
        on_delete=models.SET_NULL,
    )


class SystemMessageMember(models.Model):
    system_message = models.ForeignKey(
        SystemMessage,
        verbose_name=gettext_lazy("system message"),
        related_name="members",
        on_delete=models.CASCADE,
    )
    member = models.ForeignKey(
        Member,
        verbose_name=gettext_lazy("member"),
        on_delete=models.CASCADE,
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("is read"),
    )
    is_pinned = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("is pinned"),
    )


class SystemMessageComment(TimeStampedModel):
    system_message = models.ForeignKey(
        SystemMessage,
        verbose_name=gettext_lazy("system message"),
        related_name="comments",
        on_delete=models.CASCADE,
    )
    member = models.ForeignKey(
        Member,
        verbose_name=gettext_lazy("member"),
        on_delete=models.CASCADE,
    )
    comment = models.TextField(
        null=True,
        blank=True,
        default="",
        verbose_name=gettext_lazy("comment"),
    )
