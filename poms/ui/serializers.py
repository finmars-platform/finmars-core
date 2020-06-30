from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from mptt.utils import get_cached_trees
from rest_framework import serializers

from poms.layout_recovery.models import LayoutArchetype
from poms.layout_recovery.utils import recursive_dict_fix
from poms.ui.fields import LayoutContentTypeField, ListLayoutField
from poms.ui.models import ListLayout, EditLayout, Bookmark, Configuration, \
    ConfigurationExportLayout, TransactionUserFieldModel, InstrumentUserFieldModel, PortalInterfaceAccessModel, \
    DashboardLayout, TemplateLayout, ContextMenuLayout, EntityTooltip, ColorPaletteColor, ColorPalette
from poms.users.fields import MasterUserField, HiddenMemberField


class PortalInterfaceAccessModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalInterfaceAccessModel
        fields = [
           'id', 'value', 'system_code', 'name'
        ]


class TransactionUserFieldSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    class Meta:
        model = TransactionUserFieldModel
        fields = ['id', 'master_user', 'key', 'name']


class ColorPaletteColorSerializer(serializers.ModelSerializer):

    class Meta:
        model = ColorPaletteColor
        fields = ['id', 'order', 'name', 'value']


class ColorPaletteSerializer(serializers.ModelSerializer):

    master_user = MasterUserField()

    colors = ColorPaletteColorSerializer(many=True)

    class Meta:
        model = ColorPalette
        fields = ['id', 'master_user', 'name', 'user_code', 'short_name', 'is_default', 'colors']

    def save_colors(self, instance, colors):

        for color in colors:

            try:

                item = ColorPaletteColor.objects.get(color_palette=instance, order=color['order'])
                item.value = color['value']
                item.name = color['name']
                item.save()

            except ColorPaletteColor.DoesNotExist:

                item = ColorPaletteColor.objects.create(color_palette=instance, order=color['order'])
                item.value = color['value']
                item.name = color['name']
                item.save()

    def create(self, validated_data):

        colors = validated_data.pop('colors')

        instance = super(ColorPaletteSerializer, self).create(validated_data)

        self.save_colors(instance=instance, colors=colors)

    def update(self, instance, validated_data):

        colors = validated_data.pop('colors')

        instance = super(ColorPaletteSerializer, self).update(instance, validated_data)

        self.save_colors(instance=instance, colors=colors)


class EntityTooltipSerializer(serializers.ModelSerializer):

    master_user = MasterUserField()

    content_type = LayoutContentTypeField()

    class Meta:
        model = EntityTooltip
        fields = ['id', 'master_user', 'content_type', 'name', 'key', 'text']


class InstrumentUserFieldSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    class Meta:
        model = InstrumentUserFieldModel
        fields = ['id', 'master_user', 'key', 'name']


class TemplateLayoutSerializer(serializers.ModelSerializer):
    member = HiddenMemberField()
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = TemplateLayout
        fields = ['id', 'member', 'type', 'name', 'user_code', 'is_default', 'data']


class ContextMenuLayoutSerializer(serializers.ModelSerializer):
    member = HiddenMemberField()
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = ContextMenuLayout
        fields = ['id', 'member', 'type', 'name',  'user_code', 'data', 'origin_for_global_layout', 'sourced_from_global_layout']


class ListLayoutSerializer(serializers.ModelSerializer):
    member = HiddenMemberField()
    content_type = LayoutContentTypeField()
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = ListLayout
        fields = ['id', 'member', 'content_type', 'name', 'user_code', 'is_default', 'is_active', 'data', 'origin_for_global_layout', 'sourced_from_global_layout']

    def to_representation(self, instance):

        if instance.is_fixed:

            # print("Layout %s is already fixed" % instance.name)

            res = super(ListLayoutSerializer, self).to_representation(instance)

            return res

        else:

            try:

                layout_archetype = LayoutArchetype.objects.get(content_type=instance.content_type, master_user=instance.member.master_user)

                instance.data = recursive_dict_fix(layout_archetype.data, instance.data)

                print("Fix Layout %s" % instance.name)

            except Exception as e:

                print("Cant Fix Layout %s" % instance.name)
                print("Error %s" % e)

            res = super(ListLayoutSerializer, self).to_representation(instance)

            return res

class DashboardLayoutSerializer(serializers.ModelSerializer):
    member = HiddenMemberField()
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = DashboardLayout
        fields = ['id', 'member', 'name', 'user_code', 'is_default', 'is_active', 'data', 'origin_for_global_layout', 'sourced_from_global_layout']


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
        fields = ['id', 'member', 'content_type', 'data', 'origin_for_global_layout', 'sourced_from_global_layout']


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
