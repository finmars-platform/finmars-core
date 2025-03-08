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
        self.portfolio_1.portfolio_type = self.create_portfolio_type(PortfolioClass.GENERAL)
        self.portfolio_1.save()
        self.portfolio_2 = self.db_data.portfolios[SMALL]
        self.portfolio_2.portfolio_type = self.create_portfolio_type(PortfolioClass.POSITION)
        self.portfolio_2.save()

        self.group = self.create_reconcile_group()

    def create_reconcile_group(self) -> PortfolioReconcileGroup:
        return PortfolioReconcileGroup.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            name=self.random_string(),
            params={
                "precision": 1,
                "only_errors": True,
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
            user_code=f"user_code_{class_id}"
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
                {"portfolio_id": 1, "user_code": "UC1", "position_size": 10},
                {"portfolio_id": 2, "user_code": "UC1", "position_size": 10},
            ]
        )
        mock_compare_portfolios.return_value = ([], False)
        mock_generate_json_report.return_value = self.create_file_report()

        group = self.create_reconcile_group()
        group.portfolios.add(self.portfolio_1)
        group.portfolios.add(self.portfolio_2)

        history = self.create_reconcile_history(group)
        history.calculate()

        self.assertEqual(history.status, PortfolioReconcileHistory.STATUS_OK)
        self.assertEqual(history.error_message, "")

    # @patch("poms.portfolios.models.PortfolioReconcileHistory._finish_as_error")
    # def test_calculate_no_position_portfolio(self, mock_finish_as_error):
    #     # Arrange
    #     portfolio1 = PortfolioFactory.create(portfolio_type__portfolio_class=PortfolioClass.GENERAL)
    #     portfolio2 = PortfolioFactory.create(portfolio_type__portfolio_class=PortfolioClass.GENERAL)
    #     self.group.portfolios.set([portfolio1, portfolio2])
    #
    #     # Act
    #     self.history.calculate()
    #
    #     # Assert
    #     mock_finish_as_error.assert_called_once()
    #
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
