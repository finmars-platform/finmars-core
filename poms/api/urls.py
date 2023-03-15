from __future__ import unicode_literals

from django.conf import settings
from django.urls import re_path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework import routers

import poms.accounts.views as accounts
import poms.api.views as api
import poms.audit.views as audit
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
import poms.widgets.views as widgets
from finmars_standardized_errors.views import ErrorRecordViewSet
from poms.auth_tokens.views import ObtainAuthToken, SetAuthToken, CreateUser, CreateMasterUser, CreateMember, \
    DeleteMember, RenameMasterUser, MasterUserChangeOwner

router = routers.DefaultRouter()

router.register(r'system/ecosystem-configuration', system.EcosystemConfigurationViewSet, 'ecosystemconfiguration')

# router.register(r'users/login', users.LoginViewSet, 'login')
# router.register(r'users/logout', users.LogoutViewSet, 'logout')
router.register(r'users/ping', users.PingViewSet, "ping")
# router.register(r'users/protected-ping', users.ProtectedPingViewSet, "protectedping")
# router.register(r'users/two-factor', users.OtpTokenViewSet, "otptoken")

# router.register(r'users/reset-password/confirm', users.ResetPasswordConfirmViewSet, "resetpasswordconfirm"),
# router.register(r'users/reset-password', users.ResetPasswordRequestTokenViewSet, "resetpasswordrequest"),

# router.register(r'users/user-register', users.UserRegisterViewSet, 'userregister')
# router.register(r'users/master-user-create', users.MasterUserCreateViewSet, 'masterusercreate')
# router.register(r'users/master-user-copy', users.MasterUserCopyViewSet, 'masterusercopy')
# router.register(r'users/master-user-check-uniqueness', users.MasterUserCreateCheckUniquenessViewSet,
#                 'masterusercreatecheckuniqueness')
router.register(r'users/user', users.UserViewSet)
router.register(r'users/user-member', users.UserMemberViewSet, 'usermember')
router.register(r'users/master-user', users.MasterUserViewSet)
router.register(r'users/master-user-light', users.MasterUserLightViewSet, 'masteruserlight')
# router.register(r'users/master-user-leave', users.LeaveMasterUserViewSet, 'masteruserleave')
# router.register(r'users/master-user-delete', users.DeleteMasterUserViewSet, 'masteruserdelete')
router.register(r'users/get-current-master-user', users.GetCurrentMasterUserViewSet, 'getcurrentmasteruser')
# router.register(r'users/invite-from-master-user', users.InviteFromMasterUserViewSet, 'invitefrommasteruser')
# router.register(r'users/invite-to-user', users.InviteToUserViewSet, 'invitetouser')
# router.register(r'users/create-invite-to-user', users.CreateInviteViewSet, 'createinvitetouser')
router.register(r'users/member', users.MemberViewSet)
router.register(r'users/group', users.GroupViewSet)
router.register(r'users/language', api.LanguageViewSet, 'language')
router.register(r'users/timezone', api.TimezoneViewSet, 'timezone')
router.register(r'users/ecosystem-default', users.EcosystemDefaultViewSet, 'ecosystemdefault')
router.register(r'users/usercode-prefix', users.UsercodePrefixViewSet, 'usercodeprefix')

router.register(r'accounts/account-type-ev-group', accounts.AccountTypeEvGroupViewSet)
router.register(r'accounts/account-type', accounts.AccountTypeViewSet)
router.register(r'accounts/account-type-ev', accounts.AccountTypeEvViewSet)
router.register(r'accounts/account-type-attribute-type', accounts.AccountTypeAttributeTypeViewSet,
                'accounttypeattributetype')

# router.register(r'accounts/account-attribute-type', accounts.AccountAttributeTypeViewSet)
router.register(r'accounts/account-attribute-type', accounts.AccountAttributeTypeViewSet, 'accountattributetype')
# router.register(r'accounts/account-classifier', accounts.AccountClassifierViewSet)
router.register(r'accounts/account-classifier', accounts.AccountClassifierViewSet, 'accountclassifier')
router.register(r'accounts/account-ev-group', accounts.AccountEvGroupViewSet, 'accountevgroup')
router.register(r'accounts/account-ev', accounts.AccountEvViewSet, 'accountev')
router.register(r'accounts/account', accounts.AccountViewSet, 'account')
router.register(r'accounts/account-light', accounts.AccountLightViewSet, 'accountlight')

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
router.register(r'counterparties/counterparty', counterparties.CounterpartyViewSet, 'counterparty')
router.register(r'counterparties/counterparty-ev', counterparties.CounterpartyEvViewSet, 'counterpartyev')
router.register(r'counterparties/counterparty-light', counterparties.CounterpartyLightViewSet, 'counterpartylight')

# router.register(r'counterparties/responsible-attribute-type', counterparties.ResponsibleAttributeTypeViewSet)
router.register(r'counterparties/responsible-attribute-type', counterparties.ResponsibleAttributeTypeViewSet,
                'responsibleattributetype')
# router.register(r'counterparties/responsible-classifier', counterparties.ResponsibleClassifierViewSet)
router.register(r'counterparties/responsible-classifier', counterparties.ResponsibleClassifierViewSet,
                'responsibleclassifier')

router.register(r'counterparties/responsible-group-ev-group', counterparties.ResponsibleGroupEvGroupViewSet,
                'responsiblegroupev')
router.register(r'counterparties/responsible-group', counterparties.ResponsibleGroupViewSet, 'responsiblegroup')

router.register(r'counterparties/responsible-ev-group', counterparties.ResponsibleEvGroupViewSet, 'responsibleevgroup')
router.register(r'counterparties/responsible', counterparties.ResponsibleViewSet, 'responsible')
router.register(r'counterparties/responsible-ev', counterparties.ResponsibleEvViewSet, 'responsibleev')
router.register(r'counterparties/responsible-light', counterparties.ResponsibleLightViewSet, 'responsiblelight')

router.register(r'currencies/currency-ev-group', currencies.CurrencyEvGroupViewSet, 'currencyevgroup')
router.register(r'currencies/currency', currencies.CurrencyViewSet, 'currency')
router.register(r'currencies/currency-ev', currencies.CurrencyEvViewSet, 'currencyev')
router.register(r'currencies/currency-light', currencies.CurrencyLightViewSet, 'currencylight')

router.register(r'currencies/currency-history-ev-group', currencies.CurrencyHistoryEvGroupViewSet)
router.register(r'currencies/currency-attribute-type', currencies.CurrencyAttributeTypeViewSet, 'currencyattributetype')
router.register(r'currencies/currency-history-ev', currencies.CurrencyHistoryViewSet)
router.register(r'currencies/currency-history', currencies.CurrencyHistoryViewSet)

router.register(r'instruments/instrument-class', instruments.InstrumentClassViewSet)
router.register(r'instruments/daily-pricing-model', instruments.DailyPricingModelViewSet)
router.register(r'instruments/accrual-calculation-model', instruments.AccrualCalculationModelClassViewSet)
router.register(r'instruments/payment-size-detail', instruments.PaymentSizeDetailViewSet)
router.register(r'instruments/pricing-condition', instruments.PricingConditionViewSet)
router.register(r'instruments/country', instruments.CountryViewSet)
router.register(r'instruments/exposure-calculation-model', instruments.ExposureCalculationModelViewSet)
router.register(r'instruments/long-underlying-exposure', instruments.LongUnderlyingExposureViewSet)
router.register(r'instruments/short-underlying-exposure', instruments.ShortUnderlyingExposureViewSet)
router.register(r'instruments/periodicity', instruments.PeriodicityViewSet)
router.register(r'instruments/cost-method', instruments.CostMethodViewSet)
router.register(r'instruments/pricing-policy-ev-group', instruments.PricingPolicyEvGroupViewSet)
router.register(r'instruments/pricing-policy', instruments.PricingPolicyViewSet)
router.register(r'instruments/pricing-policy-light', instruments.PricingPolicyLightViewSet)

router.register(r'instruments/event-schedule-config', instruments.EventScheduleConfigViewSet)

router.register(r'instruments/instrument-type-ev-group', instruments.InstrumentTypeEvGroupViewSet)
router.register(r'instruments/instrument-type', instruments.InstrumentTypeViewSet)
router.register(r'instruments/instrument-type-ev', instruments.InstrumentTypeEvViewSet)
router.register(r'instruments/instrument-type-light', instruments.InstrumentTypeLightViewSet)
router.register(r'instruments/instrument-type-attribute-type', instruments.InstrumentTypeAttributeTypeViewSet)

# router.register(r'instruments/instrument-attribute-type', instruments.InstrumentAttributeTypeViewSet)
router.register(r'instruments/instrument-attribute-type', instruments.InstrumentAttributeTypeViewSet,
                'instrumentattributetype')
# router.register(r'instruments/instrument-classifier', instruments.InstrumentClassifierViewSet)
router.register(r'instruments/instrument-classifier', instruments.InstrumentClassifierViewSet, 'instrumentclassifier')

router.register(r'instruments/instrument-ev-group', instruments.InstrumentEvGroupViewSet)
router.register(r'instruments/instrument', instruments.InstrumentViewSet)
router.register(r'instruments/instrument-ev', instruments.InstrumentEvViewSet)
router.register(r'instruments/instrument-light', instruments.InstrumentLightViewSet)
router.register(r'instruments/instrument-for-select', instruments.InstrumentForSelectViewSet)

router.register(r'instruments/price-history-ev-group', instruments.PriceHistoryEvGroupViewSet, 'instrumentevgroup')
router.register(r'instruments/price-history-ev', instruments.PriceHistoryViewSet)
router.register(r'instruments/price-history', instruments.PriceHistoryViewSet)

router.register(r'instruments/generated-event-ev-group', instruments.GeneratedEventEvGroupViewSet)
router.register(r'instruments/generated-event-ev', instruments.GeneratedEventEvViewSet)
router.register(r'instruments/generated-event', instruments.GeneratedEventViewSet)

# router.register(r'portfolios/portfolio-attribute-type', portfolios.PortfolioAttributeTypeViewSet)
router.register(r'portfolios/portfolio-attribute-type', portfolios.PortfolioAttributeTypeViewSet,
                'portfolioattributetype')
# router.register(r'portfolios/portfolio-classifier', portfolios.PortfolioClassifierViewSet)
router.register(r'portfolios/portfolio-classifier', portfolios.PortfolioClassifierViewSet, 'portfolioclassifier')

router.register(r'portfolios/portfolio-ev-group', portfolios.PortfolioEvGroupViewSet, 'portfolioevgroup')
router.register(r'portfolios/portfolio-ev', portfolios.PortfolioEvViewSet, 'portfolio-ev')
router.register(r'portfolios/portfolio', portfolios.PortfolioViewSet, 'portfolio')
router.register(r'portfolios/portfolio-light', portfolios.PortfolioLightViewSet, 'portfoliolight')

router.register(r'portfolios/portfolio-register-attribute-type', portfolios.PortfolioRegisterAttributeTypeViewSet,
                'portfolioregisterattributetype')

router.register(r'portfolios/portfolio-register', portfolios.PortfolioRegisterViewSet, 'portfolioregister')
router.register(r'portfolios/portfolio-register-ev', portfolios.PortfolioRegisterEvViewSet, 'portfolioregisterev')
router.register(r'portfolios/portfolio-register-ev-group', portfolios.PortfolioRegisterEvGroupViewSet,
                'portfolioregisterevgroup')

router.register(r'portfolios/portfolio-register-record', portfolios.PortfolioRegisterRecordViewSet,
                'portfolioregisterrecord')
router.register(r'portfolios/portfolio-register-record-ev', portfolios.PortfolioRegisterRecordEvViewSet,
                'portfolioregisterrecordev')
router.register(r'portfolios/portfolio-register-record-ev-group', portfolios.PortfolioRegisterRecordEvGroupViewSet,
                'portfolioregisterrecordgroup')

router.register(r'portfolios/portfolio-bundle', portfolios.PortfolioBundleViewSet, 'portfoliobundle')
router.register(r'portfolios/portfolio-bundle-ev', portfolios.PortfolioBundleEvViewSet, 'portfoliobundleev')
router.register(r'portfolios/portfolio-bundle-ev-group', portfolios.PortfolioBundleEvGroupViewSet,
                'portfoliobundlevgroup')

router.register(r'strategies/1/group-ev-group', strategies.Strategy1GroupEvGroupViewSet, 'strategy1groupevgroup')
router.register(r'strategies/1/group', strategies.Strategy1GroupViewSet)

router.register(r'strategies/1/subgroup-ev-group', strategies.Strategy1SubgroupEvGroupViewSet,
                'strategy1subggroupevgroup')
router.register(r'strategies/1/subgroup', strategies.Strategy1SubgroupViewSet)

router.register(r'strategies/1/strategy-ev-group', strategies.Strategy1EvGroupViewSet, 'strategy1evgroup')
router.register(r'strategies/1/strategy', strategies.Strategy1ViewSet, 'strategy1')
router.register(r'strategies/1/strategy-ev', strategies.Strategy1EvViewSet, 'strategy1ev')
router.register(r'strategies/1/strategy-light', strategies.Strategy1LightViewSet, 'strategy1light')

router.register(r'strategies/1/strategy-attribute-type', strategies.Strategy1AttributeTypeViewSet)

router.register(r'strategies/2/group-ev-group', strategies.Strategy2GroupEvGroupViewSet, 'strategy2groupevgroup')
router.register(r'strategies/2/group', strategies.Strategy2GroupViewSet)

router.register(r'strategies/2/subgroup-ev-group', strategies.Strategy2SubgroupEvGroupViewSet,
                'strategy2subggroupevgroup')
router.register(r'strategies/2/subgroup', strategies.Strategy2SubgroupViewSet)

router.register(r'strategies/2/strategy-ev-group', strategies.Strategy2EvGroupViewSet, 'strategy2evgroup')
router.register(r'strategies/2/strategy', strategies.Strategy2ViewSet, 'strategy2')
router.register(r'strategies/2/strategy-ev', strategies.Strategy2EvViewSet, 'strategy2ev')
router.register(r'strategies/2/strategy-light', strategies.Strategy2LightViewSet, 'strategy2light')

router.register(r'strategies/2/strategy-attribute-type', strategies.Strategy2AttributeTypeViewSet)

router.register(r'strategies/3/group-ev-group', strategies.Strategy3GroupEvGroupViewSet, 'strategy3groupevgroup')
router.register(r'strategies/3/group', strategies.Strategy3GroupViewSet)

router.register(r'strategies/3/subgroup-ev-group', strategies.Strategy3SubgroupEvGroupViewSet,
                'strategy3subggroupevgroup')
router.register(r'strategies/3/subgroup', strategies.Strategy3SubgroupViewSet)

router.register(r'strategies/3/strategy-ev-group', strategies.Strategy3EvGroupViewSet, 'strategy3evgroup')
router.register(r'strategies/3/strategy', strategies.Strategy3ViewSet, 'strategy3')
router.register(r'strategies/3/strategy-ev', strategies.Strategy3EvViewSet, 'strategy3ev')
router.register(r'strategies/3/strategy-light', strategies.Strategy3LightViewSet, 'strategy3light')

router.register(r'strategies/3/strategy-attribute-type', strategies.Strategy3AttributeTypeViewSet)

router.register(r'reference-tables/reference-table', reference_table.ReferenceTableViewSet, 'reference_table')
router.register(r'active_processes/active_processes', celery_tasks.CeleryTaskViewSet, 'celery_tasks')
router.register(r'tasks/task', celery_tasks.CeleryTaskViewSet, 'celery_tasks')

router.register(r'transactions/event-class', transactions.EventClassViewSet)
router.register(r'transactions/notification-class', transactions.NotificationClassViewSet)
router.register(r'transactions/transaction-class', transactions.TransactionClassViewSet)

router.register(r'transactions/transaction-type-group-ev-group', transactions.TransactionTypeGroupEvGroupViewSet,
                'transactiontypegroupevgroup')
router.register(r'transactions/transaction-type-group', transactions.TransactionTypeGroupViewSet)
router.register(r'transactions/transaction-type-ev-group', transactions.TransactionTypeEvGroupViewSet,
                'transactiontypeevgroup')
router.register(r'transactions/transaction-type-light-ev-group', transactions.TransactionTypeLightEvGroupViewSet,
                'transactiontypelightevgroup')

router.register(r'transactions/transaction-type', transactions.TransactionTypeViewSet, 'transactiontype')
router.register(r'transactions/transaction-type-ev', transactions.TransactionTypeEvViewSet, 'transactiontypev')
router.register(r'transactions/transaction-type-light', transactions.TransactionTypeLightViewSet,
                'transactiontypelight')
router.register(r'transactions/transaction-type-light-with-inputs', transactions.TransactionTypeLightWithInputsViewSet,
                'transactiontypelightwithinputs')
router.register(r'transactions/transaction-type-attribute-type', transactions.TransactionTypeAttributeTypeViewSet)
# router.register(r'transactions/transaction-attribute-type', transactions.TransactionAttributeTypeViewSet)
router.register(r'transactions/transaction-attribute-type', transactions.TransactionAttributeTypeViewSet,
                'transactionattributetype')
# router.register(r'transactions/transaction-classifier', transactions.TransactionClassifierViewSet)
router.register(r'transactions/transaction-classifier', transactions.TransactionClassifierViewSet,
                'transactionclassifier')

router.register(r'transactions/transaction-ev-group', transactions.TransactionEvGroupViewSet, 'transactionevgroup')
router.register(r'transactions/transaction', transactions.TransactionViewSet, 'transaction')
router.register(r'transactions/transaction-ev', transactions.TransactionEvViewSet, 'transaction-ev')

router.register(r'transactions/complex-transaction-attribute-type', transactions.ComplexTransactionAttributeTypeViewSet,
                'complextransactionattributetype')

router.register(r'transactions/complex-transaction-ev-group', transactions.ComplexTransactionEvGroupViewSet,
                'complextransactionevgroup')
router.register(r'transactions/complex-transaction-light-ev-group', transactions.ComplexTransactionLightEvGroupViewSet,
                'complextransactionlightevgroup')
router.register(r'transactions/complex-transaction', transactions.ComplexTransactionViewSet)
router.register(r'transactions/complex-transaction-ev', transactions.ComplexTransactionEvViewSet)
router.register(r'transactions/complex-transaction-light', transactions.ComplexTransactionLightViewSet,
                'complextransactionlight')
router.register(r'transactions/recalculate-permission-transaction',
                transactions.RecalculatePermissionTransactionViewSet, 'recalculatepermissiontranscation')
router.register(r'transactions/recalculate-permission-complex-transaction',
                transactions.RecalculatePermissionComplexTransactionViewSet, 'recalculatepermissioncomplextrasaction')

router.register(r'transactions/bank-file', integrations.TransactionFileResultViewSet)

router.register(r'specific-data/values-for-select', common.ValuesForSelectViewSet, 'valuesforselect')

router.register(r'ui/portal-interface-access', ui.PortalInterfaceAccessViewSet)
router.register(r'ui/list-layout', ui.ListLayoutViewSet)
router.register(r'ui/list-layout-light', ui.ListLayoutLightViewSet)
router.register(r'ui/template-layout', ui.TemplateLayoutViewSet)
router.register(r'ui/dashboard-layout', ui.DashboardLayoutViewSet)
router.register(r'ui/edit-layout', ui.EditLayoutViewSet)
router.register(r'ui/bookmark', ui.BookmarkViewSet)
router.register(r'ui/configuration', ui.ConfigurationViewSet)
router.register(r'ui/configuration-export-layout', ui.ConfigurationExportLayoutViewSet)
router.register(r'ui/transaction-user-field', ui.TransactionUserFieldViewSet)
router.register(r'ui/instrument-user-field', ui.InstrumentUserFieldViewSet)
router.register(r'ui/entity-tooltip', ui.EntityTooltipViewSet)
router.register(r'ui/context-menu-layout', ui.ContextMenuLayoutViewSet)
router.register(r'ui/color-palette', ui.ColorPaletteViewSet)
router.register(r'ui/cross-entity-attribute-extension', ui.CrossEntityAttributeExtensionViewSet)
router.register(r'ui/column-sort-data', ui.ColumnSortDataViewSet)

# router.register(r'reports/report', reports.BalanceReportViewSet, "report")
router.register(r'reports/balance-report', reports.BalanceReportViewSet, "balance-report")
router.register(r'reports/balance-report-sql', reports.BalanceReportViewSet, "balance-report-sync-sql")  # deprecated
router.register(r'reports/balance-report/custom-field', reports.BalanceReportCustomFieldViewSet,
                'balance-report-custom-field')
# router.register(r'reports/balance-report', reports.BalanceReportSyncViewSet, "balance-report-sync")
# router.register(r'reports/pl-report', reports.PLReportViewSet, "pl-report")
router.register(r'reports/pl-report', reports.PLReportViewSet, "pl-report")
router.register(r'reports/pl-report-sql', reports.PLReportViewSet, "pl-report-sync-sql")  # deprecated, delete soon
router.register(r'reports/pl-report/custom-field', reports.PLReportCustomFieldViewSet, 'pl-report-custom-field')
# router.register(r'reports/transaction-report', reports.TransactionReportViewSet, "transaction-report")
router.register(r'reports/transaction-report', reports.TransactionReportViewSet, "transaction-report")
router.register(r'reports/transaction-report-sql', reports.TransactionReportViewSet, "transaction-report-sync-sql")

router.register(r'reports/transaction-report/custom-field', reports.TransactionReportCustomFieldViewSet,
                'transaction-report-custom-field')
# TODO not in use
# router.register(r'reports/cash-flow-projection-report', reports.CashFlowProjectionReportViewSet,
#                 "cash-flow-projection-report")

router.register(r'reports/performance-report', reports.PerformanceReportViewSet, "performance-report")

router.register(r'reports/price-history-check-sql', reports.PriceHistoryCheckViewSet,
                "price-history-check-sql")  # deprecated
router.register(r'reports/price-history-check', reports.PriceHistoryCheckViewSet, "price-history-check")

router.register(r'notifications/notification', notifications.NotificationViewSet)

# router.register(r'security/http-session', sessions.SessionViewSet)
router.register(r'audit/auth-log', audit.AuthLogViewSet)
router.register(r'audit/history', audit.ObjectHistory4ViewSet)
router.register(r'audit/history-ev', audit.ObjectHistory4EvViewSet)
router.register(r'audit/history-ev-group', audit.ObjectHistory4EvGroupViewSet)

router.register(r'data-provider/bloomberg/credential', integrations.BloombergDataProviderCredentialViewSet)
router.register(r'import/config', integrations.ImportConfigViewSet)

router.register(r'import/provider', integrations.ProviderClassViewSet)
router.register(r'import/factor-schedule-download-method', integrations.FactorScheduleDownloadMethodViewSet)
router.register(r'import/accrual-schedule-download-method', integrations.AccrualScheduleDownloadMethodViewSet)

router.register(r'import/instrument-scheme', integrations.InstrumentDownloadSchemeViewSet)
router.register(r'import/instrument-scheme-light', integrations.InstrumentDownloadSchemeLightViewSet)
# router.register(r'import/price-download-scheme', integrations.PriceDownloadSchemeViewSet)

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
router.register(r'import/finmars-database/instrument', integrations.ImportInstrumentCbondsViewSet,
                'importinstrumentcbonds')
router.register(r'import/finmars-database/currency', integrations.ImportCurrencyCbondsViewSet, 'importcurrencycbonds')
router.register(r'import/unified-data-provider', integrations.ImportUnifiedDataProviderViewSet,
                'importunifieddataprovider')
router.register(r'import/pricing', integrations.ImportPricingViewSet, 'importpricing')
router.register(r'import/test-certificate', integrations.TestCertificateViewSet, 'testcertificate')
# router.register(r'import/pricing-automated-schedule', integrations.PricingAutomatedScheduleViewSet)

router.register(r'import/task', integrations.TaskViewSet)

router.register(r'import/complex-transaction-import-scheme', integrations.ComplexTransactionImportSchemeViewSet)
router.register(r'import/complex-transaction-import-scheme-light',
                integrations.ComplexTransactionImportSchemeLightViewSet)
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

router.register(r'import/csv/scheme', csv_import.SchemeViewSet, 'import_csv_scheme')
router.register(r'import/csv/scheme-light', csv_import.SchemeLightViewSet, 'import_csv_scheme_light')
router.register(r'import/csv', csv_import.CsvDataImportViewSet, 'import_csv')
# DEPRECATED
# router.register(r'import/unified_csv', csv_import.UnifiedCsvDataImportViewSet, 'unified_csv')

router.register(r'import/csv-validate', csv_import.CsvDataImportValidateViewSet, 'import_csv-validate')

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
router.register(r'procedures/expression-procedure-instance', procedures.ExpressionProcedureInstanceViewSet)

router.register(r'credentials/credentials', credentials.CredentialsViewSet)
router.register(r'integrations/data-provider', integrations.DataProviderViewSet)

# deprecated
# router.register(r'recovery/generate-layout-archetype', layout_recovery.GenerateLayoutArchetypeViewSet, 'recovery_generate_layout_archetype')
# router.register(r'recovery/layout', layout_recovery.FixLayoutViewSet, 'recovery_layout')


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
router.register(r'explorer/create_folder', explorer.ExplorerCreateFolderViewSet, 'explorer_create_folder')

router.register(r'debug/logs', common.DebugLogViewSet, 'debug_log')  # Deprecated
router.register(r'errors/error', ErrorRecordViewSet, 'error')

router.register(r'history/historical-record', history.HistoricalRecordViewSet, 'historical-record')

# router.register(r'pricing/brokers/bloomberg/callback', csrf_exempt(pricing.PricingBrokerBloombergHandler.as_view()), 'pricing_broker_bloomberg')


urlpatterns = [
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
    re_path(r'internal/data/transactions/callback',
            csrf_exempt(integrations.TransactionFileResultUploadHandler.as_view())),
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

if 'rest_framework_swagger' in settings.INSTALLED_APPS:
    urlpatterns += [
        re_path(r'^schema/', api.SchemaViewSet.as_view()),
    ]

if settings.SERVER_TYPE == 'local':
    import debug_toolbar

    urlpatterns += [
        re_path('__debug__/', include(debug_toolbar.urls)),
    ]

    urlpatterns += [
        re_path(r'^dev/auth/', include('rest_framework.urls', namespace='rest_framework')),
    ]
