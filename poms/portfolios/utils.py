from typing import List

from poms.instruments.models import PriceHistory
from poms.portfolios.models import PortfolioRegisterRecord


def get_price_calculation_type(transaction_class, transaction) -> str:
    """
    Define calculation type for dealing price valuation currency:
    if transaction is Cash Inflow/Outflow class and Trade.Price > 0
    so type is Manual, otherwise Automatic
    """
    from poms.transactions.models import TransactionClass

    return (
        PortfolioRegisterRecord.MANUAL
        if (
            transaction_class.id
            in (TransactionClass.CASH_INFLOW, TransactionClass.CASH_OUTFLOW)
            and (transaction.trade_price > 0)
        )
        else PortfolioRegisterRecord.AUTOMATIC
    )


def update_price_histories(prices: List[PriceHistory], **kwargs):
    """
    Update PriceHistory objects with given data
    """
    PriceHistory.objects.filter(id__in=[price.id for price in prices]).update(**kwargs)
