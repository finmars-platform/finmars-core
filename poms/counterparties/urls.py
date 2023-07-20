from rest_framework import routers

import poms.counterparties.views as counterparties

router = routers.DefaultRouter()

router.register(
    "counterparty-attribute-type",
    counterparties.CounterpartyAttributeTypeViewSet,
    "CounterpartyAttributeType",
)
router.register(
    "counterparty-classifier",
    counterparties.CounterpartyClassifierViewSet,
    "counterpartyclassifier",
)
router.register(
    "counterparty-group",
    counterparties.CounterpartyGroupViewSet,
)
router.register(
    "counterparty",
    counterparties.CounterpartyViewSet,
    "counterparty",
)
router.register(
    "responsible-attribute-type",
    counterparties.ResponsibleAttributeTypeViewSet,
    "ResponsibleAttributeType",
)
router.register(
    "responsible-classifier",
    counterparties.ResponsibleClassifierViewSet,
    "responsibleclassifier",
)
router.register(
    "responsible-group",
    counterparties.ResponsibleGroupViewSet,
    "ResponsibleGroup",
)
router.register(
    "responsible",
    counterparties.ResponsibleViewSet,
    "Responsible",
)
