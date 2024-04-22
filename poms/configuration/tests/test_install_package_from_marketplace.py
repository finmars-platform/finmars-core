from copy import deepcopy
from unittest import mock

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.configuration.tasks import install_package_from_marketplace
from poms.configuration.models import Configuration
from poms.configuration.tests.common_test_data import *


class InstallPackageFromMarketplaceTaskTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.mock_response = mock.Mock()
        self.mock_response.status_code = 200

    def create_celery_task(self) -> CeleryTask:
        celery_task = CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            verbose_name="Install Configuration From Marketplace",
            type="install_configuration_from_marketplace",
        )
        options_object = {
            "configuration_code": POST_PAYLOAD["configuration_code"],
            "version": POST_PAYLOAD["version"],
            "channel": POST_PAYLOAD["channel"],
            "is_package": POST_PAYLOAD["is_package"],
            "access_token": TOKEN,
        }
        celery_task.options_object = options_object
        celery_task.save()
        return celery_task

    @mock.patch("poms.configuration.tasks.requests.post")
    def test__check_dependencies_handling_http_error(self, requests_post):
        self.mock_response.status_code = 403
        self.mock_response.text = self.random_string()
        requests_post.return_value = self.mock_response

        all_tasks_before = CeleryTask.objects.all()
        self.assertEqual(all_tasks_before.count(), 0)

        celery_task = self.create_celery_task()

        with self.assertRaises(RuntimeError) as error:
            install_package_from_marketplace(task_id=celery_task.id)

        self.assertEqual(str(error.exception), self.mock_response.text)

        all_tasks_after = CeleryTask.objects.all()
        self.assertEqual(all_tasks_after.count(), 1)

    @mock.patch("poms.configuration.tasks.install_configuration_from_marketplace")
    @mock.patch("poms.configuration.tasks.requests.post")
    def test__check_dependencies_handling_no_http_error(
        self, requests_post, install_config
    ):
        self.mock_response.json.return_value = deepcopy(PACKAGE_RESPONSE_JSON)
        requests_post.return_value = self.mock_response

        all_tasks_before = CeleryTask.objects.all()
        self.assertEqual(all_tasks_before.count(), 0)

        main_task = self.create_celery_task()

        install_package_from_marketplace(task_id=main_task.id)

        all_tasks_after = CeleryTask.objects.all()
        self.assertEqual(all_tasks_after.count(), 3)

        self.assertEqual(install_config.call_count, 2)

        main_task.refresh_from_db()
        self.assertEqual(main_task.progress_object, EXPECTED_PROGRESS_OBJECT)

        conf = Configuration.objects.get(configuration_code=CONFIGURATION_CODE)
        self.assertEqual(
            conf.name, PACKAGE_RESPONSE_JSON["configuration_object"]["name"]
        )
        self.assertEqual(
            conf.description,
            PACKAGE_RESPONSE_JSON["configuration_object"]["description"],
        )
        self.assertEqual(conf.version, PACKAGE_RESPONSE_JSON["version"])
        self.assertEqual(conf.manifest, PACKAGE_RESPONSE_JSON["manifest"])
        self.assertTrue(conf.is_package)
        self.assertTrue(conf.is_from_marketplace)
