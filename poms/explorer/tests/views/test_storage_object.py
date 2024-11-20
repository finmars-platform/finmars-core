from poms.common.common_base_test import BaseTestCase
from poms.explorer.models import DIR_SUFFIX, StorageObject
from poms.iam.models import ResourceGroup


class StorageObjectResourceGroupViewTest(BaseTestCase):
    databases = "__all__"
    maxDiff = None

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = (
            f"/{self.realm_code}/{self.space_code}/api/v1/explorer/storage-object/"
        )
        self.dirpath = f"/test/next{DIR_SUFFIX}"
        self.filepath = "/test/next/test.pdf"
        self.directory = StorageObject.objects.create(path=self.dirpath)
        self.file = StorageObject.objects.create(
            path=self.filepath, size=111, is_file=True
        )

    @staticmethod
    def create_group(name: str = "test") -> ResourceGroup:
        return ResourceGroup.objects.create(
            name=name,
            user_code=name,
            description=name,
        )

    def test__list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertEqual(response_json["count"], 2)
        self.assertEqual(len(response_json["results"]), 2)

    def test__add_resource_group(self):
        rg_name = self.random_string()
        rg = self.create_group(name=rg_name)
        patch_data = {"resource_groups": [rg_name]}
        response = self.client.patch(
            f"{self.url}{self.file.id}/", data=patch_data, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)

        so_data = response.json()
        self.assertIn("resource_groups", so_data)
        self.assertEqual(so_data["resource_groups"], [rg.name])

    def test_update_resource_groups(self):
        name_1 = self.random_string()
        self.create_group(name=name_1)
        name_2 = self.random_string()
        self.create_group(name=name_2)
        name_3 = self.random_string()
        self.create_group(name=name_3)

        response = self.client.patch(
            f"{self.url}{self.directory.id}/",
            data={"resource_groups": [name_1, name_2, name_3]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        directory_data = response.json()
        self.assertEqual(len(directory_data["resource_groups"]), 3)
        self.assertEqual(len(directory_data["resource_groups_object"]), 3)

        response = self.client.patch(
            f"{self.url}{self.directory.id}/",
            data={"resource_groups": [name_2]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        directory_data = response.json()
        self.assertEqual(len(directory_data["resource_groups"]), 1)
        self.assertEqual(directory_data["resource_groups"], [name_2])

        self.assertEqual(len(directory_data["resource_groups_object"]), 1)

    def test_remove_resource_groups(self):
        name_1 = self.random_string()
        self.create_group(name=name_1)
        name_3 = self.random_string()
        self.create_group(name=name_3)

        response = self.client.patch(
            f"{self.url}{self.file.id}/",
            data={"resource_groups": [name_1, name_3]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        file_data = response.json()
        self.assertEqual(len(file_data["resource_groups"]), 2)
        self.assertEqual(len(file_data["resource_groups_object"]), 2)

        response = self.client.patch(
            f"{self.url}{self.file.id}/",
            data={"resource_groups": []},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        file_data = response.json()
        self.assertEqual(len(file_data["resource_groups"]), 0)
        self.assertEqual(file_data["resource_groups"], [])

        self.assertEqual(len(file_data["resource_groups_object"]), 0)
        self.assertEqual(file_data["resource_groups_object"], [])

    def test_destroy_assignments(self):
        name_1 = self.random_string()
        rg_1 = self.create_group(name=name_1)
        name_3 = self.random_string()
        rg_3 = self.create_group(name=name_3)

        response = self.client.patch(
            f"{self.url}{self.directory.id}/",
            data={"resource_groups": [name_1, name_3]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        directory_data = response.json()
        self.assertEqual(len(directory_data["resource_groups"]), 2)
        self.assertEqual(len(directory_data["resource_groups_object"]), 2)

        url = f"/{self.realm_code}/{self.space_code}/api/v1/iam/resource-group/"
        response = self.client.delete(f"{url}{rg_1.id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.delete(f"{url}{rg_3.id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(f"{self.url}{self.directory.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        directory_data = response.json()
        self.assertEqual(len(directory_data["resource_groups"]), 0)
        self.assertEqual(directory_data["resource_groups"], [])
