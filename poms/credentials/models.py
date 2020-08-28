from django.db import models
from django.utils.translation import ugettext_lazy

from poms.integrations.models import DataProvider
from poms.users.models import MasterUser
from poms.common.models import NamedModel, DataTimeStampedModel


class Credentials(NamedModel, DataTimeStampedModel):

    USERNAME_WITH_PASSWORD = 1
    SSH_USERNAME_WITH_PRIVATE_KEY = 2
    USERNAME_WITH_PASSWORD_AND_PRIVATE_KEY = 2

    TYPE_CHOICES = (
        (USERNAME_WITH_PASSWORD, ugettext_lazy('Username with password')),
        (SSH_USERNAME_WITH_PRIVATE_KEY, ugettext_lazy('SSH username with private key')),
        (USERNAME_WITH_PASSWORD_AND_PRIVATE_KEY, ugettext_lazy('Username with password and private key')),
    )

    master_user = models.ForeignKey(MasterUser,  verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)
    type = models.PositiveSmallIntegerField(default=USERNAME_WITH_PASSWORD, choices=TYPE_CHOICES, db_index=True,
                                            verbose_name=ugettext_lazy('type'))

    provider = models.ForeignKey(DataProvider, verbose_name=ugettext_lazy('provider'), on_delete=models.CASCADE)

    username = models.CharField(max_length=255, null=True, blank=True, verbose_name=ugettext_lazy('username'))
    password = models.CharField(max_length=255, null=True, blank=True, verbose_name=ugettext_lazy('password'))
    key = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('key'))
