from django.db import models
from django.utils.translation import ugettext_lazy

from poms.common.models import NamedModel, DataTimeStampedModel
from poms.integrations.models import TransactionProvider
from poms.users.models import MasterUser


class RequestDataFileProcedure(NamedModel, DataTimeStampedModel):

    master_user = models.ForeignKey(MasterUser,  verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    provider = models.ForeignKey(TransactionProvider, verbose_name=ugettext_lazy('provider'), on_delete=models.CASCADE)
    scheme_name = models.CharField(max_length=255)

