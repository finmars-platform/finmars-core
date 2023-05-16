from rest_framework import routers

import poms.currencies.views as currencies

router = routers.DefaultRouter()

router.register(r'currency', currencies.CurrencyViewSet, 'currency')
router.register(r'currency-attribute-type', currencies.CurrencyAttributeTypeViewSet, 'currencyattributetype')
router.register(r'currency-history', currencies.CurrencyHistoryViewSet)


