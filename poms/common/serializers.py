from django.contrib.contenttypes.models import ContentType
from django.utils.text import Truncator
from mptt.utils import get_cached_trees
from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.serializers import ListSerializer

from poms.common.fields import PrimaryKeyRelatedFilteredField, UserCodeField
from poms.common.filters import ClassifierRootFilter
from poms.users.filters import OwnerByMasterUserFilter


class PomsClassSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['id', 'system_code', 'name', 'description', ]


class ModelWithTimeStampSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        super(ModelWithTimeStampSerializer, self).__init__(*args, **kwargs)
        self.fields['modified'] = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, data):

        if self.instance:
            if data['modified'] != self.instance.modified:
                raise serializers.ValidationError("Synchronization error")

        return data



class ModelWithUserCodeSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super(ModelWithUserCodeSerializer, self).__init__(*args, **kwargs)
        self.fields['user_code'] = UserCodeField()

    def to_internal_value(self, data):
        ret = super(ModelWithUserCodeSerializer, self).to_internal_value(data)

        # for correct message on unique error
        user_code = ret.get('user_code', empty)
        if user_code is empty or user_code is None:
            name = ret.get('name', empty)
            if name is not empty and name is not None:
                ret['user_code'] = Truncator(name).chars(25, truncate='')

        return ret


class AbstractClassifierField(PrimaryKeyRelatedFilteredField):
    filter_backends = [
        OwnerByMasterUserFilter
    ]


class AbstractClassifierRootField(PrimaryKeyRelatedFilteredField):
    filter_backends = [
        OwnerByMasterUserFilter,
        ClassifierRootFilter
    ]


class ClassifierRecursiveField(serializers.Serializer):
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


class ClassifierListSerializer(serializers.ListSerializer):
    def get_attribute(self, instance):
        tree = get_cached_trees(instance.classifiers.all())
        return tree


class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ['name', ]
        read_only_fields = fields

# class AbstractClassifierSerializer(serializers.ModelSerializer):
#     id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
#     children = ClassifierRecursiveField(source='get_children', many=True, required=False, allow_null=True)
#
#     class Meta:
#         list_serializer_class = ClassifierListSerializer
#         fields = ['id', 'name', 'level', 'children', ]
#
#     def __init__(self, *args, **kwargs):
#         show_children = kwargs.pop('show_children', True)
#         super(AbstractClassifierSerializer, self).__init__(*args, **kwargs)
#         if not show_children:
#             self.fields.pop('children')
#
#     def create(self, validated_data):
#         validated_data.pop('id', None)
#         children = validated_data.pop('get_children', validated_data.get('children', []))
#         instance = super(AbstractClassifierSerializer, self).create(validated_data)
#         self.save_tree(instance, children)
#         return instance
#
#     def update(self, instance, validated_data):
#         validated_data.pop('id', None)
#         children = validated_data.pop('get_children', validated_data.get('children', empty))
#         instance = super(AbstractClassifierSerializer, self).update(instance, validated_data)
#         if children is not empty:
#             self.save_tree(instance, children)
#         return instance
#
#     def save_tree(self, node, children):
#         children = children or []
#
#         context = {}
#         context.update(self.context)
#         if node.is_root_node():
#             processed = context['processed'] = set()
#             processed.add(node.pk)
#             root = context['root_node'] = node
#         else:
#             processed = self.context['processed']
#             root = self.context['root_node']
#
#         for child_data in children:
#             child_pk = child_data.pop('id', None)
#
#             if child_pk in processed:
#                 raise ValidationError('Tree node with id %s already processed' % child_pk)
#
#             if child_pk:
#                 child_obj = root.get_family().get(pk=child_pk)
#                 if child_obj.parent_id != node.id:
#                     child_obj.parent = node
#             else:
#                 child_obj = None
#
#             node_s = self.__class__(instance=child_obj, data=child_data, context=context)
#             node_s.is_valid(raise_exception=True)
#             child_obj = node_s.save(parent=node)
#             processed.add(child_obj.pk)
#
#         if node.is_root_node():
#             node.get_family().exclude(pk__in=processed).delete()
#
#
# class AbstractClassifierNodeSerializer(serializers.ModelSerializer):
#     attribute_type = serializers.PrimaryKeyRelatedField(read_only=True)
#     parent = serializers.PrimaryKeyRelatedField(read_only=True)
#
#     class Meta:
#         fields = ['id', 'attribute_type', 'name', 'parent', 'level', 'tree_id', ]
