import logging
import traceback

from django.conf import settings
from poms.common.http_client import HttpClient, HttpClientError
from poms.integrations.monad import Monad, MonadStatus
from poms.integrations.serializers import CallBackDataDictRequestSerializer

_l = logging.getLogger("default")
log = "DatabaseClient"

BACKEND_URL = f"https://{settings.DOMAIN_NAME}/{settings.BASE_API_URL}"
COMMON_PART = "api/v1/import/finmars-database"
BACKEND_CALLBACK_URLS = {
    "instrument": f"{BACKEND_URL}/{COMMON_PART}/instrument/callback/",
    "currency": f"{BACKEND_URL}/{COMMON_PART}/currency/callback/",
    "company": f"{BACKEND_URL}/{COMMON_PART}/company/callback/",
}

V1 = "api/v1"
FINMARS_DATABASE_URLS = {
    "currency": f"{settings.FINMARS_DATABASE_URL}{V1}/export/currency",
    "instrument": f"{settings.FINMARS_DATABASE_URL}{V1}/export/instrument",
    "company": f"{settings.FINMARS_DATABASE_URL}{V1}/export/company",
}


class CallBackDataDictMonadSerializer(CallBackDataDictRequestSerializer):
    def create_good_monad(self) -> Monad:
        task_id = self.validated_data["task_id"]
        status = MonadStatus.TASK_CREATED if task_id else MonadStatus.DATA_READY
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

        serializer = CallBackDataDictMonadSerializer(data=response_json)
        return (
            serializer.create_good_monad()
            if serializer.is_valid()
            else serializer.create_error_monad()
        )
