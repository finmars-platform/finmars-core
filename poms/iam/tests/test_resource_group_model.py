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

    def test__add_object(self):
        rg = self.create_group()
        portfolio = Portfolio.objects.first()

        ResourceGroup.objects.add_object(
            group_user_code=rg.user_code,
            app_name="portfolios",
            model_name="Portfolio",
            object_id=portfolio.id,
            object_user_code=portfolio.user_code,
        )

        self.assertEqual(rg.assignments.count(), 1)
        self.assertEqual(rg.assignments.first().content_object, portfolio)
        self.assertEqual(rg.assignments.first().resource_group, rg)
