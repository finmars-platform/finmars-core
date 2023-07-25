from rest_framework import routers

import poms.transactions.views as transactions

router = routers.DefaultRouter()

router.register(
    "event-class",
    transactions.EventClassViewSet,
)
router.register(
    "notification-class",
    transactions.NotificationClassViewSet,
)
router.register(
    "transaction-class",
    transactions.TransactionClassViewSet,
)
router.register(
    "transaction-type-group",
    transactions.TransactionTypeGroupViewSet,
)
router.register(
    "transaction-type",
    transactions.TransactionTypeViewSet,
    "transactiontype",
)
router.register(
    "transaction-type-attribute-type",
    transactions.TransactionTypeAttributeTypeViewSet,
    "TransactionTypeAttributeType",
)
router.register(
    "transaction-attribute-type",
    transactions.TransactionAttributeTypeViewSet,
    "TransactionAttributeType",
)
router.register(
    "transaction-classifie",
    transactions.TransactionClassifierViewSet,
    "transactionclassifie",
)
router.register(
    "transaction",
    transactions.TransactionViewSet,
    "transaction",
)
router.register(
    "complex-transaction-attribute-type",
    transactions.ComplexTransactionAttributeTypeViewSet,
    "complextransactionattributetype",
)
router.register(
    "complex-transaction",
    transactions.ComplexTransactionViewSet,
)
router.register(
    "recalculate-permission-transaction",
    transactions.RecalculatePermissionTransactionViewSet,
    "recalculatepermissiontranscation",
)
router.register(
    "recalculate-permission-complex-transaction",
    transactions.RecalculatePermissionComplexTransactionViewSet,
    "recalculatepermissioncomplextrasaction",
)
