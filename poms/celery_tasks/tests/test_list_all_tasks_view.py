from poms.common.common_base_test import BaseTestCase


class CeleryTaskViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/tasks/task/list-all/"

    @BaseTestCase.cases(
        ("1", "configuration.import_configuration"),
        ("2", "csv_import.simple_import"),
        ("3", "explorer.tasks.move_directory_in_storage"),
        ("5", "instruments.calculate_prices_accrued_price"),
        ("6", "portfolios.calculate_portfolio_register_record"),
        ("7", "reconciliation.process_bank_file_for_reconcile"),
    )
    def test__list_all_tasks(self, task_name):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertTrue(len(response_json) >= 70)
        self.assertIn(task_name, set(response_json))
