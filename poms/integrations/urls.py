from rest_framework import routers

import poms.integrations.views as integrations

router = routers.DefaultRouter()
router.register(r'config', integrations.ImportConfigViewSet)

router.register(r'provider', integrations.ProviderClassViewSet)
router.register(r'factor-schedule-download-method', integrations.FactorScheduleDownloadMethodViewSet)
router.register(r'accrual-schedule-download-method', integrations.AccrualScheduleDownloadMethodViewSet)

router.register(r'instrument-scheme', integrations.InstrumentDownloadSchemeViewSet)
router.register(r'instrument-scheme-light', integrations.InstrumentDownloadSchemeLightViewSet)  # DEPRECATED
router.register(r'currency-mapping', integrations.CurrencyMappingViewSet)
router.register(r'pricing-policy-mapping', integrations.PricingPolicyMappingViewSet)
router.register(r'instrument-type-mapping', integrations.InstrumentTypeMappingViewSet)
router.register(r'instrument-attribute-value-mapping', integrations.InstrumentAttributeValueMappingViewSet)
router.register(r'accrual-calculation-model-mapping', integrations.AccrualCalculationModelMappingViewSet)
router.register(r'periodicity-mapping', integrations.PeriodicityMappingViewSet)
router.register(r'account-mapping', integrations.AccountMappingViewSet)
router.register(r'account-classifier-mapping', integrations.AccountClassifierMappingViewSet)
router.register(r'account-type-mapping', integrations.AccountTypeMappingViewSet)
router.register(r'instrument-mapping', integrations.InstrumentMappingViewSet)
router.register(r'instrument-classifier-mapping', integrations.InstrumentClassifierMappingViewSet)
router.register(r'counterparty-mapping', integrations.CounterpartyMappingViewSet)
router.register(r'counterparty-classifier-mapping', integrations.CounterpartyClassifierMappingViewSet)
router.register(r'responsible-mapping', integrations.ResponsibleMappingViewSet)
router.register(r'responsible-classifier-mapping', integrations.ResponsibleClassifierMappingViewSet)
router.register(r'portfolio-mapping', integrations.PortfolioMappingViewSet)
router.register(r'portfolio-classifier-mapping', integrations.PortfolioClassifierMappingViewSet)
router.register(r'strategy1-mapping', integrations.Strategy1MappingViewSet)
router.register(r'strategy2-mapping', integrations.Strategy2MappingViewSet)
router.register(r'strategy3-mapping', integrations.Strategy3MappingViewSet)
router.register(r'daily-pricing-model-mapping', integrations.DailyPricingModelMappingViewSet)
router.register(r'payment-size-detail-mapping', integrations.PaymentSizeDetailMappingViewSet)
router.register(r'price-download-scheme-mapping', integrations.PriceDownloadSchemeMappingViewSet)
router.register(r'pricing-condition-mapping', integrations.PricingConditionMappingViewSet)

router.register(r'instrument', integrations.ImportInstrumentViewSet, 'importinstrument')
router.register(
    r'finmars-database/instrument',
    integrations.ImportInstrumentDatabaseViewSet,
    'importinstrumentdatabase',
)
router.register(
    r'finmars-database/currency',
    integrations.ImportCurrencyDatabaseViewSet,
    'importcurrencydatabase',
)
router.register(
    r'finmars-database/company',
    integrations.ImportCompanyDatabaseViewSet,
    'importcompanydatabase',
)
router.register(r'unified-data-provider', integrations.ImportUnifiedDataProviderViewSet,
                'importunifieddataprovider')
router.register(r'test-certificate', integrations.TestCertificateViewSet, 'testcertificate')

router.register(r'complex-transaction-import-scheme', integrations.ComplexTransactionImportSchemeViewSet)
router.register(r'complex-transaction-import-scheme-light',
                integrations.ComplexTransactionImportSchemeLightViewSet)  # DEPRECATED
router.register(r'complex-transaction-csv-file-import', integrations.ComplexTransactionCsvFileImportViewSet,
                'complextransactioncsvfileimport')

router.register(r'transaction-import', integrations.TransactionImportViewSet,
                'transactionimportviewset')

router.register(r'complex-transaction-preprocess-file', integrations.ComplexTransactionFilePreprocessViewSet,
                'complextransactionfilepreprocessviewSet')

router.register(r'complex-transaction-csv-file-import-validate',
                integrations.ComplexTransactionCsvFileImportValidateViewSet,
                'complextransactioncsvfileimportvalidate')
