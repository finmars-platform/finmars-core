from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from mptt.utils import get_cached_trees
from rest_framework import serializers

from poms.ui.fields import LayoutContentTypeField, ListLayoutField
from poms.ui.models import TemplateListLayout, TemplateEditLayout, ListLayout, EditLayout, Bookmark, Configuration, \
    ConfigurationExportLayout, TransactionUserFieldModel, InstrumentUserFieldModel
from poms.users.fields import MasterUserField, HiddenMemberField


class TransactionUserFieldSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    class Meta:
        model = TransactionUserFieldModel
        fields = ['id', 'master_user', 'key', 'name']


class InstrumentUserFieldSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    class Meta:
        model = InstrumentUserFieldModel
        fields = ['id', 'master_user', 'key', 'name']


class TemplateListLayoutSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    content_type = LayoutContentTypeField()
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = TemplateListLayout
        fields = ['id', 'master_user', 'content_type', 'name', 'is_default', 'data']


class TemplateEditLayoutSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    content_type = LayoutContentTypeField()
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = TemplateEditLayout
        fields = ['id', 'master_user', 'content_type', 'data']


class ListLayoutSerializer(serializers.ModelSerializer):
    member = HiddenMemberField()
    content_type = LayoutContentTypeField()
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = ListLayout
        fields = ['id', 'member', 'content_type', 'name', 'is_default', 'data']


class ConfigurationExportLayoutSerializer(serializers.ModelSerializer):
    member = HiddenMemberField()
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = ConfigurationExportLayout
        fields = ['id', 'member', 'name', 'is_default', 'data']


class EditLayoutSerializer(serializers.ModelSerializer):
    member = HiddenMemberField()
    content_type = LayoutContentTypeField()
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = EditLayout
        fields = ['id', 'member', 'content_type', 'data']


class BookmarkRecursiveField(serializers.Serializer):
    def to_representation(self, instance):
        if isinstance(self.parent, serializers.ListSerializer):
            cls = self.parent.parent.__class__
        else:
            cls = self.parent.__class__
        return cls(instance=instance, context=self.context).data

    def to_internal_value(self, data):
        if isinstance(self.parent, serializers.ListSerializer):
            cls = self.parent.parent.__class__
        else:
            cls = self.parent.__class__
        s = cls(context=self.context, data=data)
        s.is_valid(raise_exception=True)
        return s.validated_data


class BookmarkListSerializer(serializers.ListSerializer):
    def get_attribute(self, instance):
        tree = get_cached_trees(instance.children.all())
        return tree


class BookmarkSerializer(serializers.ModelSerializer):
    member = HiddenMemberField()
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    name = serializers.CharField(allow_null=False, allow_blank=False)
    uri = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    list_layout = ListLayoutField(required=False, allow_null=True)
    data = serializers.JSONField(required=False, allow_null=True)

    children = BookmarkRecursiveField(source='get_children', many=True, required=False, allow_null=True)

    class Meta:
        list_serializer_class = BookmarkListSerializer
        model = Bookmark
        fields = ['id', 'member', 'name', 'uri', 'list_layout', 'data', 'children']

    def create(self, validated_data):
        children = validated_data.pop('get_children', validated_data.pop('children', serializers.empty))
        instance = super(BookmarkSerializer, self).create(validated_data)
        if children is not serializers.empty:
            self.save_children(instance, children)
        return instance

    def update(self, instance, validated_data):
        children = validated_data.pop('get_children', validated_data.pop('children', serializers.empty))
        instance = super(BookmarkSerializer, self).update(instance, validated_data)
        if children is not serializers.empty:
            self.save_children(instance, children)
        return instance

    def save_children(self, instance, children_tree):
        children_tree = children_tree or []

        if len(children_tree) == 0:
            instance.children.all().delete()
            return

        processed = set()
        for node in children_tree:
            self.save_child(instance, node, instance, processed)

        instance.children.exclude(pk__in=processed).delete()

    def save_child(self, instance, node, parent, processed):
        if 'id' in node:
            try:
                o = Bookmark.objects.get(member=instance.member, tree_id=parent.tree_id, pk=node.pop('id'))
            except ObjectDoesNotExist:
                o = Bookmark()
        else:
            o = Bookmark()
        o.parent = parent
        o.member = instance.member
        children = node.pop('get_children', node.pop('children', []))
        for k, v in node.items():
            setattr(o, k, v)
        try:
            o.save()
        except IntegrityError as e:
            raise ValidationError(str(e))

        processed.add(o.id)

        for c in children:
            self.save_child(instance, c, o, processed)


class ConfigurationSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = Configuration
        fields = ['id', 'master_user', 'name', 'description', 'data']
