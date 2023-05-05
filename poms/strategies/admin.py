from __future__ import unicode_literals

from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.strategies.models import Strategy1Group, Strategy2Subgroup, Strategy3, Strategy1Subgroup, Strategy1, \
    Strategy2Group, Strategy2, Strategy3Group, Strategy3Subgroup


class Strategy1GroupAdmin(AbstractModelAdmin):
    model = Strategy1Group
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'user_code', 'name', 'is_deleted', ]
    list_select_related = ['master_user']
    list_filter = ['is_deleted', ]
    search_fields = ['id', 'user_code', 'name']
    raw_id_fields = ['master_user']
    inlines = [
        # UserObjectPermissionInline,
        # GroupObjectPermissionInline,
    ]


admin.site.register(Strategy1Group, Strategy1GroupAdmin)


class Strategy1SubgroupAdmin(AbstractModelAdmin):
    model = Strategy1Subgroup
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'group', 'user_code', 'name', 'is_deleted', ]
    list_select_related = ['group', 'group__master_user']
    list_filter = ['is_deleted', ]
    search_fields = ['id', 'user_code', 'name']
    raw_id_fields = ['master_user', 'group']
    inlines = [
        # UserObjectPermissionInline,
        # GroupObjectPermissionInline,
    ]


admin.site.register(Strategy1Subgroup, Strategy1SubgroupAdmin)


class Strategy1Admin(AbstractModelAdmin):
    model = Strategy1
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'group', 'subgroup', 'user_code', 'name', 'is_deleted', ]
    list_select_related = ['subgroup', 'subgroup__group', 'subgroup__group__master_user']
    list_filter = ['is_deleted', ]
    search_fields = ['id', 'user_code', 'name']
    raw_id_fields = ['master_user', 'subgroup']
    inlines = [
        # UserObjectPermissionInline,
        # GroupObjectPermissionInline,
    ]

    def group(self, obj):
        return obj.subgroup.group

    group.admin_order_field = 'subgroup__group'


admin.site.register(Strategy1, Strategy1Admin)


class Strategy2GroupAdmin(Strategy1GroupAdmin):
    model = Strategy2Group


admin.site.register(Strategy2Group, Strategy2GroupAdmin)


class Strategy2SubgroupAdmin(Strategy1SubgroupAdmin):
    model = Strategy2Subgroup


admin.site.register(Strategy2Subgroup, Strategy2SubgroupAdmin)


class Strategy2Admin(Strategy1Admin):
    model = Strategy2


admin.site.register(Strategy2, Strategy2Admin)


class Strategy3GroupAdmin(Strategy1GroupAdmin):
    model = Strategy3Group


admin.site.register(Strategy3Group, Strategy3GroupAdmin)


class Strategy3SubgroupAdmin(Strategy1SubgroupAdmin):
    model = Strategy3Subgroup


admin.site.register(Strategy3Subgroup, Strategy3SubgroupAdmin)


class Strategy3Admin(Strategy1Admin):
    model = Strategy3


admin.site.register(Strategy3, Strategy3Admin)
