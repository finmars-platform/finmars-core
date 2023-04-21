import logging
from pathlib import Path

from django.conf import settings

import requests
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import RequestException

_l = logging.getLogger("default")
log = Path(__file__).stem

MAX_RETRIES = 1
MAX_TIMEOUT = 3  # secs
MAX_SLEEP = 1  # secs
GET = "get"
POST = "post"
HEADERS = {"Accept": "application/json", "Content-type": "application/json"}


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
        # self.session.mount("http://", HTTPAdapter(max_retries=self.retries))

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
