from modeltranslation.translator import translator

from poms.common.translation import AbstractClassModelOptions
from poms.transactions.models import (
    ActionClass,
    ComplexTransactionStatus,
    EventClass,
    NotificationClass,
    PeriodicityGroup,
    TransactionClass,
)

translator.register(TransactionClass, AbstractClassModelOptions)
translator.register(ActionClass, AbstractClassModelOptions)
translator.register(EventClass, AbstractClassModelOptions)
translator.register(NotificationClass, AbstractClassModelOptions)
translator.register(PeriodicityGroup, AbstractClassModelOptions)
translator.register(ComplexTransactionStatus, AbstractClassModelOptions)
