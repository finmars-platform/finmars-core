from poms.common.common_base_test import BaseTestCase


class CeleryTaskViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/tasks/task/list-all/"

    def test__list_all_71(self):
        pass
