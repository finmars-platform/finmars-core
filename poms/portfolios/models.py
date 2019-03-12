from __future__ import unicode_literals

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import ugettext_lazy
from django.contrib.postgres.fields import JSONField
from poms.common.models import NamedModel, FakeDeletableModel
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.obj_attrs.models import GenericAttribute
from poms.obj_perms.models import GenericObjectPermission
from poms.tags.models import TagLink
from poms.users.models import MasterUser, Member


class Portfolio(NamedModelAutoMapping, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='portfolios', verbose_name=ugettext_lazy('master user'))
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

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('portfolio')
        verbose_name_plural = ugettext_lazy('portfolios')
        permissions = (
            ('view_portfolio', 'Can view portfolio'),
            ('manage_portfolio', 'Can manage portfolio'),
        )

    @property
    def is_default(self):
        return self.master_user.portfolio_id == self.id if self.master_user_id else False

# class PortfolioUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(Portfolio, related_name='user_object_permissions')
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('portfolios - user permission')
#         verbose_name_plural = ugettext_lazy('portfolios - user permissions')
#
#
# class PortfolioGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(Portfolio, related_name='group_object_permissions')
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('portfolios - group permission')
#         verbose_name_plural = ugettext_lazy('portfolios - group permissions')


# class PortfolioAttributeType(AbstractAttributeType):
#     object_permissions = GenericRelation(GenericObjectPermission)
#
#     class Meta(AbstractAttributeType.Meta):
#         verbose_name = ugettext_lazy('portfolio attribute type')
#         verbose_name_plural = ugettext_lazy('portfolio attribute types')
#         permissions = [
#             ('view_portfolioattributetype', 'Can view portfolio attribute type'),
#             ('manage_portfolioattributetype', 'Can manage portfolio attribute type'),
#         ]


# class PortfolioAttributeTypeUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(PortfolioAttributeType, related_name='user_object_permissions')
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('portfolio attribute types - user permission')
#         verbose_name_plural = ugettext_lazy('portfolio attribute types - user permissions')
#
#
# class PortfolioAttributeTypeGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(PortfolioAttributeType, related_name='group_object_permissions')
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('portfolio attribute types - group permission')
#         verbose_name_plural = ugettext_lazy('portfolio attribute types - group permissions')


# class PortfolioClassifier(AbstractClassifier):
#     attribute_type = models.ForeignKey(PortfolioAttributeType, related_name='classifiers',
#                                        verbose_name=ugettext_lazy('attribute type'))
#     parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True,
#                             verbose_name=ugettext_lazy('parent'))
#
#     class Meta(AbstractClassifier.Meta):
#         verbose_name = ugettext_lazy('portfolio classifier')
#         verbose_name_plural = ugettext_lazy('portfolio classifiers')
#
#
# class PortfolioAttributeTypeOption(AbstractAttributeTypeOption):
#     member = models.ForeignKey(Member, related_name='portfolio_attribute_type_options')
#     attribute_type = models.ForeignKey(PortfolioAttributeType, related_name='options')
#
#     class Meta(AbstractAttributeTypeOption.Meta):
#         verbose_name = ugettext_lazy('portfolio attribute types - option')
#         verbose_name_plural = ugettext_lazy('portfolio attribute types - options')
#
#
# class PortfolioAttribute(AbstractAttribute):
#     attribute_type = models.ForeignKey(PortfolioAttributeType, related_name='attributes',
#                                        verbose_name=ugettext_lazy('attribute type'))
#     content_object = models.ForeignKey(Portfolio, related_name='attributes')
#     classifier = models.ForeignKey(PortfolioClassifier, on_delete=models.SET_NULL, null=True, blank=True)
#
#     class Meta(AbstractAttribute.Meta):
#         verbose_name = ugettext_lazy('portfolio attribute')
#         verbose_name_plural = ugettext_lazy('portfolio attributes')
