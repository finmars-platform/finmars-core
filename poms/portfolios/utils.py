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


def update_price_histories_with_error(err_msg: str, prices: List[PriceHistory]):
    """
    Stores error message in all corresponding PriceHistory objects
    """
    for price in prices:
        price.nav = 0
        price.cash_flow = 0
        price.principal_price = 0
        price.error_message = err_msg
        price.save()
