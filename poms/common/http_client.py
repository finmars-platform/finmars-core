from django.conf import settings

import requests
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import RequestException

GET = "get"
POST = "post"
HEADERS = {
    "Accept": "application/json",
}


class HttpClientError(Exception):
    pass


class HttpClient:
    """
    Simple HTTP client
    """

    def __init__(
        self,
        max_timeout=settings.FINMARS_DATABASE_TIMEOUT,
        max_retries=settings.FINMARS_DATABASE_RETRIES,
    ):
        self.max_timeout = max_timeout
        self.retries = Retry(
            total=max_retries,
            backoff_factor=settings.FINMARS_DATABASE_SLEEP,
        )
        self.session = requests.Session()
        self.session.mount("https://", HTTPAdapter(max_retries=self.retries))

    def _fetch_response(self, method, url, **kwargs) -> dict:
        if not url:
            raise HttpClientError("url is not specified!")
        if not kwargs:
            kwargs = {}
        if "headers" not in kwargs:
            kwargs["headers"] = HEADERS

        response = None
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
            err_msg = response.text if response and response.text else ""
            raise HttpClientError(
                f"method={method} url={url} err='{err_msg}' except={ex}",
            ) from ex

    def get(self, url, **kwargs) -> dict:
        return self._fetch_response(GET, url, **kwargs)

    def post(self, url, **kwargs) -> dict:
        return self._fetch_response(POST, url, **kwargs)
