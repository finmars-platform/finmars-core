from django.test import TestCase
from django.test import Client
from django.contrib.auth.models import User


class AdminPageTest(TestCase):
    def setUp(self):
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin",
        )
        self.client.force_login(self.admin_user)

    def test_admin_page_loads(self):
        response = self.client.get(f"/{self.realm_code}/{self.space_code}/admin/")
        self.assertEqual(response.status_code, 200)

    def test_admin_login(self):
        self.assertTrue(self.admin_user.is_authenticated)
