from poms.common.common_base_test import BaseTestCase

from poms.explorer.models import FinmarsDirectory


class FinmarsDirectoryTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

    def _create_directory(self) -> FinmarsDirectory:
        self.name = self.random_string(7)
        self.path = f"/{self.random_string()}/{self.random_string(5)}/{self.name}/"

        return FinmarsDirectory.objects.create(name=self.name, path=self.path)

    def test__directory_created(self):
        directory = self._create_directory()

        self.assertIsNotNone(directory)
        self.assertEqual(directory.name, self.name)
        self.assertEqual(directory.path, self.path.rstrip("/"))
        self.assertIsNone(directory.parent)
        self.assertIsNotNone(directory.created)
        self.assertIsNotNone(directory.modified)

    def test__unique_path_and_name(self):
        kwargs = dict(path="/test/")
        FinmarsDirectory.objects.create(**kwargs)

        with self.assertRaises(Exception):
            FinmarsDirectory.objects.create(**kwargs)

    @BaseTestCase.cases(
        ("0", "/a/b"),
        ("1", "/a/b/"),
        ("2", "/a/b//"),
        ("3", "a/b//"),
        ("4", "a/b"),
    )
    def test__directory_path(self, path):
        kwargs = dict(path=path)
        directory = FinmarsDirectory.objects.create(**kwargs)

        self.assertEqual(directory.fullpath, "/a/b")

    @BaseTestCase.cases(
        ("0", "/"),
        ("1", "//"),
        ("2", "///"),
    )
    def test__fix_directory_name(self, path):
        kwargs = dict(path=path)
        directory = FinmarsDirectory.objects.create(**kwargs)

        self.assertEqual(directory.fullpath, "/")
