from rest_framework import routers

import poms.reports.views as reports

router = routers.DefaultRouter()
router.register(r'summary', reports.SummaryViewSet, 'indicators')
router.register(r'balance-report', reports.BalanceReportViewSet, "balance-report")
router.register(r'balance-report-sql', reports.BalanceReportViewSet, "balance-report-sync-sql")  # deprecated
router.register(r'balance-report/custom-field', reports.BalanceReportCustomFieldViewSet,
                'balance-report-custom-field')

router.register(r'pl-report', reports.PLReportViewSet, "pl-report")
router.register(r'pl-report-sql', reports.PLReportViewSet, "pl-report-sync-sql")  # deprecated, delete soon
router.register(r'pl-report/custom-field', reports.PLReportCustomFieldViewSet, 'pl-report-custom-field')

router.register(r'transaction-report', reports.TransactionReportViewSet, "transaction-report")
router.register(r'transaction-report-sql', reports.TransactionReportViewSet, "transaction-report-sync-sql")

router.register(r'transaction-report/custom-field', reports.TransactionReportCustomFieldViewSet,
                'transaction-report-custom-field')

router.register(r'performance-report', reports.PerformanceReportViewSet, "performance-report")

router.register(r'price-history-check-sql', reports.PriceHistoryCheckViewSet,
                "price-history-check-sql")  # deprecated
router.register(r'price-history-check', reports.PriceHistoryCheckViewSet, "price-history-check")


