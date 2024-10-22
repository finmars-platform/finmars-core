from poms.common.common_base_test import BaseTestCase
from poms.iam.models import ResourceGroup, ResourceGroupAssignment
from poms.portfolios.models import Portfolio


class ResourceGroupModelTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

    def create_group(self, name: str = "test") -> ResourceGroup:
        return ResourceGroup.objects.create(
            name=name,
            user_code=name,
            description=name,
        )

    def test__add_object(self):
        rg = self.create_group()
        portfolio = Portfolio.objects.first()

        ResourceGroup.objects.add_object(
            group_user_code=rg.user_code,
            obj_instance=portfolio,
        )

        self.assertEqual(rg.assignments.count(), 1)
        self.assertEqual(rg.assignments.first().content_object, portfolio)
        self.assertEqual(rg.assignments.first().resource_group, rg)
        ass = ResourceGroupAssignment.objects.filter(resource_group=rg).first()
        self.assertEqual(ass, rg.assignments.first())

        self.assertIn(rg.user_code, portfolio.resource_groups)
        self.assertEqual(len(portfolio.resource_groups), 1)

    def test_add_object_duplicate(self):
        rg = self.create_group()
        portfolio = Portfolio.objects.first()

        ResourceGroup.objects.add_object(
            group_user_code=rg.user_code,
            obj_instance=portfolio,
        )

        ResourceGroup.objects.add_object(
            group_user_code=rg.user_code,
            obj_instance=portfolio,
        )

        self.assertEqual(rg.assignments.count(), 1)
        self.assertEqual(rg.assignments.first().content_object, portfolio)
        self.assertEqual(rg.assignments.first().resource_group, rg)
        ass = ResourceGroupAssignment.objects.filter(resource_group=rg).first()
        self.assertEqual(ass, rg.assignments.first())

        self.assertIn(rg.user_code, portfolio.resource_groups)
        self.assertEqual(len(portfolio.resource_groups), 1)

    def test__delete_object(self):
        rg = self.create_group()
        portfolio = Portfolio.objects.first()

        ResourceGroup.objects.add_object(
            group_user_code=rg.user_code,
            obj_instance=portfolio,
        )
        ass = ResourceGroupAssignment.objects.filter(resource_group=rg).first()
        self.assertEqual(ass, rg.assignments.first())
        self.assertIn(rg.user_code, portfolio.resource_groups)
        self.assertEqual(len(portfolio.resource_groups), 1)

        ResourceGroup.objects.del_object(
            group_user_code=rg.user_code,
            obj_instance=portfolio,
        )

        self.assertEqual(rg.assignments.count(), 0)
        ass = ResourceGroupAssignment.objects.filter(resource_group=rg).first()
        self.assertIsNone(ass)
        self.assertEqual(portfolio.resource_groups, [])

        # delete from empty resource_groups one more time
        ResourceGroup.objects.del_object(
            group_user_code=rg.user_code,
            obj_instance=portfolio,
        )
        self.assertIsNone(ass)
        self.assertEqual(portfolio.resource_groups, [])
