from django.contrib.contenttypes.models import ContentType

from poms.common.common_base_test import BaseTestCase
from poms.iam.models import ResourceGroup, ResourceGroupAssignment


class ResourceGroupViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/iam/resource-group/"

    def create_group(self, name: str = "test") -> ResourceGroup:
        return ResourceGroup.objects.create(
            name=name,
            user_code=name,
            description=name,
        )

    def test__check_url(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test__list(self):
        self.create_group()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertEqual(len(response_json), 1)
        group_data = response_json[0]
        self.assertEqual(group_data["name"], "test")
        self.assertEqual(group_data["user_code"], "test")
        self.assertEqual(group_data["description"], "test")
        self.assertEqual(group_data["assignments"], [])
        self.assertIn("created_at", group_data)
        self.assertIn("modified_at", group_data)
        self.assertIn("id", group_data)

    def test__retrieve(self):
        rg = self.create_group(name="test2")

        response = self.client.get(f"{self.url}{rg.id}/")

        self.assertEqual(response.status_code, 200, response.content)
        group_data = response.json()

        self.assertEqual(group_data["id"], rg.id)
        self.assertEqual(group_data["name"], "test2")
        self.assertEqual(group_data["user_code"], "test2")
        self.assertEqual(group_data["description"], "test2")
        self.assertEqual(group_data["assignments"], [])
        self.assertIn("created_at", group_data)
        self.assertIn("modified_at", group_data)

    def test__destroy(self):
        rg = self.create_group(name="test2")

        response = self.client.delete(f"{self.url}{rg.id}/")

        self.assertEqual(response.status_code, 204, response.content)

    def test__patch(self):
        rg = self.create_group(name="test2")

        response = self.client.patch(
            f"{self.url}{rg.id}/", data={"name": "test3"}, format="json"
        )
        group_data = response.json()

        self.assertEqual(group_data["name"], "test3")

        self.assertEqual(response.status_code, 200, response.content)

    def test__assignment(self):
        rg = self.create_group(name="test2")
        ass = ResourceGroupAssignment.objects.create(
            resource_group=rg,
            content_type=ContentType.objects.get_for_model(rg),
            object_id=rg.id,
            object_user_code="test4",
        )
        self.assertEqual(ass.content_object, rg)

        response = self.client.get(f"{self.url}{rg.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        group_data = response.json()
        self.assertEqual(len(group_data["assignments"]), 1)
        ass_data = group_data["assignments"][0]
        self.assertEqual(ass_data["object_user_code"], ass.object_user_code)
        self.assertEqual(ass_data["content_type"], 24)
        self.assertEqual(ass_data["object_id"], rg.id)

    def test__create(self):
        group_data = dict(
            name="test9",
            user_code="test9",
            description="test9",
        )
        response = self.client.post(self.url, data=group_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        group_data = response.json()
        self.assertEqual(group_data["name"], "test9")
        self.assertEqual(group_data["user_code"], "test9")
        self.assertEqual(group_data["description"], "test9")
        self.assertEqual(group_data["assignments"], [])
        self.assertIn("id", group_data)
        self.assertIn("created_at", group_data)
        self.assertIn("modified_at", group_data)
