import logging

from rest_framework import serializers

from poms.iam.models import (
    AccessPolicy,
    Group,
    ResourceGroup,
    ResourceGroupAssignment,
    Role,
    default_list,
)
from poms.portfolios.models import Portfolio
from poms.users.models import Member

_l = logging.getLogger("poms.iam")


class IamModelWithTimeStampSerializer(serializers.ModelSerializer):
    modified_at = serializers.ReadOnlyField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, data):
        if (
            self.instance
            and "modified_at" in data
            and data["modified_at"] != self.instance.modified_at
        ):
            raise serializers.ValidationError("Synchronization error")

        return data


class IamProtectedSerializer(serializers.ModelSerializer):
    """
    Abstract serializer for models with User Code.
    """

    class Meta:
        abstract = True

    def to_representation(self, instance):
        from poms.iam.models import ResourceGroup
        from poms.iam.utils import get_allowed_resources

        member = self.context["request"].user.member

        if member.is_admin:
            return super().to_representation(instance)

        """
        Overriding to_representation to check if the user has access 
        to view the protected field. If not, hide the field.
        """

        queryset = self.Meta.model.objects.filter(pk=instance.pk)

        # Get initial allowed resources for the member and model
        allowed_resources = get_allowed_resources(member, self.Meta.model, queryset)
        expanded_resources = set()

        # Parse and expand resources if ResourceGroups are present
        for resource in allowed_resources:
            prefix, app, content_type, user_code = resource.split(":", 3)
            if resource.startswith("frn:finmars:iam:resourcegroup:"):
                # Handle ResourceGroup resource
                resource_group_code = user_code
                try:
                    # Fetch the ResourceGroup and its assignments
                    resource_group = ResourceGroup.objects.get(
                        user_code=resource_group_code
                    )
                    assignments = resource_group.assignments.all()

                    # Add each assigned object's user_code as an expanded resource
                    expanded_resources.update(
                        f"frn:finmars:{assignment.content_type.app_label}:{assignment.content_type.model}:{assignment.object_user_code}"
                        for assignment in assignments
                        if assignment.object_user_code
                    )
                except ResourceGroup.DoesNotExist:
                    _l.warning(
                        f"ResourceGroup with user_code {resource_group_code} does not exist."
                    )
                    continue
            else:
                expanded_resources.add(resource)

        # Check permission against expanded resources
        has_permission = False
        model_content_type = (
            f"{self.Meta.model._meta.app_label}:{self.Meta.model.__name__.lower()}"
        )
        instance_identifier = f"frn:finmars:{model_content_type}:{instance.user_code}"

        if instance_identifier in expanded_resources:
            has_permission = True

        # Return the appropriate representation based on permission
        if has_permission:
            return super().to_representation(instance)
        else:
            return {
                "id": getattr(instance, "id", None),
                "name": getattr(instance, "public_name", None),
                "short_name": getattr(instance, "public_name", None),
                "user_code": getattr(instance, "user_code", None),
            }


class IamModelOwnerSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        from poms.users.serializers import MemberViewSerializer

        representation = super().to_representation(instance)

        serializer = MemberViewSerializer(instance=instance.owner)

        representation["owner"] = serializer.data

        return representation

    def create(self, validated_data):
        # You should have 'request' in the serializer context
        request = self.context.get("request", None)
        member = self.context.get("member", None)
        if member:
            validated_data["owner"] = member
        elif request and hasattr(request, "user"):
            validated_data["owner"] = Member.objects.get(user=request.user)

        return super(IamModelOwnerSerializer, self).create(validated_data)


class IamModelMetaSerializer(IamModelOwnerSerializer):
    def to_representation(self, instance):
        from poms.users.utils import get_space_code_from_context

        representation = super().to_representation(instance)

        space_code = get_space_code_from_context(self.context)

        representation["meta"] = {
            "content_type": self.Meta.model._meta.app_label
            + "."
            + self.Meta.model._meta.model_name,
            "app_label": self.Meta.model._meta.app_label,
            "model_name": self.Meta.model._meta.model_name,
            "space_code": space_code,
        }

        return representation


class IamRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "user_code", "configuration_code"]


class IamGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "user_code", "configuration_code"]


class IamAccessPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPolicy
        fields = ["id", "name", "user_code", "configuration_code"]


class IamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ["id", "username"]


class RoleUserCodeField(serializers.RelatedField):
    def to_representation(self, value):
        return value.user_code

    def to_internal_value(self, data):
        try:
            return Role.objects.get(user_code=data)
        except Role.DoesNotExist as e:
            raise serializers.ValidationError(
                f"Role with user_code {data} does not exist."
            ) from e


class GroupUserCodeField(serializers.RelatedField):
    def to_representation(self, value):
        return value.user_code

    def to_internal_value(self, data):
        try:
            return Group.objects.get(user_code=data)
        except Group.DoesNotExist as e:
            raise serializers.ValidationError(
                f"Group with user_code {data} does not exist."
            ) from e


class AccessPolicyUserCodeField(serializers.RelatedField):
    def to_representation(self, value):
        return value.user_code

    def to_internal_value(self, data):
        try:
            return AccessPolicy.objects.get(user_code=data)
        except AccessPolicy.DoesNotExist as e:
            raise serializers.ValidationError(
                f"AccessPolicy with user_code {data} does not exist."
            ) from e


class RoleSerializer(IamModelMetaSerializer, IamModelWithTimeStampSerializer):
    members = serializers.PrimaryKeyRelatedField(
        queryset=Member.objects.all(), many=True, required=False
    )
    members_object = IamMemberSerializer(source="members", many=True, read_only=True)

    groups = GroupUserCodeField(
        queryset=Group.objects.all(), source="iam_groups", many=True, required=False
    )
    groups_object = IamGroupSerializer(source="iam_groups", many=True, read_only=True)

    access_policies = AccessPolicyUserCodeField(
        queryset=AccessPolicy.objects.all(), many=True, required=False
    )
    access_policies_object = IamAccessPolicySerializer(
        source="access_policies", many=True, read_only=True
    )

    created_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    modified_at = serializers.DateTimeField(format="iso-8601", read_only=True)

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "user_code",
            "configuration_code",
            "members",
            "members_object",
            "groups",
            "groups_object",
            "access_policies",
            "access_policies_object",
            "created_at",
            "modified_at",
        ]

    def create(self, validated_data):
        # role_access_policies_data = self.context['request'].data.get('access_policies', [])

        _l.info(f"validated_data {validated_data}")

        access_policies_data = validated_data.pop("access_policies", [])
        members_data = validated_data.pop("members", [])
        groups_data = validated_data.pop("iam_groups", [])

        request = self.context.get("request", None)
        member = self.context.get("member", None)
        if member:
            validated_data["owner"] = member
        elif request and hasattr(request, "user"):
            validated_data["owner"] = Member.objects.get(user=request.user)

        instance = Role.objects.create(**validated_data)

        # Update members
        instance.members.set(members_data)
        instance.iam_groups.set(groups_data)
        # Update members
        instance.access_policies.set(access_policies_data)

        return instance

    def update(self, instance, validated_data):
        access_policies_data = validated_data.pop("access_policies", [])
        members_data = validated_data.pop("members", [])
        groups_data = validated_data.pop("iam_groups", [])
        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)

        # You cannot change configuration code or user_code in existing object !!!
        instance.save()

        instance.members.set(members_data)
        instance.iam_groups.set(groups_data)
        # Update members
        instance.access_policies.set(access_policies_data)

        return instance


class GroupSerializer(IamModelMetaSerializer, IamModelWithTimeStampSerializer):
    members = serializers.PrimaryKeyRelatedField(
        queryset=Member.objects.all(), many=True, required=False
    )
    members_object = IamMemberSerializer(source="members", many=True, read_only=True)

    roles = RoleUserCodeField(queryset=Role.objects.all(), many=True, required=False)
    roles_object = IamRoleSerializer(source="roles", many=True, read_only=True)

    access_policies = AccessPolicyUserCodeField(
        queryset=AccessPolicy.objects.all(), many=True, required=False
    )
    access_policies_object = IamAccessPolicySerializer(
        source="access_policies", many=True, read_only=True
    )

    created_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    modified_at = serializers.DateTimeField(format="iso-8601", read_only=True)

    class Meta:
        model = Group
        fields = [
            "id",
            "user_code",
            "configuration_code",
            "name",
            "description",
            "access_policies",
            "members",
            "members_object",
            "roles",
            "roles_object",
            "access_policies",
            "access_policies_object",
            "created_at",
            "modified_at",
        ]

    def __init__(self, *args, **kwargs):
        super(GroupSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        # access_policies_data = self.context['request'].data.get('access_policies', [])
        access_policies_data = validated_data.pop("access_policies", [])
        members_data = validated_data.pop("members", [])
        roles_data = validated_data.pop("roles", [])

        request = self.context.get("request", None)
        member = self.context.get("member", None)
        if member:
            validated_data["owner"] = member
        elif request and hasattr(request, "user"):
            validated_data["owner"] = Member.objects.get(user=request.user)
        instance = Group.objects.create(**validated_data)

        # Update members
        instance.members.set(members_data)
        # Update roles
        instance.roles.set(roles_data)
        # Update access policies
        instance.access_policies.set(access_policies_data)

        return instance

    def update(self, instance, validated_data):
        access_policies_data = validated_data.pop("access_policies", [])
        members_data = validated_data.pop("members", [])
        roles_data = validated_data.pop("roles", [])
        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
        """ You cannot change configuration code or user_code in existing object"""
        instance.save()

        # Update members
        instance.members.set(members_data)
        # Update roles
        instance.roles.set(roles_data)
        # Update access policies
        instance.access_policies.set(access_policies_data)

        return instance


class AccessPolicySerializer(IamModelMetaSerializer, IamModelWithTimeStampSerializer):
    created_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    modified_at = serializers.DateTimeField(format="iso-8601", read_only=True)

    class Meta:
        model = AccessPolicy
        fields = [
            "id",
            "name",
            "user_code",
            "configuration_code",
            "policy",
            "description",
            "created_at",
            "modified_at",
        ]


class ResourceGroupAssignmentSerializer(serializers.ModelSerializer):
    # Explicit declaration to ensure ID presence in validated data
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ResourceGroupAssignment
        fields = [
            "id",
            "resource_group",
            "content_type",
            "object_id",
            "object_user_code",
        ]


class ResourceGroupSerializer(IamModelMetaSerializer):
    assignments = ResourceGroupAssignmentSerializer(many=True, required=False)
    created_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    modified_at = serializers.DateTimeField(format="iso-8601", read_only=True)

    members = serializers.PrimaryKeyRelatedField(
        queryset=Member.objects.all(), many=True, required=False
    )
    members_object = IamMemberSerializer(
        source="members", many=True, read_only=True
    )

    class Meta:
        model = ResourceGroup
        fields = [
            "id",
            "user_code",
            "configuration_code",
            "name",
            "description",
            "assignments",
            "created_at",
            "modified_at",
            "members",
            "members_object",
        ]

    def create(self, validated_data):
        members_data = validated_data.pop("members", [])

        instance = super().create(validated_data)
        instance.members.set(members_data)

        return instance

    def update(self, instance, validated_data):
        """
        Args:
        - instance: The instance of the ResourceGroup that is being updated.
        - validated_data: The data that has been validated and will be used

        Updates the assignments for a given instance based on the provided validated_data.
        Existing assignments can be only deleted, so assignments that are not present
        in the received list to be deleted.
        """
        members_data = validated_data.pop("members", [])
        received_assignments = validated_data.pop("assignments", None)

        if received_assignments is not None:
            received_ids = {
                assignment["id"]: assignment
                for assignment in received_assignments
                if assignment.get("id")
            }
            existing_ids = {
                assignment.id: assignment for assignment in instance.assignments.all()
            }

            ids_to_remove = set(existing_ids.keys()) - set(received_ids.keys())

            if ids_to_remove:
                for old_id in ids_to_remove:
                    existing_ids[old_id].delete()

        instance = super().update(instance, validated_data)
        instance.members.set(members_data)

        return instance


class ResourceGroupShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceGroup
        fields = [
            "id",
            "name",
            "user_code",
            "description",
        ]


class ModelWithResourceGroupSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resource_groups"] = serializers.ListSerializer(
            child=serializers.CharField(max_length=1024),
            required=False,
            default=default_list,
        )
        self.fields["resource_groups_object"] = serializers.SerializerMethodField(
            "get_resource_groups_object",
            read_only=True,
        )

    @staticmethod
    def get_resource_groups_object(obj: Portfolio) -> list:
        resource_groups = ResourceGroup.objects.filter(
            user_code__in=obj.resource_groups
        )
        return ResourceGroupShortSerializer(resource_groups, many=True).data

    @staticmethod
    def validate_resource_groups(group_list):
        for gr_user_code in group_list:
            if not ResourceGroup.objects.filter(user_code=gr_user_code).exists():
                raise serializers.ValidationError(
                    f"No such ResourceGroup {gr_user_code}"
                )
        return group_list

    def create(self, validated_data: dict) -> object:
        resource_groups = validated_data.pop("resource_groups", [])
        instance = super().create(validated_data)

        for rg_user_code in resource_groups:
            ResourceGroup.objects.add_object(
                group_user_code=rg_user_code,
                obj_instance=instance,
            )

        return instance

    def update(self, instance, validated_data: dict):
        new_resource_groups = validated_data.pop("resource_groups", [])
        instance = super().update(instance, validated_data)

        resource_group_to_remove = set(instance.resource_groups) - set(
            new_resource_groups
        )
        for rg_user_code in resource_group_to_remove:
            ResourceGroup.objects.del_object(
                group_user_code=rg_user_code,
                obj_instance=instance,
            )

        for rg_user_code in new_resource_groups:
            ResourceGroup.objects.add_object(
                group_user_code=rg_user_code,
                obj_instance=instance,
            )

        return instance
