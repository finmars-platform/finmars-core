from poms.instruments.models import GeneratedEvent
from poms.transactions.handlers import TransactionTypeProcess
from poms.transactions.models import ComplexTransaction


# Context variables here

class GeneratedEventProcess(TransactionTypeProcess):
    def __init__(self, generated_event=None, action=None, **kwargs):
        self.generated_event = generated_event
        self.action = action
        kwargs['transaction_type'] = action.transaction_type

        # Some Inputs can choose from which context variable it will take value

        context_values = kwargs.get('context_values', None) or {}
        context_values.update({
            'instrument': generated_event.instrument,
            'pricing_currency': generated_event.instrument.pricing_currency,
            'accrued_currency': generated_event.instrument.accrued_currency,
            'portfolio': generated_event.portfolio,
            'account': generated_event.account,
            'strategy1': generated_event.strategy1,
            'strategy2': generated_event.strategy2,
            'strategy3': generated_event.strategy3,
            'position': generated_event.position,
            'effective_date': generated_event.effective_date,
            'notification_date': generated_event.notification_date, # not in context variables
            # 'final_date': generated_event.event_schedule.final_date,
            # 'maturity_date': generated_event.instrument.maturity_date
        })
        kwargs['context_values'] = context_values

        # But by default Context Variables overwrites default value

        default_values = kwargs.get('default_values', None) or {}
        default_values.update({
            'instrument': generated_event.instrument,
            'pricing_currency': generated_event.instrument.pricing_currency,
            'accrued_currency': generated_event.instrument.accrued_currency,
            'portfolio': generated_event.portfolio,
            'account': generated_event.account,
            'strategy1': generated_event.strategy1,
            'strategy2': generated_event.strategy2,
            'strategy3': generated_event.strategy3,
            'position': generated_event.position,
            'effective_date': generated_event.effective_date,
            'notification_date': generated_event.notification_date, # not in context variables
            # 'final_date': generated_event.event_schedule.final_date,
            # 'maturity_date': generated_event.instrument.maturity_date
        })
        kwargs['default_values'] = default_values

        if generated_event.status == GeneratedEvent.ERROR:
            kwargs['complex_transaction_status'] = ComplexTransaction.PENDING
        else:
            if action.is_sent_to_pending:
                kwargs['complex_transaction_status'] = ComplexTransaction.PENDING
            else:
                kwargs['complex_transaction_status'] = ComplexTransaction.PRODUCTION

        # context = kwargs.get('context', None) or {}
        # if 'master_user' not in context:
        #     context['master_user'] = generated_event.master_user

        super(GeneratedEventProcess, self).__init__(**kwargs)
