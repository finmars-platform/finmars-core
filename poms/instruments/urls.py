from rest_framework import routers

import poms.instruments.views as instruments

router = routers.DefaultRouter()
router.register(r'instrument-class', instruments.InstrumentClassViewSet)
router.register(r'daily-pricing-model', instruments.DailyPricingModelViewSet)
router.register(r'accrual-calculation-model', instruments.AccrualCalculationModelClassViewSet)
router.register(r'payment-size-detail', instruments.PaymentSizeDetailViewSet)
router.register(r'pricing-condition', instruments.PricingConditionViewSet)
router.register(r'country', instruments.CountryViewSet)
router.register(r'exposure-calculation-model', instruments.ExposureCalculationModelViewSet)
router.register(r'long-underlying-exposure', instruments.LongUnderlyingExposureViewSet)
router.register(r'short-underlying-exposure', instruments.ShortUnderlyingExposureViewSet)
router.register(r'periodicity', instruments.PeriodicityViewSet)
router.register(r'cost-method', instruments.CostMethodViewSet)
router.register(r'pricing-policy', instruments.PricingPolicyViewSet)
router.register(r'event-schedule-config', instruments.EventScheduleConfigViewSet)

router.register(r'instrument-type', instruments.InstrumentTypeViewSet)

router.register(r'instrument-type-attribute-type', instruments.InstrumentTypeAttributeTypeViewSet)

router.register(r'instrument-attribute-type', instruments.InstrumentAttributeTypeViewSet,
                'instrumentattributetype')
router.register(r'instrument-classifier', instruments.InstrumentClassifierViewSet, 'instrumentclassifier')


router.register(r'instrument', instruments.InstrumentViewSet)
router.register(r'instrument-for-select', instruments.InstrumentForSelectViewSet)

router.register(r'price-history', instruments.PriceHistoryViewSet)

router.register(r'generated-event', instruments.GeneratedEventViewSet)
