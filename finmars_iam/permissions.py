
import logging

from finmars_iam.access_policy import AccessPolicy
from finmars_iam.utils import get_statements

_l = logging.getLogger('finmars_iam')

class FinmarsAccessPolicy(AccessPolicy):

    def get_policy_statements(self, request, view=None):

        return get_statements(user=request.user)



