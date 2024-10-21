from django.contrib.contenttypes.models import ContentType

from poms.common.common_base_test import BaseTestCase
from poms.iam.models import ResourceGroup, ResourceGroupAssignment


class ResourceGroupAssignmentViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        url_prefix = f"/{self.realm_code}/{self.space_code}/api/v1/iam/"
        self.url = f"{url_prefix}resource-group-assignment/"

    def create_group(self, name: str = "test") -> ResourceGroup:
        return ResourceGroup.objects.create(
            name=name,
            user_code=name,
            description=name,
        )

    def create_assignment(
        self,
        group_name: str = "test",
        model_name: str = "unknown",
        object_id: int = -1,
    ) -> ResourceGroupAssignment:
        resource_group = ResourceGroup.objects.get(name=group_name)
        content_type = ContentType.objects.get_by_natural_key(
            app_label="iam", model=model_name.lower()
        )
        self.assertIsNotNone(content_type)
        model = content_type.model_class()
        model_object = model.objects.get(id=object_id)
        return ResourceGroupAssignment.objects.create(
            resource_group=resource_group,
            content_type=content_type,
            object_id=object_id,
            object_user_code=model_object.user_code,
        )

    def test__check_url(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test__list(self):
        rg = self.create_group(name="test7")
        ass = self.create_assignment(
            group_name="test7", model_name="ResourceGroup", object_id=rg.id
        )
        self.assertEqual(
            str(ass),
            f"{rg.name} assigned to {ass.content_object}:{ass.object_user_code}",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertEqual(len(response_json["results"]), 1)
        ass_data = response_json["results"][0]
        self.assertEqual(ass_data["id"], ass.id)
        self.assertEqual(ass_data["resource_group"], rg.id)
        self.assertEqual(ass_data["object_user_code"], "test7")
        self.assertEqual(ass_data["content_type"], 24)

    def test__retrieve(self):
        rg = self.create_group(name="test7")
        ass = self.create_assignment(
            group_name="test7", model_name="ResourceGroup", object_id=rg.id
        )
        self.assertEqual(
            str(ass),
            f"{rg.name} assigned to {ass.content_object}:{ass.object_user_code}",
        )

        response = self.client.get(f"{self.url}{ass.id}/")

        self.assertEqual(response.status_code, 200, response.content)
        ass_data = response.json()

        self.assertEqual(ass_data["id"], ass.id)
        self.assertEqual(ass_data["resource_group"], rg.id)
        self.assertEqual(ass_data["object_user_code"], "test7")
        self.assertEqual(ass_data["content_type"], 24)

    def test__destroy(self):
        rg = self.create_group(name="test7")
        ass = self.create_assignment(
            group_name="test7", model_name="ResourceGroup", object_id=rg.id
        )
        response = self.client.delete(f"{self.url}{ass.id}/")

        self.assertEqual(response.status_code, 204, response.content)

    def test__patch(self):
        rg = self.create_group(name="test7")
        ass = self.create_assignment(
            group_name="test7", model_name="ResourceGroup", object_id=rg.id
        )
        response = self.client.patch(
            f"{self.url}{ass.id}/", data={"object_user_code": "test11"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)

        ass_data = response.json()
        self.assertEqual(ass_data["object_user_code"], "test11")

    def test__create(self):
        rg = self.create_group(name="test11")
        content_type = ContentType.objects.get_by_natural_key(
            app_label="iam", model="resourcegroup"
        )
        ass_data = dict(
            resource_group=rg.id,
            content_type=content_type.id,
            object_id=rg.id,
            object_user_code="test11",
        )
        response = self.client.post(self.url, data=ass_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        ass_data = response.json()
        self.assertEqual(ass_data["resource_group"], rg.id)
        self.assertEqual(ass_data["object_user_code"], "test11")
        self.assertEqual(ass_data["content_type"], 24)
