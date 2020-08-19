from __future__ import unicode_literals

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import ugettext_lazy
from django.contrib.postgres.fields import JSONField

from poms.cache_machine.base import CachingMixin, CachingManager
from poms.common.models import NamedModel, FakeDeletableModel, DataTimeStampedModel
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.obj_attrs.models import GenericAttribute
from poms.obj_perms.models import GenericObjectPermission
from poms.tags.models import TagLink
from poms.users.models import MasterUser


class Portfolio(CachingMixin, NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):

    master_user = models.ForeignKey(MasterUser, related_name='portfolios', verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)
    accounts = models.ManyToManyField('accounts.Account', related_name='portfolios', blank=True,
                                      verbose_name=ugettext_lazy('accounts'))
    responsibles = models.ManyToManyField('counterparties.Responsible', related_name='portfolios', blank=True,
                                          verbose_name=ugettext_lazy('responsibles'))
    counterparties = models.ManyToManyField('counterparties.Counterparty', related_name='portfolios', blank=True,
                                            verbose_name=ugettext_lazy('counterparties'))
    transaction_types = models.ManyToManyField('transactions.TransactionType', related_name='portfolios', blank=True,
                                               verbose_name=ugettext_lazy('transaction types'))

    attributes = GenericRelation(GenericAttribute, verbose_name=ugettext_lazy('attributes'))
    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))
    tags = GenericRelation(TagLink, verbose_name=ugettext_lazy('tags'))
    attrs = JSONField(blank=True, null=True)

    objects = CachingManager()

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('portfolio')
        verbose_name_plural = ugettext_lazy('portfolios')
        permissions = (
            # ('view_portfolio', 'Can view portfolio'),
            ('manage_portfolio', 'Can manage portfolio'),
        )

        base_manager_name = 'objects'

    @property
    def is_default(self):
        return self.master_user.portfolio_id == self.id if self.master_user_id else False
