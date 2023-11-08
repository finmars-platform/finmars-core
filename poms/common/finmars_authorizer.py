import json
from logging import getLogger

from django.contrib.auth import get_user_model

import requests
from poms_app import settings
from rest_framework_simplejwt.tokens import RefreshToken

_l = getLogger("poms.authorizer")


class AuthorizerService:
    # ?space_code=... needs for JWT Auth purpose

    @staticmethod
    def prepare_refresh_token() -> RefreshToken:
        User = get_user_model()

        # Probably need to come up with something more smart
        bot = User.objects.get(username="finmars_bot")

        refresh = RefreshToken.for_user(bot)

        refresh["space_code"] = settings.BASE_API_URL  # FIXME ???

        return refresh

    def prepare_headers(self) -> dict:
        refresh = self.prepare_refresh_token()
        return {
            "Content-type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {refresh.access_token}",
        }

    def kick_member(self, member):
        headers = self.prepare_headers()

        data = {
            "base_api_url": settings.BASE_API_URL,
            "username": member.username,
        }

        url = (
            f"{settings.AUTHORIZER_URL}/api/v1/internal/kick-member/"
            f"?space_code={settings.BASE_API_URL}"
        )

        _l.info(f"kick_member url={url} data={data}")

        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL
        )

        if response.status_code != 200:
            raise RuntimeError(f"Error kicking member {response.text}")

    def invite_member(self, member, from_user):
        headers = self.prepare_headers()

        data = {
            "base_api_url": settings.BASE_API_URL,
            "username": member.username,
            "is_admin": member.is_admin,
            "from_user_username": from_user.username,
        }

        url = (
            f"{settings.AUTHORIZER_URL}/api/v1/internal/invite-member/"
            f"?space_code={settings.BASE_API_URL}"
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

    def start_worker(self, worker):
        headers = self.prepare_headers()

        data = {
            "space_code": settings.BASE_API_URL,
            "worker_name": worker.worker_name,
        }

        url = (
            f"{settings.AUTHORIZER_URL}/api/v1/internal/start-worker/"
            f"?space_code={settings.BASE_API_URL}"
        )

        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL
        )

        if response.status_code != 200:
            raise RuntimeError(f"Error starting worker {response.text}")

    def stop_worker(self, worker):
        headers = self.prepare_headers()

        data = {
            "space_code": settings.BASE_API_URL,
            "worker_name": worker.worker_name,
        }

        url = (
            f"{settings.AUTHORIZER_URL}/api/v1/internal/stop-worker/"
            f"?space_code={settings.BASE_API_URL}"
        )

        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL
        )

        if response.status_code != 200:
            raise RuntimeError(f"Error stopping worker {response.text}")

    def restart_worker(self, worker):
        headers = self.prepare_headers()

        data = {
            "space_code": settings.BASE_API_URL,
            "worker_name": worker.worker_name,
        }

        url = (
            f"{settings.AUTHORIZER_URL}/api/v1/internal/restart-worker/"
            f"?space_code={settings.BASE_API_URL}"
        )

        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL
        )

        if response.status_code != 200:
            raise RuntimeError(f"Error restarting worker {response.text}")

    def delete_worker(self, worker):
        headers = self.prepare_headers()

        data = {
            "space_code": settings.BASE_API_URL,
            "worker_name": worker.worker_name,
        }

        url = (
            f"{settings.AUTHORIZER_URL}/api/v1/internal/delete-worker/"
            f"?space_code={settings.BASE_API_URL}"
        )

        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL
        )

        if response.status_code != 200:
            raise RuntimeError(f"Error restarting worker {response.text}")

    def get_worker_status(self, worker):
        headers = self.prepare_headers()

        url = (
            f"{settings.AUTHORIZER_URL}/api/v1/internal/worker-status/"
            f"?space_code={settings.BASE_API_URL}&worker_name={worker.worker_name}"
        )

        response = requests.get(url=url, headers=headers, verify=settings.VERIFY_SSL)

        if response.status_code != 200:
            raise RuntimeError(f"Error getting worker status {response.text}")

        return response.json()

    def create_worker(self, worker):
        headers = self.prepare_headers()

        data = {
            "space_code": settings.BASE_API_URL,
            "worker_name": worker.worker_name,
            "worker_type": worker.worker_type,
            "memory_limit": worker.memory_limit,
            "queue": worker.queue,
        }

        url = (
            f"{settings.AUTHORIZER_URL}/api/v1/internal/create-worker/"
            f"?space_code={settings.BASE_API_URL}"
        )

        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL
        )

        if response.status_code != 200:
            raise RuntimeError(f"Error creating worker {response.text}")
