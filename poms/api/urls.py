from django.urls import include, re_path
from django.views.decorators.csrf import csrf_exempt
from rest_framework import routers

import poms.accounts.urls as account_router
import poms.api.views as api
import poms.celery_tasks.views as celery_tasks
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
    CreateMasterUser,
    CreateUser,
    DeleteMember,
    MasterUserChangeOwner,
    ObtainAuthToken,
    RenameMasterUser,
    SetAuthToken,
    AcceptInvite,
    DeclineInvite,
    PersonalAccessTokenViewSet,
)
from poms.explorer.views import ExplorerServeFileViewSet

router = routers.DefaultRouter()

router.register(
    r"system/ecosystem-configuration",
    system.EcosystemConfigurationViewSet,
    "ecosystemconfiguration",
)

router.register(
    r"reference-tables/reference-table",
    reference_table.ReferenceTableViewSet,
    "ReferenceTable",
)
router.register(
    r"active_processes/active_processes",
    celery_tasks.CeleryTaskViewSet,
    "CeleryTask",
)  # deprecated
router.register(
    r"tasks/task",
    celery_tasks.CeleryTaskViewSet,
    "CeleryTask",
)

router.register(
    r"tasks/worker",
    celery_tasks.CeleryWorkerViewSet,
    "CeleryWorker",
)

router.register(
    r"tasks/stats",
    celery_tasks.CeleryStatsViewSet,
    "CeleryStats",
)

router.register(
    r"configuration/configuration",
    configuration.ConfigurationViewSet,
    "configuration"
)
router.register(
    r"configuration/new-member-setup-configuration",
    configuration.NewMemberSetupConfigurationViewSet,
    "newmembersetupconfiguration"
)
router.register(
    r"transactions/bank-file",
    integrations.TransactionFileResultViewSet,
)  # deprecated?
router.register(
    r"specific-data/values-for-select",
    common.ValuesForSelectViewSet,
    "valuesforselect",
)
router.register(
    r"notifications/notification",
    notifications.NotificationViewSet,
)
router.register(
    r"data-provider/bloomberg/credential",
    integrations.BloombergDataProviderCredentialViewSet,
)
router.register(
    r"utils/expression",
    api.ExpressionViewSet,
    "expression",
)

router.register(r"utils/send-email", api.EmailViewSet, basename="email")

router.register(
    r"utils/stats",
    api.StatsViewSet,
    "stats",
)
router.register(
    r"utils/system-info",
    api.SystemInfoViewSet,
    "system-info",
)
router.register(
    r"utils/system-logs",
    api.SystemLogsViewSet,
    "system-logs",
)
router.register(
    r"utils/calendar-events",
    api.CalendarEventsViewSet,
    "calendar-events",
)
router.register(
    r"utils/tables-size",
    api.TablesSizeViewSet,
    "tables-size",
)
router.register(
    r"utils/recycle-bin",
    api.RecycleBinViewSet,
    "recycle-bin",
)
router.register(
    r"utils/universal-input",
    api.UniversalInputViewSet,
    "universalInput",
)
router.register(
    r"import/complex/scheme",
    complex_import.ComplexImportSchemeViewSet,
    "import_complex_scheme",
)  # Probably deprecated
router.register(
    r"import/complex",
    complex_import.ComplexImportViewSet,
    "import_complex",
)  # Probably deprecated
router.register(
    r"reconciliation/process-bank-file",
    reconciliation.ProcessBankFileForReconcileViewSet,
    "process_bank_file_for_reconcile",
)
router.register(
    r"reconciliation/bank-field",
    reconciliation.ReconciliationBankFileFieldViewSet,
    "bank_fields",
)
router.register(
    r"reconciliation/new-bank-field",
    reconciliation.ReconciliationNewBankFileFieldViewSet,
    "new_bank_fields",
)
router.register(
    r"reconciliation/complex-transaction-field",
    reconciliation.ReconciliationComplexTransactionFieldViewSet,
    "complex_transaction_fields",
)
router.register(
    r"file-reports/file-report",
    file_reports.FileReportViewSet,
    "file_reports",
)

router.register(
    r"pricing/run",
    pricing.RunPricingView,
    "runpricing",
)
router.register(
    r"pricing/price-history-error-ev-group",
    pricing.PriceHistoryErrorEvGroupViewSet,
    "pricehistoryerrorevgroup",
)
router.register(
    r"pricing/price-history-error-ev",
    pricing.PriceHistoryErrorEvViewSet,
)
router.register(
    r"pricing/price-history-error",
    pricing.PriceHistoryErrorViewSet,
)
router.register(
    r"pricing/currency-history-error-ev-group",
    pricing.CurrencyHistoryErrorEvGroupViewSet,
    "currencyhistoryerrorevgroup",
)
router.register(
    r"pricing/currency-history-error-ev",
    pricing.CurrencyHistoryErrorEvViewSet,
)
router.register(
    r"pricing/currency-history-error",
    pricing.CurrencyHistoryErrorViewSet,
)
router.register(
    r"schedules/schedule",
    schedules.ScheduleViewSet,
    "schedule"
)
router.register(
    r"system-messages/message",
    system_messages.SystemMessageViewSet,
)
router.register(
    r"credentials/credentials",
    credentials.CredentialsViewSet,
)  # Probably deprecated
router.register(
    r"integrations/data-provider",
    integrations.DataProviderViewSet,
)  # Probably deprecated
router.register(
    r"widgets/history/nav",
    widgets.HistoryNavViewSet,
    "widgets_history_nav",
)
router.register(
    r"widgets/history/pl",
    widgets.HistoryPlViewSet,
    "widgets_history_pl",
)
router.register(
    r"widgets/stats",
    widgets.StatsViewSet,
    "widgets_stats",
)
router.register(
    r"widgets/collect-history",
    widgets.CollectHistoryViewSet,
    "widgets_collect_history",
)
router.register(
    r"widgets/collect-balance-history",
    widgets.CollectBalanceHistoryViewSet,
    "widgets_collect_balance_history",
)
router.register(
    r"widgets/collect-pl-history",
    widgets.CollectPlHistoryViewSet,
    "widgets_collect_pl_history",
)
router.register(
    r"widgets/collect-stats",
    widgets.CollectStatsViewSet,
    "widgets_collect_stats",
)
router.register(
    r"debug/logs",
    common.DebugLogViewSet,
    "debug_log",
)  # Deprecated
router.register(
    r"errors/error",
    ErrorRecordViewSet,
    "error",
)
router.register(
    r"history/historical-record", history.HistoricalRecordViewSet, "historical-record"
)

router.register(
    r"auth-tokens/personal-access-token",
    PersonalAccessTokenViewSet,
    "personal_access_token",
)

urlpatterns = [
    re_path(r"^v1/users/", include(users_router.router.urls)),
    re_path(r"^v1/accounts/", include(account_router.router.urls)),
    re_path(r"^v1/portfolios/", include(portfolio_router.router.urls)),
    re_path(r"^v1/currencies/", include(currency_router.router.urls)),
    re_path(r"^v1/instruments/", include(instrument_router.router.urls)),
    re_path(r"^v1/transactions/", include(transaction_router.router.urls)),
    re_path(r"^v1/counterparties/", include(counterparty_router.router.urls)),
    re_path(r"^v1/strategies/", include(strategy_router.router.urls)),
    re_path(r"^v1/reports/", include(report_router.router.urls)),
    re_path(r"^v1/procedures/", include(procedure_router.router.urls)),
    re_path(r"^v1/import/", include(integrations_router.router.urls)),
    re_path(r"^v1/import/", include(csv_import_router.router.urls)),
    re_path(r"^v1/ui/", include(ui_router.router.urls)),
    re_path(r"^v1/explorer/", include(explorer_router.router.urls)),
    re_path(r"^v1/vault/", include(vault_router.router.urls)),
    re_path(r"^v1/iam/", include(iam_router.router.urls)),
    re_path(r"^v1/", include(router.urls)),
    re_path(
        r"instruments/instrument-database-search",
        instruments.InstrumentDatabaseSearchViewSet.as_view(),
    ),
    # Authorizer, Workflow, Backend Internal API section
    re_path(r"^internal/accept-invite/", AcceptInvite.as_view(), name="accept-invite"),
    re_path(
        r"^internal/decline-invite/", DeclineInvite.as_view(), name="decline-invite"
    ),
    # re_path(r'internal/data/transactions/callback',
    #         csrf_exempt(integrations.TransactionFileResultUploadHandler.as_view())),
    re_path(
        r"internal/data/transactions/json",
        csrf_exempt(integrations.TransactionImportJson.as_view()),
    ),
    re_path(
        r"integrations/superset/get-security-token",
        csrf_exempt(integrations.SupersetGetSecurityToken.as_view()),
    ),
    re_path(
        r"instruments/instrument-external-api",
        csrf_exempt(instruments.InstrumentExternalAPIViewSet.as_view()),
    ),
    re_path(
        r"instruments/fdb-create-from-callback",
        csrf_exempt(instruments.InstrumentFDBCreateFromCallbackViewSet.as_view()),
    ),
    re_path(
        r"^authorizer/token-auth/", ObtainAuthToken.as_view(), name="api-token-auth"
    ),
    re_path(
        r"^authorizer/set-token-auth/", SetAuthToken.as_view(), name="set-token-auth"
    ),
    re_path(r"^authorizer/create-user/", CreateUser.as_view(), name="create-user"),
    re_path(
        r"^authorizer/create-master-user/",
        CreateMasterUser.as_view(),
        name="create-master-user",
    ),
    # TODO deprecated delete soon
    re_path(
        r"^authorizer/rename-master-user/",
        RenameMasterUser.as_view(),
        name="rename-master-user",
    ),
    # re_path(r'^authorizer/create-member/', CreateMember.as_view(), name='create-member'), # Deprecated
    re_path(
        r"^authorizer/delete-member/", DeleteMember.as_view(), name="delete-member"
    ),
    re_path(
        r"^authorizer/master-user-change-owner/",
        MasterUserChangeOwner.as_view(),
        name="master-user-change-owner",
    ),
    re_path(
        r"^storage/(?P<filepath>.+)",
        ExplorerServeFileViewSet.as_view({"get": "retrieve"}),
        name="storage",
    ),

    re_path(r"^authorizer/migrate/",
            common.RealmMigrateSchemeView.as_view(),
            name="migrate")

]

# if 'rest_framework_swagger' in settings.INSTALLED_APPS:
#     urlpatterns += [
#         re_path(r'^schema/', api.SchemaViewSet.as_view()),
#     ]
