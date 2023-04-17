from enum import IntEnum
import json
import logging
from dataclasses import dataclass
from typing import Any
from pathlib import Path

from django.conf import settings

import requests
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import RequestException

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


class Status(IntEnum):
    NO_ANSWER = 0
    DATA_READY = 1
    TASK_READY = 2
    ERROR = 666


@dataclass
class ServiceMonad:
    status: int = Status.NO_ANSWER.value
    task_id: int = 0
    message: str = ""
    data: Any = None


class HttpClientError(Exception):
    pass


class HttpClient:
    """
    Simple HTTP client
    """

    def __init__(self, max_timeout=MAX_TIMEOUT, max_retries=MAX_RETRIES):
        self.max_timeout = max_timeout
        self.retries = Retry(
            total=max_retries,
            backoff_factor=MAX_SLEEP,
        )
        self.session = requests.Session()
        self.session.mount("https://", HTTPAdapter(max_retries=self.retries))
        self.session.mount("http://", HTTPAdapter(max_retries=self.retries))

    def _fetch_response(self, method, url, **kwargs) -> dict:
        if not url:
            raise HttpClientError("url is not specified!")
        if not kwargs:
            kwargs = {}
        kwargs["headers"] = HEADERS

        try:
            http_method = getattr(self.session, method)
            response = http_method(
                url,
                timeout=self.max_timeout,
                verify=settings.VERIFY_SSL,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()

        except RequestException as ex:
            raise HttpClientError(f"method={method} url={url} error={ex}") from ex

    def get(self, url, **kwargs) -> dict:
        return self._fetch_response(GET, url, **kwargs)

    def post(self, url, **kwargs) -> dict:
        return self._fetch_response(POST, url, **kwargs)


class DatabaseService:
    """
    Client to work with FINMARS-DATABASE Service
    """

    def __init__(self):
        self.http_client = HttpClient()

    def get_info(self, service: str, request_options: dict) -> ServiceMonad:
        _l.info(f"{log} started, service={service} request_options={request_options}")

        if service not in SERVICE_URLS or not request_options:
            raise RuntimeError(f"{log} invalid args!")

        try:
            response_data = self.http_client.post(
                POST,
                url=SERVICE_URLS[service],
                data=json.dumps(request_options),
            )
        except HttpClientError as err:
            monad = ServiceMonad(status=Status.ERROR.value, message=str(err))
        else:
            if "task_id" in response_data:
                monad = ServiceMonad(
                    status=Status.TASK_READY.value, task_id=response_data["task_id"]
                )
            else:
                monad = ServiceMonad(Status.DATA_READY.value, data=response_data)

        return monad
