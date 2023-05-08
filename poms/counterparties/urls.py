from rest_framework import routers

import poms.counterparties.views as counterparties

router = routers.DefaultRouter()
router.register(r'counterparty-attribute-type', counterparties.CounterpartyAttributeTypeViewSet,
                'CounterpartyAttributeType')
router.register(r'counterparty-classifier', counterparties.CounterpartyClassifierViewSet,
                'counterpartyclassifier')

router.register(r'counterparty-group', counterparties.CounterpartyGroupViewSet)
router.register(r'counterparty', counterparties.CounterpartyViewSet, 'counterparty')

router.register(r'responsible-attribute-type', counterparties.ResponsibleAttributeTypeViewSet,
                'ResponsibleAttributeType')
router.register(r'responsible-classifier', counterparties.ResponsibleClassifierViewSet,
                'responsibleclassifier')

router.register(r'responsible-group', counterparties.ResponsibleGroupViewSet, 'ResponsibleGroup')
router.register(r'responsible', counterparties.ResponsibleViewSet, 'Responsible')


