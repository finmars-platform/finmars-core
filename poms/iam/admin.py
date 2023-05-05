from django.contrib import admin

from poms.iam.models import MemberAccessPolicy, Role, Group, AccessPolicyTemplate, RoleAccessPolicy, GroupAccessPolicy


class RoleAccessPolicyInline(admin.TabularInline):
    model = RoleAccessPolicy
    extra = 1

class RoleAdmin(admin.ModelAdmin):
    model = Role
    list_display = ['id', 'name', 'user_code', 'configuration_code']
    search_fields = ['id', 'name', 'user_code', 'configuration_code']
    filter_horizontal = ("members",)
    inlines = [RoleAccessPolicyInline]

    actions_on_bottom = True


admin.site.register(Role, RoleAdmin)


class GroupAccessPolicyInline(admin.TabularInline):
    model = GroupAccessPolicy
    extra = 1


class GroupAdmin(admin.ModelAdmin):
    model = Group
    list_display = ['id', 'name', 'user_code', 'configuration_code']
    search_fields = ['id', 'name', 'user_code', 'configuration_code']
    filter_horizontal = ("members", "roles")
    inlines = [GroupAccessPolicyInline]

    actions_on_bottom = True


admin.site.register(Group, GroupAdmin)


class MemberAccessPolicyAdmin(admin.ModelAdmin):
    model = MemberAccessPolicy
    list_display = ['id', 'member', 'name', 'user_code', 'created']
    search_fields = ['id', 'member', 'name', 'user_code', 'created']

    actions_on_bottom = True


admin.site.register(MemberAccessPolicy, MemberAccessPolicyAdmin)


class AccessPolicyTemplateAdmin(admin.ModelAdmin):
    model = AccessPolicyTemplate
    list_display = ['id', 'name', 'user_code', 'configuration_code']
    search_fields = ['id', 'name', 'user_code', 'configuration_code']

    actions_on_bottom = True


admin.site.register(AccessPolicyTemplate, AccessPolicyTemplateAdmin)
