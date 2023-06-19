import logging
import traceback

from django.conf import settings
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.common.http_client import HttpClient, HttpClientError
from poms.common.monad import Monad, MonadStatus
from poms.celery_tasks.models import CeleryTask

_l = logging.getLogger("default")
log = "DatabaseClient"

BACKEND_URL = f"https://{settings.DOMAIN_NAME}/{settings.BASE_API_URL}"
COMMON_PART = "api/v1/import/finmars-database"
BACKEND_CALLBACK_URLS = {
    "instrument": f"{BACKEND_URL}/{COMMON_PART}/instrument/callback/",
    "currency": f"{BACKEND_URL}/{COMMON_PART}/currency/callback/",
    "company": f"{BACKEND_URL}/{COMMON_PART}/company/callback/",
}

V1 = "api/v1/"
FINMARS_DATABASE_URLS = {
    "currency": f"{settings.FINMARS_DATABASE_URL}{V1}/export/currency",
    "instrument": f"{settings.FINMARS_DATABASE_URL}{V1}export/instrument",
    "company": f"{settings.FINMARS_DATABASE_URL}{V1}export/company",
}



class DatabaseRequestSerializer(serializers.Serializer):
    request_id = serializers.IntegerField(required=True, min_value=1)
    task_id = serializers.IntegerField(required=True, allow_null=True)
    data = serializers.DictField(required=True, allow_null=True)

    def validate(self, attrs: dict) -> dict:
        if (attrs["task_id"] is None) and (attrs["data"] is None):
            err_msg = "data & task_id can't be both null"
            raise ValidationError({"task_id": "null", "data": "null"}, err_msg)

        if not CeleryTask.objects.filter(id=attrs["request_id"]).first():
            err_msg = f"no celery task with id={attrs['request_id']}"
            raise ValidationError({"request_id": "invalid"}, err_msg)

        return attrs


class DatabaseMonadSerializer(DatabaseRequestSerializer):
    def create_good_monad(self) -> Monad:
        task_id = self.validated_data["task_id"]
        status = MonadStatus.TASK_READY if task_id else MonadStatus.DATA_READY
        return Monad(
            status=status,
            task_id=task_id,
            data=self.validated_data["data"],
            request_id=self.validated_data["request_id"],
        )

    def create_error_monad(self) -> Monad:
        return Monad(
            status=MonadStatus.ERROR,
            message=str(self.errors),
        )


class DatabaseService:
    """
    Client to work with FINMARS-DATABASE Service
    """

    def __init__(self):
        self.http_client = HttpClient()

    def get_monad(self, service_name: str, request_options: dict) -> Monad:
        _l.info(f"{log}.get_monad service={service_name} options={request_options}")

        if (service_name not in FINMARS_DATABASE_URLS) or not request_options:
            raise RuntimeError(f"{log}.get_monad invalid args!")

        try:
            response_json = self.http_client.post(
                url=FINMARS_DATABASE_URLS[service_name],
                json=request_options,
            )
        except HttpClientError as e:
            return Monad(status=MonadStatus.ERROR, message=repr(e))
        except Exception as e:
            _l.error(f"{log}.get_monad unexpected {repr(e)} {traceback.format_exc()}")
            raise

        serializer = DatabaseMonadSerializer(data=response_json)
        return (
            serializer.create_good_monad()
            if serializer.is_valid()
            else serializer.create_error_monad()
        )
