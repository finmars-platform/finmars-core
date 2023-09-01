from unittest import mock

from django.conf import settings

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.configuration.tests.common_test_data import *

GET_RESPONSE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {
            "id": 1,
            "configuration_code": "local.poms.space00000",
            "name": "Local Configuration",
            "short_name": None,
            "description": "Local Configuration",
            "version": "1.0.0",
            "is_from_marketplace": False,
            "is_package": False,
            "manifest": None,
            "is_primary": True,
        }
    ],
}


class ConfigurationViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/configuration/configuration/"

    def test__get_200(self):
        response = self.client.get(path=self.url, data={})
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json, GET_RESPONSE)

    @mock.patch("poms.configuration.views.get_access_token")
    def test__install_configuration_from_marketplace(self, get_access_token):
        get_access_token.return_value = TOKEN

        response = self.client.post(
            path=f"{self.url}install-configuration-from-marketplace/",
            format="json",
            data=POST_PAYLOAD,
        )
        self.assertEqual(response.status_code, 200, response.content)
        get_access_token.assert_called_once()

        response_json = response.json()

        self.assertIn("task_id", response_json)

        task = CeleryTask.objects.get(id=response_json["task_id"])

        self.assertEqual(task.type, "install_configuration_from_marketplace")

        self.assertEqual(task.options_object, OPTIONS)
