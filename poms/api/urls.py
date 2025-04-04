from django.urls import include, re_path
from django.views.decorators.csrf import csrf_exempt
from rest_framework import routers

import poms.accounts.urls as account_router
import poms.api.views as api
import poms.celery_tasks.views as celery_tasks
import poms.clients.urls as clients_router
import poms.common.views as common
import poms.complex_import.views as complex_import
import poms.configuration.views as configuration
import poms.counterparties.urls as counterparty_router
import poms.credentials.views as credentials
import poms.csv_import.urls as csv_import_router
import poms.currencies.urls as currency_router
import poms.explorer.urls as explorer_router
import poms.file_reports.views as file_reports
import poms.history.views as history
import poms.iam.urls as iam_router
import poms.instruments.urls as instrument_router
import poms.instruments.views as instruments
import poms.integrations.urls as integrations_router
import poms.integrations.views as integrations
import poms.notifications.views as notifications
import poms.portfolios.urls as portfolio_router
import poms.pricing.views as pricing
import poms.procedures.urls as procedure_router
import poms.reconciliation.views as reconciliation
import poms.reference_tables.views as reference_table
import poms.reports.urls as report_router
import poms.schedules.views as schedules
import poms.strategies.urls as strategy_router
import poms.system.views as system
import poms.system_messages.views as system_messages
import poms.transactions.urls as transaction_router
import poms.ui.urls as ui_router
import poms.users.urls as users_router
import poms.vault.urls as vault_router
import poms.widgets.views as widgets
from finmars_standardized_errors.views import ErrorRecordViewSet
from poms.auth_tokens.views import (
    AcceptInvite,
    CreateMasterUser,
    CreateUser,
    DeclineInvite,
    DeleteMember,
    MasterUserChangeOwner,
    ObtainAuthToken,
    PersonalAccessTokenViewSet,
    RenameMasterUser,
    SetAuthToken,
)
from poms.explorer.views import ExplorerServerFileViewSet

router = routers.DefaultRouter()

router.register(
    "system/ecosystem-configuration",
    system.EcosystemConfigurationViewSet,
    "ecosystemconfiguration",
)
router.register(
    "system/whitelabel",
    system.WhitelabelViewSet,
    "Whitelabel",
)
router.register(
    "reference-tables/reference-table",
    reference_table.ReferenceTableViewSet,
    "ReferenceTable",
)
router.register(
    "tasks/task",
    celery_tasks.CeleryTaskViewSet,
    "CeleryTask",
)
router.register(
    "tasks/worker",
    celery_tasks.CeleryWorkerViewSet,
    "CeleryWorker",
)
router.register(
    "tasks/stats",
    celery_tasks.CeleryStatsViewSet,
    "CeleryStats",
)
router.register(
    "configuration/configuration",
    configuration.ConfigurationViewSet,
    "configuration",
)
router.register(
    "configuration/new-member-setup-configuration",
    configuration.NewMemberSetupConfigurationViewSet,
    "newmembersetupconfiguration",
)
router.register(
    "specific-data/values-for-select",
    common.ValuesForSelectViewSet,
    "valuesforselect",
)
router.register(
    "utils/expression",
    api.ExpressionViewSet,
    "expression",
)
router.register(
    "utils/send-email",
    api.EmailViewSet,
    "email",
)
router.register(
    "utils/stats",
    api.StatsViewSet,
    "stats",
)
router.register(
    "utils/system-info",
    api.SystemInfoViewSet,
    "system-info",
)
router.register(
    "utils/system-logs",
    api.SystemLogsViewSet,
    "system-logs",
)
router.register(
    "utils/calendar-events",
    api.CalendarEventsViewSet,
    "calendar-events",
)
router.register(
    "utils/tables-size",
    api.TablesSizeViewSet,
    "tables-size",
)
router.register(
    "utils/recycle-bin",
    api.RecycleBinViewSet,
    "recycle-bin",
)
router.register(
    "utils/universal-input",
    api.UniversalInputViewSet,
    "universalInput",
)
router.register(
    "utils/date/split-date-range",
    api.SplitDateRangeViewSet,
    "split_date_range",
)
router.register(
    "utils/date/pick-dates-from-range",
    api.PickDatesFromRangeViewSet,
    "pick_dates_from_range",
)
router.register(
    "utils/date/calc-period-date",
    api.CalcPeriodDateViewSet,
    "calculate_period_date",
)
router.register(
    "utils/date/last-business-day",
    api.LastBusinessDayViewSet,
    "last_business_day",
)
router.register(
    "utils/date/is-business-day",
    api.IsBusinessDayViewSet,
    "is_business_day",
)
router.register(
    "utils/date/last-day-of-month",
    api.LastDayOfMonthViewSet,
    "last_day_of_month",
)
router.register(
    "file-reports/file-report",
    file_reports.FileReportViewSet,
    "file_reports",
)
router.register(
    "pricing/run",
    pricing.RunPricingView,
    "runpricing",
)
router.register(
    "pricing/price-history-error-ev-group",
    pricing.PriceHistoryErrorEvGroupViewSet,
    "pricehistoryerrorevgroup",
)
router.register(
    "pricing/price-history-error-ev",
    pricing.PriceHistoryErrorEvViewSet,
    "price_history_error_ev",
)
router.register(
    "pricing/price-history-error",
    pricing.PriceHistoryErrorViewSet,
    "price_history_error",
)
router.register(
    "pricing/currency-history-error-ev-group",
    pricing.CurrencyHistoryErrorEvGroupViewSet,
    "currencyhistoryerrorevgroup",
)
router.register(
    "pricing/currency-history-error-ev",
    pricing.CurrencyHistoryErrorEvViewSet,
    "currency_history_error_ev",
)
router.register(
    "pricing/currency-history-error",
    pricing.CurrencyHistoryErrorViewSet,
    "currency_history_error",
)
router.register(
    "schedules/schedule",
    schedules.ScheduleViewSet,
    "schedule",
)
router.register(
    "widgets/history/nav",
    widgets.HistoryNavViewSet,
    "widgets_history_nav",
)
router.register(
    "widgets/history/pl",
    widgets.HistoryPlViewSet,
    "widgets_history_pl",
)
router.register(
    "widgets/stats",
    widgets.StatsViewSet,
    "widgets_stats",
)
router.register(
    "widgets/collect-history",
    widgets.CollectHistoryViewSet,
    "widgets_collect_history",
)
router.register(
    "widgets/collect-balance-history",
    widgets.CollectBalanceHistoryViewSet,
    "widgets_collect_balance_history",
)
router.register(
    "widgets/collect-pl-history",
    widgets.CollectPlHistoryViewSet,
    "widgets_collect_pl_history",
)
router.register(
    "widgets/collect-stats",
    widgets.CollectStatsViewSet,
    "widgets_collect_stats",
)
router.register(
    "errors/error",
    ErrorRecordViewSet,
    "error",
)
router.register(
    "history/historical-record",
    history.HistoricalRecordViewSet,
    "HistoricalRecord",
)
router.register(
    "auth-tokens/personal-access-token",
    PersonalAccessTokenViewSet,
    "PersonalAccessToken",
)
router.register(
    "system-messages/message",
    system_messages.SystemMessageViewSet,
    "SystemMessage"
)
router.register(
    "notifications/notification",
    notifications.NotificationViewSet,
    "Notification",
)

# DEPRECATED
router.register(
    "debug/logs",
    common.DebugLogViewSet,
    "debug_log",
)
router.register(
    "credentials/credentials",
    credentials.CredentialsViewSet,
    "Credentials"
)
router.register(
    "integrations/data-provider",
    integrations.DataProviderViewSet,
    "integrations_data_provider",
)
router.register(
    "import/complex/scheme",
    complex_import.ComplexImportSchemeViewSet,
    "import_complex_scheme",
)
router.register(
    "import/complex",
    complex_import.ComplexImportViewSet,
    "import_complex",
)
router.register(
    "active_processes/active_processes",
    celery_tasks.CeleryTaskViewSet,
    "activeprocesses",
)
router.register(
    "transactions/bank-file",
    integrations.TransactionFileResultViewSet,
    "transaction_bank_file",
)
router.register(
    "data-provider/bloomberg/credential",
    integrations.BloombergDataProviderCredentialViewSet,
    "bloomberg_credential",
)
router.register(
    "reconciliation/process-bank-file",
    reconciliation.ProcessBankFileForReconcileViewSet,
    "process_bank_file_for_reconcile",
)
router.register(
    "reconciliation/bank-field",
    reconciliation.ReconciliationBankFileFieldViewSet,
    "bank_fields",
)
router.register(
    "reconciliation/new-bank-field",
    reconciliation.ReconciliationNewBankFileFieldViewSet,
    "new_bank_fields",
)
router.register(
    "reconciliation/complex-transaction-field",
    reconciliation.ReconciliationComplexTransactionFieldViewSet,
    "complex_transaction_fields",
)


urlpatterns = [
    re_path("^v1/system-notifications/", include("poms.system_messages.urls")),
    re_path("^v1/users/", include(users_router.router.urls)),
    re_path("^v1/accounts/", include(account_router.router.urls)),
    re_path("^v1/portfolios/", include(portfolio_router.router.urls)),
    re_path("^v1/currencies/", include(currency_router.router.urls)),
    re_path("^v1/instruments/", include(instrument_router.router.urls)),
    re_path("^v1/transactions/", include(transaction_router.router.urls)),
    re_path("^v1/counterparties/", include(counterparty_router.router.urls)),
    re_path("^v1/strategies/", include(strategy_router.router.urls)),
    re_path("^v1/reports/", include(report_router.router.urls)),
    re_path("^v1/procedures/", include(procedure_router.router.urls)),
    re_path("^v1/import/", include(integrations_router.router.urls)),
    re_path("^v1/import/", include(csv_import_router.router.urls)),
    re_path("^v1/ui/", include(ui_router.router.urls)),
    re_path("^v1/explorer/", include(explorer_router.router.urls)),
    re_path("^v1/clients/", include(clients_router.router.urls)),
    re_path("^v1/vault/", include(vault_router.router.urls)),
    re_path("^v1/iam/", include(iam_router.router.urls)),
    re_path("^v1/", include(router.urls)),
    re_path(
        "instruments/instrument-database-search",
        instruments.InstrumentDatabaseSearchViewSet.as_view(),
    ),
    # Authorizer, Workflow, Backend Internal API section
    re_path(
        "^internal/accept-invite/",
        AcceptInvite.as_view(),
        name="accept-invite",
    ),
    re_path(
        "^internal/decline-invite/",
        DeclineInvite.as_view(),
        name="decline-invite",
    ),
    re_path(
        "internal/data/transactions/json",
        csrf_exempt(integrations.TransactionImportJson.as_view()),
    ),
    re_path(
        "integrations/superset/get-security-token",
        csrf_exempt(integrations.SupersetGetSecurityToken.as_view()),
    ),
    re_path(
        "instruments/instrument-external-api",
        csrf_exempt(instruments.InstrumentExternalAPIViewSet.as_view()),
    ),
    re_path(
        "instruments/fdb-create-from-callback",
        csrf_exempt(instruments.InstrumentFDBCreateFromCallbackViewSet.as_view()),
    ),
    re_path(
        "^authorizer/token-auth/",
        ObtainAuthToken.as_view(),
        name="api-token-auth",
    ),
    re_path(
        "^authorizer/set-token-auth/",
        SetAuthToken.as_view(),
        name="set-token-auth",
    ),
    re_path(
        "^authorizer/create-user/",
        CreateUser.as_view(),
        name="create-user",
    ),
    re_path(
        "^authorizer/create-master-user/",
        CreateMasterUser.as_view(),
        name="create-master-user",
    ),
    # TODO deprecated delete soon
    re_path(
        "^authorizer/rename-master-user/",
        RenameMasterUser.as_view(),
        name="rename-master-user",
    ),
    re_path(
        "^authorizer/delete-member/",
        DeleteMember.as_view(),
        name="delete-member",
    ),
    re_path(
        "^authorizer/master-user-change-owner/",
        MasterUserChangeOwner.as_view(),
        name="master-user-change-owner",
    ),
    re_path(
        "^storage/(?P<filepath>.+)",
        ExplorerServerFileViewSet.as_view({"get": "retrieve"}),
        name="storage",
    ),
    re_path(
        "^authorizer/migrate/",
        common.RealmMigrateSchemeView.as_view(),
        name="migrate",
    ),
]

# if 'rest_framework_swagger' in settings.INSTALLED_APPS:
#     urlpatterns += [
#         re_path(r'^schema/', api.SchemaViewSet.as_view()),
#     ]
