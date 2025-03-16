from rest_framework import routers

import poms.procedures.views as procedures

router = routers.DefaultRouter()

router.register(
    "pricing-procedure",
    procedures.PricingProcedureViewSet,
    "pricing_procedure",
)
router.register(
    "pricing-procedure-instance",
    procedures.PricingProcedureInstanceViewSet,
    "pricing_procedure_instance",
)
router.register(
    "pricing-parent-procedure-instance",
    procedures.PricingParentProcedureInstanceViewSet,
    "pricing_parent_procedure_instance",
)
router.register(
    "request-data-procedure",
    procedures.RequestDataFileProcedureViewSet,
    "request_data_procedure",
)
router.register(
    "data-procedure",
    procedures.RequestDataFileProcedureViewSet,
    "data_procedure",
)
router.register(
    "data-procedure-instance",
    procedures.RequestDataFileProcedureInstanceViewSet,
    "data_procedure_instance",
)
router.register(
    "expression-procedure",
    procedures.ExpressionProcedureViewSet,
    "expression_procedure",
)
