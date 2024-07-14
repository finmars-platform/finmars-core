from poms.common.common_base_test import BaseTestCase

from poms.explorer.models import FinmarsDirectory
from poms.instruments.models import Instrument


class FinmarsDirectoryTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

    def test__directory_created(self):
        extension = self.random_string(3)
        name = f"{self.random_string()}.{extension}"
        path = (
            f"/{self.random_string()}/{self.random_string(5)}/{self.random_string(7)}/"
        )
        size = self.random_int()
        directory = FinmarsDirectory.objects.create(name=name, path=path, size=size)

        self.assertIsNotNone(directory)
        self.assertEqual(directory.name, name)
        self.assertEqual(directory.path, path)
        self.assertEqual(directory.size, size)
        self.assertEqual(directory.extension, extension)
        self.assertIsNotNone(directory.created)
        self.assertIsNotNone(directory.modified)

    def test__add_directorys_to_instrument(self):
        kwargs_1 = dict(
            name="name_1.pdf",
            path="/test/",
            size=self.random_int(1, 10000000),
        )
        directory_1 = FinmarsDirectory.objects.create(**kwargs_1)

        kwargs_2 = dict(
            name="name_2.pdf",
            path="/test/",
            size=self.random_int(1, 10000000),
        )
        directory_2 = FinmarsDirectory.objects.create(**kwargs_2)

        instrument = Instrument.objects.last()
        self.assertEqual(len(instrument.directorys.all()), 0)

        instrument.directorys.add(directory_1, directory_2)
        self.assertEqual(len(instrument.directorys.all()), 2)

    def test__unique_path_and_name(self):
        kwargs = dict(
            name="name.pdf",
            path="/test/",
            size=self.random_int(1, 10000000),
        )
        FinmarsDirectory.objects.create(**kwargs)

        kwargs["size"] = self.random_int(100000, 100000000)
        with self.assertRaises(Exception):
            FinmarsDirectory.objects.create(**kwargs)

    @BaseTestCase.cases(
        ("0", "/a/b"),
        ("1", "/a/b/"),
        ("2", "/a/b//"),
    )
    def test__directorypath(self, path):
        kwargs = dict(
            name="name.pdf",
            path=path,
            size=self.random_int(10, 10000000),
        )
        directory = FinmarsDirectory.objects.create(**kwargs)

        self.assertEqual(directory.fullpath, "/a/b/name.pdf")
