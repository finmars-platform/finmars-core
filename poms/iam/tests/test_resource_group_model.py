from poms.common.common_base_test import BaseTestCase
from poms.iam.models import ResourceGroup, ResourceGroupAssignment
from poms.portfolios.models import Portfolio
from django.core.exceptions import ObjectDoesNotExist


class ResourceGroupViewTest(BaseTestCase):
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
            app_name="portfolios",
            model_name="Portfolio",
            object_id=portfolio.id,
            object_user_code=portfolio.user_code,
        )

        self.assertEqual(rg.assignments.count(), 1)
        self.assertEqual(rg.assignments.first().content_object, portfolio)
        self.assertEqual(rg.assignments.first().resource_group, rg)
        ass = ResourceGroupAssignment.objects.filter(resource_group=rg).first()
        self.assertEqual(ass, rg.assignments.first())

    def test_add_object_duplicate(self):
        rg = self.create_group()
        portfolio = Portfolio.objects.first()

        ResourceGroup.objects.add_object(
            group_user_code=rg.user_code,
            app_name="portfolios",
            model_name="Portfolio",
            object_id=portfolio.id,
            object_user_code=portfolio.user_code,
        )

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
        ass = ResourceGroupAssignment.objects.filter(resource_group=rg).first()
        self.assertEqual(ass, rg.assignments.first())

    def test_add_object_error_invalid_model(self):
        rg = self.create_group()
        portfolio = Portfolio.objects.first()

        with self.assertRaises(ObjectDoesNotExist):
            ResourceGroup.objects.add_object(
                group_user_code=rg.user_code,
                app_name="portfolios",
                model_name="InvalidModel",
                object_id=portfolio.id,
                object_user_code=portfolio.user_code,
            )

    def test_add_object_error_invalid_app(self):
        rg = self.create_group()
        portfolio = Portfolio.objects.first()

        with self.assertRaises(ObjectDoesNotExist):
            ResourceGroup.objects.add_object(
                group_user_code=rg.user_code,
                app_name="invalid",
                model_name="Portfolio",
                object_id=portfolio.id,
                object_user_code=portfolio.user_code,
            )

    def test_add_object_error_invalid_object_id(self):
        rg = self.create_group()
        portfolio = Portfolio.objects.first()

        with self.assertRaises(ObjectDoesNotExist):
            ResourceGroup.objects.add_object(
                group_user_code=rg.user_code,
                app_name="portfolios",
                model_name="Portfolio",
                object_id=self.random_int(10000, 1000000),
                object_user_code=portfolio.user_code,
            )

    def test_add_object_error_invalid_object_user_code(self):
        rg = self.create_group()
        portfolio = Portfolio.objects.first()

        with self.assertRaises(ValueError):
            ResourceGroup.objects.add_object(
                group_user_code=rg.user_code,
                app_name="portfolios",
                model_name="Portfolio",
                object_id=portfolio.id,
                object_user_code=self.random_string(),
            )

    def test__delete_object(self):
        rg = self.create_group()
        portfolio = Portfolio.objects.first()

        ResourceGroup.objects.add_object(
            group_user_code=rg.user_code,
            app_name="portfolios",
            model_name="Portfolio",
            object_id=portfolio.id,
            object_user_code=portfolio.user_code,
        )
        ass = ResourceGroupAssignment.objects.filter(resource_group=rg).first()
        self.assertEqual(ass, rg.assignments.first())

        ResourceGroup.objects.remove_object(
            group_user_code=rg.user_code,
            app_name="portfolios",
            model_name="Portfolio",
            object_id=portfolio.id,
        )

        self.assertEqual(rg.assignments.count(), 0)
        ass = ResourceGroupAssignment.objects.filter(resource_group=rg).first()
        self.assertIsNone(ass)
