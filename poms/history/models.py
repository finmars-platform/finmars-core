import contextlib
import json
import logging
import sys
import traceback
from datetime import datetime, timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.forms.models import model_to_dict
from django.utils.translation import gettext_lazy

from deepdiff import DeepDiff
from poms_app import settings

from poms.common.celery import get_active_celery_task, get_active_celery_task_id
from poms.common.middleware import get_request

_l = logging.getLogger("poms.history")

DATETIME_FORMAT = "%Y-%m-%d, %H:%M:%S"

# TODO important to keep this list up to date
# Just not to log history for too meta models
excluded_to_track_history_models = [
    "celery_tasks.celerytask",
    "celery_tasks.celerytaskattachment",
    "system_messages.systemmessage",
    "system_messages.systemmessagemember",
    "obj_attrs.genericattribute",
    "transactions.complextransactioninput",
    "migrations.migration",
    "django_celery_results.taskresult",
    "django_celery_beat.periodictask",
    "django_celery_beat.periodictasks",
    "django_celery_beat.crontabschedule",
    "csv_import.csvfield",
    "csv_import.entityfield",
    "pricing.instrumentpricingschemetype",
    "pricing.currencypricingschemetype",
    "pricing.instrumentpricingpolicy",
    "pricing.currencypricingpolicy",
    "pricing.pricehistoryerror",
    "pricing.currencyhistoryerror",
    "pricing.pricingprocedurebloomberginstrumentresult",
    "pricing.pricingprocedurebloombergforwardinstrumentresult",
    "pricing.pricingprocedurebloombergcurrencyresult",
    "integrations.dataprovider",
    "integrations.accrualscheduledownloadmethod",
    "integrations.providerclass",
    "transactions.periodicitygroup",
    "transactions.eventclass",
    "transactions.notificationclass",
    "transactions.actionclass",
    "transactions.complextransactionstatus",
    "transactions.transactionclass",
    "instruments.country",
    "instruments.shortunderlyingexposure",
    "instruments.longunderlyingexposure",
    "instruments.pricingcondition",
    "instruments.paymentsizedetail",
    "instruments.costmethod",
    "instruments.periodicity",
    "integrations.factorscheduledownloadmethod",
    "instruments.exposurecalculationmodel",
    "instruments.dailypricingmodel",
    "instruments.instrumentclass",
    "ui.portalinterfaceaccessmodel",
    "instruments.accrualcalculationmodel",
    "instruments.pricehistory",
    "currencies.currencyhistory",
    "widgets.collect_stats",
    "widgets.collect_pl_report_history",
    "widgets.collect_balance_report_history",
    "widgets.plreporthistoryitem",
    "widgets.balancereporthistoryitem",
    "portfolios.portfolioregisterrecord",
    "ui.listlayout",
    "ui.editlayout",
    "users.fakesequence",
    "widgets.plreporthistoryitem",
    "widgets.balancereporthistoryitem",
    "file_reports.filereport",
    "finmars_standardized_errors.errorrecord",
]


class HistoricalRecord(models.Model):
    ACTION_CREATE = "create"
    ACTION_CHANGE = "change"
    ACTION_DELETE = "delete"
    ACTION_DANGER = "danger"
    ACTION_RECYCLE_BIN = "recycle_bin"

    ACTION_CHOICES = (
        (ACTION_CREATE, gettext_lazy("Create")),
        (ACTION_CHANGE, gettext_lazy("Change")),
        (ACTION_DELETE, gettext_lazy("Delete")),
        (ACTION_DANGER, gettext_lazy("Danger")),
        (ACTION_RECYCLE_BIN, gettext_lazy("Recycle Bin")),
    )

    """
    2023.01 Feature
    It listen changes of models and store JSON output after save
    In Finmars Web interface users can check history of changes for specific entity e.g.
     Instrument, Complex Transaction
    TODO: probably need to store only diff with change, not the whole JSON output
    """
    master_user = models.ForeignKey(
        "users.MasterUser",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    member = models.ForeignKey(
        "users.Member",
        null=True,
        blank=True,
        verbose_name=gettext_lazy("member"),
        on_delete=models.SET_NULL,
    )
    user_code = models.CharField(
        max_length=1024,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("user code"),
    )
    action = models.CharField(
        max_length=25,
        default=ACTION_CHANGE,
        choices=ACTION_CHOICES,
        verbose_name="action",
    )
    content_type = models.ForeignKey(
        ContentType,
        verbose_name=gettext_lazy("content type"),
        on_delete=models.CASCADE,
    )
    context_url = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("context_url"),
    )
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("notes"),
    )
    created = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        null=True,
        db_index=True,
        verbose_name=gettext_lazy("created"),
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

    def __str__(self):
        return (
            f"{self.member.username} changed {self.user_code} ({self.content_type}) "
            f"at {self.created.strftime(DATETIME_FORMAT)}"
        )

    @property
    def as_dict(self) -> dict:
        return {
            "master_user": str(self.master_user),
            "member": str(self.member),
            "user_code": self.user_code,
            "action": self.action,
            "content_type": str(self.content_type),
            "context_url": self.context_url,
            "notes": self.notes,
            "created": self.created.strftime(DATETIME_FORMAT),
            "json_data": self.json_data,
        }

    class Meta:
        verbose_name = gettext_lazy("history record")
        verbose_name_plural = gettext_lazy("history records")
        index_together = [["user_code", "content_type"]]
        ordering = ["-created"]


def get_user_code_from_instance(instance, content_type_key):
    user_code = None

    if getattr(instance, "code", None) and content_type_key in [
        "transactions.transaction",
        "transactions.complextransaction",
    ]:
        user_code = instance.code
    elif getattr(instance, "user_code", None):
        user_code = instance.user_code
    elif getattr(instance, "name", None):
        user_code = instance.name

    if not user_code:
        user_code = str(instance)

    return user_code


def get_model_content_type_as_text(sender):
    content_type = ContentType.objects.get_for_model(sender)
    return f"{content_type.app_label}.{content_type.model}"


def get_serialized_data(sender, instance):
    from poms.accounts.serializers import AccountSerializer, AccountTypeSerializer
    from poms.counterparties.serializers import (
        CounterpartySerializer,
        ResponsibleSerializer,
    )
    from poms.csv_import.serializers import CsvImportSchemeSerializer
    from poms.currencies.serializers import (
        CurrencyHistorySerializer,
        CurrencySerializer,
    )
    from poms.instruments.serializers import (
        GeneratedEventSerializer,
        InstrumentSerializer,
        InstrumentTypeSerializer,
        PriceHistorySerializer,
        PricingPolicySerializer,
    )
    from poms.integrations.serializers import (
        ComplexTransactionImportSchemeSerializer,
        InstrumentDownloadSchemeSerializer,
    )
    from poms.portfolios.serializers import (
        PortfolioRegisterRecordSerializer,
        PortfolioRegisterSerializer,
        PortfolioSerializer,
    )
    from poms.procedures.serializers import (
        ExpressionProcedureSerializer,
        PricingProcedureSerializer,
        RequestDataFileProcedureSerializer,
    )
    from poms.schedules.serializers import ScheduleSerializer
    from poms.transactions.serializers import (
        ComplexTransactionSerializer,
        TransactionSerializer,
        TransactionTypeSerializer,
    )
    from poms.users.serializers import MasterUserSerializer, MemberSerializer

    model_serializer_map = {
        "users.masteruser": MasterUserSerializer,
        "users.member": MemberSerializer,
        "accounts.account": AccountSerializer,
        "accounts.accounttype": AccountTypeSerializer,
        "counterparties.counterparty": CounterpartySerializer,
        "counterparties.responsible": ResponsibleSerializer,
        "portfolios.portfolio": PortfolioSerializer,
        "portfolios.portfolioregister": PortfolioRegisterSerializer,
        "portfolios.portfolioregisterrecord": PortfolioRegisterRecordSerializer,
        "currencies.currency": CurrencySerializer,
        "currencies.currencyhistory": CurrencyHistorySerializer,
        "instruments.instrument": InstrumentSerializer,
        "instruments.instrumenttype": InstrumentTypeSerializer,
        "instruments.pricehistory": PriceHistorySerializer,
        "instruments.pricingpolicy": PricingPolicySerializer,
        "instruments.generatedevent": GeneratedEventSerializer,
        "integrations.instrumentdownloadscheme": InstrumentDownloadSchemeSerializer,
        "integrations.complextransactionimportscheme": ComplexTransactionImportSchemeSerializer,
        "csv_import.csvimportscheme": CsvImportSchemeSerializer,
        "transactions.complextransaction": ComplexTransactionSerializer,
        "transactions.transaction": TransactionSerializer,
        "transactions.transactiontype": TransactionTypeSerializer,
        "procedures.pricingprocedure": PricingProcedureSerializer,
        "procedures.requestdatafileprocedure": RequestDataFileProcedureSerializer,
        "procedures.expressionprocedure": ExpressionProcedureSerializer,
        "schedules.schedule": ScheduleSerializer,
    }

    record_context = get_record_context()
    context = {
        "master_user": record_context["master_user"],
        "member": record_context["member"],
    }
    try:
        content_type_key = get_model_content_type_as_text(sender)
        result = model_serializer_map[content_type_key](
            instance=instance,
            context=context,
        ).data
    except Exception:
        try:
            result = json.dumps(model_to_dict(instance), default=str)
        except Exception:
            result = None

    return result


def get_notes_for_history_record(user_code, content_type, serialized_data):
    notes = None
    with contextlib.suppress(Exception):
        last_record = HistoricalRecord.objects.filter(
            user_code=user_code,
            content_type=content_type,
            action__in=[
                HistoricalRecord.ACTION_CREATE,
                HistoricalRecord.ACTION_CHANGE,
                HistoricalRecord.ACTION_DELETE,
                HistoricalRecord.ACTION_DANGER,
            ],
        ).order_by("-created")[0]

        everything_is_dict = json.loads(
            json.dumps(serialized_data)
        )  # because deep diff counts different Dict and Ordered dict

        result = DeepDiff(
            last_record.data,
            everything_is_dict,
            ignore_string_type_changes=True,
            ignore_order=True,
            ignore_type_subclasses=True,
        )

        # _l.info('result %s' % result)

        notes = result.to_json()

    return notes


def get_record_context():
    from poms.users.models import MasterUser, Member

    result = {"master_user": None, "member": None, "context_url": "Unknown"}

    if request := get_request():

        # _l.info('request.user %s' % request.user)

        # result["master_user"] = request.user.master_user
        result["master_user"] = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)
        # result["master_user"] = request.user.member
        result["member"] = Member.objects.get(user=request.user)
        result["context_url"] = request.path

    else:
        try:
            celery_task_id = get_active_celery_task_id()
            lib_celery_task = get_active_celery_task()

            # _l.info('celery_task_id %s' % celery_task_id)

            try:
                update_result_with_celery_task_data(celery_task_id, result)

            except Exception:
                finmars_bot = Member.objects.get(username="finmars_bot")
                master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

                result["member"] = finmars_bot
                result["master_user"] = master_user
                result["context_url"] = (
                    lib_celery_task.name if lib_celery_task else "Shell"
                )

        except Exception as e:
            _l.error(
                f"Error getting context for celery exception {e} "
                f"traceback {traceback.format_exc()}"
            )

    return result


def update_result_with_celery_task_data(celery_task_id, result):
    from poms.celery_tasks.models import CeleryTask

    if not celery_task_id:
        raise RuntimeError("Celery task id is not set")

    celery_task = CeleryTask.objects.get(celery_task_id=celery_task_id)

    result["member"] = celery_task.member
    result["master_user"] = celery_task.master_user
    result["context_url"] = f"{celery_task.type} [{str(celery_task.id)}]"


def post_save(sender, instance, created, using=None, update_fields=None, **kwargs):
    # _l.info('post_save.sender %s' % sender)
    # _l.info('post_save.update_fields %s' % update_fields)

    from poms.users.models import MasterUser

    master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

    if sender == MasterUser and instance.journal_status == "disabled":
        record_context = get_record_context()
        content_type = ContentType.objects.get_for_model(sender)

        already_disabled = False

        with contextlib.suppress(Exception):
            last_record = HistoricalRecord.objects.filter(
                user_code=master_user.name,
                content_type=content_type,
            ).order_by("-created")[0]

            _l.info(f"last_record {last_record.data}")

            if last_record.data["journal_status"] == "disabled":
                already_disabled = True

        if not already_disabled:
            data = get_serialized_data(sender, instance)

            HistoricalRecord.objects.create(
                master_user=record_context["master_user"],
                member=record_context["member"],
                action=HistoricalRecord.ACTION_DANGER,
                user_code=master_user.name,
                data=data,
                notes="JOURNAL IS DISABLED. OBJECTS ARE NOT TRACKED",
                content_type=content_type,
            )

    if master_user.journal_status != MasterUser.JOURNAL_STATUS_DISABLED:
        user_code = None

        try:
            record_context = get_record_context()
            content_type = ContentType.objects.get_for_model(sender)
            content_type_key = get_model_content_type_as_text(sender)
            user_code = get_user_code_from_instance(instance, content_type_key)

            exist = bool(
                HistoricalRecord.objects.filter(
                    user_code=user_code, content_type=content_type
                ).count()
            )
            if exist:
                action = HistoricalRecord.ACTION_CHANGE
            else:
                action = HistoricalRecord.ACTION_CREATE

            # _l.info('created %s' % created)
            # _l.info('update_fields %s' % update_fields)

            if update_fields and "is_deleted" in update_fields:
                if instance.is_deleted:
                    action = HistoricalRecord.ACTION_RECYCLE_BIN
                else:
                    action = HistoricalRecord.ACTION_CHANGE

            # TODO think about better performance
            # if HistoricalRecord.ACTION_RECYCLE_BIN:
            #     data = {"is_deleted": True}
            #     notes = {"is_deleted": True}
            # else:

            if action != HistoricalRecord.ACTION_RECYCLE_BIN:
                data = get_serialized_data(sender, instance)
                notes = get_notes_for_history_record(user_code, content_type, data)
            else:
                data = None
                notes = {"message": "User moved object to Recycle Bin"}

            HistoricalRecord.objects.create(
                master_user=record_context["master_user"],
                member=record_context["member"],
                action=action,
                context_url=record_context["context_url"],
                data=data,
                notes=notes,
                user_code=user_code,
                content_type=content_type,
            )

        except Exception as e:
            _l.error(
                f"Could not save history user_code {user_code} exception {e} "
                f"traceback {traceback.format_exc()}"
            )


def post_delete(sender, instance, using=None, **kwargs):
    from poms.users.models import MasterUser

    master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

    if master_user.journal_status != MasterUser.JOURNAL_STATUS_DISABLED:
        try:
            post_delete_action(sender, instance)
        except Exception as e:
            _l.error(
                f"Could not save history record exception {e} "
                f"traceback {traceback.format_exc()} "
            )


def post_delete_action(sender, instance):
    record_context = get_record_context()

    action = HistoricalRecord.ACTION_DELETE

    content_type = ContentType.objects.get_for_model(sender)
    content_type_key = get_model_content_type_as_text(sender)

    user_code = get_user_code_from_instance(instance, content_type_key)

    data = get_serialized_data(sender, instance)

    HistoricalRecord.objects.create(
        master_user=record_context["master_user"],
        member=record_context["member"],
        context_url=record_context["context_url"],
        action=action,
        data=data,
        user_code=user_code,
        content_type=content_type,
    )


def add_history_listeners(sender, **kwargs):
    # _l.debug("History listener registered Entity %s" % sender)

    # IMPORTANT TO DO ONLY LOCAL IMPORTS
    # BECAUSE IF YOU DO AN IMPORT, CLASS WILL NOT BE LISTENED VIA signals.class_prepared

    content_type_key = get_model_content_type_as_text(sender)

    if content_type_key not in excluded_to_track_history_models:
        models.signals.post_save.connect(post_save, sender=sender, weak=False)
        models.signals.post_delete.connect(post_delete, sender=sender, weak=False)


def record_history():

    _l = logging.getLogger('provision')

    if "test" in sys.argv or "makemigrations" in sys.argv or "migrate" in sys.argv:
        _l.info("History is not recording. Probably Test or Migration context")
    else:
        _l.info("History is recording")
        models.signals.class_prepared.connect(add_history_listeners, weak=False)


record_history()
