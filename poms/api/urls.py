from __future__ import unicode_literals

from django.conf import settings
from django.urls import re_path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework import routers

import poms.api.views as api
import poms.celery_tasks.views as celery_tasks
import poms.common.views as common
import poms.complex_import.views as complex_import
import poms.configuration.views as configuration
import poms.configuration_export.views as configuration_export
import poms.configuration_import.views as configuration_import
import poms.configuration_sharing.views as configuration_sharing
import poms.credentials.views as credentials
import poms.currencies.views as currencies
import poms.file_reports.views as file_reports
import poms.history.views as history
import poms.instruments.views as instruments
import poms.integrations.views as integrations
import poms.notifications.views as notifications
import poms.pricing.views as pricing
import poms.reconciliation.views as reconciliation
import poms.reference_tables.views as reference_table
import poms.schedules.views as schedules
import poms.system.views as system
import poms.system_messages.views as system_messages
import poms.users.views as users
import poms.widgets.views as widgets
import poms.iam.views as iam
from finmars_standardized_errors.views import ErrorRecordViewSet
from poms.auth_tokens.views import ObtainAuthToken, SetAuthToken, CreateUser, CreateMasterUser, CreateMember, \
    DeleteMember, RenameMasterUser, MasterUserChangeOwner
from poms.explorer.views import ExplorerServeFileViewSet

router = routers.DefaultRouter()

router.register(r'system/ecosystem-configuration', system.EcosystemConfigurationViewSet, 'ecosystemconfiguration')
router.register(r'users/ping', users.PingViewSet, "ping")

router.register(r'users/user', users.UserViewSet)
router.register(r'users/user-member', users.UserMemberViewSet, 'usermember')
router.register(r'users/master-user', users.MasterUserViewSet)
router.register(r'users/master-user-light', users.MasterUserLightViewSet,
                'masteruserlight')  # Deprecated at all, no light-method needed
router.register(r'users/get-current-master-user', users.GetCurrentMasterUserViewSet, 'getcurrentmasteruser')

router.register(r'users/member', users.MemberViewSet)
# router.register(r'users/group', users.GroupViewSet)
router.register(r'users/group', iam.GroupViewSet)
router.register(r'users/language', api.LanguageViewSet, 'language')
router.register(r'users/timezone', api.TimezoneViewSet, 'timezone')
router.register(r'users/ecosystem-default', users.EcosystemDefaultViewSet, 'ecosystemdefault')
router.register(r'users/usercode-prefix', users.UsercodePrefixViewSet, 'usercodeprefix')

router.register(r'reference-tables/reference-table', reference_table.ReferenceTableViewSet, 'ReferenceTable')
router.register(r'active_processes/active_processes', celery_tasks.CeleryTaskViewSet, 'CeleryTask')  # deprecated
router.register(r'tasks/task', celery_tasks.CeleryTaskViewSet, 'CeleryTask')

router.register(r'configuration/configuration', configuration.ConfigurationViewSet)
router.register(r'configuration/new-member-setup-configuration', configuration.NewMemberSetupConfigurationViewSet)

router.register(r'transactions/bank-file', integrations.TransactionFileResultViewSet)  # deprecated?

router.register(r'specific-data/values-for-select', common.ValuesForSelectViewSet, 'valuesforselect')

router.register(r'notifications/notification', notifications.NotificationViewSet)

router.register(r'data-provider/bloomberg/credential', integrations.BloombergDataProviderCredentialViewSet)

router.register(r'utils/expression', api.ExpressionViewSet, 'expression')
router.register(r'utils/stats', api.StatsViewSet, 'stats')
router.register(r'utils/system-info', api.SystemInfoViewSet, 'system-info')
router.register(r'utils/system-logs', api.SystemLogsViewSet, 'system-logs')
router.register(r'utils/calendar-events', api.CalendarEventsViewSet, 'calendar-events')
router.register(r'utils/tables-size', api.TablesSizeViewSet, 'tables-size')
router.register(r'utils/recycle-bin', api.RecycleBinViewSet, 'recycle-bin')
router.register(r'utils/universal-input', api.UniversalInputViewSet, 'universalInput')

router.register(r'import/complex/scheme', complex_import.ComplexImportSchemeViewSet,
                'import_complex_scheme')  # Probably deprecated
router.register(r'import/complex', complex_import.ComplexImportViewSet, 'import_complex')  # Probably deprecated

router.register(r'import/configuration-json', configuration_import.ConfigurationImportAsJsonViewSet,
                'configuration_import')

router.register(r'export/configuration', configuration_export.ConfigurationExportViewSet, 'configuration_export')
router.register(r'export/mapping', configuration_export.MappingExportViewSet, 'mapping_export')
router.register(r'import/configuration/check-duplicates', configuration_export.ConfigurationDuplicateCheckViewSet,
                'configuration_import_check_duplicates')

router.register(r'reconciliation/process-bank-file', reconciliation.ProcessBankFileForReconcileViewSet,
                'process_bank_file_for_reconcile')
router.register(r'reconciliation/bank-field', reconciliation.ReconciliationBankFileFieldViewSet, 'bank_fields')
router.register(r'reconciliation/new-bank-field', reconciliation.ReconciliationNewBankFileFieldViewSet,
                'new_bank_fields')
router.register(r'reconciliation/complex-transaction-field',
                reconciliation.ReconciliationComplexTransactionFieldViewSet, 'complex_transaction_fields')

router.register(r'file-reports/file-report', file_reports.FileReportViewSet, 'file_reports')

router.register(r'configuration-sharing/shared-configuration-file',
                configuration_sharing.SharedConfigurationFileViewSet,
                'shared_configuration_file')  # Probably deprecated
router.register(r'configuration-sharing/invites', configuration_sharing.InviteToSharedConfigurationFileViewSet,
                'invites_to_shared_configuration_file')  # Probably deprecated

router.register(r'configuration-sharing/my-invites', configuration_sharing.MyInviteToSharedConfigurationFileViewSet,
                'my_invites_to_shared_configuration_file')  # Probably deprecated

router.register(r'pricing/instrument-pricing-scheme', pricing.InstrumentPricingSchemeViewSet,
                'pricing_instrument_pricing_scheme')
router.register(r'pricing/instrument-pricing-scheme-type', pricing.InstrumentPricingSchemeTypeViewSet,
                'pricing_instrument_pricing_scheme type')
router.register(r'pricing/currency-pricing-scheme', pricing.CurrencyPricingSchemeViewSet,
                'pricing_currency_pricing_scheme')
router.register(r'pricing/currency-pricing-scheme-type', pricing.CurrencyPricingSchemeTypeViewSet,
                'pricing_currency_pricing_scheme_type')

router.register(r'pricing/price-history-error-ev-group', pricing.PriceHistoryErrorEvGroupViewSet,
                'pricehistoryerrorevgroup')
router.register(r'pricing/price-history-error-ev', pricing.PriceHistoryErrorEvViewSet)
router.register(r'pricing/price-history-error', pricing.PriceHistoryErrorViewSet)
router.register(r'pricing/currency-history-error-ev-group', pricing.CurrencyHistoryErrorEvGroupViewSet,
                'currencyhistoryerrorevgroup')
router.register(r'pricing/currency-history-error-ev', pricing.CurrencyHistoryErrorEvViewSet)
router.register(r'pricing/currency-history-error', pricing.CurrencyHistoryErrorViewSet)

router.register(r'schedules/schedule', schedules.ScheduleViewSet)

router.register(r'system-messages/message', system_messages.SystemMessageViewSet)

router.register(r'credentials/credentials', credentials.CredentialsViewSet)  # Probably deprecated
router.register(r'integrations/data-provider', integrations.DataProviderViewSet)  # Probably deprecated

router.register(r'widgets/history/nav', widgets.HistoryNavViewSet, 'widgets_history_nav')
router.register(r'widgets/history/pl', widgets.HistoryPlViewSet, 'widgets_history_pl')
router.register(r'widgets/stats', widgets.StatsViewSet, 'widgets_stats')
router.register(r'widgets/collect-history', widgets.CollectHistoryViewSet, 'widgets_collect_history')
router.register(r'widgets/collect-balance-history', widgets.CollectBalanceHistoryViewSet,
                'widgets_collect_balance_history')
router.register(r'widgets/collect-pl-history', widgets.CollectPlHistoryViewSet, 'widgets_collect_pl_history')
router.register(r'widgets/collect-stats', widgets.CollectStatsViewSet, 'widgets_collect_stats')

router.register(r'debug/logs', common.DebugLogViewSet, 'debug_log')  # Deprecated
router.register(r'errors/error', ErrorRecordViewSet, 'error')

router.register(r'history/historical-record', history.HistoricalRecordViewSet, 'historical-record')

import poms.accounts.urls as account_router
import poms.portfolios.urls as portfolio_router
import poms.currencies.urls as currency_router
import poms.instruments.urls as instrument_router
import poms.transactions.urls as transaction_router
import poms.counterparties.urls as counterparty_router
import poms.strategies.urls as strategy_router
import poms.reports.urls as report_router
import poms.procedures.urls as procedure_router
import poms.ui.urls as ui_router
import poms.explorer.urls as explorer_router
import poms.vault.urls as vault_router
import poms.integrations.urls as integrations_router
import poms.csv_import.urls as csv_import_router
import poms.iam.urls as iam_router

urlpatterns = [
    re_path(r'^v1/accounts/', include(account_router.router.urls)),
    re_path(r'^v1/portfolios/', include(portfolio_router.router.urls)),
    re_path(r'^v1/currencies/', include(currency_router.router.urls)),
    re_path(r'^v1/instruments/', include(instrument_router.router.urls)),
    re_path(r'^v1/transactions/', include(transaction_router.router.urls)),
    re_path(r'^v1/counterparties/', include(counterparty_router.router.urls)),
    re_path(r'^v1/strategies/', include(strategy_router.router.urls)),
    re_path(r'^v1/reports/', include(report_router.router.urls)),
    re_path(r'^v1/procedures/', include(procedure_router.router.urls)),
    re_path(r'^v1/import/', include(integrations_router.router.urls)),
    re_path(r'^v1/import/', include(csv_import_router.router.urls)),
    re_path(r'^v1/ui/', include(ui_router.router.urls)),
    re_path(r'^v1/explorer/', include(explorer_router.router.urls)),
    re_path(r'^v1/vault/', include(vault_router.router.urls)),
    re_path(r'^v1/iam/', include(iam_router.router.urls)),
    re_path(r'^v1/', include(router.urls)),

    re_path(
        r'instruments/instrument-database-search',
        instruments.InstrumentDatabaseSearchViewSet.as_view(),
    ),

    # external callbacks
    re_path(r'internal/brokers/bloomberg/callback', csrf_exempt(pricing.PricingBrokerBloombergHandler.as_view())),
    re_path(r'internal/brokers/bloomberg-forwards/callback',
            csrf_exempt(pricing.PricingBrokerBloombergForwardsHandler.as_view())),
    re_path(r'internal/brokers/wtrade/callback', csrf_exempt(pricing.PricingBrokerWtradeHandler.as_view())),
    re_path(r'internal/brokers/cbonds/callback', csrf_exempt(pricing.PricingBrokerCbondsHandler.as_view())),
    re_path(r'internal/brokers/fx-cbonds/callback', csrf_exempt(pricing.PricingBrokerFxCbondsHandler.as_view())),
    re_path(r'internal/brokers/fixer/callback', csrf_exempt(pricing.PricingBrokerFixerHandler.as_view())),
    re_path(r'internal/brokers/alphav/callback', csrf_exempt(pricing.PricingBrokerAlphavHandler.as_view())),
    # re_path(r'internal/data/transactions/callback',
    #         csrf_exempt(integrations.TransactionFileResultUploadHandler.as_view())),
    re_path(r'internal/data/transactions/json', csrf_exempt(integrations.TransactionImportJson.as_view())),
    re_path(r'integrations/superset/get-security-token', csrf_exempt(integrations.SupersetGetSecurityToken.as_view())),
    re_path(r'instruments/instrument-external-api', csrf_exempt(instruments.InstrumentExternalAPIViewSet.as_view())),
    re_path(r'instruments/fdb-create-from-callback',
            csrf_exempt(instruments.InstrumentFDBCreateFromCallbackViewSet.as_view())),

    re_path(r'^authorizer/token-auth/', ObtainAuthToken.as_view(), name='api-token-auth'),
    re_path(r'^authorizer/set-token-auth/', SetAuthToken.as_view(), name='set-token-auth'),
    re_path(r'^authorizer/create-user/', CreateUser.as_view(), name='create-user'),  # TODO deprecated delete soon
    re_path(r'^authorizer/create-master-user/', CreateMasterUser.as_view(), name='create-master-user'),
    # TODO deprecated delete soon
    re_path(r'^authorizer/rename-master-user/', RenameMasterUser.as_view(), name='rename-master-user'),
    re_path(r'^authorizer/create-member/', CreateMember.as_view(), name='create-member'),
    re_path(r'^authorizer/delete-member/', DeleteMember.as_view(), name='delete-member'),
    re_path(r'^authorizer/master-user-change-owner/', MasterUserChangeOwner.as_view(), name='master-user-change-owner'),


    re_path(r'^storage/(?P<filepath>.+)', ExplorerServeFileViewSet.as_view({'get': 'retrieve'}), name='storage'),
]

# if 'rest_framework_swagger' in settings.INSTALLED_APPS:
#     urlpatterns += [
#         re_path(r'^schema/', api.SchemaViewSet.as_view()),
#     ]

if settings.SERVER_TYPE == 'local':
    import debug_toolbar

    urlpatterns += [
        re_path('__debug__/', include(debug_toolbar.urls)),
    ]

    urlpatterns += [
        re_path(r'^dev/auth/', include('rest_framework.urls', namespace='rest_framework')),
    ]
