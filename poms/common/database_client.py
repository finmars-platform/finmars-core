import json
import logging
from pathlib import Path

from django.conf import settings

from poms.common.http_client import HttpClient, HttpClientError
from poms.common.monad import Monad, MonadStatus

_l = logging.getLogger("default")
log = Path(__file__).stem

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
                url=SERVICE_URLS[service],
                data=json.dumps(request_options),
            )
        except HttpClientError as err:
            monad = Monad(status=MonadStatus.ERROR, message=repr(err))
        else:
            if "task_id" in data:
                monad = Monad(status=MonadStatus.TASK_READY, task_id=data["task_id"])
            else:
                monad = Monad(status=MonadStatus.DATA_READY, data=data)

        return monad
