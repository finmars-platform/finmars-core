from django.core.cache import cache
from poms.common.common_base_test import BaseTestCase
from poms.users.models import EcosystemDefault, MasterUser


class EcosystemDefaultCacheTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.init_test_case()
        cache.clear()
        self.ed = EcosystemDefault.objects.first()
        cache.clear()

    def get_ed_from_cache(self):
        cache_key = EcosystemDefault.cache.get_cache_key(
            master_user_pk=self.ed.master_user.pk
        )
        return cache.get(cache_key)

    def check_ed_is_not_in_cache(self):
        ed_cheched = self.get_ed_from_cache() 
        self.assertIsNone(ed_cheched)

    def check_ed_is_in_cache(self):
        ed_cheched = self.get_ed_from_cache()
        self.assertIsNotNone(ed_cheched)

    def test__set_cache(self):
        self.check_ed_is_not_in_cache()

        EcosystemDefault.cache.set_cache(self.ed)
        ed_cheched = self.get_ed_from_cache()

        self.assertIsNotNone(ed_cheched)
        self.assertEqual(self.ed, ed_cheched)

    def test__get_cache_with_updating_cache(self):
        self.check_ed_is_not_in_cache()

        ed_cheched = EcosystemDefault.cache.get_cache(
            master_user_pk=self.ed.master_user.pk
        )
        self.assertIsNotNone(ed_cheched)

        ed_cheched = self.get_ed_from_cache()
        self.assertIsNotNone(ed_cheched)
        self.assertEqual(self.ed, ed_cheched)

    def test__get_existing_cache(self):
        self.check_ed_is_not_in_cache()

        EcosystemDefault.cache.set_cache(self.ed)
        self.check_ed_is_in_cache()

        ed_cheched = ed_cheched = EcosystemDefault.cache.get_cache(
            master_user_pk=self.ed.master_user.pk
        )
        self.assertIsNotNone(ed_cheched)
        self.assertEqual(self.ed, ed_cheched)

        ed_cheched = self.get_ed_from_cache()
        self.assertIsNotNone(ed_cheched)
        self.assertEqual(self.ed, ed_cheched)

    def test__delete_cache(self):
        self.check_ed_is_not_in_cache()

        EcosystemDefault.cache.set_cache(self.ed)
        self.check_ed_is_in_cache()

        EcosystemDefault.cache.delete_cache(self.ed)
        self.check_ed_is_not_in_cache()

    def test__update_model(self):
        self.check_ed_is_not_in_cache()

        EcosystemDefault.cache.set_cache(self.ed)
        self.check_ed_is_in_cache()

        self.ed.save()
        self.check_ed_is_not_in_cache()

    def test__incorrect_pk(self):
        master_users_pk = [ms.pk for ms in MasterUser.objects.all()]
        if fake_pk:=self.random_int(10, 15) in master_users_pk:
            fake_pk = self.random_int(10, 15)

        with self.assertRaises(EcosystemDefault.DoesNotExist):
            EcosystemDefault.cache.get_cache(fake_pk)

    def tearDown(self):
        cache.clear()
