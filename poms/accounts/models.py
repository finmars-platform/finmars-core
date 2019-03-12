from __future__ import unicode_literals, print_function

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import ugettext_lazy
from mptt.models import MPTTModel

from poms.common.models import NamedModel, FakeDeletableModel, EXPRESSION_FIELD_LENGTH
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.currencies.models import Currency
from poms.obj_attrs.models import GenericAttribute
from poms.obj_perms.models import GenericObjectPermission
from poms.tags.models import TagLink
from poms.users.models import MasterUser, Member


class AccountType(NamedModel, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='account_types', verbose_name=ugettext_lazy('master user'))
    show_transaction_details = models.BooleanField(default=False,
                                                   verbose_name=ugettext_lazy('show transaction details'))
    transaction_details_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True,
                                                verbose_name=ugettext_lazy('transaction details expr'))

    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))
    tags = GenericRelation(TagLink, verbose_name=ugettext_lazy('tags'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('account type')
        verbose_name_plural = ugettext_lazy('account types')
        permissions = [
            ('view_accounttype', 'Can view account type'),
            ('manage_accounttype', 'Can manage account type'),
        ]

    @property
    def is_default(self):
        return self.master_user.account_type_id == self.id if self.master_user_id else False


# class AccountTypeUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(AccountType, related_name='user_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('account types - user permission')
#         verbose_name_plural = ugettext_lazy('account types - user permissions')
#
#
# class AccountTypeGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(AccountType, related_name='group_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('account types - group permission')
#         verbose_name_plural = ugettext_lazy('account types - group permissions')


class Account(NamedModelAutoMapping, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='accounts', verbose_name=ugettext_lazy('master user'))
    type = models.ForeignKey(AccountType, on_delete=models.PROTECT, null=True, blank=True,
                             verbose_name=ugettext_lazy('account type'))
    is_valid_for_all_portfolios = models.BooleanField(default=True,
                                                      verbose_name=ugettext_lazy('is valid for all portfolios'))

    attributes = GenericRelation(GenericAttribute, verbose_name=ugettext_lazy('attributes'))
    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))
    tags = GenericRelation(TagLink, verbose_name=ugettext_lazy('tags'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('account')
        verbose_name_plural = ugettext_lazy('accounts')
        permissions = [
            ('view_account', 'Can view account'),
            ('manage_account', 'Can manage account'),
        ]

    @property
    def is_default(self):
        return self.master_user.account_id == self.id if self.master_user_id else False

# class AccountUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(Account, related_name='user_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('accounts - user permission')
#         verbose_name_plural = ugettext_lazy('accounts - user permissions')
#
#
# class AccountGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(Account, related_name='group_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('accounts - group permission')
#         verbose_name_plural = ugettext_lazy('accounts - group permissions')


# class AccountAttributeType(AbstractAttributeType):
#     # classifier_root = models.OneToOneField(
#     #     AccountClassifier,
#     #     null=True,
#     #     blank=True,
#     #     on_delete=models.PROTECT,
#     #     verbose_name=ugettext_lazy('classifier')
#     # )
#
#     object_permissions = GenericRelation(GenericObjectPermission)
#
#     class Meta(AbstractAttributeType.Meta):
#         verbose_name = ugettext_lazy('account attribute type')
#         verbose_name_plural = ugettext_lazy('account attribute types')
#         permissions = [
#             ('view_accountattributetype', 'Can view account attribute type'),
#             ('manage_accountattributetype', 'Can manage account attribute type'),
#         ]


# class AccountAttributeTypeUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(AccountAttributeType, related_name='user_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('account attribute types - user permission')
#         verbose_name_plural = ugettext_lazy('account attribute types - user permissions')
#
#
# class AccountAttributeTypeGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(AccountAttributeType, related_name='group_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('account attribute types - group permission')
#         verbose_name_plural = ugettext_lazy('account attribute types - group permissions')


# class AccountClassifier(AbstractClassifier):
#     attribute_type = models.ForeignKey(AccountAttributeType, related_name='classifiers',
#                                        verbose_name=ugettext_lazy('attribute type'))
#     parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True,
#                             verbose_name=ugettext_lazy('parent'))
#
#     class Meta(AbstractClassifier.Meta):
#         verbose_name = ugettext_lazy('account classifier')
#         verbose_name_plural = ugettext_lazy('account classifiers')
#
#
# class AccountAttributeTypeOption(AbstractAttributeTypeOption):
#     member = models.ForeignKey(Member, related_name='account_attribute_type_options',
#                                verbose_name=ugettext_lazy('member'))
#     attribute_type = models.ForeignKey(AccountAttributeType, related_name='options',
#                                        verbose_name=ugettext_lazy('attribute type'))
#
#     class Meta(AbstractAttributeTypeOption.Meta):
#         verbose_name = ugettext_lazy('account attribute types - option')
#         verbose_name_plural = ugettext_lazy('account attribute types - options')
#
#
# class AccountAttribute(AbstractAttribute):
#     attribute_type = models.ForeignKey(AccountAttributeType, related_name='attributes',
#                                        verbose_name=ugettext_lazy('attribute type'))
#     content_object = models.ForeignKey(Account, related_name='attributes',
#                                        verbose_name=ugettext_lazy('content object'))
#     classifier = models.ForeignKey(AccountClassifier, on_delete=models.SET_NULL, null=True, blank=True,
#                                    verbose_name=ugettext_lazy('classifier'))
#
#     class Meta(AbstractAttribute.Meta):
#         verbose_name = ugettext_lazy('account attribute')
#         verbose_name_plural = ugettext_lazy('account attributes')
