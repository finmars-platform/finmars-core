
import logging

from poms.iam.access_policy import AccessPolicy
from poms.iam.utils import get_statements

_l = logging.getLogger('poms.iam')

class FinmarsAccessPolicy(AccessPolicy):

    def get_policy_statements(self, request, view=None):

        return get_statements(user=request.user)



