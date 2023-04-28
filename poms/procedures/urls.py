from rest_framework import routers

import poms.procedures.views as procedures

router = routers.DefaultRouter()
router.register(r'pricing-procedure', procedures.PricingProcedureViewSet, 'pricing_procedure')
router.register(r'pricing-procedure-instance', procedures.PricingProcedureInstanceViewSet,
                'pricing_procedure_instance')
router.register(r'pricing-parent-procedure-instance', procedures.PricingParentProcedureInstanceViewSet,
                'pricing_parent_procedure_instance')

router.register(r'request-data-procedure', procedures.RequestDataFileProcedureViewSet)
router.register(r'data-procedure', procedures.RequestDataFileProcedureViewSet)
router.register(r'data-procedure-instance', procedures.RequestDataFileProcedureInstanceViewSet)

router.register(r'expression-procedure', procedures.ExpressionProcedureViewSet)


