import logging

from django.conf import settings

from poms.common.http_client import HttpClient, HttpClientError
from poms.common.monad import Monad, MonadStatus

_l = logging.getLogger("default")
log = "DatabaseClient"

BACKEND_URL = f"https://{settings.DOMAIN_NAME}/{settings.BASE_API_URL}"
COMMON_PART = "api/v1/import/finmars-database"
BACKEND_CALLBACK_URLS ={
    "instrument": f"{BACKEND_URL}/{COMMON_PART}/instrument/callback/",
    "currency": f"{BACKEND_URL}/{COMMON_PART}/currency/callback/",
    "company": f"{BACKEND_URL}/{COMMON_PART}/company/callback/",
}

V1 = "api/v1/"
FINMARS_DATABASE_URLS = {
    "instrument": f"{settings.FINMARS_DATABASE_URL}{V1}export/instrument",
    "instrument-narrow": f"{settings.FINMARS_DATABASE_URL}{V1}instrument-narrow",
    "currency": f"{settings.FINMARS_DATABASE_URL}{V1}currency",
    "company": f"{settings.FINMARS_DATABASE_URL}{V1}company",
}


class DatabaseService:
    """
    Client to work with FINMARS-DATABASE Service
    """

    def __init__(self):
        self.http_client = HttpClient()

    def get_task(self, service_name: str, request_options: dict) -> Monad:
        _l.info(f"{log}.get_task service={service_name} options={request_options}")

        if (service_name not in FINMARS_DATABASE_URLS) or not request_options:
            raise RuntimeError(f"{log} invalid args!")

        try:
            data = self.http_client.post(
                url=FINMARS_DATABASE_URLS[service_name],
                json=request_options,
            )
        except HttpClientError as err:
            monad = Monad(status=MonadStatus.ERROR, message=repr(err))
        else:
            if "task_id" in data:
                monad = Monad(status=MonadStatus.TASK_READY, task_id=data["task_id"])
            else:
                monad = Monad(status=MonadStatus.DATA_READY, data=data)

        return monad

    def get_results(self, service_name: str, request_params: dict) -> Monad:
        _l.info(f"{log}.get_result service={service_name} options={request_params}")

        if service_name not in FINMARS_DATABASE_URLS:
            raise RuntimeError(f"{log}.get_result no service_name!")

        try:
            data = self.http_client.get(
                url=FINMARS_DATABASE_URLS[service_name],
                params=request_params,
            )
        except HttpClientError as err:
            monad = Monad(status=MonadStatus.ERROR, message=repr(err))
        else:
            if "results" in data:
                monad = Monad(status=MonadStatus.DATA_READY, data=data)
            else:
                err_msg = f"{log}.get_result no 'results' in response.data={data}"
                monad = Monad(status=MonadStatus.ERROR, message=err_msg)

        return monad
