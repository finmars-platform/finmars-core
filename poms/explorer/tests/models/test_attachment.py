from poms.common.common_base_test import BaseTestCase

from poms.explorer.models import StorageObject
from poms.instruments.models import Instrument


class FinmarsFileTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

    def test__file_created(self):
        extension = self.random_string(3)
        name = f"{self.random_string()}.{extension}"
        path = f"/{self.random_string()}/{self.random_string(7)}/{name}"
        size = self.random_int()
        file = StorageObject.objects.create(path=path, size=size, is_file=True)

        self.assertIsNotNone(file)
        self.assertEqual(file.name, name)
        self.assertEqual(file.path, path.rstrip("/"))
        self.assertEqual(file.size, size)
        self.assertEqual(file.extension, f".{extension}")
        self.assertIsNotNone(file.created_at)
        self.assertIsNotNone(file.modified_at)

    def test__add_files_to_instrument(self):
        kwargs_1 = dict(
            path="/test/name_1.pdf",
            size=self.random_int(1, 10000000),
            is_file=True,
        )
        file_1 = StorageObject.objects.create(**kwargs_1)

        kwargs_2 = dict(
            path="/test/name_2.pdf",
            size=self.random_int(1, 10000000),
            is_file=True,
        )
        file_2 = StorageObject.objects.create(**kwargs_2)

        instrument = Instrument.objects.last()
        self.assertEqual(len(instrument.files.all()), 0)

        instrument.files.add(file_1, file_2)
        self.assertEqual(len(instrument.files.all()), 2)

    def test__unique_path_and_name(self):
        kwargs = dict(path="/test/name.pdf", size=1, is_file=True)
        StorageObject.objects.create(**kwargs)

        kwargs["size"] = 2
        with self.assertRaises(Exception):
            StorageObject.objects.create(**kwargs)
