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
        path = f"/{self.random_string()}/{self.random_string(5)}/{self.random_string(7)}/"
        size = self.random_int()
        file = FinmarsFile.objects.create(
            name=name,
            path=path,
            size=size
        )

        self.assertIsNotNone(file)
        self.assertEqual(file.name, name)
        self.assertEqual(file.path, path)
        self.assertEqual(file.size, size)
        self.assertEqual(file.extension, extension)
        self.assertIsNotNone(file.created)
        self.assertIsNotNone(file.modified)
