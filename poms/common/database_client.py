import json
import logging
from pathlib import Path

from django.conf import settings

from poms.common.http_client import HttpClient, HttpClientError
from poms.common.monad import Monad, Status

_l = logging.getLogger("poms.integrations")
log = Path(__file__).stem
HEADERS = {"Accept": "application/json", "Content-type": "application/json"}
MAX_RETRIES = 5
MAX_TIMEOUT = 600  # secs
MAX_SLEEP = 3  # secs
GET = "get"
POST = "post"
SERVICE_URLS = {
    "instrument": f"{settings.FINMARS_DATABASE_URL}api/v1/export/instrument",
}


class DatabaseService:
    """
    Client to work with FINMARS-DATABASE Service
    """

    def __init__(self):
        self.http_client = HttpClient()

    def get_info(self, service: str, request_options: dict) -> Monad:
        _l.info(f"{log} started, service={service} request_options={request_options}")

        if service not in SERVICE_URLS or not request_options:
            raise RuntimeError(f"{log} invalid args!")

        try:
            data = self.http_client.post(
                POST,
                url=SERVICE_URLS[service],
                data=json.dumps(request_options),
            )
        except HttpClientError as err:
            monad = Monad(status=Status.ERROR, message=str(err))
        else:
            if "task_id" in data:
                monad = Monad(status=Status.TASK_READY, task_id=data["task_id"])
            else:
                monad = Monad(status=Status.DATA_READY, data=data)

        return monad
