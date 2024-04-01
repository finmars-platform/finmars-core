import json
from logging import getLogger

from django.contrib.auth import get_user_model

import requests
from poms_app import settings
from rest_framework_simplejwt.tokens import RefreshToken

_l = getLogger("poms.authorizer")


class AuthorizerService:
    # ?space_code=... needs for JWT Auth purpose !!!

    # @staticmethod
    # def prepare_refresh_token() -> RefreshToken:
    #     User = get_user_model()
    #
    #     # Probably need to come up with something more smart
    #     bot = User.objects.get(username="finmars_bot")
    #
    #     return RefreshToken.for_user(bot)

    def prepare_headers(self) -> dict:
        # refresh = self.prepare_refresh_token()
        return {
            "Content-type": "application/json",
            "Accept": "application/json"
            # "Authorization": f"Bearer {refresh.access_token}", # for internal call no auth,
            # TODO create authorizer - realms auth
        }

    def invite_member(self, member, from_user, realm_code, space_code):
        headers = self.prepare_headers()
        data = {
            "realm_code": realm_code,
            "space_code": space_code,
            "base_api_url": space_code, # deprecated, delete, but be sure authorizer not using it
            "username": member.username,
            "is_admin": member.is_admin,
            "from_user_username": from_user.username,
        }
        url = (
            f"{settings.AUTHORIZER_URL}/api/v1/internal/invite-member/"
            f"?space_code={space_code}"
        )

        _l.info(f"invite_member url={url} data={data}")

        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Authorizer API error, data={data} code={response.status_code} "
                f"details={response.text}"
            )

    def kick_member(self, member, realm_code, space_code):
        headers = self.prepare_headers()
        data = {
            "realm_code": realm_code,
            "space_code": space_code,
            "base_api_url": space_code, # deprecated, but, be sure that authorizer not using it
            "username": member.username,
        }
        url = (
            f"{settings.AUTHORIZER_URL}/api/v1/internal/kick-member/"
            f"?space_code={space_code}"
        )

        _l.info(f"kick_member url={url} data={data}")

        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL
        )
        if response.status_code != 200:
            raise RuntimeError(f"Error kicking member {response.text}")

    def prepare_and_post_request(self, worker, url, realm_code, err_msg):
        headers = self.prepare_headers()
        data = {
            "realm_code": realm_code,
            "worker_name": worker.worker_name,
        }
        url = f"{settings.AUTHORIZER_URL}{url}"
        response = requests.post(
            url=url,
            data=json.dumps(data),
            headers=headers,
            verify=settings.VERIFY_SSL,
        )
        if response.status_code != 200:
            raise RuntimeError(f"{err_msg}{response.text}")

    def start_worker(self, worker, realm_code):
        self.prepare_and_post_request(
            worker,
            realm_code,
            "/api/v1/internal/start-worker/",
            "Error starting worker ",
        )

    def stop_worker(self, worker, realm_code):
        self.prepare_and_post_request(
            worker,
            realm_code,
            "/api/v1/internal/stop-worker/",
            "Error stopping worker ",
        )

    def restart_worker(self, worker, realm_code):
        self.prepare_and_post_request(
            worker,
            realm_code,
            "/api/v1/internal/restart-worker/",
            "Error restarting worker ",
        )

    def delete_worker(self, worker, realm_code):
        self.prepare_and_post_request(
            worker,
            realm_code,
            "/api/v1/internal/delete-worker/",
            "Error deleting worker ",
        )

    def get_worker_status(self, worker, realm_code):
        headers = self.prepare_headers()
        url = (
            f"{settings.AUTHORIZER_URL}/api/v1/internal/worker-status/"
            f"?realm_code={realm_code}&worker_name={worker.worker_name}"
        )

        response = requests.get(url=url, headers=headers, verify=settings.VERIFY_SSL)
        if response.status_code != 200:
            raise RuntimeError(f"Error getting worker status {response.text}")

        return response.json()

    def create_worker(self, worker, realm_code):
        headers = self.prepare_headers()
        data = {
            "realm_code": realm_code,
            "worker_name": worker.worker_name,
            "worker_type": worker.worker_type,
            "memory_limit": worker.memory_limit,
            "queue": worker.queue,
        }
        url = f"{settings.AUTHORIZER_URL}/api/v1/internal/create-worker/"

        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL
        )
        if response.status_code != 200:
            raise RuntimeError(f"Error creating worker {response.text}")
