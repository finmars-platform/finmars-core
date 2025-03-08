import json
from unittest.mock import MagicMock, patch

from poms.common.common_base_test import BIG, SMALL, BaseTestCase
from poms.file_reports.models import FileReport
from poms.portfolios.models import (
    PortfolioClass,
    PortfolioReconcileGroup,
    PortfolioReconcileHistory,
    PortfolioType,
)


class PortfolioReconcileHistoryTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.portfolio_1 = self.db_data.portfolios[BIG]
        self.type_general = self.create_portfolio_type(PortfolioClass.GENERAL)
        self.type_position = self.create_portfolio_type(PortfolioClass.POSITION)
        self.portfolio_1.portfolio_type = self.type_general
        self.portfolio_1.save()
        self.portfolio_2 = self.db_data.portfolios[SMALL]
        self.portfolio_2.portfolio_type = self.type_position
        self.portfolio_2.save()

    def create_reconcile_group(self) -> PortfolioReconcileGroup:
        return PortfolioReconcileGroup.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            name=self.random_string(),
            params={
                "precision": 1,
                "round_digits": 2,
                "only_errors": False,
            },
        )

    def create_reconcile_history(self, group: PortfolioReconcileGroup) -> PortfolioReconcileHistory:
        return PortfolioReconcileHistory.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            date=self.random_future_date(),
            portfolio_reconcile_group=group,
        )

    def create_file_report(self) -> FileReport:
        return FileReport.objects.create(
            master_user=self.master_user,
            file_name=self.random_string(),
        )

    def create_portfolio_type(self, class_id: int) -> PortfolioType:
        return PortfolioType.objects.create(
            master_user=self.master_user,
            owner=self.member,
            portfolio_class_id=class_id,
            user_code=f"user_code_{class_id}",
        )

    @patch("poms.portfolios.models.PortfolioReconcileHistory.generate_json_report")
    @patch("poms.portfolios.models.PortfolioReconcileHistory.compare_portfolios")
    @patch("poms.reports.sql_builders.balance.BalanceReportBuilderSql")
    @patch("poms.reports.common.Report")
    @patch("poms.portfolios.models.EcosystemDefault.objects")
    def test_calculate_history_only_errors(
        self,
        mock_ecosystem_defaults,
        mock_report_class,
        mock_balance_builder,
        mock_compare_portfolios,
        mock_generate_json_report,
    ):
        mock_ecosystem_defaults.filter.return_value.first.return_value = MagicMock()
        mock_report = MagicMock()
        mock_report_class.return_value = mock_report
        mock_balance_builder.return_value.build_balance_sync.return_value = MagicMock(
            items=[
                {
                    "portfolio_id": self.portfolio_1.id,
                    "user_code": self.portfolio_1.user_code,
                    "position_size": 10,
                },
                {
                    "portfolio_id": self.portfolio_2.id,
                    "user_code": self.portfolio_2.user_code,
                    "position_size": 10,
                },
            ]
        )
        mock_compare_portfolios.return_value = ([], False)
        mock_generate_json_report.return_value = self.create_file_report()

        group = self.create_reconcile_group()
        group.portfolios.set([self.portfolio_1, self.portfolio_2])
        group.params = {
            "precision": 1,
            "round_digits": 2,
            "only_errors": True,
        }
        group.save()

        history = self.create_reconcile_history(group)
        history.calculate()

        self.assertEqual(history.status, PortfolioReconcileHistory.STATUS_OK)
        self.assertEqual(history.error_message, "")
        mock_generate_json_report.assert_called_once_with([])

    @patch("poms.portfolios.models.PortfolioReconcileHistory.generate_json_report")
    @patch("poms.portfolios.models.PortfolioReconcileHistory.compare_portfolios")
    @patch("poms.reports.sql_builders.balance.BalanceReportBuilderSql")
    @patch("poms.reports.common.Report")
    @patch("poms.portfolios.models.EcosystemDefault.objects")
    def test_calculate_history_default(
        self,
        mock_ecosystem_defaults,
        mock_report_class,
        mock_balance_builder,
        mock_compare_portfolios,
        mock_generate_json_report,
    ):
        mock_ecosystem_defaults.filter.return_value.first.return_value = MagicMock()
        mock_report = MagicMock()
        mock_report_class.return_value = mock_report
        mock_balance_builder.return_value.build_balance_sync.return_value = MagicMock(
            items=[
                {
                    "portfolio_id": self.portfolio_1.id,
                    "user_code": self.portfolio_1.user_code,
                    "position_size": 10,
                },
                {
                    "portfolio_id": self.portfolio_2.id,
                    "user_code": self.portfolio_2.user_code,
                    "position_size": 10,
                },
            ]
        )
        mock_compare_portfolios.return_value = (["good report"], False)
        mock_generate_json_report.return_value = self.create_file_report()

        group = self.create_reconcile_group()
        group.portfolios.set([self.portfolio_1, self.portfolio_2])

        history = self.create_reconcile_history(group)
        history.calculate()

        self.assertEqual(history.status, PortfolioReconcileHistory.STATUS_OK)
        self.assertEqual(history.error_message, "")
        mock_generate_json_report.assert_called_once_with(["good report"])

    @patch("poms.portfolios.models.PortfolioReconcileHistory._finish_as_error")
    def test_calculate_no_position_portfolio(self, mock_finish_as_error):
        self.portfolio_2.portfolio_type = self.type_general
        self.portfolio_2.save()

        group = self.create_reconcile_group()
        group.portfolios.set([self.portfolio_1, self.portfolio_2])

        history = self.create_reconcile_history(group)
        history.calculate()

        mock_finish_as_error.assert_called_once()

    # @patch("poms.portfolios.models.now")
    # @patch("poms.portfolios.models.FileReport")
    # @patch("poms.portfolios.models.json")
    # def test_generate_json_report(self, mock_json, mock_file_report, mock_now):
    #     # Arrange
    #     report = [{"test": "data"}]
    #     mock_now.return_value.strftime.return_value = "2024-12-08-10-00"
    #     mock_file_report_instance = MagicMock()
    #     mock_file_report.return_value = mock_file_report_instance
    #     mock_json.dumps.return_value = json.dumps(report)
    #     self.history.linked_task_id = "123"
    #
    #     # Act
    #     result = self.history.generate_json_report(report)
    #
    #     # Assert
    #     self.assertEqual(result, mock_file_report_instance)
    #     mock_file_report_instance.upload_file.assert_called_once_with(
    #         file_name=f"{self.history.user_code}_2024-12-08-10-00_n123.json",
    #         text=mock_json.dumps.return_value,
    #         master_user=self.history.master_user,
    #     )
