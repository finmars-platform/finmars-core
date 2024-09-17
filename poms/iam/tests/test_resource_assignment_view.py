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
            master_user=self.master_user,
            name=name,
            user_code=name,
            description=name,
        )

    @staticmethod
    def create_assignment(
        group_name: str = "test",
        model_name: str = "unknown",
        object_id: int = -1,
    ) -> ResourceGroupAssignment:
        resource_group = ResourceGroup.objects.get(name=group_name)
        content_type = ContentType.objects.get_by_natural_key(
            app_label="iam", model=model_name.lower()
        )
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

        self.assertEqual(len(response_json), 1)
        ass_data = response_json[0]
        self.assertEqual(ass_data["id"], ass.id)
        self.assertEqual(ass_data["resource_group"], rg.id)
        self.assertEqual(ass_data["object_user_code"], "test7")
        self.assertEqual(ass_data["content_type"], "iam | resource group")
        self.assertEqual(ass_data["content_object"], "test7")
        self.assertIn("created_at", ass_data)
        self.assertIn("modified_at", ass_data)

    # def test__retrieve(self):
    #     rg = ResourceGroup.objects.create(
    #         master_user=self.master_user,
    #         name="test2",
    #         object_user_code="test2",
    #         description="test2",
    #     )
    #     response = self.client.get(f"{self.url}{rg.id}/")
    #
    #     self.assertEqual(response.status_code, 200, response.content)
    #     group_data = response.json()
    #
    #     self.assertEqual(group_data["id"], rg.id)
    #     self.assertEqual(group_data["name"], "test2")
    #     self.assertEqual(group_data["object_user_code"], "test2")
    #     self.assertEqual(group_data["description"], "test2")
    #     self.assertEqual(group_data["master_user"], self.master_user.id)
    #     self.assertEqual(group_data["assignments"], [])
    #     self.assertIn("created_at", group_data)
    #     self.assertIn("modified_at", group_data)
    #
    # def test__destroy(self):
    #     rg = ResourceGroup.objects.create(
    #         master_user=self.master_user,
    #         name="test2",
    #         object_user_code="test2",
    #         description="test2",
    #     )
    #     response = self.client.delete(f"{self.url}{rg.id}/")
    #
    #     self.assertEqual(response.status_code, 204, response.content)
    #
    # def test__destroy_no_permission(self):
    #     rg = ResourceGroup.objects.create(
    #         master_user=self.master_user,
    #         name="test2",
    #         object_user_code="test2",
    #         description="test2",
    #     )
    #     self.user.is_staff = False
    #     self.user.is_superuser = False
    #     self.user.save()
    #
    #     response = self.client.delete(f"{self.url}{rg.id}/")
    #
    #     self.assertEqual(response.status_code, 403, response.content)
    #
    # def test__patch(self):
    #     rg = ResourceGroup.objects.create(
    #         master_user=self.master_user,
    #         name="test2",
    #         object_user_code="test2",
    #         description="test2",
    #     )
    #     response = self.client.patch(
    #         f"{self.url}{rg.id}/", data={"name": "test3"}, format="json"
    #     )
    #     group_data = response.json()
    #
    #     self.assertEqual(group_data["name"], "test3")
    #
    #     self.assertEqual(response.status_code, 200, response.content)
    #
    # def test__patch_no_permission(self):
    #     rg = ResourceGroup.objects.create(
    #         master_user=self.master_user,
    #         name="test2",
    #         object_user_code="test2",
    #         description="test2",
    #     )
    #     self.user.is_staff = False
    #     self.user.is_superuser = False
    #     self.user.save()
    #
    #     response = self.client.patch(
    #         f"{self.url}{rg.id}/", data={"name": "test3"}, format="json"
    #     )
    #
    #     self.assertEqual(response.status_code, 403, response.content)
    #
    # def test__assignment(self):
    #     rg = ResourceGroup.objects.create(
    #         master_user=self.master_user,
    #         name="test2",
    #         object_user_code="test2",
    #         description="test2",
    #     )
    #     ass = ResourceGroupAssignment.objects.create(
    #         resource_group=rg,
    #         content_type=ContentType.objects.get_for_model(rg),
    #         object_id=rg.id,
    #         object_user_code="test4",
    #     )
    #     self.assertEqual(ass.content_object, rg)
    #
    #     response = self.client.get(f"{self.url}{rg.id}/")
    #     self.assertEqual(response.status_code, 200, response.content)
    #
    #     group_data = response.json()
    #     self.assertEqual(len(group_data["assignments"]), 1)
    #     ass_data = group_data["assignments"][0]
    #     self.assertEqual(ass_data["object_user_code"], ass.object_user_code)
    #     self.assertEqual(ass_data["content_type"], "iam | resource group")
    #     self.assertEqual(ass_data["object_id"], rg.id)
    #     self.assertEqual(ass_data["content_object"], str(rg))
    #     self.assertIn("created_at", ass_data)
    #     self.assertIn("modified_at", ass_data)
