from poms.common.common_base_test import BaseTestCase
from poms.portfolios.models import Portfolio


class DeleteReconcileHistoryTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
