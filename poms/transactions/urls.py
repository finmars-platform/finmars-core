from rest_framework import routers

import poms.transactions.views as transactions

router = routers.DefaultRouter()
router.register(r'event-class', transactions.EventClassViewSet)
router.register(r'notification-class', transactions.NotificationClassViewSet)
router.register(r'transaction-class', transactions.TransactionClassViewSet)

router.register(r'transaction-type-group', transactions.TransactionTypeGroupViewSet)

router.register(r'transaction-type-light-ev-group', transactions.TransactionTypeLightEvGroupViewSet,
                'transactiontypelightevgroup')  # Deprecated why even needed?
router.register(r'transaction-type', transactions.TransactionTypeViewSet, 'transactiontype')

router.register(r'transaction-type-light-with-inputs', transactions.TransactionTypeLightWithInputsViewSet,
                'transactiontypelightwithinputs')  # Deprecated
router.register(r'transaction-type-attribute-type', transactions.TransactionTypeAttributeTypeViewSet)
router.register(r'transaction-attribute-type', transactions.TransactionAttributeTypeViewSet,
                'transactionattributetype')
router.register(r'transaction-classifier', transactions.TransactionClassifierViewSet,
                'transactionclassifier')

router.register(r'transaction', transactions.TransactionViewSet, 'transaction')
router.register(r'complex-transaction-attribute-type', transactions.ComplexTransactionAttributeTypeViewSet,
                'complextransactionattributetype')

router.register(r'complex-transaction', transactions.ComplexTransactionViewSet)

router.register(r'recalculate-permission-transaction',
                transactions.RecalculatePermissionTransactionViewSet, 'recalculatepermissiontranscation')
router.register(r'recalculate-permission-complex-transaction',
                transactions.RecalculatePermissionComplexTransactionViewSet, 'recalculatepermissioncomplextrasaction')


