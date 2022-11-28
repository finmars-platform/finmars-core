from __future__ import unicode_literals

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import NamedModel, FakeDeletableModel, DataTimeStampedModel
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.obj_attrs.models import GenericAttribute
from poms.obj_perms.models import GenericObjectPermission
from poms.users.models import MasterUser


class CounterpartyGroup(NamedModel, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='counterparty_groups',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=gettext_lazy('object permissions'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('counterparty group')
        verbose_name_plural = gettext_lazy('counterparty groups')
        permissions = [
            # ('view_counterpartygroup', 'Can view counterparty group'),
            ('manage_counterpartygroup', 'Can manage counterparty group'),
        ]

    @property
    def is_default(self):
        return self.master_user.counterparty_group_id == self.id if self.master_user_id else False


class Counterparty(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser, related_name='counterparties',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    group = models.ForeignKey(CounterpartyGroup, related_name='counterparties', null=True, blank=True,
                              verbose_name=gettext_lazy('group'), on_delete=models.SET_NULL)
    is_valid_for_all_portfolios = models.BooleanField(default=True,
                                                      verbose_name=gettext_lazy('is valid for all portfolios'))

    attributes = GenericRelation(GenericAttribute, verbose_name=gettext_lazy('attributes'))
    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=gettext_lazy('object permissions'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('counterparty')
        verbose_name_plural = gettext_lazy('counterparties')
        ordering = ['user_code']
        permissions = [
            # ('view_counterparty', 'Can view counterparty'),
            ('manage_counterparty', 'Can manage counterparty'),
        ]

    @property
    def is_default(self):
        return self.master_user.counterparty_id == self.id if self.master_user_id else False


class ResponsibleGroup(NamedModel, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='responsible_groups',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=gettext_lazy('object permissions'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('responsible group')
        verbose_name_plural = gettext_lazy('responsible groups')
        permissions = [
            # ('view_responsiblegroup', 'Can view responsible group'),
            ('manage_responsiblegroup', 'Can manage responsible group'),
        ]

    @property
    def is_default(self):
        return self.master_user.counterparty_group_id == self.id if self.master_user_id else False


class Responsible(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser, related_name='responsibles', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    group = models.ForeignKey(ResponsibleGroup, related_name='responsibles', null=True, blank=True,
                              verbose_name=gettext_lazy('group'), on_delete=models.SET_NULL)
    is_valid_for_all_portfolios = models.BooleanField(default=True,
                                                      verbose_name=gettext_lazy('is valid for all portfolios'))

    attributes = GenericRelation(GenericAttribute, verbose_name=gettext_lazy('attributes'))
    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=gettext_lazy('object permissions'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('responsible')
        verbose_name_plural = gettext_lazy('responsibles')
        ordering = ['user_code']
        permissions = [
            # ('view_responsible', 'Can view responsible'),
            ('manage_responsible', 'Can manage responsible'),
        ]

    @property
    def is_default(self):
        return self.master_user.responsible_id == self.id if self.master_user_id else False
