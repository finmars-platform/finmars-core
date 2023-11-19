from rest_framework import routers

import poms.portfolios.views as portfolios

router = routers.DefaultRouter()

router.register(
    r"portfolio-attribute-type",
    portfolios.PortfolioAttributeTypeViewSet,
    "portfolioattributetype",
)
router.register(
    r"portfolio-classifier",
    portfolios.PortfolioClassifierViewSet,
    "portfolioclassifier",
)
router.register(
    r"portfolio",
    portfolios.PortfolioViewSet,
    "portfolio",
)
router.register(
    r"portfolio-register-attribute-type",
    portfolios.PortfolioRegisterAttributeTypeViewSet,
    "portfolioregisterattributetype",
)
router.register(
    r"portfolio-register",
    portfolios.PortfolioRegisterViewSet,
    "portfolioregister",
)
router.register(
    r"portfolio-register-record",
    portfolios.PortfolioRegisterRecordViewSet,
    "portfolioregisterrecord",
)
router.register(
    r"portfolio-bundle",
    portfolios.PortfolioBundleViewSet,
    "portfoliobundle",
)
router.register(
    r"first-transaction-date",
    portfolios.PortfolioFirstTransactionViewSet,
    "firsttransactiondate",
)

router.register(
    r"portfolio-history",
    portfolios.PortfolioHistoryViewSet,
    "portfoliohistory",
)