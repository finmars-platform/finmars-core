from django.contrib.auth import get_user_model
from rest_framework import serializers

from poms.iam.models import Role, Group, AccessPolicy
from poms.users.models import Member

User = get_user_model()


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


class RoleSerializer(serializers.ModelSerializer):

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



class GroupSerializer(serializers.ModelSerializer):

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


class AccessPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPolicy
        fields = ['id', 'name', 'user_code', 'configuration_code', 'policy', 'description']
