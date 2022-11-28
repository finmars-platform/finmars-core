from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import NamedModel, DataTimeStampedModel
from poms.integrations.models import DataProvider
from poms.users.models import MasterUser


class Credentials(NamedModel, DataTimeStampedModel):
    USERNAME_WITH_PASSWORD = 1
    SSH_USERNAME_WITH_PRIVATE_KEY = 2
    USERNAME_WITH_PASSWORD_AND_PRIVATE_KEY = 3

    TYPE_CHOICES = (
        (USERNAME_WITH_PASSWORD, gettext_lazy('Username with password')),
        (SSH_USERNAME_WITH_PRIVATE_KEY, gettext_lazy('SSH username with private key')),
        (USERNAME_WITH_PASSWORD_AND_PRIVATE_KEY, gettext_lazy('Username with password and private key')),
    )

    master_user = models.ForeignKey(MasterUser, verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    type = models.PositiveSmallIntegerField(default=USERNAME_WITH_PASSWORD, choices=TYPE_CHOICES, db_index=True,
                                            verbose_name=gettext_lazy('type'))

    provider = models.ForeignKey(DataProvider, verbose_name=gettext_lazy('provider'), on_delete=models.CASCADE)

    username = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('username'))
    password = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('password'))
    public_key = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('public key'))
    path_to_public_key = models.TextField(blank=True, default='', verbose_name=gettext_lazy('Path to public key'))

    private_key = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('private key'))
    path_to_private_key = models.TextField(blank=True, default='', verbose_name=gettext_lazy('Path to private key'))
