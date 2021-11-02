from modeltranslation.translator import translator

from poms.common.translation import AbstractClassModelOptions
from poms.transactions.models import TransactionClass, ActionClass, EventClass, NotificationClass, PeriodicityGroup, \
    ComplexTransactionStatus

translator.register(TransactionClass, AbstractClassModelOptions)
translator.register(ActionClass, AbstractClassModelOptions)
translator.register(EventClass, AbstractClassModelOptions)
translator.register(NotificationClass, AbstractClassModelOptions)
translator.register(PeriodicityGroup, AbstractClassModelOptions)
translator.register(ComplexTransactionStatus, AbstractClassModelOptions)
