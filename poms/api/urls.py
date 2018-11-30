from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import url, include
from rest_framework import routers

import poms.accounts.views as accounts
import poms.api.views as api
import poms.audit.views as audit
import poms.chats.views as chats
import poms.counterparties.views as counterparties
import poms.currencies.views as currencies
import poms.http_sessions.views as sessions
import poms.instruments.views as instruments
import poms.integrations.views as integrations
import poms.notifications.views as notifications
import poms.portfolios.views as portfolios
import poms.reports.views as reports
import poms.strategies.views as strategies
import poms.tags.views as tags
import poms.transactions.views as transactions
import poms.ui.views as ui
import poms.users.views as users
import poms.data_import.views as data_import

import poms.csv_import.views as csv_import

import poms.configuration_export.views as configuration_export

router = routers.DefaultRouter()
router.register(r'users/login', users.LoginViewSet, 'login')
router.register(r'users/logout', users.LogoutViewSet, 'logout')
router.register(r'users/ping', users.PingViewSet, "ping")
router.register(r'users/protected-ping', users.ProtectedPingViewSet, "protectedping")

router.register(r'users/reset-password/confirm', users.ResetPasswordConfirmViewSet, "resetpasswordconfirm"),
router.register(r'users/reset-password', users.ResetPasswordRequestTokenViewSet, "resetpasswordrequest"),

router.register(r'users/user-register', users.UserRegisterViewSet, 'userregister')
router.register(r'users/master-user-create', users.MasterUserCreateViewSet, 'masterusercreate')
router.register(r'users/user', users.UserViewSet)
router.register(r'users/master-user', users.MasterUserViewSet)
router.register(r'users/master-user-leave', users.LeaveMasterUserViewSet, 'masteruserleave')
router.register(r'users/invite-to-master-user', users.InviteToMasterUserViewSet, 'invitetomasteruser')
router.register(r'users/create-invite-to-master-user', users.CreateInviteViewSet, 'createinvitetomasteruser')
router.register(r'users/member', users.MemberViewSet)
router.register(r'users/group', users.GroupViewSet)
router.register(r'users/language', api.LanguageViewSet, 'language')
router.register(r'users/timezone', api.TimezoneViewSet, 'timezone')

router.register(r'accounts/account-type-ev-group', accounts.AccountTypeEvGroupViewSet)
router.register(r'accounts/account-type', accounts.AccountTypeViewSet)

# router.register(r'accounts/account-attribute-type', accounts.AccountAttributeTypeViewSet)
router.register(r'accounts/account-attribute-type', accounts.AccountAttributeTypeViewSet, 'accountattributetype')
# router.register(r'accounts/account-classifier', accounts.AccountClassifierViewSet)
router.register(r'accounts/account-classifier', accounts.AccountClassifierViewSet, 'accountclassifier')
router.register(r'accounts/account-ev-group', accounts.AccountEvGroupViewSet, 'accountevgroup')
router.register(r'accounts/account', accounts.AccountViewSet)

# router.register(r'counterparties/counterparty-attribute-type', counterparties.CounterpartyAttributeTypeViewSet)
router.register(r'counterparties/counterparty-attribute-type', counterparties.CounterpartyAttributeTypeViewSet,
                'counterpartyattributetype')
# router.register(r'counterparties/counterparty-classifier', counterparties.CounterpartyClassifierViewSet)
router.register(r'counterparties/counterparty-classifier', counterparties.CounterpartyClassifierViewSet,
                'counterpartyclassifier')
router.register(r'counterparties/counterparty-group-ev-group', counterparties.CounterpartyGroupEvGroupViewSet,
                'counterpartygroupevgroup')
router.register(r'counterparties/counterparty-group', counterparties.CounterpartyGroupViewSet)

router.register(r'counterparties/counterparty-ev-group', counterparties.CounterpartyEvGroupViewSet,
                'counterpartyevgroup')
router.register(r'counterparties/counterparty', counterparties.CounterpartyViewSet)

# router.register(r'counterparties/responsible-attribute-type', counterparties.ResponsibleAttributeTypeViewSet)
router.register(r'counterparties/responsible-attribute-type', counterparties.ResponsibleAttributeTypeViewSet,
                'responsibleattributetype')
# router.register(r'counterparties/responsible-classifier', counterparties.ResponsibleClassifierViewSet)
router.register(r'counterparties/responsible-classifier', counterparties.ResponsibleClassifierViewSet,
                'responsibleclassifier')

router.register(r'counterparties/responsible-group-ev-group', counterparties.ResponsibleGroupEvGroupViewSet)
router.register(r'counterparties/responsible-group', counterparties.ResponsibleGroupViewSet)

router.register(r'counterparties/responsible-ev-group', counterparties.ResponsibleEvGroupViewSet, 'responsibleevgroup')
router.register(r'counterparties/responsible', counterparties.ResponsibleViewSet)

router.register(r'currencies/currency-ev-group', currencies.CurrencyEvGroupViewSet, 'currencyevgroup')
router.register(r'currencies/currency', currencies.CurrencyViewSet)

router.register(r'currencies/currency-history-ev-group', currencies.CurrencyHistoryEvGroupViewSet)
router.register(r'currencies/currency-attribute-type', currencies.CurrencyAttributeTypeViewSet, 'currencyattributetype')
router.register(r'currencies/currency-history', currencies.CurrencyHistoryViewSet)

router.register(r'instruments/instrument-class', instruments.InstrumentClassViewSet)
router.register(r'instruments/daily-pricing-model', instruments.DailyPricingModelViewSet)
router.register(r'instruments/accrual-calculation-model', instruments.AccrualCalculationModelClassViewSet)
router.register(r'instruments/payment-size-detail', instruments.PaymentSizeDetailViewSet)
router.register(r'instruments/periodicity', instruments.PeriodicityViewSet)
router.register(r'instruments/cost-method', instruments.CostMethodViewSet)
router.register(r'instruments/pricing-policy-ev-group', instruments.PricingPolicyEvGroupViewSet)
router.register(r'instruments/pricing-policy', instruments.PricingPolicyViewSet)

router.register(r'instruments/event-schedule-config', instruments.EventScheduleConfigViewSet)

router.register(r'instruments/instrument-type-ev-group', instruments.InstrumentTypeEvGroupViewSet)
router.register(r'instruments/instrument-type', instruments.InstrumentTypeViewSet)

# router.register(r'instruments/instrument-attribute-type', instruments.InstrumentAttributeTypeViewSet)
router.register(r'instruments/instrument-attribute-type', instruments.InstrumentAttributeTypeViewSet,
                'instrumentattributetype')
# router.register(r'instruments/instrument-classifier', instruments.InstrumentClassifierViewSet)
router.register(r'instruments/instrument-classifier', instruments.InstrumentClassifierViewSet, 'instrumentclassifier')

router.register(r'instruments/instrument-ev-group', instruments.InstrumentEvGroupViewSet)
router.register(r'instruments/instrument', instruments.InstrumentViewSet)

router.register(r'instruments/price-history-ev-group', instruments.PriceHistoryEvGroupViewSet, 'instrumentevgroup')
router.register(r'instruments/price-history', instruments.PriceHistoryViewSet)

router.register(r'instruments/generated-event', instruments.GeneratedEventViewSet)

# router.register(r'portfolios/portfolio-attribute-type', portfolios.PortfolioAttributeTypeViewSet)
router.register(r'portfolios/portfolio-attribute-type', portfolios.PortfolioAttributeTypeViewSet,
                'portfolioattributetype')
# router.register(r'portfolios/portfolio-classifier', portfolios.PortfolioClassifierViewSet)
router.register(r'portfolios/portfolio-classifier', portfolios.PortfolioClassifierViewSet, 'portfolioclassifier')

router.register(r'portfolios/portfolio-ev-group', portfolios.PortfolioEvGroupViewSet, 'portfolioevgroup')
router.register(r'portfolios/portfolio', portfolios.PortfolioViewSet)

router.register(r'strategies/1/group-ev-group', strategies.Strategy1GroupEvGroupViewSet, 'strategy1groupevgroup')
router.register(r'strategies/1/group', strategies.Strategy1GroupViewSet)

router.register(r'strategies/1/subgroup-ev-group', strategies.Strategy1SubgroupEvGroupViewSet,
                'strategy1subggroupevgroup')
router.register(r'strategies/1/subgroup', strategies.Strategy1SubgroupViewSet)

router.register(r'strategies/1/strategy-ev-group', strategies.Strategy1EvGroupViewSet, 'strategy1evgroup')
router.register(r'strategies/1/strategy', strategies.Strategy1ViewSet)

router.register(r'strategies/2/group-ev-group', strategies.Strategy2GroupEvGroupViewSet, 'strategy2groupevgroup')
router.register(r'strategies/2/group', strategies.Strategy2GroupViewSet)

router.register(r'strategies/2/subgroup-ev-group', strategies.Strategy2SubgroupEvGroupViewSet,
                'strategy2subggroupevgroup')
router.register(r'strategies/2/subgroup', strategies.Strategy2SubgroupViewSet)

router.register(r'strategies/2/strategy-ev-group', strategies.Strategy2EvGroupViewSet, 'strategy2evgroup')
router.register(r'strategies/2/strategy', strategies.Strategy2ViewSet)

router.register(r'strategies/3/group-ev-group', strategies.Strategy3GroupEvGroupViewSet, 'strategy3groupevgroup')
router.register(r'strategies/3/group', strategies.Strategy3GroupViewSet)

router.register(r'strategies/3/subgroup-ev-group', strategies.Strategy3SubgroupEvGroupViewSet,
                'strategy3subggroupevgroup')
router.register(r'strategies/3/subgroup', strategies.Strategy3SubgroupViewSet)

router.register(r'strategies/3/strategy-ev-group', strategies.Strategy3EvGroupViewSet, 'strategy3evgroup')
router.register(r'strategies/3/strategy', strategies.Strategy3ViewSet)

router.register(r'tags/tag', tags.TagViewSet)

router.register(r'transactions/event-class', transactions.EventClassViewSet)
router.register(r'transactions/notification-class', transactions.NotificationClassViewSet)
router.register(r'transactions/transaction-class', transactions.TransactionClassViewSet)

router.register(r'transactions/transaction-type-group-ev-group', transactions.TransactionTypeGroupEvGroupViewSet,
                'transactiontypegroupevgroup')
router.register(r'transactions/transaction-type-group', transactions.TransactionTypeGroupViewSet)
router.register(r'transactions/transaction-type-ev-group', transactions.TransactionTypeEvGroupViewSet,
                'transactiontypeevgroup')
router.register(r'transactions/transaction-type', transactions.TransactionTypeViewSet)
# router.register(r'transactions/transaction-attribute-type', transactions.TransactionAttributeTypeViewSet)
router.register(r'transactions/transaction-attribute-type', transactions.TransactionAttributeTypeViewSet,
                'transactionattributetype')
# router.register(r'transactions/transaction-classifier', transactions.TransactionClassifierViewSet)
router.register(r'transactions/transaction-classifier', transactions.TransactionClassifierViewSet,
                'transactionclassifier')

router.register(r'transactions/transaction-ev-group', transactions.TransactionEvGroupViewSet, 'transactionevgroup')
router.register(r'transactions/transaction', transactions.TransactionViewSet)

router.register(r'transactions/complex-transaction-attribute-type', transactions.ComplexTransactionAttributeTypeViewSet,
                'complextransactionattributetype')

router.register(r'transactions/complex-transaction-ev-group', transactions.ComplexTransactionEvGroupViewSet,
                'complextransactionevgroup')
router.register(r'transactions/complex-transaction', transactions.ComplexTransactionViewSet)

router.register(r'ui/list-layout', ui.ListLayoutViewSet)
router.register(r'ui/edit-layout', ui.EditLayoutViewSet)
router.register(r'ui/template-list-layout', ui.TemplateListLayoutViewSet)
router.register(r'ui/template-edit-layout', ui.TemplateEditLayoutViewSet)
router.register(r'ui/bookmark', ui.BookmarkViewSet)

router.register(r'reports/custom-field', reports.CustomFieldViewSet)
router.register(r'reports/report', reports.BalanceReportViewSet, "report")
router.register(r'reports/balance-report', reports.BalanceReportViewSet, "balance-report")
router.register(r'reports/pl-report', reports.PLReportViewSet, "pl-report")
router.register(r'reports/transaction-report', reports.TransactionReportViewSet, "transaction-report")
router.register(r'reports/cash-flow-projection-report', reports.CashFlowProjectionReportViewSet,
                "cash-flow-projection-report")
router.register(r'reports/performance-report', reports.PerformanceReportViewSet, "performance-report")

router.register(r'notifications/notification', notifications.NotificationViewSet)

router.register(r'chats/thread-group', chats.ThreadGroupViewSet)
router.register(r'chats/thread', chats.ThreadViewSet)
router.register(r'chats/message', chats.MessageViewSet)
router.register(r'chats/direct-message', chats.DirectMessageViewSet)

router.register(r'security/http-session', sessions.SessionViewSet)
router.register(r'audit/auth-log', audit.AuthLogViewSet)
router.register(r'audit/history', audit.ObjectHistory4ViewSet)

router.register(r'import/config', integrations.ImportConfigViewSet)

router.register(r'import/provider', integrations.ProviderClassViewSet)
router.register(r'import/factor-schedule-download-method', integrations.FactorScheduleDownloadMethodViewSet)
router.register(r'import/accrual-schedule-download-method', integrations.AccrualScheduleDownloadMethodViewSet)

router.register(r'import/instrument-scheme', integrations.InstrumentDownloadSchemeViewSet)
router.register(r'import/price-download-scheme', integrations.PriceDownloadSchemeViewSet)

router.register(r'import/currency-mapping', integrations.CurrencyMappingViewSet)
router.register(r'import/instrument-type-mapping', integrations.InstrumentTypeMappingViewSet)
router.register(r'import/instrument-attribute-value-mapping', integrations.InstrumentAttributeValueMappingViewSet)
router.register(r'import/accrual-calculation-model-mapping', integrations.AccrualCalculationModelMappingViewSet)
router.register(r'import/periodicity-mapping', integrations.PeriodicityMappingViewSet)
router.register(r'import/account-mapping', integrations.AccountMappingViewSet)
router.register(r'import/account-classifier-mapping', integrations.AccountClassifierMappingViewSet)
router.register(r'import/instrument-mapping', integrations.InstrumentMappingViewSet)
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

router.register(r'import/instrument', integrations.ImportInstrumentViewSet, 'importinstrument')
router.register(r'import/pricing', integrations.ImportPricingViewSet, 'importpricing')
router.register(r'import/pricing-automated-schedule', integrations.PricingAutomatedScheduleViewSet)

router.register(r'import/task', integrations.TaskViewSet)

router.register(r'import/complex-transaction-import-scheme', integrations.ComplexTransactionImportSchemeViewSet)
router.register(r'import/complex-transaction-csv-file-import', integrations.ComplexTransactionCsvFileImportViewSet,
                'complextransactioncsvfileimport')

router.register(r'utils/expression', api.ExpressionViewSet, 'expression')

router.register(r'import/data', data_import.DataImportViewSet, 'data_import')
router.register(r'import/data_schema', data_import.DataImportSchemaViewSet, 'data_import_schema')
router.register(r'import/schema_fields', data_import.DataImportSchemaFieldsViewSet, 'data_import_schema_fields')
router.register(r'import/schema_models', data_import.DataImportSchemaModelsViewSet, 'data_import_schema_models')
router.register(r'import/schema_matching', data_import.DataImportSchemaMatchingViewSet, 'data_import_schema_matching')
router.register(r'import/content_type', data_import.ContentTypeViewSet, 'data_import_content_types')

# router.register(r'import/csv', data_import.ContentTypeViewSet, 'data_import_content_types')
router.register(r'import/csv/scheme', csv_import.SchemeViewSet, 'import_csv_scheme')
router.register(r'import/csv', csv_import.CsvDataImportViewSet, 'import_csv')

router.register(r'export/configuration', configuration_export.ConfigurationExportViewSet, 'configuration_export')
router.register(r'export/mapping', configuration_export.MappingExportViewSet, 'mapping_export')

urlpatterns = [
    url(r'^v1/', include(router.urls, namespace='v1')),
]

if settings.DEV:
    urlpatterns += [
        url(r'^dev/auth/', include('rest_framework.urls', namespace='rest_framework')),
    ]

if 'rest_framework_swagger' in settings.INSTALLED_APPS:
    urlpatterns += [
        url(r'^schema/', api.SchemaViewSet.as_view()),
    ]
