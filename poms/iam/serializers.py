from django.contrib.auth import get_user_model
from rest_framework import serializers

from poms.iam.models import Role, Group, AccessPolicy
from poms.users.models import Member
from poms_app import settings


import logging
_l = logging.getLogger('poms.iam')
User = get_user_model()


class IamAbstractSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True

    def to_representation(self, instance):

        member = self.context['request'].user.member

        if member.is_admin:
            return super().to_representation(instance)
        """
        Overriding to_representation to check if the user has access to view the protected field.
        If not, hide the field.
        """

        queryset = self.Meta.model.objects.filter(pk=instance.pk)

        from poms.iam.utils import get_allowed_resources
        allowed_resources = get_allowed_resources(member, self.Meta.model, queryset)

        has_permission = False
        for resource in allowed_resources:

            # _l.debug('to_representation.resource %s' % resource)

            prefix, app, content_type, user_code = resource.split(':', 3)
            model_content_type = self.Meta.model._meta.app_label + '.' + self.Meta.model.__name__.lower()
            if model_content_type == content_type and user_code == instance.user_code:
                has_permission = True
                break

        if has_permission:
            return super().to_representation(instance)
        else:
            return {
                'id': instance.id,
                'name': instance.public_name,
                'short_name': instance.public_name,
                'user_code': instance.user_code
            }


class IamModelMetaSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['meta'] = {
            'content_type': self.Meta.model._meta.app_label + '.' + self.Meta.model._meta.model_name,
            'app_label': self.Meta.model._meta.app_label,
            'model_name': self.Meta.model._meta.model_name,
            'space_code': settings.BASE_API_URL
        }

        return representation


class IamRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'user_code', 'configuration_code']


class IamGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name', 'user_code', 'configuration_code']


class IamAccessPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPolicy
        fields = ['id', 'name', 'user_code', 'configuration_code']


class IamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['id', 'username']


class RoleUserCodeField(serializers.RelatedField):
    def to_representation(self, value):
        return value.user_code

    def to_internal_value(self, data):
        try:
            return Role.objects.get(user_code=data)
        except Role.DoesNotExist:
            raise serializers.ValidationError('Role with user_code {} does not exist.'.format(data))


class GroupUserCodeField(serializers.RelatedField):
    def to_representation(self, value):
        return value.user_code

    def to_internal_value(self, data):
        try:
            return Group.objects.get(user_code=data)
        except Group.DoesNotExist:
            raise serializers.ValidationError('Group with user_code {} does not exist.'.format(data))


class AccessPolicyUserCodeField(serializers.RelatedField):
    def to_representation(self, value):
        return value.user_code

    def to_internal_value(self, data):
        try:
            return AccessPolicy.objects.get(user_code=data)
        except AccessPolicy.DoesNotExist:
            raise serializers.ValidationError('AccessPolicy with user_code {} does not exist.'.format(data))


class RoleSerializer(IamModelMetaSerializer):
    members = serializers.PrimaryKeyRelatedField(queryset=Member.objects.all(), many=True, required=False)
    members_object = IamMemberSerializer(source="members", many=True, read_only=True)

    groups = GroupUserCodeField(queryset=Group.objects.all(), source="iam_groups", many=True, required=False)
    groups_object = IamGroupSerializer(source="iam_groups", many=True, read_only=True)

    access_policies = AccessPolicyUserCodeField(queryset=AccessPolicy.objects.all(), many=True, required=False)
    access_policies_object = IamAccessPolicySerializer(source="access_policies", many=True, read_only=True)

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'user_code', 'configuration_code',
                  'members', 'members_object',
                  'groups', 'groups_object',
                  'access_policies', 'access_policies_object'
                  ]

    def create(self, validated_data):
        # role_access_policies_data = self.context['request'].data.get('access_policies', [])
        access_policies_data = validated_data.pop('access_policies', [])
        members_data = validated_data.pop('members', [])
        instance = Role.objects.create(**validated_data)

        # Update members
        instance.members.set(members_data)
        # Update members
        instance.access_policies.set(access_policies_data)

        return instance

    def update(self, instance, validated_data):
        access_policies_data = validated_data.pop('access_policies', [])
        members_data = validated_data.pop('members', [])
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        ''' You cannot change configuration code or user_code in existing object'''
        instance.save()

        # Update users
        instance.members.set(members_data)
        # Update members
        instance.access_policies.set(access_policies_data)

        return instance


class GroupSerializer(IamModelMetaSerializer):
    members = serializers.PrimaryKeyRelatedField(queryset=Member.objects.all(), many=True, required=False)
    members_object = IamMemberSerializer(source="members", many=True, read_only=True)

    roles = RoleUserCodeField(queryset=Role.objects.all(), many=True, required=False)
    roles_object = IamRoleSerializer(source="roles", many=True, read_only=True)

    access_policies = AccessPolicyUserCodeField(queryset=AccessPolicy.objects.all(), many=True, required=False)
    access_policies_object = IamAccessPolicySerializer(source="access_policies", many=True, read_only=True)

    class Meta:
        model = Group
        fields = ['id',
                  'user_code', 'configuration_code',
                  'name', 'description',
                  'access_policies',
                  'members', 'members_object',
                  'roles', 'roles_object',
                  'access_policies', 'access_policies_object'
                  ]

    def __init__(self, *args, **kwargs):
        super(GroupSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        # access_policies_data = self.context['request'].data.get('access_policies', [])
        access_policies_data = validated_data.pop('access_policies', [])
        members_data = validated_data.pop('members', [])
        roles_data = validated_data.pop('roles', [])
        instance = Group.objects.create(**validated_data)

        # Update members
        instance.members.set(members_data)
        # Update roles
        instance.roles.set(roles_data)
        # Update access policies
        instance.access_policies.set(access_policies_data)

        return instance

    def update(self, instance, validated_data):
        access_policies_data = validated_data.pop('access_policies', [])
        members_data = validated_data.pop('members', [])
        roles_data = validated_data.pop('roles', [])
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        ''' You cannot change configuration code or user_code in existing object'''
        instance.save()

        # Update members
        instance.members.set(members_data)
        # Update roles
        instance.roles.set(roles_data)
        # Update access policies
        instance.access_policies.set(access_policies_data)

        return instance


class AccessPolicySerializer(IamModelMetaSerializer):
    class Meta:
        model = AccessPolicy
        fields = ['id', 'name', 'user_code', 'configuration_code', 'policy', 'description']
