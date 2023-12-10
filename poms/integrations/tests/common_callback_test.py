from poms.celery_tasks.models import CeleryTask


# noinspection PyUnresolvedReferences
class CallbackSetTestMixin:
    def create_task(self, name: str, func: str):
        return CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            verbose_name=name,
            function_name=func,
            type="import_from_database",
            status=CeleryTask.STATUS_PENDING,
            result="{}",
        )

    def post_and_check_response(self, post_data):
        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 400, response.content)
        response_json = response.json()
        self.assertIn("error", response_json)

    def test__no_request_id(self):
        post_data = {
            "data": {"data": "test"},
            "task_id": self.random_int(),
        }
        self.post_and_check_response(post_data)

    def test__invalid_request_id(self):
        post_data = {
            "request_id": self.random_int(),
            "data": {"data": "test"},
            "task_id": self.random_int(),
        }
        self.post_and_check_response(post_data)

    def test__no_data(self):
        post_data = {
            "request_id": self.random_int(),
            "task_id": self.random_int(),
        }
        self.post_and_check_response(post_data)

    def test__empty_data(self):
        post_data = {
            "request_id": self.random_int(),
            "data": [],
            "task_id": self.random_int(),
        }
        self.post_and_check_response(post_data)

    def test__no_task_id(self):
        post_data = {
            "request_id": self.random_int(),
            "data": [],
        }
        self.post_and_check_response(post_data)
