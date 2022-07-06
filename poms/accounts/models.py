from __future__ import unicode_literals, print_function

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy
from mptt.models import MPTTModel


from poms.common.models import NamedModel, FakeDeletableModel, EXPRESSION_FIELD_LENGTH, DataTimeStampedModel
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.currencies.models import Currency
from poms.obj_attrs.models import GenericAttribute
from poms.obj_perms.models import GenericObjectPermission
from poms.tags.models import TagLink
from poms.users.models import MasterUser, Member


class AccountType(NamedModel, FakeDeletableModel, DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser, related_name='account_types', verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    show_transaction_details = models.BooleanField(default=False,
                                                   verbose_name=gettext_lazy('show transaction details'))
    transaction_details_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True,
                                                verbose_name=gettext_lazy('transaction details expr'))

    attributes = GenericRelation(GenericAttribute, verbose_name=gettext_lazy('attributes'))

    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=gettext_lazy('object permissions'))
    tags = GenericRelation(TagLink, verbose_name=gettext_lazy('tags'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('account type')
        verbose_name_plural = gettext_lazy('account types')
        permissions = [
            # ('view_accounttype', 'Can view account type'),
            ('manage_accounttype', 'Can manage account type'),
        ]

    @property
    def is_default(self):
        return self.master_user.account_type_id == self.id if self.master_user_id else False


class Account(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser, related_name='accounts', verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    type = models.ForeignKey(AccountType, on_delete=models.PROTECT, null=True, blank=True,
                             verbose_name=gettext_lazy('account type'))
    is_valid_for_all_portfolios = models.BooleanField(default=True,
                                                      verbose_name=gettext_lazy('is valid for all portfolios'))

    attributes = GenericRelation(GenericAttribute, verbose_name=gettext_lazy('attributes'))
    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=gettext_lazy('object permissions'))
    tags = GenericRelation(TagLink, verbose_name=gettext_lazy('tags'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('account')
        verbose_name_plural = gettext_lazy('accounts')
        permissions = [
            # ('view_account', 'Can view account'),
            ('manage_account', 'Can manage account'),
        ]


    @property
    def is_default(self):
        return self.master_user.account_id == self.id if self.master_user_id else False
