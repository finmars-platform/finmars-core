from __future__ import unicode_literals

from django.db import models
from rest_framework import serializers
from rest_framework.fields import empty

from poms.obj_perms.fields import PermissionField, GrantedPermissionField
from poms.obj_perms.models import GenericObjectPermission
from poms.obj_perms.utils import has_view_perms, get_all_perms, has_manage_perm, assign_perms3
from poms.users.fields import MemberField, GroupField
from poms.users.utils import get_member_from_context


class UserObjectPermissionListSerializer(serializers.ListSerializer):
    def get_attribute(self, instance):
        if hasattr(instance, 'object_permissions'):
            return [op for op in instance.object_permissions.all() if op.member_id]
        return []


class UserObjectPermissionSerializer(serializers.Serializer):
    member = MemberField()
    permission = PermissionField()

    class Meta:
        list_serializer_class = UserObjectPermissionListSerializer
        fields = ['id', 'member', 'permission']


class GroupObjectPermissionListSerializer(serializers.ListSerializer):
    def get_attribute(self, instance):
        if hasattr(instance, 'object_permissions'):
            return [op for op in instance.object_permissions.all() if op.group_id]
        return []


class GroupObjectPermissionSerializer(serializers.Serializer):
    group = GroupField()
    permission = PermissionField()

    class Meta:
        list_serializer_class = GroupObjectPermissionListSerializer
        fields = ['id', 'member', 'permission']


# class BulkObjectPermission(object):
#     def __init__(self, content_objects=None, user_object_permissions=None, group_object_permissions=None, success=None):
#         self.content_objects = content_objects or []
#         self.user_object_permissions = user_object_permissions or []
#         self.group_object_permissions = group_object_permissions or []
#         self.success = success or {}
#
#
# class AbstractBulkObjectPermissionSerializer(serializers.Serializer):
#     user_object_permissions = UserObjectPermissionSerializer(many=True, required=False, allow_null=True)
#     group_object_permissions = GroupObjectPermissionSerializer(many=True, required=False, allow_null=True)
#     success = serializers.ReadOnlyField()
#
#     def create(self, validated_data):
#         ret = BulkObjectPermission(**validated_data)
#
#         member = self.context['request'].user.member
#         for content_object in ret.content_objects:
#             if has_manage_perm(member, content_object):
#                 ret.success[content_object.id] = True
#                 assign_perms2(content_object, user_perms=ret.user_object_permissions,
#                               group_perms=ret.group_object_permissions)
#             else:
#                 ret.success[content_object.id] = False
#
#         return ret
#
#     def update(self, instance, validated_data):
#         raise PermissionDenied()


class ModelWithObjectPermissionViewListSerializer(serializers.ListSerializer):
    def get_attribute(self, instance):
        objects = super(ModelWithObjectPermissionViewListSerializer, self).get_attribute(instance)
        objects = objects.all() if isinstance(objects, models.Manager) else objects
        member = get_member_from_context(self.context)
        return [o for o in objects if has_view_perms(member, o)]
        # member = get_member_from_context(self.context)
        # if member.is_superuser:
        #     return instance.attributes
        # master_user = get_master_user_from_context(self.context)
        # attribute_type_model = getattr(self.child.Meta, 'attribute_type_model', None) or get_attr_type_model(instance)
        # attribute_types = attribute_type_model.objects.filter(master_user=master_user)
        # attribute_types = obj_perms_filter_objects(member, get_attr_type_view_perms(attribute_type_model), attribute_types)
        # return instance.attributes.filter(attribute_type__in=attribute_types)


class ModelWithObjectPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        list_serializer_class = ModelWithObjectPermissionViewListSerializer

    def __init__(self, *args, **kwargs):
        super(ModelWithObjectPermissionSerializer, self).__init__(*args, **kwargs)

        self.fields['display_name'] = serializers.SerializerMethodField()

        self.fields['granted_permissions'] = GrantedPermissionField()
        self.fields['user_object_permissions'] = UserObjectPermissionSerializer(many=True, required=False,
                                                                                allow_null=True)
        self.fields['group_object_permissions'] = GroupObjectPermissionSerializer(many=True, required=False,
                                                                                  allow_null=True)
        self.fields['object_permissions'] = GenericObjectPermissionSerializer(many=True, required=False,
                                                                              allow_null=True)

    def get_display_name(self, instance):
        member = get_member_from_context(self.context)
        if has_view_perms(member, instance):
            return getattr(instance, 'name', '') or ''
        else:
            return getattr(instance, 'public_name', '') or ''

    # def to_representation(self, instance):
    #     member = self.context['request'].user.member
    #     if not has_view_perms(member, instance):
    #         ret = OrderedDict()
    #         fields = self._readable_fields
    #         for field in fields:
    #             if field.field_name not in ['url', 'id', 'public_name', 'granted_permissions']:
    #                 continue
    #             try:
    #                 attribute = field.get_attribute(instance)
    #             except SkipField:
    #                 continue
    #             if attribute is None:
    #                 ret[field.field_name] = None
    #             else:
    #                 ret[field.field_name] = field.to_representation(attribute)
    #         return ret
    #     return super(ModelWithObjectPermissionSerializer, self).to_representation(instance)
    def to_representation(self, instance):
        ret = super(ModelWithObjectPermissionSerializer, self).to_representation(instance)
        member = get_member_from_context(self.context)
        if not has_view_perms(member, instance):
            for k in list(ret.keys()):
                if k not in ['id', 'public_name', 'display_name', 'granted_permissions']:
                    ret.pop(k)

        if self.context.get('show_object_permissions', True):
            if not has_manage_perm(member, instance):
                # for k in list(ret.keys()):
                #     if k in ['object_permissions', 'user_object_permissions', 'group_object_permissions']:
                #         ret.pop(k)
                ret.pop('object_permissions', None)
                ret.pop('user_object_permissions', None)
                ret.pop('group_object_permissions', None)

        else:
            ret.pop('granted_permissions', None)
            ret.pop('object_permissions', None)
            ret.pop('user_object_permissions', None)
            ret.pop('group_object_permissions', None)
        return ret

    def create(self, validated_data):
        user_object_permissions = validated_data.pop('user_object_permissions', None)
        group_object_permissions = validated_data.pop('group_object_permissions', None)
        object_permissions = validated_data.pop('object_permissions', None)
        instance = super(ModelWithObjectPermissionSerializer, self).create(validated_data)
        # self.save_user_object_permissions(instance, user_object_permissions, True)
        # self.save_group_object_permissions(instance, group_object_permissions, True)
        object_permissions = self._merge_permissions(instance, object_permissions, user_object_permissions,
                                                     group_object_permissions)
        if object_permissions is not empty:
            self.save_object_permissions(instance, object_permissions, True)
        return instance

    def update(self, instance, validated_data):
        user_object_permissions = validated_data.pop('user_object_permissions', empty)
        group_object_permissions = validated_data.pop('group_object_permissions', empty)
        object_permissions = validated_data.pop('object_permissions', empty)
        instance = super(ModelWithObjectPermissionSerializer, self).update(instance, validated_data)
        # if user_object_permissions is not empty:
        #     self.save_user_object_permissions(instance, user_object_permissions, False)
        # if group_object_permissions is not empty:
        #     self.save_group_object_permissions(instance, group_object_permissions, False)
        object_permissions = self._merge_permissions(instance, object_permissions, user_object_permissions,
                                                     group_object_permissions)
        if object_permissions is not empty:
            self.save_object_permissions(instance, object_permissions, False)
        return instance

    # def save_object_permission(self, instance, user_object_permissions=None, group_object_permissions=None,
    #                            created=False):
    #     member = get_member_from_context(self.context)
    #     member_perms = [{'member': member, 'permission': p,} for p in get_all_perms(instance)]
    #
    #     if created:
    #         if user_object_permissions:
    #             user_object_permissions = [uop for uop in user_object_permissions if uop['member'].id != member.id]
    #         else:
    #             user_object_permissions = []
    #         user_object_permissions += member_perms
    #         assign_perms2(instance, user_perms=user_object_permissions, group_perms=group_object_permissions)
    #     else:
    #         if has_manage_perm(member, instance):
    #             assign_perms2(instance, user_perms=user_object_permissions, group_perms=group_object_permissions)

    # def save_user_object_permissions(self, instance, user_object_permissions=None, created=False):
    #     member = get_member_from_context(self.context)
    #     member_perms = [{'member': member, 'permission': p,} for p in get_all_perms(instance)]
    #
    #     if created:
    #         if user_object_permissions:
    #             user_object_permissions = [uop for uop in user_object_permissions if uop['member'].id != member.id]
    #         else:
    #             user_object_permissions = []
    #         user_object_permissions += member_perms
    #         assign_perms2(instance, user_perms=user_object_permissions)
    #     else:
    #         if has_manage_perm(member, instance):
    #             assign_perms2(instance, user_perms=user_object_permissions)
    #
    # def save_group_object_permissions(self, instance, group_object_permissions=None, created=False):
    #     member = get_member_from_context(self.context)
    #     if created:
    #         assign_perms2(instance, group_perms=group_object_permissions)
    #     else:
    #         if has_manage_perm(member, instance):
    #             assign_perms2(instance, group_perms=group_object_permissions)

    def _merge_permissions(self, instance, object_permissions, user_object_permissions, group_object_permissions):
        if user_object_permissions is not empty or group_object_permissions is not empty:
            object_permissions = []

            if user_object_permissions is empty:
                object_permissions += [
                    {'group': None, 'member': op.member, 'permission': op.p}
                    for op in instance.object_permissions.all()
                    if op.member_id
                    ]

            elif user_object_permissions is not None:
                object_permissions += [
                    {'group': None, 'member': op['member'], 'permission': op['permission']}
                    for op in user_object_permissions
                    ]

            if group_object_permissions is empty:
                object_permissions += [
                    {'group': op.group, 'member': op.member, 'permission': op.p}
                    for op in instance.object_permissions.all()
                    if op.group_id
                    ]
            elif group_object_permissions is not None:
                object_permissions += [
                    {'group': op['group'], 'member': None, 'permission': op['permission']}
                    for op in group_object_permissions
                    ]
            return object_permissions

        if object_permissions is not empty:
            return object_permissions

        return empty

    def save_object_permissions(self, instance, object_permissions=None, created=False):
        member = get_member_from_context(self.context)
        if created:
            if object_permissions:
                object_permissions = [uop for uop in object_permissions
                                      if 'member' in uop and getattr(uop['member'], 'id', None) != member.id]
            else:
                object_permissions = []
            member_perms = [{'group': None, 'member': member, 'permission': p} for p in get_all_perms(instance)]
            object_permissions += member_perms
            assign_perms3(instance, perms=object_permissions)
        else:
            if has_manage_perm(member, instance):
                assign_perms3(instance, perms=object_permissions)


class ModelWithObjectPermissionVewSerializer(serializers.ModelSerializer):
    class Meta:
        list_serializer_class = ModelWithObjectPermissionViewListSerializer

    def __init__(self, *args, **kwargs):
        super(ModelWithObjectPermissionVewSerializer, self).__init__(*args, **kwargs)

        self.fields['display_name'] = serializers.SerializerMethodField()

        self.fields['granted_permissions'] = GrantedPermissionField()

    def get_display_name(self, instance):
        member = get_member_from_context(self.context)
        if has_view_perms(member, instance):
            return getattr(instance, 'name', None)
        else:
            return getattr(instance, 'public_name', None)

    def to_representation(self, instance):
        ret = super(ModelWithObjectPermissionVewSerializer, self).to_representation(instance)
        member = get_member_from_context(self.context)
        if not has_view_perms(member, instance):
            for k in list(ret.keys()):
                if k not in ['id', 'public_name', 'display_name', 'granted_permissions']:
                    ret.pop(k)

        if self.context.get('show_object_permissions', True):
            if not has_manage_perm(member, instance):
                # for k in list(ret.keys()):
                #     if k in ['object_permissions', 'user_object_permissions', 'group_object_permissions']:
                #         ret.pop(k)
                ret.pop('object_permissions', None)
                ret.pop('user_object_permissions', None)
                ret.pop('group_object_permissions', None)
        else:
            ret.pop('granted_permissions', None)
            ret.pop('object_permissions', None)
            ret.pop('user_object_permissions', None)
            ret.pop('group_object_permissions', None)
        return ret


# class ReadonlyModelWithObjectPermissionListSerializer(ReadonlyModelListSerializer):
#     def to_representation(self, data):
#         ret = super(ReadonlyModelWithObjectPermissionListSerializer, self).to_representation(data)
#         return [a for a in ret if a.get('granted_permissions', None)]
#
#
# class ReadonlyModelWithObjectPermissionSerializer(ReadonlyModelSerializer):
#     class Meta:
#         list_serializer_class = ReadonlyModelWithObjectPermissionListSerializer
#
#     def __init__(self, *args, **kwargs):
#         super(ReadonlyModelWithObjectPermissionSerializer, self).__init__(*args, **kwargs)
#         self.fields['granted_permissions'] = GrantedPermissionField()
#
#     def get_display_name(self, instance):
#         member = get_member_from_context(self.context)
#         if has_view_perms(member, instance):
#             return getattr(instance, 'name', None)
#         else:
#             return getattr(instance, 'public_name', None)
#
#     def to_representation(self, instance):
#         ret = super(ReadonlyModelWithObjectPermissionSerializer, self).to_representation(instance)
#         member = get_member_from_context(self.context)
#         if not has_view_perms(member, instance):
#             for k in list(ret.keys()):
#                 if k not in ['id', 'public_name', 'display_name', 'granted_permissions']:
#                     ret.pop(k)
#         return ret
#
#
# class ReadonlyNamedModelWithObjectPermissionSerializer(ReadonlyModelWithObjectPermissionSerializer):
#     def __init__(self, *args, **kwargs):
#         fields = kwargs.get('fields', None)
#         if fields is None:
#             fields = ['id', 'user_code', 'name', 'short_name', 'public_name']
#             kwargs['fields'] = fields
#         super(ReadonlyNamedModelWithObjectPermissionSerializer, self).__init__(*args, **kwargs)
#         self.fields['display_name'] = serializers.SerializerMethodField()


class GenericObjectPermissionSerializer(serializers.Serializer):
    group = GroupField(allow_null=True, allow_empty=True)
    member = MemberField(allow_null=True, allow_empty=True)
    permission = PermissionField()

    class Meta:
        model = GenericObjectPermission
        fields = ['id', 'group', 'member', 'permission']
