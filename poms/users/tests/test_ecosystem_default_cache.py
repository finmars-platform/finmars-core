from django.core.cache import cache
from poms.common.common_base_test import BaseTestCase
from poms.users.models import EcosystemDefault


class EcosystemDefaultCacheTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.ed = EcosystemDefault.objects.first()
        cache.clear()

    def get_ed_from_cache(self):
        cache_key = EcosystemDefault.cache.get_cache_key(self.ed.pk)
        return cache.get(cache_key)

    def test__set_cache(self):
        ed_cheched = self.get_ed_from_cache() 
        self.assertIsNone(ed_cheched)

        EcosystemDefault.cache.set_cache(self.ed)
        ed_cheched = self.get_ed_from_cache()

        self.assertIsNotNone(ed_cheched)
        self.assertEqual(self.ed, ed_cheched)

    def test__get_cache_with_updating_cache(self):
        ed_cheched = self.get_ed_from_cache()  
        self.assertIsNone(ed_cheched)

        ed_cheched = EcosystemDefault.cache.get_cache(self.ed.pk)
        self.assertIsNotNone(ed_cheched)

        ed_cheched = self.get_ed_from_cache()
        self.assertIsNotNone(ed_cheched)
        self.assertEqual(self.ed, ed_cheched)

    def test__get_cache(self):
        ed_cheched = self.get_ed_from_cache()   
        self.assertIsNone(ed_cheched)

        EcosystemDefault.cache.set_cache(self.ed)
        ed_cheched = self.get_ed_from_cache()
        self.assertIsNotNone(ed_cheched)

        ed_cheched = EcosystemDefault.cache.get_cache(self.ed.pk)
        self.assertIsNotNone(ed_cheched)
        self.assertEqual(self.ed, ed_cheched)

        ed_cheched = self.get_ed_from_cache()
        self.assertIsNotNone(ed_cheched)
        self.assertEqual(self.ed, ed_cheched)

    def test__delete_cache(self):
        ed_cheched = self.get_ed_from_cache()   
        self.assertIsNone(ed_cheched)

        EcosystemDefault.cache.set_cache(self.ed)
        ed_cheched = self.get_ed_from_cache()
        self.assertIsNotNone(ed_cheched)

        EcosystemDefault.cache.delete_cache(self.ed)
        ed_cheched = self.get_ed_from_cache()
        self.assertIsNone(ed_cheched)

    def tearDown(self):
        cache.clear()
