import logging
import traceback

from django.conf import settings

from poms.common.exceptions import FinmarsBaseException
from poms.common.http_client import HttpClient, HttpClientError
from poms.integrations.monad import Monad, MonadStatus
from poms.integrations.serializers import CallBackDataDictRequestSerializer

_l = logging.getLogger("default")


v1_export = "api/v1/export"
FINMARS_DATABASE_URLS = {
    "instrument": f"{settings.FINMARS_DATABASE_URL}{v1_export}/instrument/",
    "currency": f"{settings.FINMARS_DATABASE_URL}{v1_export}/currency/",
    "company": f"{settings.FINMARS_DATABASE_URL}{v1_export}/company/",
}


def get_backend_callback_urls() -> dict:
    """
    Returns a dictionary containing callback URLs for 'instrument', 'currency', and 'company' services.
    """
    from poms.users.models import MasterUser

    master_user = MasterUser.objects.first()
    if not master_user:
        RuntimeError("No MasterUser defined!")

    base_url = f"https://{settings.DOMAIN_NAME}"
    if master_user.realm_code:
        base_url += f"/{master_user.realm_code}/{master_user.space_code}"
    else:
        base_url += f"/{master_user.space_code}"

    common_part = "api/v1/import/finmars-database"
    return {
        "instrument": f"{base_url}/{common_part}/instrument/callback/",
        "currency": f"{base_url}/{common_part}/currency/callback/",
        "company": f"{base_url}/{common_part}/company/callback/",
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
    Client of FINMARS-DATABASE Service
    """

    def __init__(self):
        self.http_client = HttpClient()

    def get_monad(self, service_name: str, request_options: dict) -> Monad:
        """
        Retrieves data from the FINMARS-DATABASE service.
        Args:
            service_name: The name of the service to call (e.g., 'instrument', 'currency').
            request_options: A dictionary containing request options.
        Returns:
            A Monad object containing the service response data or an error message.
        Raises:
            FinmarsBaseException: For unexpected errors during the API call.
        """
        _l.info(f"get_monad service={service_name} options={request_options}")

        if (service_name not in FINMARS_DATABASE_URLS) or not request_options:
            err_msg = "get_monad: invalid service name or request options"
            _l.error(err_msg)
            raise FinmarsBaseException(message=err_msg, error_key="finmars_database_error")

        try:
            response_json = self.http_client.post(url=FINMARS_DATABASE_URLS[service_name], json=request_options)

        except HttpClientError as e:
            return Monad(status=MonadStatus.ERROR, message=repr(e))

        except Exception as e:
            err_msg = f"get_monad: unexpected error {repr(e)}"
            _l.error(f"{err_msg}  trace {traceback.format_exc()}")
            raise FinmarsBaseException(message=err_msg, error_key="finmars_database_error") from e

        serializer = CallBackDataDictMonadSerializer(data=response_json)
        if serializer.is_valid():
            return serializer.create_good_monad()
        else:
            return serializer.create_error_monad()
