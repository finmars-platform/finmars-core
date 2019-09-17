from __future__ import unicode_literals

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import ugettext_lazy
from mptt.models import MPTTModel

from poms.common.models import NamedModel, FakeDeletableModel
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.obj_attrs.models import GenericAttribute
from poms.obj_perms.models import GenericObjectPermission
from poms.tags.models import TagLink
from poms.users.models import MasterUser, Member


class CounterpartyGroup(NamedModel, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='counterparty_groups',
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))
    tags = GenericRelation(TagLink, verbose_name=ugettext_lazy('tags'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('counterparty group')
        verbose_name_plural = ugettext_lazy('counterparty groups')
        permissions = [
            # ('view_counterpartygroup', 'Can view counterparty group'),
            ('manage_counterpartygroup', 'Can manage counterparty group'),
        ]

    @property
    def is_default(self):
        return self.master_user.counterparty_group_id == self.id if self.master_user_id else False


# class CounterpartyGroupUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(CounterpartyGroup, related_name='user_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('counterparty groups - user permission')
#         verbose_name_plural = ugettext_lazy('counterparty groups - user permissions')
#
#
# class CounterpartyGroupGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(CounterpartyGroup, related_name='group_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('counterparty groups - group permission')
#         verbose_name_plural = ugettext_lazy('counterparty groups - group permissions')


class Counterparty(NamedModelAutoMapping, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='counterparties',
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)
    group = models.ForeignKey(CounterpartyGroup, related_name='counterparties', null=True, blank=True,
                              verbose_name=ugettext_lazy('group'), on_delete=models.SET_NULL)
    is_valid_for_all_portfolios = models.BooleanField(default=True,
                                                      verbose_name=ugettext_lazy('is valid for all portfolios'))

    attributes = GenericRelation(GenericAttribute, verbose_name=ugettext_lazy('attributes'))
    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))
    tags = GenericRelation(TagLink, verbose_name=ugettext_lazy('tags'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('counterparty')
        verbose_name_plural = ugettext_lazy('counterparties')
        ordering = ['user_code']
        permissions = [
            # ('view_counterparty', 'Can view counterparty'),
            ('manage_counterparty', 'Can manage counterparty'),
        ]

    @property
    def is_default(self):
        return self.master_user.counterparty_id == self.id if self.master_user_id else False


# class CounterpartyUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(Counterparty, related_name='user_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('counterparties - user permission')
#         verbose_name_plural = ugettext_lazy('counterparties - user permissions')
#
#
# class CounterpartyGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(Counterparty, related_name='group_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('counterparties - group permission')
#         verbose_name_plural = ugettext_lazy('counterparties - group permissions')


# class CounterpartyAttributeType(AbstractAttributeType):
#     object_permissions = GenericRelation(GenericObjectPermission)
#
#     class Meta(AbstractAttributeType.Meta):
#         verbose_name = ugettext_lazy('counterparty attribute type')
#         verbose_name_plural = ugettext_lazy('counterparty attribute types')
#         permissions = [
#             ('view_counterpartyattributetype', 'Can view counterparty attribute type'),
#             ('manage_counterpartyattributetype', 'Can manage counterparty attribute type'),
#         ]


# class CounterpartyAttributeTypeUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(CounterpartyAttributeType, related_name='user_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('counterparty attribute types - user permission')
#         verbose_name_plural = ugettext_lazy('counterparty attribute types - user permissions')
#
#
# class CounterpartyAttributeTypeGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(CounterpartyAttributeType, related_name='group_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('counterparty attribute types - group permission')
#         verbose_name_plural = ugettext_lazy('counterparty attribute types - group permissions')


# class CounterpartyClassifier(AbstractClassifier):
#     attribute_type = models.ForeignKey(CounterpartyAttributeType, related_name='classifiers',
#                                        verbose_name=ugettext_lazy('attribute type'))
#     parent = TreeForeignKey('self', related_name='children', null=True, blank=True, db_index=True,
#                             verbose_name=ugettext_lazy('parent'))
#
#     class Meta(AbstractClassifier.Meta):
#         verbose_name = ugettext_lazy('counterparty classifier')
#         verbose_name_plural = ugettext_lazy('counterparty classifiers')
#
#
# class CounterpartyAttributeTypeOption(AbstractAttributeTypeOption):
#     member = models.ForeignKey(Member, related_name='counterparty_attribute_type_options',
#                                verbose_name=ugettext_lazy('member'))
#     attribute_type = models.ForeignKey(CounterpartyAttributeType, related_name='options',
#                                        verbose_name=ugettext_lazy('attribute type'))
#
#     class Meta(AbstractAttributeTypeOption.Meta):
#         verbose_name = ugettext_lazy('counterparty attribute types - option')
#         verbose_name_plural = ugettext_lazy('counterparty attribute types - options')
#
#
# class CounterpartyAttribute(AbstractAttribute):
#     attribute_type = models.ForeignKey(CounterpartyAttributeType, related_name='attributes',
#                                        verbose_name=ugettext_lazy('attribute type'))
#     content_object = models.ForeignKey(Counterparty, related_name='attributes',
#                                        verbose_name=ugettext_lazy('content object'))
#     classifier = models.ForeignKey(CounterpartyClassifier, on_delete=models.SET_NULL, null=True, blank=True,
#                                    verbose_name=ugettext_lazy('classifier'))
#
#     class Meta(AbstractAttribute.Meta):
#         verbose_name = ugettext_lazy('counterparty attribute')
#         verbose_name_plural = ugettext_lazy('counterparty attributes')


# -----


class ResponsibleGroup(NamedModel, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='responsible_groups',
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))
    tags = GenericRelation(TagLink, verbose_name=ugettext_lazy('tags'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('responsible group')
        verbose_name_plural = ugettext_lazy('responsible groups')
        permissions = [
            # ('view_responsiblegroup', 'Can view responsible group'),
            ('manage_responsiblegroup', 'Can manage responsible group'),
        ]

    @property
    def is_default(self):
        return self.master_user.counterparty_group_id == self.id if self.master_user_id else False


# class ResponsibleGroupUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(ResponsibleGroup, related_name='user_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('responsible groups - user permission')
#         verbose_name_plural = ugettext_lazy('responsible groups - user permissions')
#
#
# class ResponsibleGroupGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(ResponsibleGroup, related_name='group_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('responsible groups - group permission')
#         verbose_name_plural = ugettext_lazy('responsible groups - group permissions')


class Responsible(NamedModelAutoMapping, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='responsibles', verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)
    group = models.ForeignKey(ResponsibleGroup, related_name='responsibles', null=True, blank=True,
                              verbose_name=ugettext_lazy('group'), on_delete=models.SET_NULL)
    is_valid_for_all_portfolios = models.BooleanField(default=True,
                                                      verbose_name=ugettext_lazy('is valid for all portfolios'))

    attributes = GenericRelation(GenericAttribute, verbose_name=ugettext_lazy('attributes'))
    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))
    tags = GenericRelation(TagLink, verbose_name=ugettext_lazy('tags'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('responsible')
        verbose_name_plural = ugettext_lazy('responsibles')
        ordering = ['user_code']
        permissions = [
            # ('view_responsible', 'Can view responsible'),
            ('manage_responsible', 'Can manage responsible'),
        ]

    @property
    def is_default(self):
        return self.master_user.responsible_id == self.id if self.master_user_id else False

# class ResponsibleUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(Responsible, related_name='user_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('responsibles - user permission')
#         verbose_name_plural = ugettext_lazy('responsibles - user permissions')
#
#
# class ResponsibleGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(Responsible, related_name='group_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('responsibles - group permission')
#         verbose_name_plural = ugettext_lazy('responsibles - group permissions')


# class ResponsibleAttributeType(AbstractAttributeType):
#     object_permissions = GenericRelation(GenericObjectPermission)
#
#     class Meta(AbstractAttributeType.Meta):
#         verbose_name = ugettext_lazy('responsible attribute type')
#         verbose_name_plural = ugettext_lazy('responsible attribute types')
#         permissions = [
#             ('view_responsibleattributetype', 'Can view responsible attribute type'),
#             ('manage_responsibleattributetype', 'Can manage responsible attribute type'),
#         ]


# class ResponsibleAttributeTypeUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(ResponsibleAttributeType, related_name='user_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('responsible attribute types - user permission')
#         verbose_name_plural = ugettext_lazy('responsible attribute types - user permissions')
#
#
# class ResponsibleAttributeTypeGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(ResponsibleAttributeType, related_name='group_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('responsible attribute types - group permission')
#         verbose_name_plural = ugettext_lazy('responsible attribute types - group permissions')


# class ResponsibleClassifier(AbstractClassifier):
#     attribute_type = models.ForeignKey(ResponsibleAttributeType, related_name='classifiers',
#                                        verbose_name=ugettext_lazy('attribute type'))
#     parent = TreeForeignKey('self', related_name='children', null=True, blank=True, db_index=True,
#                             verbose_name=ugettext_lazy('parent'))
#
#     class Meta(AbstractClassifier.Meta):
#         verbose_name = ugettext_lazy('responsible classifier')
#         verbose_name_plural = ugettext_lazy('responsible classifiers')
#
#
# class ResponsibleAttributeTypeOption(AbstractAttributeTypeOption):
#     member = models.ForeignKey(Member, related_name='responsible_attribute_type_options',
#                                verbose_name=ugettext_lazy('member'))
#     attribute_type = models.ForeignKey(ResponsibleAttributeType, related_name='options',
#                                        verbose_name=ugettext_lazy('attribute type'))
#
#     class Meta(AbstractAttributeTypeOption.Meta):
#         verbose_name = ugettext_lazy('responsible attribute types - option')
#         verbose_name_plural = ugettext_lazy('responsible attribute types - options')
#
#
# class ResponsibleAttribute(AbstractAttribute):
#     attribute_type = models.ForeignKey(ResponsibleAttributeType, related_name='attributes',
#                                        verbose_name=ugettext_lazy('attribute type'))
#     content_object = models.ForeignKey(Responsible, related_name='attributes',
#                                        verbose_name=ugettext_lazy('content object'))
#     classifier = models.ForeignKey(ResponsibleClassifier, on_delete=models.SET_NULL, null=True, blank=True,
#                                    verbose_name=ugettext_lazy('classifier'))
#
#     class Meta(AbstractAttribute.Meta):
#         verbose_name = ugettext_lazy('responsible attribute')
#         verbose_name_plural = ugettext_lazy('responsible attributes')
