from poms.common.common_base_test import BaseTestCase


class ContentTypeViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/iam/content-types/"

    def test__list(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        from pprint import pprint

        pprint(response_json)

    def test__retrieve(self):

        response = self.client.get(f"{self.url}24/")

        self.assertEqual(response.status_code, 405, response.content)

    def test__destroy(self):
        response = self.client.delete(f"{self.url}1/")

        self.assertEqual(response.status_code, 405, response.content)

    def test__patch(self):
        response = self.client.patch(f"{self.url}1/", data={}, format="json")

        self.assertEqual(response.status_code, 405, response.content)

    def test__create(self):
        response = self.client.post(self.url, data={}, format="json")

        self.assertEqual(response.status_code, 405, response.content)
