from __future__ import unicode_literals

# metestig
import logging
import traceback

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db import models
from mptt.utils import get_cached_trees
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.serializers import ListSerializer

from poms.common.fields import ExpressionField, ContentTypeOrPrimaryKeyRelatedField
from poms.common.formula import safe_eval, ExpressionEvalError
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.common.serializers import ModelWithUserCodeSerializer, ModelMetaSerializer
from poms.integrations.models import PortfolioClassifierMapping, ProviderClass, AccountClassifierMapping, \
    CounterpartyClassifierMapping, ResponsibleClassifierMapping, InstrumentClassifierMapping
from poms.obj_attrs.fields import GenericAttributeTypeField, GenericClassifierField
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier, GenericAttribute
from poms.users.fields import MasterUserField, HiddenMemberField
from poms.users.utils import get_member_from_context, get_master_user_from_context

_l = logging.getLogger('poms.obj_attrs')


class ModelWithAttributesSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super(ModelWithAttributesSerializer, self).__init__(*args, **kwargs)
        self.fields['attributes'] = GenericAttributeSerializer(many=True, required=False, allow_null=True)

    def create(self, validated_data):

        attributes = validated_data.pop('attributes', empty)
        instance = super(ModelWithAttributesSerializer, self).create(validated_data)

        self.create_attributes_if_not_exists(instance)

        self.save_attributes(instance, attributes, True)

        self.calculate_attributes(instance)

        return instance

    def update(self, instance, validated_data):

        attributes = validated_data.pop('attributes', empty)

        instance = super(ModelWithAttributesSerializer, self).update(instance, validated_data)

        # _l.info('attributes %s' % attributes)

        self.create_attributes_if_not_exists(instance)

        if attributes is not empty:
            self.save_attributes(instance, attributes, False)

        self.calculate_attributes(instance)

        return instance

    def create_attributes_if_not_exists(self, instance):

        master_user = get_master_user_from_context(self.context)

        content_type = ContentType.objects.get_for_model(instance)

        attribute_types = GenericAttributeType.objects.filter(content_type=content_type,
                                                              master_user=master_user)

        attributes_to_create = []

        for attribute_type in attribute_types:

            try:

                exists = GenericAttribute.objects.get(attribute_type=attribute_type, content_type=content_type,
                                                      object_id=instance.id)

            except Exception as e:

                _l.debug("create_attributes_if_not_exists.exception %s" % e)
                _l.info("Creating empty attribute %s for %s" % (attribute_type, instance.id))
                _l.info("Creating empty attribute %s for %s" % (attribute_type, instance))

                attributes_to_create.append(GenericAttribute(attribute_type=attribute_type, content_type=content_type,
                                                             object_id=instance.id))

        if len(attributes_to_create):
            GenericAttribute.objects.bulk_create(attributes_to_create)
            _l.info('attributes_to_create %s ' % len(attributes_to_create))

    def recursive_calculation(self, attribute_types, executed_expressions, eval_data, current_index, limit):

        for attribute_type in attribute_types:

            if attribute_type.can_recalculate:
                try:
                    executed_expressions[attribute_type.user_code] = safe_eval(attribute_type.expr,
                                                                               names={'this': eval_data},
                                                                               context={})
                except (ExpressionEvalError, TypeError, Exception, KeyError):
                    executed_expressions[attribute_type.user_code] = 'Invalid Expression'

                eval_data['attributes'][attribute_type.user_code] = executed_expressions[attribute_type.user_code]

        current_index = current_index + 1

        if current_index < limit:
            self.recursive_calculation(attribute_types, executed_expressions, eval_data, current_index, limit)

    def get_attributes_as_obj(self, attributes):

        attributes_converted = {}

        for attr in attributes:

            attribute_type = attr.attribute_type

            if attribute_type.value_type == 10:
                attributes_converted[attribute_type.user_code] = attr.value_string

            if attribute_type.value_type == 20:
                attributes_converted[attribute_type.user_code] = attr.value_float

            if attribute_type.value_type == 30:
                if attr.classifier:
                    attributes_converted[attribute_type.user_code] = attr.classifier.name
                else:
                    attributes_converted[attribute_type.user_code] = None

            if attribute_type.value_type == 40:
                attributes_converted[attribute_type.user_code] = attr.value_date

        return attributes_converted

    def calculate_attributes(self, instance):

        master_user = get_master_user_from_context(self.context)
        content_type = ContentType.objects.get_for_model(instance)

        attr_types_qs = GenericAttributeType.objects.filter(content_type=content_type, master_user=master_user)
        attrs_qs = GenericAttribute.objects.filter(content_type=content_type, object_id=instance.id)

        data = super(ModelWithAttributesSerializer, self).to_representation(instance)

        data['attributes'] = self.get_attributes_as_obj(attrs_qs)

        executed_expressions = {}

        self.recursive_calculation(attr_types_qs, executed_expressions, data, current_index=0, limit=4)

        for attr in attrs_qs:

            if attr.attribute_type.can_recalculate:

                if attr.attribute_type.value_type == GenericAttributeType.STRING:

                    if executed_expressions[attr.attribute_type.user_code] == 'Invalid Expression':
                        attr.value_string = None
                    else:
                        attr.value_string = executed_expressions[attr.attribute_type.user_code]

                if attr.attribute_type.value_type == GenericAttributeType.NUMBER:

                    if executed_expressions[attr.attribute_type.user_code] == 'Invalid Expression':
                        attr.value_float = None
                    else:
                        attr.value_float = executed_expressions[attr.attribute_type.user_code]

                if attr.attribute_type.value_type == GenericAttributeType.DATE:

                    if executed_expressions[attr.attribute_type.user_code] == 'Invalid Expression':
                        attr.value_date = None
                    else:
                        attr.value_date = executed_expressions[attr.attribute_type.user_code]

                if attr.attribute_type.value_type == GenericAttributeType.CLASSIFIER:

                    if executed_expressions[attr.attribute_type.user_code] == 'Invalid Expression':
                        attr.classifier = None
                    else:
                        attr.classifier = executed_expressions[attr.attribute_type.user_code]

                attr.save()

    def save_attributes(self, instance, attributes, created):
        try:
            member = get_member_from_context(self.context)
            attributes = attributes or []

            ctype = ContentType.objects.get_for_model(instance)

            for attr in attributes:

                attribute_type = attr['attribute_type']

                # _l.info('save_attributes.attr %s' % attr)

                oattr = GenericAttribute.objects.get(content_type=ctype, object_id=instance.id,
                                                     attribute_type_id=attribute_type.id)

                if 'value_string' in attr:

                    if attr['value_string'] == '':
                        oattr.value_string = None
                    else:
                        oattr.value_string = attr['value_string']
                if 'value_float' in attr:
                    if attr['value_float'] == '':
                        oattr.value_float = None
                    else:
                        oattr.value_float = attr['value_float']
                if 'value_date' in attr:
                    if attr['value_date'] == '':
                        oattr.value_date = None
                    else:
                        oattr.value_date = attr['value_date']
                if 'classifier' in attr:
                    if attr['classifier'] == '':
                        oattr.classifier = None
                    else:
                        oattr.classifier = attr['classifier']

                oattr.save()

        except Exception as e:
            _l.error("Attribute save error %s " % e)
            _l.error("Attribute save traceback %s " % traceback.format_exc())


class ModelWithAttributesOnlySerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super(ModelWithAttributesOnlySerializer, self).__init__(*args, **kwargs)
        self.fields['attributes'] = GenericAttributeOnlySerializer(many=True, required=False, allow_null=True)


class GenericClassifierRecursiveField(serializers.Serializer):
    def to_representation(self, instance):
        if isinstance(self.parent, ListSerializer):
            cls = self.parent.parent.__class__
        else:
            cls = self.parent.__class__
        return cls(instance=instance, context=self.context).data

    def to_internal_value(self, data):
        if isinstance(self.parent, ListSerializer):
            cls = self.parent.parent.__class__
        else:
            cls = self.parent.__class__
        s = cls(context=self.context, data=data)
        s.is_valid(raise_exception=True)
        return s.validated_data


class GenericClassifierListSerializer(serializers.ListSerializer):
    def get_attribute(self, instance):
        tree = get_cached_trees(instance.classifiers.all())

        return tree


class GenericClassifierSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    children = GenericClassifierRecursiveField(source='get_children', many=True, required=False, allow_null=True)

    class Meta:
        list_serializer_class = GenericClassifierListSerializer
        model = GenericClassifier
        fields = ['id', 'name', 'level', 'children', ]


class GenericClassifierWithoutChildrenSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    parent = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = GenericClassifier
        fields = ['id', 'name', 'level', 'parent', ]


class GenericClassifierNodeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    attribute_type = serializers.PrimaryKeyRelatedField(read_only=True)
    parent = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = GenericClassifier
        fields = ['id', 'attribute_type', 'level', 'parent', 'name', ]

    def create(self, validated_data):
        # print('Create classifier node')

        return GenericClassifier(**validated_data)


class GenericClassifierViewSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(read_only=True)
    parent_object = GenericClassifierRecursiveField(source='parent', read_only=True)

    class Meta:
        list_serializer_class = GenericClassifierListSerializer
        model = GenericClassifier
        fields = ['id', 'name', 'level', 'parent',
                  'parent_object',
                  ]

    def to_representation(self, instance):
        return super(GenericClassifierViewSerializer, self).to_representation(instance)


class GenericAttributeTypeOptionIsHiddenField(serializers.BooleanField):
    def __init__(self, **kwargs):
        kwargs['required'] = False
        kwargs['default'] = False
        # kwargs['allow_null'] = True
        super(GenericAttributeTypeOptionIsHiddenField, self).__init__(**kwargs)

    def get_attribute(self, obj):
        return obj

    def to_representation(self, value):
        # some "optimization" to use preloaded data through prefetch_related
        member = get_member_from_context(self.context)
        for o in value.options.all():
            if o.member_id == member.id:
                return o.is_hidden
        return False


# class GenericAttributeTypeSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer):
class GenericAttributeTypeSerializer(ModelWithUserCodeSerializer, ModelMetaSerializer):
    master_user = MasterUserField()
    is_hidden = GenericAttributeTypeOptionIsHiddenField()
    classifiers = GenericClassifierSerializer(required=False, allow_null=True, many=True)
    classifiers_flat = GenericClassifierWithoutChildrenSerializer(source='classifiers', read_only=True, many=True)

    expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, allow_null=True,
                           default='""')

    content_type = ContentTypeOrPrimaryKeyRelatedField()

    class Meta:
        model = GenericAttributeType
        fields = ['id', 'master_user',

                  'user_code', 'configuration_code',

                  'name', 'short_name', 'public_name', 'notes',
                  'prefix',
                  'favorites',
                  'expr', 'can_recalculate',
                  'tooltip',
                  'kind', 'content_type',
                  'value_type', 'order', 'is_hidden', 'classifiers', 'classifiers_flat']

    def __init__(self, *args, **kwargs):
        # show_classifiers = kwargs.pop('show_classifiers', False)
        # read_only_value_type = kwargs.pop('read_only_value_type', False)
        super(GenericAttributeTypeSerializer, self).__init__(*args, **kwargs)
        # if not show_classifiers:
        #     self.fields.pop('classifiers', None)
        #     self.fields.pop('classifiers_flat', None)
        # if read_only_value_type:
        #     self.fields['value_type'].read_only = True

    def validate(self, attrs):
        attrs = super(GenericAttributeTypeSerializer, self).validate(attrs)
        classifiers = attrs.get('classifiers', None)
        if classifiers:
            self._validate_classifiers(classifiers, id_set=set(), user_code_set=set())
        return attrs

    def _validate_classifiers(self, classifiers, id_set, user_code_set):
        for c in classifiers:
            c_id = c.get('id', None)
            c_user_code = c.get('user_code', None)
            if c_id and c_id in id_set:
                raise ValidationError("classifiers non unique id")
            if c_user_code and c_user_code in user_code_set:
                raise ValidationError("classifiers non unique user_code")
            if c_id:
                id_set.add(c_id)
            if c_user_code:
                user_code_set.add(c_user_code)
            children = c.get('get_children', c.pop('children', []))
            self._validate_classifiers(children, id_set, user_code_set)

    def create(self, validated_data):
        member = get_member_from_context(self.context)
        is_hidden = validated_data.pop('is_hidden', False)
        classifiers = validated_data.pop('classifiers', None)
        instance = super(GenericAttributeTypeSerializer, self).create(validated_data)
        instance.options.create(member=member, is_hidden=is_hidden)
        self.save_classifiers(instance, classifiers)

        self.create_attribute_for_entity_if_not_exist(instance)

        # Do not delete, somehow this awfulness make it works
        instance = GenericAttributeType.objects.get(id=instance.id)

        return instance

    def update(self, instance, validated_data):

        member = get_member_from_context(self.context)
        is_hidden = validated_data.pop('is_hidden', empty)
        classifiers = validated_data.pop('classifiers', empty)
        instance = super(GenericAttributeTypeSerializer, self).update(instance, validated_data)

        if is_hidden is not empty:
            instance.options.update_or_create(member=member, defaults={'is_hidden': is_hidden})

        if classifiers is not empty:
            self.save_classifiers(instance, classifiers)

        # Do not delete, somehow this awfulness make it works (same magic here)
        instance = GenericAttributeType.objects.get(id=instance.id)

        return instance

    def save_classifiers(self, instance, classifier_tree):
        if instance.value_type != GenericAttributeType.CLASSIFIER:
            return
        classifier_tree = classifier_tree or []
        # if classifier_tree is None:
        #     return
        if len(classifier_tree) == 0:
            instance.classifiers.all().delete()
            return

        processed = set()
        prev_node = None

        for node in classifier_tree:
            prev_node = self.save_classifier(instance, node, None, processed, prev_node)

        instance.classifiers.exclude(pk__in=processed).delete()

    def save_classifier(self, instance, node, parent, processed, prev_node_instance=None):

        is_new_node = False
        previous_node_id = None

        if prev_node_instance is not None and hasattr(prev_node_instance, 'id'):  # 'id' in prev_node_instance:
            previous_node_id = prev_node_instance.id

        if 'id' in node:
            try:
                o = instance.classifiers.get(pk=node['id'])
            except ObjectDoesNotExist:
                o = GenericClassifier()
                is_new_node = True
        else:
            o = GenericClassifier()
            is_new_node = True

        # print('o %s', o)

        try:

            self.delete_matched_classifier_node_mapping(instance, o)

            o.parent = parent
            o.attribute_type = instance
            children = node.pop('get_children', node.pop('children', []))
            for k, v in node.items():
                setattr(o, k, v)

            o.save()

            prev_sibling = o.get_previous_sibling()
            prev_sibling_id = None

            if prev_sibling is not None:
                prev_sibling_id = prev_sibling.id

            if prev_sibling_id != previous_node_id:

                if previous_node_id is not None:

                    # instance may contain old data after previous saves, update it
                    prev_node_instance.refresh_from_db()

                    o.move_to(prev_node_instance, 'right')

                else:
                    o.move_to(parent, 'first-child')

            # if  and o.id == prev_sibling.id:

            self.create_classifier_node_mapping(instance, o)

        except IntegrityError as e:
            _l.error("Error save_classifier %s " % e)
            raise ValidationError("non unique user_code")

        processed.add(o.id)
        prev_node = None

        for c in children:
            prev_node = self.save_classifier(instance, c, o, processed, prev_node)

        return o

    def create_classifier_node_mapping(self, instance, node):

        master_user = get_master_user_from_context(self.context)
        bloomberg = ProviderClass.objects.get(pk=ProviderClass.BLOOMBERG)

        if instance.content_type.model == 'portfolio':
            PortfolioClassifierMapping.objects.create(master_user=master_user,
                                                      content_object=node,
                                                      provider=bloomberg,
                                                      attribute_type=instance,
                                                      value=node.name)

        if instance.content_type.model == 'account':
            AccountClassifierMapping.objects.create(master_user=master_user,
                                                    content_object=node,
                                                    provider=bloomberg,
                                                    attribute_type=instance,
                                                    value=node.name)
        if instance.content_type.model == 'counterparty':
            CounterpartyClassifierMapping.objects.create(master_user=master_user,
                                                         content_object=node,
                                                         provider=bloomberg,
                                                         attribute_type=instance,
                                                         value=node.name)
        if instance.content_type.model == 'responsible':
            ResponsibleClassifierMapping.objects.create(master_user=master_user,
                                                        content_object=node,
                                                        provider=bloomberg,
                                                        attribute_type=instance,
                                                        value=node.name)

        if instance.content_type.model == 'instrument':
            InstrumentClassifierMapping.objects.create(master_user=master_user,
                                                       content_object=node,
                                                       provider=bloomberg,
                                                       attribute_type=instance,
                                                       value=node.name)

    def delete_matched_classifier_node_mapping(self, instance, node):

        if instance.content_type.model == 'portfolio':
            PortfolioClassifierMapping.objects.filter(attribute_type=instance,
                                                      value=node.name).delete()

        if instance.content_type.model == 'account':
            AccountClassifierMapping.objects.filter(attribute_type=instance,
                                                    value=node.name).delete()
        if instance.content_type.model == 'counterparty':
            CounterpartyClassifierMapping.objects.filter(attribute_type=instance,
                                                         value=node.name).delete()
        if instance.content_type.model == 'responsible':
            ResponsibleClassifierMapping.objects.filter(attribute_type=instance,
                                                        value=node.name).delete()

        if instance.content_type.model == 'instrument':
            InstrumentClassifierMapping.objects.filter(attribute_type=instance,
                                                       value=node.name).delete()

    def create_attribute_for_entity_if_not_exist(self, instance):

        attrs = []

        master_user = get_master_user_from_context(self.context)

        items = instance.content_type.model_class().objects.filter(master_user=master_user)

        for item in items:

            try:
                exists = GenericAttribute.objects.get(attribute_type=instance, content_type=instance.content_type,
                                                      object_id=item.pk)

            except GenericAttribute.DoesNotExist:

                attrs.append(
                    GenericAttribute(attribute_type=instance, content_type=instance.content_type, object_id=item.pk))

        GenericAttribute.objects.bulk_create(attrs)


class GenericAttributeTypeViewSerializer(serializers.ModelSerializer):
    is_hidden = GenericAttributeTypeOptionIsHiddenField()

    class Meta:
        model = GenericAttributeType
        fields = ['id', 'user_code', 'name', 'short_name', 'public_name', 'notes', 'can_recalculate',
                  'value_type', 'order', 'is_hidden', 'kind']


class GenericAttributeListSerializer(serializers.ListSerializer):
    # Used as list_serializer_class if many=True in AbstractAttributeSerializer
    def get_attribute(self, instance):
        member = get_member_from_context(self.context)
        if member.is_superuser:
            return instance.attributes
        master_user = get_master_user_from_context(self.context)
        attribute_type_qs = GenericAttributeType.objects.filter(master_user=master_user)
        # return instance.attributes.filter(attribute_type__in=attribute_type_qs)

        # Probably deprecated 2023-03-10
        # from poms.reports.builders.transaction_item import TransactionReportItem
        # from poms.transactions.models import Transaction
        # if isinstance(instance, TransactionReportItem):
        #     content_type = ContentType.objects.get_for_model(Transaction)
        # else:
        #     content_type = ContentType.objects.get_for_model(instance)

        content_type = ContentType.objects.get_for_model(instance)

        return GenericAttribute.objects.filter(
            content_type=content_type,
            object_id=instance.id,
            attribute_type__in=attribute_type_qs
        )


class GenericAttributeViewListSerializer(serializers.ListSerializer):
    def get_attribute(self, instance):
        objects = super(GenericAttributeViewListSerializer, self).get_attribute(instance)
        objects = objects.all() if isinstance(objects, models.Manager) else objects
        member = get_member_from_context(self.context)
        return objects


class GenericAttributeSerializer(serializers.ModelSerializer):
    attribute_type = GenericAttributeTypeField()
    classifier = GenericClassifierField(required=False, allow_null=True)
    attribute_type_object = GenericAttributeTypeViewSerializer(source='attribute_type', read_only=True)
    classifier_object = GenericClassifierViewSerializer(source='classifier', read_only=True)
    list_serializer_class = GenericAttributeViewListSerializer

    class Meta:
        model = GenericAttribute
        list_serializer_class = GenericAttributeListSerializer
        fields = [
            'id', 'attribute_type', 'value_string', 'value_float', 'value_date', 'classifier',
            'attribute_type_object', 'classifier_object'
        ]

    def __init__(self, *args, **kwargs):
        super(GenericAttributeSerializer, self).__init__(*args, **kwargs)
        self._attribute_type_classifiers = {}

    def validate(self, attrs):
        attrs = super(GenericAttributeSerializer, self).validate(attrs)

        parent = self.parent
        if isinstance(parent, ListSerializer):
            parent = parent.parent
        owner_model_content_type = ContentType.objects.get_for_model(parent.Meta.model)
        # root_model_content_type = ContentType.objects.get_for_model(self.root.Meta.model)

        # attribute_type = attrs['attribute_type']
        # if attribute_type.content_type_id != owner_model_content_type.id:
        #     # raise ValidationError({
        #     #     'attribute_type':
        #     # })
        #     self.fields['attribute_type'].fail('does_not_exist', pk_value=attribute_type.id)

        # classifier = attrs.get('classifier', None)
        # if attribute_type.value_type == GenericAttributeType.CLASSIFIER and classifier:
        #     if attribute_type.id != classifier.attribute_type_id:
        #         # raise ValidationError(
        #         #     {'classifier': gettext_lazy('Invalid pk "%(pk)s" - object does not exist.') % {
        #         #         'pk': classifier.id}})
        #         self.fields['classifier'].fail('does_not_exist', pk_value=classifier.id)

        return attrs

    def to_representation(self, instance):

        if instance.classifier_id:
            # classifiers must be already loaded through prefetch_related()
            if instance.attribute_type_id not in self._attribute_type_classifiers:
                l = list(instance.attribute_type.classifiers.all())
                for c in l:
                    self._attribute_type_classifiers[c.id] = c
                get_cached_trees(l)

            # print('_attribute_type_classifiers %s' % self._attribute_type_classifiers)

            if instance.classifier_id in self._attribute_type_classifiers:
                instance.classifier = self._attribute_type_classifiers[instance.classifier_id]

        return super(GenericAttributeSerializer, self).to_representation(instance)


class GenericAttributeOnlySerializer(serializers.ModelSerializer):
    attribute_type = GenericAttributeTypeField()
    classifier = GenericClassifierField(required=False, allow_null=True)
    classifier_object = GenericClassifierViewSerializer(source='classifier', read_only=True)
    list_serializer_class = GenericAttributeViewListSerializer

    class Meta:
        model = GenericAttribute
        list_serializer_class = GenericAttributeListSerializer
        fields = [
            'id', 'attribute_type', 'value_string', 'value_float', 'value_date', 'classifier', 'classifier_object'
        ]

    def __init__(self, *args, **kwargs):
        super(GenericAttributeOnlySerializer, self).__init__(*args, **kwargs)
        self._attribute_type_classifiers = {}

    def to_representation(self, instance):
        # if instance.classifier_id:
        #     # classifiers must be already loaded through prefetch_related()
        #     if instance.attribute_type_id not in self._attribute_type_classifiers:
        #         l = list(instance.attribute_type.classifiers.all())
        #         for c in l:
        #             self._attribute_type_classifiers[c.id] = c
        #         get_cached_trees(l)
        #
        #     # print('_attribute_type_classifiers %s' % self._attribute_type_classifiers)
        #
        #     instance.classifier = self._attribute_type_classifiers[instance.classifier_id]

        return super(GenericAttributeOnlySerializer, self).to_representation(instance)


class RecalculateAttributes:
    def __init__(self, task_id=None, task_status=None, master_user=None, member=None, attribute_type_id=None,
                 target_model_content_type=None, target_model=None, target_model_serializer=None,
                 total_rows=None, processed_rows=None, stats_file_report=None, stats=None):
        self.task_id = task_id
        self.task_status = task_status

        self.master_user = master_user
        self.member = member
        self.attribute_type_id = attribute_type_id
        self.target_model_content_type = target_model_content_type
        self.target_model = target_model
        self.target_model_serializer = target_model_serializer

        self.total_rows = total_rows
        self.processed_rows = processed_rows

        self.stats = stats
        self.stats_file_report = stats_file_report

    def __str__(self):
        return '%s' % (getattr(self.master_user, 'name', None))


class RecalculateAttributesSerializer(serializers.Serializer):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    master_user = MasterUserField()
    member = HiddenMemberField()
    # attribute_type_id = serializers.IntegerField(allow_null=True, required=False)

    processed_rows = serializers.ReadOnlyField()
    total_rows = serializers.ReadOnlyField()

    stats = serializers.ReadOnlyField()
    stats_file_report = serializers.ReadOnlyField()

    def create(self, validated_data):
        return RecalculateAttributes(**validated_data)
