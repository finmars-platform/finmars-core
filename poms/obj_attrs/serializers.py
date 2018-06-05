from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.utils.translation import ugettext_lazy
from mptt.utils import get_cached_trees
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.serializers import ListSerializer

from poms.common.serializers import ModelWithUserCodeSerializer
from poms.integrations.models import PortfolioClassifierMapping, ProviderClass, AccountClassifierMapping, \
    CounterpartyClassifierMapping, ResponsibleClassifierMapping
from poms.obj_attrs.fields import GenericAttributeTypeField, GenericClassifierField
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier, GenericAttribute
from poms.obj_perms.serializers import ModelWithObjectPermissionSerializer
from poms.obj_perms.utils import has_view_perms, get_permissions_prefetch_lookups, obj_perms_filter_objects_for_view
from poms.users.fields import MasterUserField
from poms.users.utils import get_member_from_context, get_master_user_from_context


# class AttributeTypeOptionIsHiddenField(serializers.BooleanField):
#     def __init__(self, **kwargs):
#         kwargs['required'] = False
#         kwargs['default'] = False
#         # kwargs['allow_null'] = True
#         super(AttributeTypeOptionIsHiddenField, self).__init__(**kwargs)
#
#     def get_attribute(self, obj):
#         return obj
#
#     def to_representation(self, value):
#         # some "optimization" to use preloaded data through prefetch_related
#         member = get_member_from_context(self.context)
#         for o in value.options.all():
#             if o.member_id == member.id:
#                 return o.is_hidden
#         return False
#
#
# class AbstractAttributeTypeSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer):
#     master_user = MasterUserField()
#     is_hidden = AttributeTypeOptionIsHiddenField()
#
#     class Meta:
#         fields = ['url', 'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name', 'notes', 'value_type',
#                   'order', 'is_hidden']
#
#     def __init__(self, *args, **kwargs):
#         show_classifiers = kwargs.pop('show_classifiers', False)
#         read_only_value_type = kwargs.pop('read_only_value_type', False)
#         super(AbstractAttributeTypeSerializer, self).__init__(*args, **kwargs)
#         if not show_classifiers:
#             self.fields.pop('classifiers', None)
#         if read_only_value_type:
#             self.fields['value_type'].read_only = True
#
#     def validate(self, attrs):
#         attrs = super(AbstractAttributeTypeSerializer, self).validate(attrs)
#         classifiers = attrs.get('classifiers', None)
#         if classifiers:
#             self._validate_classifiers(classifiers, id_set=set(), user_code_set=set())
#         return attrs
#
#     def _validate_classifiers(self, classifiers, id_set, user_code_set):
#         for c in classifiers:
#             c_id = c.get('id', None)
#             c_user_code = c.get('user_code', None)
#             if c_id and c_id in id_set:
#                 raise ValidationError("non unique id")
#             if c_user_code and c_user_code in user_code_set:
#                 raise ValidationError("non unique user_code")
#             if c_id:
#                 id_set.add(c_id)
#             if c_user_code:
#                 user_code_set.add(c_user_code)
#             children = c.get('get_children', c.pop('children', []))
#             self._validate_classifiers(children, id_set, user_code_set)
#
#     def create(self, validated_data):
#         member = get_member_from_context(self.context)
#         is_hidden = validated_data.pop('is_hidden', False)
#         classifiers = validated_data.pop('classifiers', None)
#         instance = super(AbstractAttributeTypeSerializer, self).create(validated_data)
#         instance.options.create(member=member, is_hidden=is_hidden)
#         self.save_classifiers(instance, classifiers)
#         return instance
#
#     def update(self, instance, validated_data):
#         member = get_member_from_context(self.context)
#         is_hidden = validated_data.pop('is_hidden', empty)
#         classifiers = validated_data.pop('classifiers', empty)
#         instance = super(AbstractAttributeTypeSerializer, self).update(instance, validated_data)
#         if is_hidden is not empty:
#             instance.options.update_or_create(member=member, defaults={'is_hidden': is_hidden})
#         if classifiers is not empty:
#             self.save_classifiers(instance, classifiers)
#         return instance
#
#     def save_classifiers(self, instance, classifier_tree):
#         if instance.value_type != AbstractAttributeType.CLASSIFIER:
#             return
#         classifier_tree = classifier_tree or []
#         # if classifier_tree is None:
#         #     return
#         if len(classifier_tree) == 0:
#             instance.classifiers.all().delete()
#             return
#
#         classifier_model = instance._meta.get_field('classifiers').related_model
#
#         processed = set()
#         for node in classifier_tree:
#             self.save_classifier(instance, node, None, processed, classifier_model)
#
#         instance.classifiers.exclude(pk__in=processed).delete()
#
#     def save_classifier(self, instance, node, parent, processed, classifier_model):
#         if 'id' in node:
#             try:
#                 o = instance.classifiers.get(pk=node.pop('id'))
#             except ObjectDoesNotExist:
#                 o = classifier_model()
#         else:
#             o = classifier_model()
#         o.parent = parent
#         o.attribute_type = instance
#         children = node.pop('get_children', node.pop('children', []))
#         for k, v in node.items():
#             setattr(o, k, v)
#         try:
#             o.save()
#         except IntegrityError:
#             raise ValidationError("non unique user_code")
#         processed.add(o.id)
#
#         for c in children:
#             self.save_classifier(instance, c, o, processed, classifier_model)
#
#
# class AttributeListSerializer(serializers.ListSerializer):
#     # Used as list_serializer_class if many=True in AbstractAttributeSerializer
#     def get_attribute(self, instance):
#         member = get_member_from_context(self.context)
#         if member.is_superuser:
#             return instance.attributes
#         master_user = get_master_user_from_context(self.context)
#         attribute_type_model = getattr(self.child.Meta, 'attribute_type_model', None) or get_attr_type_model(instance)
#         attribute_types = attribute_type_model.objects.filter(master_user=master_user)
#         attribute_types = obj_perms_filter_objects(member, get_attr_type_view_perms(attribute_type_model),
#                                                    attribute_types)
#         return instance.attributes.filter(attribute_type__in=attribute_types)
#
#
# class AttributeTypeViewSerializer(serializers.Serializer):
#     id = serializers.IntegerField(read_only=True)
#     value_type = serializers.PrimaryKeyRelatedField(read_only=True)
#     user_code = serializers.CharField(read_only=True)
#     name = serializers.CharField(read_only=True)
#     short_name = serializers.CharField(read_only=True)
#     order = serializers.CharField(read_only=True)
#     is_hidden = serializers.BooleanField(read_only=True)
#
#
# class ClassifierViewSerializer(serializers.Serializer):
#     id = serializers.IntegerField(read_only=True)
#     name = serializers.CharField(read_only=True)
#     level = serializers.IntegerField(read_only=True)
#
#
# class AbstractAttributeSerializer(serializers.ModelSerializer):
#     attribute_type_object = AttributeTypeViewSerializer(source='attribute_type', read_only=True)
#     classifier_object = ClassifierViewSerializer(source='classifier', read_only=True)
#
#     class Meta:
#         list_serializer_class = AttributeListSerializer
#         fields = ['value_string', 'value_float', 'value_date', 'attribute_type_object', 'classifier_object']
#
#     def __init__(self, *args, **kwargs):
#         super(AbstractAttributeSerializer, self).__init__(*args, **kwargs)
#         # if self.instance:
#         #     value_type = self.instance.attribute_type.value_type
#         #     value_fields = ['value_string', 'value_float', 'value_date', 'classifier']
#         #     if value_type == AbstractAttributeType.STRING:
#         #         value_fields.remove('value_string')
#         #     elif value_type == AbstractAttributeType.NUMBER:
#         #         value_fields.remove('value_float')
#         #     elif value_type == AbstractAttributeType.CLASSIFIER:
#         #         value_fields.remove('classifier')
#         #     elif value_type == AbstractAttributeType.DATE:
#         #         value_fields.remove('value_date')
#         #     for f in value_fields:
#         #         self.fields.pop(f, None)
#
#     def validate(self, attrs):
#         attribute_type = attrs['attribute_type']
#         if attribute_type.value_type == AbstractAttributeType.CLASSIFIER:
#             classifier = attrs.get('classifier', None)
#             if classifier:
#                 if classifier.attribute_type_id != attribute_type.id:
#                     raise ValidationError(
#                         {'classifier': ugettext_lazy('Invalid pk "%(pk)s" - object does not exist.') % {
#                             'pk': classifier.id}})
#                     # else:
#                     #     raise ValidationError({'classifier': ugettext_lazy('This field may not be null.')})
#         return attrs


class ModelWithAttributesSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super(ModelWithAttributesSerializer, self).__init__(*args, **kwargs)
        self.fields['attributes'] = GenericAttributeSerializer(many=True, required=False, allow_null=True)

    def create(self, validated_data):
        attributes = validated_data.pop('attributes', None)
        # attributes2 = validated_data.pop('attributes2', None)
        instance = super(ModelWithAttributesSerializer, self).create(validated_data)
        self.save_attributes(instance, attributes, True)
        # self.save_attributes2(instance, attributes2, True)
        return instance

    def update(self, instance, validated_data):
        attributes = validated_data.pop('attributes', empty)
        # attributes2 = validated_data.pop('attributes2', empty)
        instance = super(ModelWithAttributesSerializer, self).update(instance, validated_data)
        if attributes is not empty:
            self.save_attributes(instance, attributes, False)
        # if attributes2 is not empty:
        #     self.save_attributes2(instance, attributes2, False)
        return instance

    # def save_attributes(self, instance, attributes, created):
    #     if attributes is None:
    #         return
    #
    #     member = get_member_from_context(self.context)
    #     cur_attrs = {a.attribute_type_id: a
    #                  for a in instance.attributes.select_related('attribute_type').all()}
    #     processed = set()
    #
    #     for attr in attributes:
    #         attr_type = attr['attribute_type']
    #         if has_view_perms(member, attr_type):
    #             if attr_type.id in processed:
    #                 raise ValidationError("Duplicated attribute type %s" % attr_type.id)
    #             processed.add(attr_type.id)
    #
    #             if attr_type.id in cur_attrs:
    #                 cur_attr = cur_attrs[attr_type.id]
    #                 # verify value_ and classifier -> DONE in AttributeSerializerBase
    #                 for k, v in attr.items():
    #                     if k not in ['id', 'attribute_type']:
    #                         setattr(cur_attr, k, v)
    #                 cur_attr.save()
    #             else:
    #                 # verify value_ and classifier -> DONE in AttributeSerializerBase
    #                 instance.attributes.create(**attr)
    #         else:
    #             # perms error...
    #             pass
    #
    #     for attr in cur_attrs.values():
    #         # add attrs that not visible for current member
    #         attr_type = attr.attribute_type
    #         if not has_view_perms(member, attr_type):
    #             processed.add(attr_type.id)
    #
    #     instance.attributes.exclude(attribute_type_id__in=processed).delete()

    def save_attributes(self, instance, attributes, created):
        member = get_member_from_context(self.context)
        attributes = attributes or []

        ctype = ContentType.objects.get_for_model(instance)
        # if hasattr(instance, 'attributes'):
        #     attrs_qs = instance.attributes.all()
        # else:
        attrs_qs = GenericAttribute.objects.filter(content_type=ctype, object_id=instance.id)

        read_attrs_qs = attrs_qs.select_related('attribute_type').prefetch_related(
            *get_permissions_prefetch_lookups(
                ('attribute_type', GenericAttributeType),
            )
        )
        protected = {a.attribute_type_id for a in read_attrs_qs if not has_view_perms(member, instance)}
        existed = {a.attribute_type_id: a for a in read_attrs_qs if has_view_perms(member, instance)}

        processed = set()
        for attr in attributes:
            attribute_type = attr['attribute_type']

            if attribute_type.content_type_id != ctype.id:
                raise ValidationError(
                    {'attribute_type': ugettext_lazy('Invalid pk "%(pk)s" - object does not exist.') % {
                        'pk': attribute_type.id}})

            if has_view_perms(member, attribute_type):
                if attribute_type.id in processed:
                    raise ValidationError("Duplicated attribute type %s" % attribute_type.id)
                processed.add(attribute_type.id)

                try:
                    oattr = existed[attribute_type.id]
                except KeyError:
                    oattr = GenericAttribute(**attr)
                    oattr.content_object = instance
                    oattr.attribute_type = attribute_type
                if 'value_string' in attr:
                    oattr.value_string = attr['value_string']
                if 'value_float' in attr:
                    oattr.value_float = attr['value_float']
                if 'value_date' in attr:
                    oattr.value_date = attr['value_date']
                if 'classifier' in attr:
                    oattr.classifier = attr['classifier']
                oattr.save()
            else:
                # perms error...
                pass

        processed.update(protected)
        attrs_qs.exclude(attribute_type_id__in=processed).delete()


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
        print('Create classifier node')

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


class GenericAttributeTypeSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer):
    master_user = MasterUserField()
    is_hidden = GenericAttributeTypeOptionIsHiddenField()
    classifiers = GenericClassifierSerializer(required=False, allow_null=True, many=True)
    classifiers_flat = GenericClassifierWithoutChildrenSerializer(source='classifiers', read_only=True, many=True)

    class Meta:
        model = GenericAttributeType
        fields = ['id', 'master_user', 'user_code', 'name', 'short_name', 'public_name', 'notes',
                  'value_type', 'order', 'is_hidden', 'classifiers', 'classifiers_flat']

    def __init__(self, *args, **kwargs):
        show_classifiers = kwargs.pop('show_classifiers', False)
        read_only_value_type = kwargs.pop('read_only_value_type', False)
        super(GenericAttributeTypeSerializer, self).__init__(*args, **kwargs)
        if not show_classifiers:
            self.fields.pop('classifiers', None)
            self.fields.pop('classifiers_flat', None)
        if read_only_value_type:
            self.fields['value_type'].read_only = True

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
                raise ValidationError("non unique id")
            if c_user_code and c_user_code in user_code_set:
                raise ValidationError("non unique user_code")
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
        for node in classifier_tree:
            self.save_classifier(instance, node, None, processed)

        instance.classifiers.exclude(pk__in=processed).delete()

    def save_classifier(self, instance, node, parent, processed):

        print('Save classifier instance content_type %s' % instance.content_type)
        print('Save classifier instance value_type %s' % instance.value_type)
        print('Save classifier node %s' % node)

        is_new_node = False

        if 'id' in node:
            try:
                o = instance.classifiers.get(pk=node.pop('id'))
            except ObjectDoesNotExist:
                o = GenericClassifier()
                is_new_node = True
        else:
            o = GenericClassifier()
            is_new_node = True

        print('o %s', o)


        try:

            self.delete_matched_classifier_node_mapping(instance, o)

            o.parent = parent
            o.attribute_type = instance
            children = node.pop('get_children', node.pop('children', []))
            for k, v in node.items():
                setattr(o, k, v)

            o.save()

            self.create_classifier_node_mapping(instance, o)

        except IntegrityError:
            raise ValidationError("non unique user_code")
        processed.add(o.id)

        for c in children:
            self.save_classifier(instance, c, o, processed)

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

    def delete_matched_classifier_node_mapping(self, instance, node):

        print('delete node %s' %node )

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



class GenericAttributeTypeViewSerializer(ModelWithObjectPermissionSerializer):
    is_hidden = GenericAttributeTypeOptionIsHiddenField()

    class Meta:
        model = GenericAttributeType
        fields = ['id', 'user_code', 'name', 'short_name', 'public_name', 'notes',
                  'value_type', 'order', 'is_hidden']


class GenericAttributeListSerializer(serializers.ListSerializer):
    # Used as list_serializer_class if many=True in AbstractAttributeSerializer
    def get_attribute(self, instance):
        member = get_member_from_context(self.context)
        if member.is_superuser:
            return instance.attributes
        master_user = get_master_user_from_context(self.context)
        attribute_type_qs = GenericAttributeType.objects.filter(master_user=master_user)
        attribute_type_qs = obj_perms_filter_objects_for_view(member, attribute_type_qs)
        # return instance.attributes.filter(attribute_type__in=attribute_type_qs)

        from poms.reports.builders.transaction_item import TransactionReportItem
        from poms.transactions.models import Transaction
        if isinstance(instance, TransactionReportItem):
            content_type = ContentType.objects.get_for_model(Transaction)
        else:
            content_type = ContentType.objects.get_for_model(instance)

        return GenericAttribute.objects.filter(
            content_type=content_type,
            object_id=instance.id,
            attribute_type__in=attribute_type_qs
        )


class GenericAttributeSerializer(serializers.ModelSerializer):
    attribute_type = GenericAttributeTypeField()
    classifier = GenericClassifierField(required=False, allow_null=True)
    attribute_type_object = GenericAttributeTypeViewSerializer(source='attribute_type', read_only=True)
    classifier_object = GenericClassifierViewSerializer(source='classifier', read_only=True)

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

        attribute_type = attrs['attribute_type']
        if attribute_type.content_type_id != owner_model_content_type.id:
            # raise ValidationError({
            #     'attribute_type':
            # })
            self.fields['attribute_type'].fail('does_not_exist', pk_value=attribute_type.id)

        classifier = attrs.get('classifier', None)
        if attribute_type.value_type == GenericAttributeType.CLASSIFIER and classifier:
            if attribute_type.id != classifier.attribute_type_id:
                # raise ValidationError(
                #     {'classifier': ugettext_lazy('Invalid pk "%(pk)s" - object does not exist.') % {
                #         'pk': classifier.id}})
                self.fields['classifier'].fail('does_not_exist', pk_value=classifier.id)

        return attrs

    def to_representation(self, instance):

        if instance.classifier_id:
            # classifiers must be already loaded through prefetch_related()
            if instance.attribute_type_id not in self._attribute_type_classifiers:
                l = list(instance.attribute_type.classifiers.all())
                for c in l:
                    self._attribute_type_classifiers[c.id] = c
                get_cached_trees(l)
            instance.classifier = self._attribute_type_classifiers[instance.classifier_id]

        return super(GenericAttributeSerializer, self).to_representation(instance)
