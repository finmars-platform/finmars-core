from modeltranslation.translator import translator

from poms.common.translation import AbstractClassModelOptions
from poms.instruments.models import InstrumentClass, DailyPricingModel, AccrualCalculationModel, PaymentSizeDetail, \
    Periodicity, CostMethod, PricingCondition

translator.register(InstrumentClass, AbstractClassModelOptions)
translator.register(DailyPricingModel, AbstractClassModelOptions)
translator.register(AccrualCalculationModel, AbstractClassModelOptions)
translator.register(PaymentSizeDetail, AbstractClassModelOptions)
translator.register(Periodicity, AbstractClassModelOptions)
translator.register(CostMethod, AbstractClassModelOptions)
translator.register(PricingCondition, AbstractClassModelOptions)