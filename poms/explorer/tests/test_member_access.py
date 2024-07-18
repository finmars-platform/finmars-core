from poms.common.common_base_test import BaseTestCase
from poms.explorer.models import AccessLevel, FinmarsDirectory, FinmarsFile
from poms.explorer.policy_handlers import (
    get_or_create_storage_access_policy,
    member_has_access,
)


class MemberHasAccessTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.file = self._create_file()
        self.dir = self._create_directory()

    def _create_file(self) -> FinmarsFile:
        extension = self.random_string(3)
        name = f"{self.random_string()}.{extension}"
        path = f"/{self.random_string()}/{self.random_string(5)}/{name}/"
        size = self.random_int()
        return FinmarsFile.objects.create(path=path, size=size)

    def _create_directory(self) -> FinmarsDirectory:
        path = f"/{self.random_string()}/{self.random_string(3)}"
        return FinmarsDirectory.objects.create(path=path, parent=None)

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("full", AccessLevel.FULL),
    )
    def test__access_to_file(self, access):
        get_or_create_storage_access_policy(self.file, self.member, access)
        self.assertTrue(member_has_access(self.file, self.member, access))

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("full", AccessLevel.FULL),
    )
    def test__access_to_dir(self, access):
        get_or_create_storage_access_policy(self.dir, self.member, access)
        self.assertTrue(member_has_access(self.dir, self.member, access))
