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

    def _create_file(self, parent: FinmarsDirectory = None) -> FinmarsFile:
        extension = self.random_string(3)
        name = f"{self.random_string()}.{extension}"
        path = f"/{self.random_string()}/{self.random_string(5)}/{name}/"
        size = self.random_int()
        return FinmarsFile.objects.create(path=path, size=size, parent=parent)

    def _create_directory(self, parent: FinmarsDirectory = None) -> FinmarsDirectory:
        path = f"/{self.random_string()}/{self.random_string(3)}"
        return FinmarsDirectory.objects.create(path=path, parent=parent)

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__access_to_file(self, access):
        get_or_create_storage_access_policy(self.file, self.member, access)
        self.assertTrue(member_has_access(self.file, self.member, access))

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__access_to_dir(self, access):
        get_or_create_storage_access_policy(self.dir, self.member, access)
        self.assertTrue(member_has_access(self.dir, self.member, access))

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__access_to_dir(self, access):
        get_or_create_storage_access_policy(self.dir, self.member, access)
        self.assertTrue(member_has_access(self.dir, self.member, access))

    def create_dir_tree(self):
        kwargs = dict(path="/root")
        self.root = FinmarsDirectory.objects.create(**kwargs)

        kwargs = dict(path=f"/root/path_1")
        self.dir_1 = FinmarsDirectory.objects.create(parent=self.root, **kwargs)

        kwargs = dict(path=f"/root/path_2")
        self.dir_2 = FinmarsDirectory.objects.create(parent=self.root, **kwargs)

        kwargs = dict(path=f"/root/path_1/path_3")
        self.dir_3 = FinmarsDirectory.objects.create(parent=self.dir_1, **kwargs)

        kwargs = dict(path=f"/root/path_4")
        self.dir_4 = FinmarsDirectory.objects.create(parent=self.root, **kwargs)

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__tree_access_to_dir(self, access):
        self.create_dir_tree()
        get_or_create_storage_access_policy(self.root, self.member, access)

        self.assertTrue(member_has_access(self.dir_4, self.member, access))

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__tree_access_by_root_level_dir_4(self, access):
        self.create_dir_tree()
        get_or_create_storage_access_policy(self.root, self.member, access)

        self.assertTrue(member_has_access(self.dir_3, self.member, access))

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__tree_access_by_root_level_dir_2(self, access):
        self.create_dir_tree()
        get_or_create_storage_access_policy(self.root, self.member, access)

        self.assertTrue(member_has_access(self.dir_3, self.member, access))

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__tree_access_by_root_dir_3(self, access):
        self.create_dir_tree()
        get_or_create_storage_access_policy(self.root, self.member, access)

        self.assertTrue(member_has_access(self.dir_3, self.member, access))

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__tree_access_by_dir1_dir3(self, access):
        self.create_dir_tree()
        get_or_create_storage_access_policy(self.dir_1, self.member, access)

        self.assertTrue(member_has_access(self.dir_3, self.member, access))

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__tree_no_access_by_dir2_to_dir3(self, access):
        self.create_dir_tree()
        get_or_create_storage_access_policy(self.dir_2, self.member, access)

        self.assertFalse(member_has_access(self.dir_3, self.member, access))

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__tree_access_to_file(self, access):
        self.create_dir_tree()
        get_or_create_storage_access_policy(self.root, self.member, access)

        file = self._create_file(parent=self.root)
        self.assertTrue(member_has_access(file, self.member, access))

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__tree_access_to_file_by_root_level_dir_3(self, access):
        self.create_dir_tree()
        get_or_create_storage_access_policy(self.root, self.member, access)

        file = self._create_file(parent=self.dir_3)
        self.assertTrue(member_has_access(file, self.member, access))

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__tree_access_to_file_by_root_level_dir_1(self, access):
        self.create_dir_tree()
        get_or_create_storage_access_policy(self.root, self.member, access)

        file = self._create_file(parent=self.dir_1)
        self.assertTrue(member_has_access(file, self.member, access))

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__tree_access_to_file_by_root_level_dir_4(self, access):
        self.create_dir_tree()
        get_or_create_storage_access_policy(self.root, self.member, access)

        file = self._create_file(parent=self.dir_4)
        self.assertTrue(member_has_access(file, self.member, access))

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__tree_access_to_file_by_dir1_level_dir3(self, access):
        self.create_dir_tree()
        get_or_create_storage_access_policy(self.dir_1, self.member, access)

        file = self._create_file(parent=self.dir_3)
        self.assertTrue(member_has_access(file, self.member, access))

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__tree_no_access_to_file(self, access):
        self.create_dir_tree()
        get_or_create_storage_access_policy(self.dir_1, self.member, access)

        file = self._create_file(parent=self.dir_4)
        self.assertFalse(member_has_access(file, self.member, access))
