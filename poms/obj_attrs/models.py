from datetime import date

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from poms.common.models import NamedModel
from poms.obj_perms.models import GenericObjectPermission
from poms.users.models import MasterUser, Member


# class AbstractAttributeType(NamedModel):
#     STRING = 10
#     NUMBER = 20
#     CLASSIFIER = 30
#     DATE = 40
#
#     VALUE_TYPES = (
#         (NUMBER, ugettext_lazy('Number')),
#         (STRING, ugettext_lazy('String')),
#         (DATE, ugettext_lazy('Date')),
#         (CLASSIFIER, ugettext_lazy('Classifier')),
#     )
#
#     master_user = models.ForeignKey(MasterUser, verbose_name=ugettext_lazy('master user'))
#     value_type = models.PositiveSmallIntegerField(choices=VALUE_TYPES, default=STRING,
#                                                   verbose_name=ugettext_lazy('value type'))
#     order = models.IntegerField(default=0, verbose_name=ugettext_lazy('order'))
#
#     class Meta(NamedModel.Meta):
#         abstract = True
#         unique_together = [
#             ['master_user', 'name']
#         ]
#         ordering = ['name']
#
#     def get_value_atr(self):
#         if self.value_type == self.STRING:
#             return 'value_string'
#         elif self.value_type == self.NUMBER:
#             return 'value_float'
#         elif self.value_type == self.DATE:
#             return 'value_date'
#         elif self.value_type == self.CLASSIFIER:
#             return 'classifier'
#         raise ValueError('Unknown value_type: %s' % self.value_type)
#
#     def get_value(self, obj):
#         attr_name = self.get_value_atr()
#         return getattr(obj, attr_name)
#
#     def __str__(self):
#         return self.name
#
#
# class AbstractClassifier(MPTTModel):
#     # attribute_type
#     # parent
#     name = models.CharField(max_length=255, blank=True, verbose_name=ugettext_lazy('name'))
#
#     class MPTTMeta:
#         order_insertion_by = ['attribute_type', 'name']
#
#     class Meta:
#         abstract = True
#         ordering = ['tree_id', 'level', 'name']
#
#     def __str__(self):
#         return self.name
#
#
# class AbstractAttributeTypeOption(models.Model):
#     # attribute_type -> actual attribute model
#     is_hidden = models.BooleanField(default=False, verbose_name=ugettext_lazy('is hidden'))
#
#     class Meta:
#         abstract = True
#         unique_together = [
#             ['member', 'attribute_type']
#         ]
#
#     def __str__(self):
#         # return '%s - %s' % (self.member, self.attribute_type)
#         return '%s' % (self.attribute_type,)
#
#
# class AbstractAttribute(models.Model):
#     # attribute_type -> actual attribute model
#     # content_object -> actual object
#
#     value_string = models.CharField(max_length=255, default='', blank=True,
#                                     verbose_name=ugettext_lazy('value (String)'))
#     value_float = models.FloatField(default=0.0, verbose_name=ugettext_lazy('value (Float)'))
#     value_date = models.DateField(default=date.min, verbose_name=ugettext_lazy('value (Date)'))
#
#     class Meta:
#         abstract = True
#         unique_together = [
#             ['content_object', 'attribute_type']
#         ]
#         ordering = ['attribute_type']
#
#     def __str__(self):
#         # return '%s' % (self.get_value(), )
#         return '%s' % (self.attribute_type,)
#
#     def get_value(self):
#         t = self.attribute_type.value_type
#         if t == AbstractAttributeType.STRING:
#             return self.value_string
#         elif t == AbstractAttributeType.NUMBER:
#             return self.value_float
#         elif t == AbstractAttributeType.DATE:
#             return self.value_date
#         elif t == AbstractAttributeType.CLASSIFIER:
#             return self.classifier
#         return None
#
#     def set_value(self, value):
#         t = self.attribute_type.value_type
#         if t == AbstractAttributeType.STRING:
#             self.value_string = value
#         elif t == AbstractAttributeType.NUMBER:
#             self.value_float = value
#         elif t == AbstractAttributeType.DATE:
#             self.value_date = value
#         elif t == AbstractAttributeType.CLASSIFIER:
#             self.classifier = value
#
#     value = property(get_value, set_value)


class GenericAttributeType(NamedModel):
    STRING = 10
    NUMBER = 20
    CLASSIFIER = 30
    DATE = 40

    VALUE_TYPES = (
        (NUMBER, ugettext_lazy('Number')),
        (STRING, ugettext_lazy('String')),
        (DATE, ugettext_lazy('Date')),
        (CLASSIFIER, ugettext_lazy('Classifier')),
    )

    master_user = models.ForeignKey(MasterUser, verbose_name=ugettext_lazy('master user'))
    content_type = models.ForeignKey(ContentType, verbose_name=ugettext_lazy('content type'))
    value_type = models.PositiveSmallIntegerField(choices=VALUE_TYPES, default=STRING,
                                                  verbose_name=ugettext_lazy('value type'))
    order = models.IntegerField(default=0, verbose_name=ugettext_lazy('order'))

    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))

    class Meta(NamedModel.Meta):
        verbose_name = ugettext_lazy('attribute type')
        verbose_name_plural = ugettext_lazy('attribute types')
        ordering = ['name']
        unique_together = [
            ['master_user', 'content_type', 'name']
        ]

    def get_value_atr(self):
        if self.value_type == self.STRING:
            return 'value_string'
        elif self.value_type == self.NUMBER:
            return 'value_float'
        elif self.value_type == self.DATE:
            return 'value_date'
        elif self.value_type == self.CLASSIFIER:
            return 'classifier'
        raise ValueError('Unknown value_type: %s' % self.value_type)

    def get_value(self, obj):
        attr_name = self.get_value_atr()
        return getattr(obj, attr_name)

    def __str__(self):
        return self.name


class GenericAttributeTypeOption(models.Model):
    attribute_type = models.ForeignKey(GenericAttributeType, related_name='options',
                                       verbose_name=ugettext_lazy('attribute type'))
    member = models.ForeignKey(Member, verbose_name=ugettext_lazy('member'))
    is_hidden = models.BooleanField(default=False, verbose_name=ugettext_lazy('is hidden'))

    class Meta:
        unique_together = [
            ['member', 'attribute_type']
        ]

    def __str__(self):
        # return '%s - %s' % (self.member, self.attribute_type)
        return '%s' % (self.attribute_type,)


class GenericClassifier(MPTTModel):
    attribute_type = models.ForeignKey(GenericAttributeType, related_name='classifiers',
                                       verbose_name=ugettext_lazy('attribute type'))

    parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True,
                            verbose_name=ugettext_lazy('parent'))

    name = models.CharField(max_length=255, blank=True, verbose_name=ugettext_lazy('name'))

    class MPTTMeta:
        order_insertion_by = ['attribute_type', 'name']

    class Meta:
        verbose_name = ugettext_lazy('classifier')
        verbose_name_plural = ugettext_lazy('classifiers')
        ordering = ['tree_id', 'level', 'name']

    def __str__(self):
        return self.name


class GenericAttribute(models.Model):
    attribute_type = models.ForeignKey(GenericAttributeType, verbose_name=ugettext_lazy('attribute type'))

    content_type = models.ForeignKey(ContentType, verbose_name=ugettext_lazy('content type'))
    object_id = models.BigIntegerField(db_index=True, verbose_name=ugettext_lazy('object id'))
    content_object = GenericForeignKey('content_type', 'object_id')

    value_string = models.CharField(db_index=True, max_length=255, null=True, blank=True,
                                    verbose_name=ugettext_lazy('value (String)'))
    value_float = models.FloatField(db_index=True, null=True, blank=True, verbose_name=ugettext_lazy('value (Float)'))
    value_date = models.DateField(db_index=True, null=True, blank=True, verbose_name=ugettext_lazy('value (Date)'))
    classifier = models.ForeignKey(GenericClassifier, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name=ugettext_lazy('classifier'))

    class Meta:
        verbose_name = ugettext_lazy('attribute')
        verbose_name_plural = ugettext_lazy('attributes')
        index_together = [
            ['content_type', 'object_id']
        ]
        ordering = ['attribute_type']

    def __str__(self):
        # return '%s' % (self.get_value(), )
        return '%s' % (self.attribute_type,)

    def get_value(self):
        t = self.attribute_type.value_type
        if t == GenericAttributeType.STRING:
            return self.value_string
        elif t == GenericAttributeType.NUMBER:
            return self.value_float
        elif t == GenericAttributeType.DATE:
            return self.value_date
        elif t == GenericAttributeType.CLASSIFIER:
            return self.classifier
        return None

    def set_value(self, value):
        t = self.attribute_type.value_type
        if t == GenericAttributeType.STRING:
            self.value_string = value
        elif t == GenericAttributeType.NUMBER:
            self.value_float = value
        elif t == GenericAttributeType.DATE:
            self.value_date = value
        elif t == GenericAttributeType.CLASSIFIER:
            self.classifier = value

    value = property(get_value, set_value)
