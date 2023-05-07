from django.contrib import admin

from poms.iam.models import  Role, Group, AccessPolicy



class RoleAdmin(admin.ModelAdmin):
    model = Role
    list_display = ['id', 'name', 'user_code', 'configuration_code']
    search_fields = ['id', 'name', 'user_code', 'configuration_code']
    filter_horizontal = ("members",)

    actions_on_bottom = True


admin.site.register(Role, RoleAdmin)



class GroupAdmin(admin.ModelAdmin):
    model = Group
    list_display = ['id', 'name', 'user_code', 'configuration_code']
    search_fields = ['id', 'name', 'user_code', 'configuration_code']
    filter_horizontal = ("members", "roles")

    actions_on_bottom = True


admin.site.register(Group, GroupAdmin)



class AccessPolicyAdmin(admin.ModelAdmin):
    model = AccessPolicy
    list_display = ['id', 'name', 'user_code', 'configuration_code']
    search_fields = ['id', 'name', 'user_code', 'configuration_code']

    actions_on_bottom = True


admin.site.register(AccessPolicy, AccessPolicyAdmin)
