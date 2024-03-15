from django.conf import settings
from django.contrib.auth.models import User

from poms.bootstrap.apps import FINMARS_BOT, BootstrapConfig, BootstrapError
from poms.common.common_base_test import BaseTestCase
from poms.users.models import MasterUser, Member


class CreateFinmarsBotTestCase(BaseTestCase):
    """
    Test doesn't run whole BootstrapConfig class,
    it checks only one method: create_finmars_bot
    """

    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

    def test__finmars_user_created(self):
        self.assertEqual(
            User.objects.using(settings.DB_DEFAULT)
            .filter(username=FINMARS_BOT)
            .count(),
            0,
        )

        BootstrapConfig.create_finmars_bot()

        self.assertEqual(
            User.objects.using(settings.DB_DEFAULT)
            .filter(username=FINMARS_BOT)
            .count(),
            1,
        )

    def test__raise_error_if_no_master_user(self):
        master_user = MasterUser.objects.using(settings.DB_DEFAULT).get(
            base_api_url=settings.BASE_API_URL
        )
        master_user.base_api_url = "no_such_api_url"
        master_user.save()

        with self.assertRaises(BootstrapError):
            BootstrapConfig.create_finmars_bot()

    def test__finmars_bot_member_created(self):
        self.assertEqual(
            Member.objects.using(settings.DB_DEFAULT)
            .filter(username=FINMARS_BOT)
            .count(),
            0,
        )

        BootstrapConfig.create_finmars_bot()

        member = Member.objects.using(settings.DB_DEFAULT).get(username=FINMARS_BOT)
        master_user = MasterUser.objects.using(settings.DB_DEFAULT).get(
            base_api_url=settings.BASE_API_URL
        )
        user = User.objects.using(settings.DB_DEFAULT).get(username=FINMARS_BOT)

        self.assertTrue(member.is_admin)
        self.assertEqual(member.master_user, master_user)
        self.assertEqual(member.user, user)
