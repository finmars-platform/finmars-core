from poms.common.common_base_test import BaseTestCase

from poms.explorer.models import FinmarsFile
from poms.instruments.models import Instrument


class FinmarsFileTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

    def test__file_created(self):
        extension = self.random_string(3)
        name = f"{self.random_string()}.{extension}"
        path = (
            f"/{self.random_string()}/{self.random_string(5)}/{self.random_string(7)}/"
        )
        size = self.random_int()
        file = FinmarsFile.objects.create(name=name, path=path, size=size)

        self.assertIsNotNone(file)
        self.assertEqual(file.name, name)
        self.assertEqual(file.path, path)
        self.assertEqual(file.size, size)
        self.assertEqual(file.extension, extension)
        self.assertIsNotNone(file.created)
        self.assertIsNotNone(file.modified)

    def test__add_files_to_instrument(self):
        kwargs_1 = dict(
            name="name_1.pdf",
            path="/test/",
            size=self.random_int(1, 10000000),
        )
        file_1 = FinmarsFile.objects.create(**kwargs_1)

        kwargs_2 = dict(
            name="name_2.pdf",
            path="/test/",
            size=self.random_int(1, 10000000),
        )
        file_2 = FinmarsFile.objects.create(**kwargs_2)

        instrument = Instrument.objects.last()
        self.assertEqual(len(instrument.files.all()), 0)

        instrument.files.add(file_1, file_2)
        self.assertEqual(len(instrument.files.all()), 2)

    def test__unique_path_and_name(self):
        kwargs = dict(
            name="name.pdf",
            path="/test/",
            size=self.random_int(1, 10000000),
        )
        FinmarsFile.objects.create(**kwargs)

        kwargs["size"] = self.random_int(100000, 100000000)
        with self.assertRaises(Exception):
            FinmarsFile.objects.create(**kwargs)

    @BaseTestCase.cases(
        ("0", "/a/b"),
        ("1", "/a/b/"),
        ("2", "/a/b//"),
    )
    def test__filepath(self, path):
        kwargs = dict(
            name="name.pdf",
            path=path,
            size=self.random_int(10, 10000000),
        )
        file = FinmarsFile.objects.create(**kwargs)

        self.assertEqual(file.filepath, "/a/b/name.pdf")
