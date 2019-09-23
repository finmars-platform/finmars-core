from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import ugettext_lazy
from rest_framework import serializers
from rest_framework.fields import empty

from poms.common.serializers import ModelWithUserCodeSerializer
from poms.obj_perms.serializers import ModelWithObjectPermissionSerializer
from poms.obj_perms.utils import obj_perms_filter_objects_for_view, has_view_perms, get_permissions_prefetch_lookups
from poms.tags.fields import TagContentTypeField
from poms.tags.models import Tag, TagLink
from poms.users.fields import MasterUserField
from poms.users.utils import get_member_from_context, get_master_user_from_context


class TagSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer):
    master_user = MasterUserField()
    content_types = TagContentTypeField(many=True)

    # account_types = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # accounts = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # currencies = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # instrument_types = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # instruments = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # counterparties = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # responsibles = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # strategy_groups = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # strategy_subgroups = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # strategies = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # portfolios = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # transaction_types = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Tag
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name', 'notes', 'content_types',
            # 'account_types', 'accounts', 'currencies', 'instrument_types', 'instruments',
            # 'counterparties', 'responsibles',
            # 'strategy_groups', 'strategy_subgroups', 'strategies',
            # 'portfolios', 'transaction_types'
        ]


# class TagBulkObjectPermissionSerializer(AbstractBulkObjectPermissionSerializer):
#     content_objects = TagField(many=True, allow_null=False, allow_empty=False)
#
#     class Meta:
#         model = Tag


# class TagViewSerializer(ModelWithObjectPermissionSerializer):
#     class Meta:
#         model = Tag
#         fields = [
#             'id', 'user_code', 'name', 'short_name', 'public_name', 'notes',
#         ]


class TagField(serializers.RelatedField):
    default_error_messages = {
        'required': ugettext_lazy('This field is required.'),
        'does_not_exist': ugettext_lazy('Invalid pk "{pk_value}" - object does not exist.'),
        'incorrect_type': ugettext_lazy('Incorrect type. Expected pk value, received {data_type}.'),
    }

    def get_queryset(self):
        queryset = super(TagField, self).get_queryset()

        if not issubclass(self.root.Meta.model, Tag):
            ctype = ContentType.objects.get_for_model(self.root.Meta.model)
            queryset = queryset.filter(content_types__in=[ctype])

        master_user = get_master_user_from_context(self.context)
        queryset = queryset.filter(master_user=master_user)

        member = get_member_from_context(self.context)
        queryset = obj_perms_filter_objects_for_view(member, queryset)
        return queryset

    # def to_representation(self, value):
    #     if isinstance(value, Tag):
    #         tag = value
    #     else:
    #         tag = value.tag
    #     member = get_member_from_context(self.context)
    #     if has_view_perms(member, tag):
    #         return tag.id
    #     else:
    #         return None

    def to_internal_value(self, data):
        try:
            return self.get_queryset().get(pk=data)
        except ObjectDoesNotExist:
            self.fail('does_not_exist', pk_value=data)
        except (TypeError, ValueError):
            self.fail('incorrect_type', data_type=type(data).__name__)


class TagViewListSerializer(serializers.ListSerializer):
    def get_attribute(self, instance):
        objects = super(TagViewListSerializer, self).get_attribute(instance)
        objects = objects.all() if isinstance(objects, models.Manager) else objects
        member = get_member_from_context(self.context)
        return [
            o for o in objects if has_view_perms(member, o.tag)
            ]


class TagViewSerializer(ModelWithObjectPermissionSerializer):
    class Meta(ModelWithObjectPermissionSerializer.Meta):
        list_serializer_class = TagViewListSerializer
        model = Tag
        fields = [
            'id', 'user_code', 'name', 'short_name', 'public_name', 'notes',
        ]

    def to_representation(self, instance):
        return super(TagViewSerializer, self).to_representation(instance.tag)


class ModelWithTagSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super(ModelWithTagSerializer, self).__init__(*args, **kwargs)

        self.fields['tags'] = TagField(many=True, queryset=Tag.objects.all(), required=False, allow_null=True, allow_empty=True)
        self.fields['tags_object'] = TagViewSerializer(source='tags', many=True, read_only=True)

    def create(self, validated_data):
        tags = validated_data.pop('tags', empty)
        instance = super(ModelWithTagSerializer, self).create(validated_data)
        if tags is not empty:
            self.save_tags(instance, tags, True)
        return instance

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', empty)
        instance = super(ModelWithTagSerializer, self).update(instance, validated_data)
        if tags is not empty:
            self.save_tags(instance, tags, False)
        return instance

    def save_tags(self, instance, tags=None, created=False):
        tags = tags or []

        tag_link_qs = TagLink.objects.filter(
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.id
        )
        existed = {t.tag_id for t in tag_link_qs}
        processed = set()
        for t in tags:
            if t.id in existed:
                processed.add(t.id)
            else:
                TagLink.objects.create(content_object=instance, tag=t)
                processed.add(t.id)

        master_user = get_master_user_from_context(self.context)
        member = get_member_from_context(self.context)
        tags_qs = Tag.objects.filter(master_user=master_user).prefetch_related(
            *get_permissions_prefetch_lookups((None, Tag))
        )
        hidden = {t.id for t in tags_qs if not has_view_perms(member, t)}
        processed.update(hidden)

        tag_link_qs.filter(tag_id__in=tags_qs).exclude(tag_id__in=processed).delete()

    # def to_representation(self, instance):
    #     ret = super(ModelWithTagSerializer, self).to_representation(instance)
    #     tags = ret.get('tags')
    #     if tags:
    #         ret['tags'] = [t for t in tags if t is not None]
    #     return ret
