from rest_framework import routers

import poms.reports.views as reports

router = routers.DefaultRouter()

router.register(
    r"summary",
    reports.SummaryViewSet,
    "Summary",
)
router.register(
    r"backend-balance-report",
    reports.BackendBalanceReportViewSet,
    "BackendBalanceReport",
)
router.register(
    r"balance-report",
    reports.BalanceReportViewSet,
    "BalanceReport",
)

# seems deprecated, delete in 1.12.0
router.register(
    r"balance-report-light",
    reports.BalanceReportLightViewSet,
    "BalanceReportLight",
)


router.register(
    r"balance-report-sql",
    reports.BalanceReportViewSet,
    "BalanceReportSyncSql",
)  # deprecated
router.register(
    r"balance-report/custom-field",
    reports.BalanceReportCustomFieldViewSet,
    "BalanceReportCustomField",
)
router.register(
    r"backend-pl-report",
    reports.BackendPLReportViewSet,
    "BackendPLReport",
)
router.register(
    r"pl-report",
    reports.PLReportViewSet,
    "PlReport",
)
router.register(
    r"pl-report-sql",
    reports.PLReportViewSet,
    "PlReportSyncSql",
)  # deprecated, delete soon
router.register(
    r"pl-report/custom-field",
    reports.PLReportCustomFieldViewSet,
    "PlReportCustomField",
)
router.register(
    r"backend-transaction-report",
    reports.BackendTransactionReportViewSet,
    "BackendTransactionReport",
)
router.register(
    r"transaction-report",
    reports.TransactionReportViewSet,
    "TransactionReport",
)
router.register(
    r"transaction-report-sql",
    reports.TransactionReportViewSet,
    "TransactionReportSyncSql",
)
router.register(
    r"transaction-report/custom-field",
    reports.TransactionReportCustomFieldViewSet,
    "TransactionReportCustomField",
)
router.register(
    r"performance-report",
    reports.PerformanceReportViewSet,
    "PerformanceReport",
)
router.register(
    r"price-history-check-sql",
    reports.PriceHistoryCheckViewSet,
    "PriceHistoryCheckSql",
)  # deprecated
router.register(
    r"price-history-check",
    reports.PriceHistoryCheckViewSet,
    "priceHistoryCheck",
)


router.register(
    r"balance-report-instance",
    reports.BalanceReportInstanceViewSet,
    "balanceReportInstance",
)

router.register(
    r"pl-report-instance",
    reports.PLReportInstanceViewSet,
    "plReportInstance",
)