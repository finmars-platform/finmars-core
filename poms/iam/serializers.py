from django.contrib.auth import get_user_model
from rest_framework import serializers

from poms.iam.models import Role, Group, AccessPolicyTemplate, RoleAccessPolicy, GroupAccessPolicy

User = get_user_model()


class RoleUserCodeField(serializers.RelatedField):
    def to_representation(self, value):
        return value.user_code

    def to_internal_value(self, data):
        try:
            return Role.objects.get(user_code=data)
        except Role.DoesNotExist:
            raise serializers.ValidationError('Role with user_code {} does not exist.'.format(data))


class RoleAccessPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAccessPolicy
        fields = ('id', 'name', 'user_code', 'policy')


class RoleSerializer(serializers.ModelSerializer):
    access_policies = RoleAccessPolicySerializer(many=True)
    users = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, required=False)

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'user_code', 'configuration_code', 'access_policies', 'users']

    def create(self, validated_data):
        role_access_policies_data = self.context['request'].data.get('access_policies', [])
        users_data = validated_data.pop('users', [])
        instance = Role.objects.create(**validated_data)

        # Update users
        instance.users.set(users_data)

        for role_access_policy_data in role_access_policies_data:
            role_access_policy_id = role_access_policy_data.get('id')
            role_access_policy = RoleAccessPolicy.objects.get(pk=role_access_policy_id)
            instance.access_policies.add(role_access_policy)

        return instance

    def update(self, instance, validated_data):
        access_policies_data = validated_data.pop('access_policies', [])
        users_data = validated_data.pop('users', [])
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        ''' You cannot change configuration code or user_code in existing object'''
        instance.save()

        # Update users
        instance.users.set(users_data)

        existing_access_policies_ids = [ap.id for ap in instance.access_policies.all()]

        # Add new access policies and update existing ones
        for access_policy_data in access_policies_data:
            access_policy_id = access_policy_data.get('id')
            if access_policy_id and access_policy_id in existing_access_policies_ids:
                access_policy = RoleAccessPolicy.objects.get(id=access_policy_id)
                access_policy.name = access_policy_data.get('name', access_policy.name)
                access_policy.save()
                existing_access_policies_ids.remove(access_policy_id)
            else:
                access_policy = RoleAccessPolicy.objects.create(**access_policy_data)
                instance.access_policies.add(access_policy)

        # Remove access policies that are not in the new data
        for access_policy_id in existing_access_policies_ids:
            access_policy = RoleAccessPolicy.objects.get(id=access_policy_id)
            instance.access_policies.remove(access_policy)

        return instance


class GroupAccessPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupAccessPolicy
        fields = ('id', 'name', 'user_code', 'policy')


class GroupSerializer(serializers.ModelSerializer):
    access_policies = GroupAccessPolicySerializer(many=True)

    users = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, required=False)
    # roles = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), many=True, required=False)
    roles = RoleUserCodeField(queryset=Role.objects.all(), many=True, required=False)

    class Meta:
        model = Group
        fields = ['id',
                  'user_code', 'configuration_code',
                  'name', 'description',
                  'access_policies',
                  'users', 'roles'
                  ]

    def create(self, validated_data):
        access_policies_data = self.context['request'].data.get('access_policies', [])
        users_data = validated_data.pop('users', [])
        roles_data = validated_data.pop('roles', [])
        instance = Group.objects.create(**validated_data)

        # Update users
        instance.users.set(users_data)
        # Update roles
        instance.roles.set(roles_data)

        for group_access_policy_data in access_policies_data:
            group_access_policy_id = group_access_policy_data.get('id')
            group_access_policy = GroupAccessPolicy.objects.get(pk=group_access_policy_id)
            instance.access_policies.add(group_access_policy)

        return instance

    def update(self, instance, validated_data):
        access_policies_data = validated_data.pop('access_policies', [])
        users_data = validated_data.pop('users', [])
        roles_data = validated_data.pop('roles', [])
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        ''' You cannot change configuration code or user_code in existing object'''
        instance.save()

        # Update users
        instance.users.set(users_data)
        # Update roles
        instance.roles.set(roles_data)

        existing_access_policies_ids = [ap.id for ap in instance.access_policies.all()]

        # Add new access policies and update existing ones
        for access_policy_data in access_policies_data:
            access_policy_id = access_policy_data.get('id')
            if access_policy_id and access_policy_id in existing_access_policies_ids:
                access_policy = GroupAccessPolicy.objects.get(id=access_policy_id)
                access_policy.name = access_policy_data.get('name', access_policy.name)
                access_policy.save()
                existing_access_policies_ids.remove(access_policy_id)
            else:
                access_policy = GroupAccessPolicy.objects.create(**access_policy_data)
                instance.access_policies.add(access_policy)

        # Remove access policies that are not in the new data
        for access_policy_id in existing_access_policies_ids:
            access_policy = GroupAccessPolicy.objects.get(id=access_policy_id)
            instance.access_policies.remove(access_policy)

        return instance


class AccessPolicyTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPolicyTemplate
        fields = ['id', 'name', 'user_code', 'configuration_code', 'policy']
