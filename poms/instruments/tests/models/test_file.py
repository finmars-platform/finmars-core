from poms.common.common_base_test import BaseTestCase

from poms.instruments.models import Instrument, FinmarsFile


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

    @BaseTestCase.cases(
        ("name", "name", "&name.txt"),
        ("extension", "name", "name.pdf*"),
        ("size", "size", 0),
    )
    def test__validators(self, attr, value):
        kwargs = dict(
            name="name.pdf",
            path="/test/",
            size=self.random_int(10000),
        )
        kwargs[attr] = value

        with self.assertRaises(Exception):
            FinmarsFile.objects.create(**kwargs)

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
