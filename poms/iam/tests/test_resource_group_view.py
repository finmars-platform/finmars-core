from poms.common.common_base_test import BaseTestCase
from poms.iam.models import ResourceGroup


class ResourceGroupViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/iam/resource-group/"

    def test__check_url(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test__list(self):
        ResourceGroup.objects.create(
            master_user=self.master_user,
            name="test",
            user_code="test",
            description="test",
        )
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertEqual(len(response_json), 1)
        group_data = response_json[0]
        self.assertEqual(group_data["name"], "test")
        self.assertEqual(group_data["user_code"], "test")
        self.assertEqual(group_data["description"], "test")
        self.assertEqual(group_data["master_user"], self.master_user.id)
        self.assertIn("created_at", group_data)
        self.assertIn("modified_at", group_data)
        self.assertIn("id", group_data)

    def test__retrieve(self):
        rg = ResourceGroup.objects.create(
            master_user=self.master_user,
            name="test2",
            user_code="test2",
            description="test2",
        )
        response = self.client.get(f"{self.url}{rg.id}/")

        self.assertEqual(response.status_code, 200, response.content)
        group_data = response.json()

        self.assertEqual(group_data["id"], rg.id)
        self.assertEqual(group_data["name"], "test2")
        self.assertEqual(group_data["user_code"], "test2")
        self.assertEqual(group_data["description"], "test2")
        self.assertEqual(group_data["master_user"], self.master_user.id)
        self.assertIn("created_at", group_data)
        self.assertIn("modified_at", group_data)

    def test__destroy(self):
        rg = ResourceGroup.objects.create(
            master_user=self.master_user,
            name="test2",
            user_code="test2",
            description="test2",
        )
        response = self.client.delete(f"{self.url}{rg.id}/")

        self.assertEqual(response.status_code, 204, response.content)
        group_data = response.json()

        self.assertEqual(group_data["id"], rg.id)
        self.assertEqual(group_data["name"], "test2")
        self.assertEqual(group_data["user_code"], "test2")
        self.assertEqual(group_data["description"], "test2")
        self.assertEqual(group_data["master_user"], self.master_user.id)
        self.assertIn("created_at", group_data)
        self.assertIn("modified_at", group_data)
