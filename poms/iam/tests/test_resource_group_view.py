from django.contrib.contenttypes.models import ContentType

from poms.common.common_base_test import BaseTestCase
from poms.iam.models import ResourceGroup, ResourceGroupAssignment
from poms.users.models import Member


class ResourceGroupViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/iam/resource-group/"

    @staticmethod
    def create_group(name: str = "test") -> ResourceGroup:
        return ResourceGroup.objects.create(
            name=name,
            user_code=name,
            description=name,
            configuration_code=name,
            owner=Member.objects.all().first(),
        )

    def test__check_url(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test__list(self):
        self.create_group()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertEqual(len(response_json["results"]), 1)
        group_data = response_json["results"][0]
        self.assertEqual(group_data["name"], "test")
        self.assertEqual(group_data["user_code"], "test")
        self.assertEqual(group_data["description"], "test")
        self.assertEqual(group_data["assignments"], [])
        self.assertEqual(group_data["members"], [])
        self.assertEqual(group_data["configuration_code"], "test")
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
        self.assertEqual(group_data["configuration_code"], "test2")
        self.assertEqual(group_data["members"], [])
        self.assertIn("created_at", group_data)
        self.assertIn("modified_at", group_data)

    def test__destroy(self):
        rg = self.create_group(name="test2")

        response = self.client.delete(f"{self.url}{rg.id}/")

        self.assertEqual(response.status_code, 204, response.content)

    def test__patch(self):
        rg = self.create_group(name="test2")

        response = self.client.patch(
            f"{self.url}{rg.id}/",
            data={"name": "test3", "members": [self.member.pk]},
            format="json",
        )
        group_data = response.json()

        self.assertEqual(group_data["name"], "test3")
        self.assertEqual(group_data["members"], [self.member.pk])

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
            configuration_code="test9",
            owner=1,
        )
        response = self.client.post(self.url, data=group_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        group_data = response.json()
        self.assertEqual(group_data["name"], "test9")
        self.assertEqual(group_data["user_code"], "test9")
        self.assertEqual(group_data["description"], "test9")
        self.assertEqual(group_data["assignments"], [])
        self.assertEqual(group_data["members"], [])
        self.assertEqual(group_data["configuration_code"], "test9")
        self.assertIn("id", group_data)
        self.assertIn("created_at", group_data)
        self.assertIn("modified_at", group_data)

    def test__create_and_try_add_assignments(self):
        rg = self.create_group(name="test2")
        group_data = dict(
            name="test10",
            user_code="test10",
            description="test10",
            configuration_code="test10",
            owner=1,
        )
        response = self.client.post(self.url, data=group_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        group_data = response.json()
        self.assertIn("id", group_data)
        new_group_id = group_data["id"]
        self.assertEqual(group_data["name"], "test10")
        self.assertEqual(group_data["user_code"], "test10")
        self.assertEqual(group_data["description"], "test10")
        self.assertEqual(group_data["configuration_code"], "test10")

        # add assignment to the new resource group
        content_type_id = ContentType.objects.get_for_model(rg).id
        update_data = {
            "assignments": [
                dict(
                    object_user_code=rg.user_code,
                    content_type=content_type_id,
                    object_id=rg.id,
                )
            ]
        }
        response = self.client.patch(
            f"{self.url}{new_group_id}/", data=update_data, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)

        group_data = response.json()
        self.assertEqual(group_data["assignments"], [])  # no new assignments

    def test__remove_assignments_patch(self):
        rg = self.create_group(name="test2")
        ass = ResourceGroupAssignment.objects.create(
            resource_group=rg,
            content_type=ContentType.objects.get_for_model(rg),
            object_id=rg.id,
            object_user_code="test2",
        )
        self.assertEqual(ass.content_object, rg)

        response = self.client.get(f"{self.url}{rg.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        group_data = response.json()

        self.assertEqual(group_data["id"], rg.id)
        self.assertEqual(group_data["name"], rg.name)
        self.assertEqual(group_data["user_code"], rg.user_code)
        self.assertEqual(group_data["description"], rg.description)
        self.assertEqual(len(group_data["assignments"]), 1)
        self.assertEqual(group_data["configuration_code"], rg.configuration_code)

        # remove assignment
        update_data = {"assignments": []}
        response = self.client.patch(
            f"{self.url}{rg.id}/", data=update_data, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        updated_group_data = response.json()

        new = ResourceGroupAssignment.objects.filter(resource_group_id=rg.id).first()
        self.assertIsNone(new)

        self.assertEqual(len(updated_group_data["assignments"]), 0)

    def test__remove_assignments_put(self):
        rg = self.create_group(name="test3")
        ass = ResourceGroupAssignment.objects.create(
            resource_group=rg,
            content_type=ContentType.objects.get_for_model(rg),
            object_id=rg.id,
            object_user_code="test3",
        )
        self.assertEqual(ass.content_object, rg)

        response = self.client.get(f"{self.url}{rg.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        group_data = response.json()

        self.assertEqual(group_data["id"], rg.id)
        self.assertEqual(group_data["name"], rg.name)
        self.assertEqual(group_data["user_code"], rg.user_code)
        self.assertEqual(group_data["description"], rg.description)
        self.assertEqual(len(group_data["assignments"]), 1)
        self.assertEqual(group_data["configuration_code"], rg.configuration_code)

        # remove assignment
        update_data = group_data.copy()
        update_data["assignments"] = []
        response = self.client.put(
            f"{self.url}{rg.id}/", data=update_data, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        updated_group_data = response.json()

        new = ResourceGroupAssignment.objects.filter(resource_group_id=rg.id).first()
        self.assertIsNone(new)

        self.assertEqual(len(updated_group_data["assignments"]), 0)

    def test__no_changes_put(self):
        rg = self.create_group(name="test4")
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

        self.assertEqual(group_data["id"], rg.id)
        self.assertEqual(group_data["name"], rg.name)
        self.assertEqual(group_data["user_code"], rg.user_code)
        self.assertEqual(group_data["description"], rg.description)
        self.assertEqual(len(group_data["assignments"]), 1)
        self.assertEqual(group_data["configuration_code"], rg.configuration_code)

        response = self.client.put(
            f"{self.url}{rg.id}/", data=group_data, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        updated_group_data = response.json()

        ra = ResourceGroupAssignment.objects.filter(resource_group_id=rg.id).first()
        self.assertIsNotNone(ra)

        self.assertEqual(len(updated_group_data["assignments"]), 1)

    def test__remove_assignments_patch_no_change(self):
        rg = self.create_group(name="test2")
        ass = ResourceGroupAssignment.objects.create(
            resource_group=rg,
            content_type=ContentType.objects.get_for_model(rg),
            object_id=rg.id,
            object_user_code="test2",
        )
        self.assertEqual(ass.content_object, rg)

        response = self.client.get(f"{self.url}{rg.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        group_data = response.json()

        self.assertEqual(group_data["id"], rg.id)
        self.assertEqual(group_data["name"], rg.name)
        self.assertEqual(group_data["user_code"], rg.user_code)
        self.assertEqual(group_data["description"], rg.description)
        self.assertEqual(len(group_data["assignments"]), 1)
        self.assertEqual(group_data["configuration_code"], rg.configuration_code)

        response = self.client.patch(
            f"{self.url}{rg.id}/", data=group_data, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        updated_group_data = response.json()

        new = ResourceGroupAssignment.objects.filter(resource_group_id=rg.id).first()
        self.assertIsNotNone(new)

        self.assertEqual(len(updated_group_data["assignments"]), 1)
