from poms.common.common_base_test import BaseTestCase

from poms.explorer.models import FinmarsDirectory, ROOT_PATH


class FinmarsDirectoryTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

    def _create_directory(self) -> FinmarsDirectory:
        self.path = f"/{self.random_string()}/{self.random_string(5)}/*"

        return FinmarsDirectory.objects.create(path=self.path)

    def test__directory_created(self):
        directory = self._create_directory()

        self.assertIsNotNone(directory)
        self.assertEqual(directory.path, self.path)
        self.assertIsNone(directory.parent)
        self.assertIsNotNone(directory.created_at)
        self.assertIsNotNone(directory.modified_at)
        self.assertEqual(directory.size, 0)
        self.assertEqual(directory.extension, "")

    @BaseTestCase.cases(
        ("0", "/test/*"),
        ("2", "/test/path/*"),
        ("3", "/test/path/more/*"),
    )
    def test__unique_path(self, path):
        kwargs = dict(path=path)
        FinmarsDirectory.objects.create(**kwargs)

        with self.assertRaises(Exception):
            FinmarsDirectory.objects.create(**kwargs)

    def test__directory_tree(self):
        kwargs = dict(path=ROOT_PATH)
        root = FinmarsDirectory.objects.create(**kwargs)

        kwargs = dict(path=f"/path_1/*")
        dir_1 = FinmarsDirectory.objects.create(parent=root, **kwargs)

        kwargs = dict(path=f"/path_2/*")
        dir_2 = FinmarsDirectory.objects.create(parent=root, **kwargs)

        kwargs = dict(path=f"/path_1/path_3/*")
        dir_3 = FinmarsDirectory.objects.create(parent=dir_1, **kwargs)

        kwargs = dict(path=f"/path_4/*")
        dir_4 = FinmarsDirectory.objects.create(parent=root, **kwargs)

        self.assertEqual(dir_1.get_root(), root)
        self.assertEqual(dir_2.get_root(), root)
        self.assertEqual(dir_3.get_root(), root)

        self.assertEqual(root.children.count(), 3)
        self.assertEqual(dir_1.children.count(), 1)
        self.assertEqual(dir_2.children.count(), 0)
        self.assertEqual(dir_3.children.count(), 0)
        self.assertEqual(dir_4.children.count(), 0)

        self.assertTrue(root.is_root_node())
        self.assertTrue(dir_2.is_leaf_node())
        self.assertTrue(dir_3.is_leaf_node())
        self.assertTrue(dir_4.is_leaf_node())

        self.assertEqual(root.get_siblings().count(), 0)
        self.assertEqual(dir_1.get_siblings().count(), 2)
        self.assertEqual(dir_2.get_siblings().count(), 2)
        self.assertEqual(dir_4.get_siblings().count(), 2)
        self.assertEqual(dir_3.get_siblings().count(), 0)

        self.assertEqual(root.get_descendant_count(), 4)
        self.assertEqual(dir_1.get_descendants().count(), 1)

        self.assertEqual(dir_3.get_family().count(), 3)  # ancestors, itself, descendants
