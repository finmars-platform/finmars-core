from django.contrib import admin

from poms.iam.models import AccessPolicy, Group, ResourceGroup, Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    model = Role
    list_display = ["id", "name", "user_code", "configuration_code"]
    search_fields = ["id", "name", "user_code", "configuration_code"]
    filter_horizontal = ("members",)
    actions_on_bottom = True


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    model = Group
    list_display = ["id", "name", "user_code", "configuration_code"]
    search_fields = ["id", "name", "user_code", "configuration_code"]
    filter_horizontal = ("members", "roles")

    actions_on_bottom = True


@admin.register(AccessPolicy)
class AccessPolicyAdmin(admin.ModelAdmin):
    model = AccessPolicy
    list_display = ["id", "name", "user_code", "configuration_code"]
    search_fields = ["id", "name", "user_code", "configuration_code"]

    actions_on_bottom = True


@admin.register(ResourceGroup)
class ResourceGroupAdmin(admin.ModelAdmin):
    model = ResourceGroup
