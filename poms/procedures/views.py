from logging import getLogger

from django_filters import FilterSet
from rest_framework.decorators import action
from rest_framework.response import Response

from poms.common.filters import CharFilter, NoOpFilter
from poms.common.views import AbstractModelViewSet
from poms.integrations.providers.base import parse_date_iso
from poms.pricing.handlers import PricingProcedureProcess
from poms.procedures.handlers import ExpressionProcedureProcess
from poms.procedures.models import (
    ExpressionProcedure,
    PricingParentProcedureInstance,
    PricingProcedure,
    PricingProcedureInstance,
    RequestDataFileProcedure,
    RequestDataFileProcedureInstance,
)
from poms.procedures.serializers import (
    ExpressionProcedureSerializer,
    PricingParentProcedureInstanceSerializer,
    PricingProcedureInstanceSerializer,
    PricingProcedureSerializer,
    RequestDataFileProcedureInstanceSerializer,
    RequestDataFileProcedureSerializer,
    RunExpressionProcedureSerializer,
    RunProcedureSerializer,
)
from poms.procedures.tasks import execute_data_procedure
from poms.system_messages.handlers import send_system_message
from poms.users.filters import OwnerByMasterUserFilter

_l = getLogger("poms.procedures")


class PricingProcedureFilterSet(FilterSet):
    class Meta:
        model = PricingProcedure
        fields = []


class PricingProcedureViewSet(AbstractModelViewSet):
    queryset = PricingProcedure.objects.filter(type=PricingProcedure.CREATED_BY_USER)
    serializer_class = PricingProcedureSerializer
    filter_class = PricingProcedureFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + []

    @action(
        detail=True,
        methods=["post"],
        url_path="run-procedure",
        serializer_class=RunProcedureSerializer,
    )
    def run_procedure(self, request, pk=None, realm_code=None, space_code=None):
        _l.debug(f"Run Procedure {pk} data {request.data}")

        procedure = PricingProcedure.objects.get(pk=pk)

        master_user = request.user.master_user

        date_from = None
        date_to = None

        if (
            "user_price_date_from" in request.data
            and request.data["user_price_date_from"]
        ):
            date_from = parse_date_iso(request.data["user_price_date_from"])

        if "user_price_date_to" in request.data and request.data["user_price_date_to"]:
            date_to = parse_date_iso(request.data["user_price_date_to"])

        instance = PricingProcedureProcess(
            procedure=procedure,
            master_user=master_user,
            date_from=date_from,
            date_to=date_to,
        )
        instance.process()

        serializer = self.get_serializer(instance=instance)

        return Response(serializer.data)


class PricingParentProcedureInstanceFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = PricingParentProcedureInstance
        fields = []


class PricingParentProcedureInstanceViewSet(AbstractModelViewSet):
    queryset = PricingParentProcedureInstance.objects.select_related(
        "master_user",
    )
    serializer_class = PricingParentProcedureInstanceSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = PricingParentProcedureInstanceFilterSet


class PricingProcedureInstanceFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = PricingProcedureInstance
        fields = []


class PricingProcedureInstanceViewSet(AbstractModelViewSet):
    queryset = PricingProcedureInstance.objects.select_related(
        "master_user",
    )
    serializer_class = PricingProcedureInstanceSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = PricingProcedureInstanceFilterSet


class RequestDataFileProcedureFilterSet(FilterSet):
    user_code = CharFilter()
    name = CharFilter()

    class Meta:
        model = RequestDataFileProcedure
        fields = []


class RequestDataFileProcedureViewSet(AbstractModelViewSet):
    queryset = RequestDataFileProcedure.objects
    serializer_class = RequestDataFileProcedureSerializer
    filter_class = RequestDataFileProcedureFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]

    permission_classes = []

    @action(detail=True, methods=["post"], url_path="run-procedure")
    def run_procedure(self, request, pk=None, realm_code=None, space_code=None):
        _l.debug(f"Run Procedure {pk} data {request.data}")

        procedure = RequestDataFileProcedure.objects.get(pk=pk)

        master_user = request.user.master_user
        member = request.user.member

        procedure_instance = RequestDataFileProcedureInstance.objects.create(
            procedure=procedure,
            master_user=master_user,
            member=member,
            status=RequestDataFileProcedureInstance.STATUS_PENDING,
            schedule_instance=None,
            action="request_transaction_file",
            provider="finmars",
            action_verbose="Request file with Transactions",
            provider_verbose="Finmars",
        )

        execute_data_procedure.apply_async(
            kwargs={"procedure_instance_id": procedure_instance.id}
        )

        return Response(
            {"procedure_id": pk, "procedure_instance_id": procedure_instance.id}
        )

    @action(detail=False, methods=["post"], url_path="execute")
    def execute(self, request, realm_code=None, space_code=None):
        _l.info(f"RequestDataFileProcedureViewSet.execute.data {request.data}")

        user_code = request.data["user_code"]

        procedure = RequestDataFileProcedure.objects.get(user_code=user_code)

        master_user = request.user.master_user
        member = request.user.member

        procedure_instance = RequestDataFileProcedureInstance.objects.create(
            procedure=procedure,
            master_user=master_user,
            member=member,
            status=RequestDataFileProcedureInstance.STATUS_PENDING,
            schedule_instance=None,
            action="request_transaction_file",
            provider="finmars",
            action_verbose="Request file with Transactions",
            provider_verbose="Finmars",
        )

        execute_data_procedure.apply_async(
            kwargs={
                "procedure_instance_id": procedure_instance.id,
                "date_from": request.data.get("date_from", None),
                "date_to": request.data.get("date_to", None),
                "options": request.data.get("options", None),
            }
        )

        return Response(
            {
                "procedure_id": procedure.id,
                "procedure_instance_id": procedure_instance.id,
            }
        )


class RequestDataFileProcedureInstanceFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = RequestDataFileProcedureInstance
        fields = []


class RequestDataFileProcedureInstanceViewSet(AbstractModelViewSet):
    queryset = RequestDataFileProcedureInstance.objects.select_related(
        "master_user",
    )
    serializer_class = RequestDataFileProcedureInstanceSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = RequestDataFileProcedureInstanceFilterSet


class ExpressionProcedureFilterSet(FilterSet):
    user_code = CharFilter()
    name = CharFilter()

    class Meta:
        model = ExpressionProcedure
        fields = []


class ExpressionProcedureViewSet(AbstractModelViewSet):
    queryset = ExpressionProcedure.objects
    serializer_class = ExpressionProcedureSerializer
    filter_class = ExpressionProcedureFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]

    permission_classes = []

    @action(
        detail=True,
        methods=["post"],
        url_path="run-procedure",
        serializer_class=RunExpressionProcedureSerializer,
    )
    def run_procedure(self, request, pk=None, realm_code=None, space_code=None):
        _l.debug(f"Run Procedure {pk} data {request.data}")

        procedure = ExpressionProcedure.objects.get(pk=pk)

        master_user = request.user.master_user
        member = request.user.member

        instance = ExpressionProcedureProcess(
            procedure=procedure, master_user=master_user, member=member
        )
        instance.process()

        text = f"Expression Procedure {procedure.name}. Start processing"

        send_system_message(
            master_user=master_user, performed_by="System", description=text
        )

        return Response({"task_id": instance.celery_task.id})
