from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from poms.common.models import NamedModel, EXPRESSION_FIELD_LENGTH
from poms.configuration.models import ConfigurationModel
from poms.obj_perms.models import GenericObjectPermission
from poms.users.models import MasterUser, Member


class GenericAttributeType(NamedModel, ConfigurationModel):
    '''
    Important Entity, which allows users to create own columns
    it support following data types
        String(text,char) = 10
        Number(actually its float) = 20
        Classifier(Nested Dictionaries) = 30
        Date(yyyy-mm-dd format) = 40

    GenericAttributeType is Entity depended
    it means that
        Instrument.attributes.country
    is not the same GenericAttributeType as
        Currency.attributes.country

    So each entity has own namespace for user attributes

    Sometimes User Attributes could contain formula instead of value
    In that case we call in Calculated User Attribute (look at can_recalculate checkbox)

    ==== Important ====
    This entity is part of Configuration Engine
    Also it relates to Finmars Marketplace

    '''
    STRING = 10
    NUMBER = 20
    CLASSIFIER = 30
    DATE = 40

    VALUE_TYPES = (
        (NUMBER, gettext_lazy('Number')),
        (STRING, gettext_lazy('String')),
        (DATE, gettext_lazy('Date')),
        (CLASSIFIER, gettext_lazy('Classifier')),
    )

    USER = 1
    SYSTEM = 2

    KIND_TYPES = (
        (USER, gettext_lazy('User')),
        (SYSTEM, gettext_lazy('System')),
    )

    master_user = models.ForeignKey(MasterUser, verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, verbose_name=gettext_lazy('content type'), on_delete=models.CASCADE)
    value_type = models.PositiveSmallIntegerField(choices=VALUE_TYPES, default=STRING,
                                                  verbose_name=gettext_lazy('value type'))

    kind = models.PositiveSmallIntegerField(choices=KIND_TYPES, default=USER,
                                            verbose_name=gettext_lazy('kind'))

    tooltip = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('tooltip'))

    favorites = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('favorites'))

    prefix = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('prefix'))

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, null=True,
                            verbose_name=gettext_lazy('expression'))

    can_recalculate = models.BooleanField(default=False, verbose_name=gettext_lazy("can recalculate"))

    order = models.IntegerField(default=0, verbose_name=gettext_lazy('order'))

    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=gettext_lazy('object permissions'))

    class Meta(NamedModel.Meta):
        verbose_name = gettext_lazy('attribute type')
        verbose_name_plural = gettext_lazy('attribute types')
        ordering = ['name']
        unique_together = [
            ['master_user', 'content_type', 'user_code']
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
    '''
    Really weird entity, probably need refactor
    '''
    attribute_type = models.ForeignKey(GenericAttributeType, related_name='options',
                                       verbose_name=gettext_lazy('attribute type'), on_delete=models.CASCADE)
    member = models.ForeignKey(Member, verbose_name=gettext_lazy('member'), on_delete=models.CASCADE)
    is_hidden = models.BooleanField(default=False, verbose_name=gettext_lazy('is hidden'))

    class Meta:
        unique_together = [
            ['member', 'attribute_type']
        ]

    def __str__(self):
        # return '%s - %s' % (self.member, self.attribute_type)
        return '%s' % (self.attribute_type,)


class GenericClassifier(MPTTModel):
    '''
        This Nested-dictionary entity, most of the time is headache
        poor concept and poor implementation

        Most of the time there was an example of Country
            USA (country level)
               NY (city level)
            Russia
               Moscow

        But not ironically Country becomes system Relation field, and now most of the use cases are just flat lists

        I wish there will be another value_type for AttributeType like: List
        and its just list of values


    '''
    attribute_type = models.ForeignKey(GenericAttributeType, related_name='classifiers',
                                       verbose_name=gettext_lazy('attribute type'), on_delete=models.CASCADE)

    parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True,
                            verbose_name=gettext_lazy('parent'), on_delete=models.CASCADE)

    name = models.CharField(max_length=255, blank=True, verbose_name=gettext_lazy('name'))

    class MPTTMeta:
        order_insertion_by = ['attribute_type', 'name']

    class Meta:
        verbose_name = gettext_lazy('classifier')
        verbose_name_plural = gettext_lazy('classifiers')
        ordering = ['tree_id', 'level', 'name']

    def __str__(self):
        return self.name


class GenericAttribute(models.Model):
    '''
    Actual Instance of AttributeType linked with instance of Entity

    so whole picture looks like this

    "instrument": {
        "id": 1,
        "user_code": "FMRS"
        "name": "Finmars SA"
        "attributes": [
            {
              "id": 1,
              "attribute_type": {
                "id": 1,
                "user_code": "asset_type",
                "name": "Asset Type"
                "value_type": 10
              },
              value_string: "Stock"
            }
        ]

    }

    '''
    attribute_type = models.ForeignKey(GenericAttributeType, verbose_name=gettext_lazy('attribute type'),
                                       on_delete=models.CASCADE)

    content_type = models.ForeignKey(ContentType, verbose_name=gettext_lazy('content type'), on_delete=models.CASCADE)
    object_id = models.BigIntegerField(db_index=True, verbose_name=gettext_lazy('object id'))
    content_object = GenericForeignKey('content_type', 'object_id')

    value_string = models.CharField(db_index=True, max_length=255, null=True, blank=True,
                                    verbose_name=gettext_lazy('value (String)'))
    value_float = models.FloatField(db_index=True, null=True, blank=True, verbose_name=gettext_lazy('value (Float)'))
    value_date = models.DateField(db_index=True, null=True, blank=True, verbose_name=gettext_lazy('value (Date)'))
    classifier = models.ForeignKey(GenericClassifier, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name=gettext_lazy('classifier'))

    class Meta:
        verbose_name = gettext_lazy('attribute')
        verbose_name_plural = gettext_lazy('attributes')
        index_together = [
            ['content_type', 'object_id']
        ]
        unique_together = [
            ['attribute_type', 'object_id', 'content_type']
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
