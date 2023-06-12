from poms.celery_tasks.models import CeleryTask


# noinspection PyUnresolvedReferences
class CallbackSetTestMixin:
    def create_task(self, name: str, func: str):
        return CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            verbose_name=name,
            function_name=func,
            type="import",
            result_object={"task_id": self.random_int()},
            status=CeleryTask.STATUS_PENDING,
        )

    def test__no_request_id(self):
        post_data = {
            "data": [],
        }
        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["status"], "error")
        self.assertIn("message", response_json)

    def test__invalid_request_id(self):
        post_data = {
            "request_id": self.random_int(),
            "data": [],
        }
        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["status"], "error")
        self.assertIn("message", response_json)

    def test__no_data(self):
        post_data = {
            "request_id": self.random_int(),
        }
        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["status"], "error")
        self.assertIn("message", response_json)
