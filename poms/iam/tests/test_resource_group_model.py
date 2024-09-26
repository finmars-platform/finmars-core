from django.contrib.contenttypes.models import ContentType

from poms.common.common_base_test import BaseTestCase
from poms.iam.models import ResourceGroup, ResourceGroupAssignment
from poms.portfolios.models import Portfolio


class ResourceGroupViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

    def create_group(self, name: str = "test") -> ResourceGroup:
        return ResourceGroup.objects.create(
            master_user=self.master_user,
            name=name,
            user_code=name,
            description=name,
        )

    def test_add_assignment(self):
        rg = self.create_group()

        p = Portfolio.objects.first()

        ResourceGroup.objects.add_object(
            group_user_code=rg.user_code,
            app_name="portfolios",
            model_name="portfolio",
            object_id=p.id,
            object_user_code=p.user_code,
        )
