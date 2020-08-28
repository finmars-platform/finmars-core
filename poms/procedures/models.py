from django.db import models
from django.utils.translation import ugettext_lazy

from poms.common.models import NamedModel, DataTimeStampedModel
from poms.integrations.models import DataProvider
from poms.users.models import MasterUser

from poms.common.models import EXPRESSION_FIELD_LENGTH


class RequestDataFileProcedure(NamedModel, DataTimeStampedModel):

    master_user = models.ForeignKey(MasterUser,  verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    provider = models.ForeignKey(DataProvider, verbose_name=ugettext_lazy('provider'), on_delete=models.CASCADE)

    scheme_name = models.CharField(max_length=255)

    price_date_from = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('price date from'))

    price_date_from_expr = models.CharField(null=True, max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                            verbose_name=ugettext_lazy('price date from expr'))

    price_date_to = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('price date to'))

    price_date_to_expr = models.CharField(null=True, max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                          verbose_name=ugettext_lazy('price date to expr'))


class RequestDataFileProcedureInstance(models.Model):
    STATUS_INIT = 'I'
    STATUS_PENDING = 'P'
    STATUS_DONE = 'D'
    STATUS_ERROR = 'E'

    STATUS_CHOICES = (
        (STATUS_INIT, ugettext_lazy('Init')),
        (STATUS_PENDING, ugettext_lazy('Pending')),
        (STATUS_DONE, ugettext_lazy('Done')),
        (STATUS_ERROR, ugettext_lazy('Error')),
    )

    procedure = models.ForeignKey(RequestDataFileProcedure, on_delete=models.CASCADE,
                                          verbose_name=ugettext_lazy('procedure'))

    created = models.DateTimeField(auto_now_add=True, editable=False, db_index=True, verbose_name='created')
    modified = models.DateTimeField(auto_now=True, editable=False, db_index=True)

    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    status = models.CharField(max_length=1, default=STATUS_INIT, choices=STATUS_CHOICES,
                              verbose_name=ugettext_lazy('status'))
