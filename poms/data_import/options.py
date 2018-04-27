from poms.counterparties.models import Counterparty, Responsible
from poms.accounts.models import Account
PUBLIC_FIELDS = {
    'account': ['user_code', 'name', 'short_name', 'public_name', 'notes'],
    'responsible': [],
    'counterparty': [],
    'currency': ['user_code', 'name', 'short_name', 'public_name'],
    'instrument': ['user_code', 'name', 'short_name', 'public_name'],
    'pricingpolicy': ['user_code', 'name', 'short_name', 'public_name', 'expr'],
    'portfolio': ['user_code', 'name', 'short_name', 'public_name', 'notes', Counterparty, Account, Responsible],
    'strategy1': ['user_code', 'name', 'short_name', 'public_name'],
    'strategy2': ['user_code', 'name', 'short_name', 'public_name'],
    'strategy3': ['user_code', 'name', 'short_name', 'public_name'],
}
