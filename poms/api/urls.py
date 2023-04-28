from __future__ import unicode_literals

from django.conf import settings
from django.urls import re_path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework import routers

import poms.accounts.views as accounts
import poms.api.views as api
import poms.celery_tasks.views as celery_tasks
import poms.common.views as common
import poms.complex_import.views as complex_import
import poms.configuration_export.views as configuration_export
import poms.configuration_import.views as configuration_import
import poms.configuration_sharing.views as configuration_sharing
import poms.counterparties.views as counterparties
import poms.credentials.views as credentials
import poms.csv_import.views as csv_import
import poms.currencies.views as currencies
import poms.explorer.views as explorer
import poms.file_reports.views as file_reports
import poms.history.views as history
import poms.instruments.views as instruments
import poms.integrations.views as integrations
import poms.notifications.views as notifications
import poms.portfolios.views as portfolios
import poms.pricing.views as pricing
import poms.procedures.views as procedures
import poms.reconciliation.views as reconciliation
import poms.reference_tables.views as reference_table
import poms.reports.views as reports
import poms.schedules.views as schedules
import poms.strategies.views as strategies
import poms.system.views as system
import poms.system_messages.views as system_messages
import poms.transactions.views as transactions
import poms.ui.views as ui
import poms.users.views as users
import poms.configuration.views as configuration
import poms.widgets.views as widgets
from finmars_standardized_errors.views import ErrorRecordViewSet
from poms.auth_tokens.views import ObtainAuthToken, SetAuthToken, CreateUser, CreateMasterUser, CreateMember, \
    DeleteMember, RenameMasterUser, MasterUserChangeOwner

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
router.register(r'users/group', users.GroupViewSet)
router.register(r'users/language', api.LanguageViewSet, 'language')
router.register(r'users/timezone', api.TimezoneViewSet, 'timezone')
router.register(r'users/ecosystem-default', users.EcosystemDefaultViewSet, 'ecosystemdefault')
router.register(r'users/usercode-prefix', users.UsercodePrefixViewSet, 'usercodeprefix')



router.register(r'reference-tables/reference-table', reference_table.ReferenceTableViewSet, 'reference_table')
router.register(r'active_processes/active_processes', celery_tasks.CeleryTaskViewSet, 'celery_tasks')  # deprecated
router.register(r'tasks/task', celery_tasks.CeleryTaskViewSet, 'celery_tasks')


router.register(r'configuration/configuration', configuration.ConfigurationViewSet)


router.register(r'transactions/bank-file', integrations.TransactionFileResultViewSet)  # deprecated?

router.register(r'specific-data/values-for-select', common.ValuesForSelectViewSet, 'valuesforselect')

router.register(r'ui/portal-interface-access', ui.PortalInterfaceAccessViewSet)
router.register(r'ui/list-layout', ui.ListLayoutViewSet)
router.register(r'ui/list-layout-light', ui.ListLayoutLightViewSet)  # deprecated
router.register(r'ui/template-layout', ui.TemplateLayoutViewSet)
router.register(r'ui/dashboard-layout', ui.DashboardLayoutViewSet)
router.register(r'ui/edit-layout', ui.EditLayoutViewSet)
router.register(r'ui/bookmark', ui.BookmarkViewSet)
# router.register(r'ui/configuration', ui.ConfigurationViewSet)
router.register(r'ui/configuration-export-layout', ui.ConfigurationExportLayoutViewSet)
router.register(r'ui/complex-transaction-user-field', ui.ComplexTransactionUserFieldViewSet)
router.register(r'ui/transaction-user-field', ui.TransactionUserFieldViewSet)
router.register(r'ui/instrument-user-field', ui.InstrumentUserFieldViewSet)
router.register(r'ui/entity-tooltip', ui.EntityTooltipViewSet)
router.register(r'ui/context-menu-layout', ui.ContextMenuLayoutViewSet)
router.register(r'ui/color-palette', ui.ColorPaletteViewSet)
router.register(r'ui/cross-entity-attribute-extension', ui.CrossEntityAttributeExtensionViewSet)
router.register(r'ui/column-sort-data', ui.ColumnSortDataViewSet)
router.register(r'ui/system-attributes', ui.SystemAttributesViewSet, basename="System attributes")

router.register(r'reports/summary', reports.SummaryViewSet, 'indicators')
router.register(r'reports/balance-report', reports.BalanceReportViewSet, "balance-report")
router.register(r'reports/balance-report-sql', reports.BalanceReportViewSet, "balance-report-sync-sql")  # deprecated
router.register(r'reports/balance-report/custom-field', reports.BalanceReportCustomFieldViewSet,
                'balance-report-custom-field')

router.register(r'reports/pl-report', reports.PLReportViewSet, "pl-report")
router.register(r'reports/pl-report-sql', reports.PLReportViewSet, "pl-report-sync-sql")  # deprecated, delete soon
router.register(r'reports/pl-report/custom-field', reports.PLReportCustomFieldViewSet, 'pl-report-custom-field')

router.register(r'reports/transaction-report', reports.TransactionReportViewSet, "transaction-report")
router.register(r'reports/transaction-report-sql', reports.TransactionReportViewSet, "transaction-report-sync-sql")

router.register(r'reports/transaction-report/custom-field', reports.TransactionReportCustomFieldViewSet,
                'transaction-report-custom-field')

router.register(r'reports/performance-report', reports.PerformanceReportViewSet, "performance-report")

router.register(r'reports/price-history-check-sql', reports.PriceHistoryCheckViewSet,
                "price-history-check-sql")  # deprecated
router.register(r'reports/price-history-check', reports.PriceHistoryCheckViewSet, "price-history-check")

router.register(r'notifications/notification', notifications.NotificationViewSet)

router.register(r'data-provider/bloomberg/credential', integrations.BloombergDataProviderCredentialViewSet)
router.register(r'import/config', integrations.ImportConfigViewSet)

router.register(r'import/provider', integrations.ProviderClassViewSet)
router.register(r'import/factor-schedule-download-method', integrations.FactorScheduleDownloadMethodViewSet)
router.register(r'import/accrual-schedule-download-method', integrations.AccrualScheduleDownloadMethodViewSet)

router.register(r'import/instrument-scheme', integrations.InstrumentDownloadSchemeViewSet)
router.register(r'import/instrument-scheme-light', integrations.InstrumentDownloadSchemeLightViewSet)  # DEPRECATED
router.register(r'import/currency-mapping', integrations.CurrencyMappingViewSet)
router.register(r'import/pricing-policy-mapping', integrations.PricingPolicyMappingViewSet)
router.register(r'import/instrument-type-mapping', integrations.InstrumentTypeMappingViewSet)
router.register(r'import/instrument-attribute-value-mapping', integrations.InstrumentAttributeValueMappingViewSet)
router.register(r'import/accrual-calculation-model-mapping', integrations.AccrualCalculationModelMappingViewSet)
router.register(r'import/periodicity-mapping', integrations.PeriodicityMappingViewSet)
router.register(r'import/account-mapping', integrations.AccountMappingViewSet)
router.register(r'import/account-classifier-mapping', integrations.AccountClassifierMappingViewSet)
router.register(r'import/account-type-mapping', integrations.AccountTypeMappingViewSet)
router.register(r'import/instrument-mapping', integrations.InstrumentMappingViewSet)
router.register(r'import/instrument-classifier-mapping', integrations.InstrumentClassifierMappingViewSet)
router.register(r'import/counterparty-mapping', integrations.CounterpartyMappingViewSet)
router.register(r'import/counterparty-classifier-mapping', integrations.CounterpartyClassifierMappingViewSet)
router.register(r'import/responsible-mapping', integrations.ResponsibleMappingViewSet)
router.register(r'import/responsible-classifier-mapping', integrations.ResponsibleClassifierMappingViewSet)
router.register(r'import/portfolio-mapping', integrations.PortfolioMappingViewSet)
router.register(r'import/portfolio-classifier-mapping', integrations.PortfolioClassifierMappingViewSet)
router.register(r'import/strategy1-mapping', integrations.Strategy1MappingViewSet)
router.register(r'import/strategy2-mapping', integrations.Strategy2MappingViewSet)
router.register(r'import/strategy3-mapping', integrations.Strategy3MappingViewSet)
router.register(r'import/daily-pricing-model-mapping', integrations.DailyPricingModelMappingViewSet)
router.register(r'import/payment-size-detail-mapping', integrations.PaymentSizeDetailMappingViewSet)
router.register(r'import/price-download-scheme-mapping', integrations.PriceDownloadSchemeMappingViewSet)
router.register(r'import/pricing-condition-mapping', integrations.PricingConditionMappingViewSet)

router.register(r'import/instrument', integrations.ImportInstrumentViewSet, 'importinstrument')
router.register(r'import/finmars-database/instrument', integrations.ImportInstrumentDatabaseViewSet,
                'importinstrumentdatabase')
router.register(r'import/finmars-database/currency', integrations.ImportCurrencyCbondsViewSet, 'importcurrencycbonds')
router.register(r'import/unified-data-provider', integrations.ImportUnifiedDataProviderViewSet,
                'importunifieddataprovider')
router.register(r'import/test-certificate', integrations.TestCertificateViewSet, 'testcertificate')

router.register(r'import/complex-transaction-import-scheme', integrations.ComplexTransactionImportSchemeViewSet)
router.register(r'import/complex-transaction-import-scheme-light',
                integrations.ComplexTransactionImportSchemeLightViewSet)  # DEPRECATED
router.register(r'import/complex-transaction-csv-file-import', integrations.ComplexTransactionCsvFileImportViewSet,
                'complextransactioncsvfileimport')

router.register(r'import/transaction-import', integrations.TransactionImportViewSet,
                'transactionimportviewset')
router.register(r'import/simple-import', csv_import.CsvDataImportViewSet,
                'simpleimportviewset')

router.register(r'import/complex-transaction-preprocess-file', integrations.ComplexTransactionFilePreprocessViewSet,
                'complextransactionfilepreprocessviewSet')

router.register(r'import/complex-transaction-csv-file-import-validate',
                integrations.ComplexTransactionCsvFileImportValidateViewSet,
                'complextransactioncsvfileimportvalidate')

router.register(r'utils/expression', api.ExpressionViewSet, 'expression')
router.register(r'utils/stats', api.StatsViewSet, 'stats')
router.register(r'utils/system-info', api.SystemInfoViewSet, 'system-info')
router.register(r'utils/system-logs', api.SystemLogsViewSet, 'system-logs')
router.register(r'utils/calendar-events', api.CalendarEventsViewSet, 'calendar-events')
router.register(r'utils/tables-size', api.TablesSizeViewSet, 'tables-size')
router.register(r'utils/recycle-bin', api.RecycleBinViewSet, 'recycle-bin')
router.register(r'utils/universal-input', api.UniversalInputViewSet, 'universalInput')

router.register(r'import/csv/scheme', csv_import.SchemeViewSet, 'import_csv_scheme')
router.register(r'import/csv/scheme-light', csv_import.SchemeLightViewSet, 'import_csv_scheme_light')  # deprecated
router.register(r'import/csv', csv_import.CsvDataImportViewSet, 'import_csv')

router.register(r'import/complex/scheme', complex_import.ComplexImportSchemeViewSet, 'import_complex_scheme')
router.register(r'import/complex', complex_import.ComplexImportViewSet, 'import_complex')

router.register(r'import/configuration-json', configuration_import.ConfigurationImportAsJsonViewSet,
                'configuration_import')

# DEPRECATED
# router.register(r'import/generate-configuration-entity-archetype', configuration_import.GenerateConfigurationEntityArchetypeViewSet, 'generate_configuration_entity_archetype')

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
                configuration_sharing.SharedConfigurationFileViewSet, 'shared_configuration_file')
router.register(r'configuration-sharing/invites', configuration_sharing.InviteToSharedConfigurationFileViewSet,
                'invites_to_shared_configuration_file')

router.register(r'configuration-sharing/my-invites', configuration_sharing.MyInviteToSharedConfigurationFileViewSet,
                'my_invites_to_shared_configuration_file')

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

router.register(r'system-messages/message', system_messages.MessageViewSet)

router.register(r'procedures/pricing-procedure', procedures.PricingProcedureViewSet, 'pricing_procedure')
router.register(r'procedures/pricing-procedure-instance', procedures.PricingProcedureInstanceViewSet,
                'pricing_procedure_instance')
router.register(r'procedures/pricing-parent-procedure-instance', procedures.PricingParentProcedureInstanceViewSet,
                'pricing_parent_procedure_instance')

router.register(r'procedures/request-data-procedure', procedures.RequestDataFileProcedureViewSet)
router.register(r'procedures/data-procedure', procedures.RequestDataFileProcedureViewSet)
router.register(r'procedures/data-procedure-instance', procedures.RequestDataFileProcedureInstanceViewSet)

router.register(r'procedures/expression-procedure', procedures.ExpressionProcedureViewSet)

router.register(r'credentials/credentials', credentials.CredentialsViewSet)
router.register(r'integrations/data-provider', integrations.DataProviderViewSet)

router.register(r'widgets/history/nav', widgets.HistoryNavViewSet, 'widgets_history_nav')
router.register(r'widgets/history/pl', widgets.HistoryPlViewSet, 'widgets_history_pl')
router.register(r'widgets/stats', widgets.StatsViewSet, 'widgets_stats')
router.register(r'widgets/collect-history', widgets.CollectHistoryViewSet, 'widgets_collect_history')
router.register(r'widgets/collect-balance-history', widgets.CollectBalanceHistoryViewSet,
                'widgets_collect_balance_history')
router.register(r'widgets/collect-pl-history', widgets.CollectPlHistoryViewSet, 'widgets_collect_pl_history')
router.register(r'widgets/collect-stats', widgets.CollectStatsViewSet, 'widgets_collect_stats')

router.register(r'explorer/explorer', explorer.ExplorerViewSet, 'explorer')
router.register(r'explorer/view', explorer.ExplorerViewFileViewSet, 'explorer_view')
router.register(r'explorer/upload', explorer.ExplorerUploadViewSet, 'explorer_upload')
router.register(r'explorer/delete', explorer.ExplorerDeleteViewSet, 'explorer_delete')
router.register(r'explorer/create-folder', explorer.ExplorerCreateFolderViewSet, 'explorer_create_folder')
router.register(r'explorer/delete-folder', explorer.ExplorerDeleteFolderViewSet, 'explorer_delete_folder')
router.register(r'explorer/download-folder-as-zip', explorer.DownloadFolderAsZipViewSet, 'download_folder_as_zip')

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

urlpatterns = [
    re_path(r'^v1/accounts/', include(account_router.router.urls)),
    re_path(r'^v1/portfolios/', include(portfolio_router.router.urls)),
    re_path(r'^v1/currencies/', include(currency_router.router.urls)),
    re_path(r'^v1/instruments/', include(instrument_router.router.urls)),
    re_path(r'^v1/transactions/', include(transaction_router.router.urls)),
    re_path(r'^v1/counterparties/', include(counterparty_router.router.urls)),
    re_path(r'^v1/strategies/', include(strategy_router.router.urls)),
    re_path(r'^v1/', include(router.urls)),

    # external callbacks

    re_path(r'instruments/instrument-database-search', instruments.InstrumentDatabaseSearchViewSet.as_view()),
    re_path(r'currencies/currency-database-search', currencies.CurrencyDatabaseSearchViewSet.as_view()),
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
