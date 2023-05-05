# from django.contrib import admin
# from django.contrib.contenttypes.admin import GenericTabularInline
# from django.contrib.contenttypes.models import ContentType
#
# from poms.common.admin import AbstractModelAdmin
# from poms.obj_perms.models import GenericObjectPermission
#
#
# # class AbstractObjectPermissionAdmin(admin.ModelAdmin):
# #     def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
# #         if db_field.name == 'permission':
# #             qs = kwargs.get('queryset', db_field.remote_field.model.objects)
# #             obj_field = self.model._meta.get_field('content_object')
# #             obj_ctype = ContentType.objects.get_for_model(obj_field.rel.to)
# #             kwargs['queryset'] = qs.select_related('content_type').filter(content_type=obj_ctype)
# #             # kwargs['queryset'] = qs.select_related('content_type')
# #         return super(AbstractObjectPermissionAdmin, self).formfield_for_foreignkey(db_field, request=request, **kwargs)
# #
# #
# # class UserObjectPermissionAdmin(AbstractObjectPermissionAdmin):
# #     list_display = ['id', 'member', 'content_object', 'permission', ]
# #     search_fields = ['content_object__id', 'member__id', 'member__user__username']
# #     list_select_related = ['member', 'content_object', 'permission', 'permission__content_type']
# #     fields = ['member', 'content_object', 'permission']
# #     raw_id_fields = ['member', 'content_object']
# #     save_as = True
# #     # list_filter = ['permission']
# #
# #
# # class GroupObjectPermissionAdmin(AbstractObjectPermissionAdmin):
# #     list_display = ['id', 'group', 'content_object', 'permission', ]
# #     search_fields = ['content_object__id', 'group__id', 'group__name']
# #     list_select_related = ['group', 'content_object', 'permission', 'permission__content_type']
# #     fields = ['group', 'content_object', 'permission']
# #     raw_id_fields = ['group', 'content_object']
# #     save_as = True
# #     # list_filter = ['permission']
# #
# #
# # class AbstractObjectPermissionInline(admin.TabularInline):
# #     def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
# #         if db_field.name == 'permission':
# #             qs = kwargs.get('queryset', db_field.remote_field.model.objects)
# #             obj_field = self.model._meta.get_field('content_object')
# #             obj_ctype = ContentType.objects.get_for_model(obj_field.rel.to)
# #             kwargs['queryset'] = qs.select_related('content_type').filter(content_type=obj_ctype)
# #             # kwargs['queryset'] = qs.select_related('content_type')
# #         return super(AbstractObjectPermissionInline, self).formfield_for_foreignkey(db_field, request=request, **kwargs)
# #
# #
# # class UserObjectPermissionInline(AbstractObjectPermissionInline):
# #     fields = ['member', 'permission']
# #     raw_id_fields = ['member', 'content_object']
# #     model = AbstractUserObjectPermission
# #     extra = 0
# #
# #     def __init__(self, parent_model, *args, **kwargs):
# #         _, self.model = get_user_obj_perms_model(parent_model)
# #         super(UserObjectPermissionInline, self).__init__(parent_model, *args, **kwargs)
# #
# #
# # class GroupObjectPermissionInline(AbstractObjectPermissionInline):
# #     fields = ['group', 'permission']
# #     raw_id_fields = ['group', 'content_object']
# #     model = AbstractGroupObjectPermission
# #     extra = 0
# #
# #     def __init__(self, parent_model, *args, **kwargs):
# #         _, self.model = get_group_obj_perms_model(parent_model)
# #         super(GroupObjectPermissionInline, self).__init__(parent_model, *args, **kwargs)
#
#
# class GenericObjectPermissionInline(GenericTabularInline):
#     fields = ['member', 'group', 'permission']
#     raw_id_fields = ['member', 'group', 'permission']
#     model = GenericObjectPermission
#     extra = 0
#
#     def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
#         if db_field.name == 'permission':
#             qs = kwargs.get('queryset', db_field.remote_field.model.objects)
#             kwargs['queryset'] = qs.select_related('content_type').filter(
#                 content_type=ContentType.objects.get_for_model(self.parent_model)
#             )
#         return super(GenericObjectPermissionInline, self).formfield_for_foreignkey(db_field, request=request, **kwargs)
#
#
# class GenericObjectPermissionAdmin(AbstractModelAdmin):
#     model = GenericObjectPermission
#     master_user_path = ('group__master_user', 'member__master_user')
#     list_display = ['id', 'master_user', 'group', 'member', 'content_type', 'object_id', 'content_object', 'permission']
#     raw_id_fields = ['group', 'member', 'content_type', 'permission']
#     list_filter = ['content_type']
#     search_fields = ['object_id']
#     save_as = True
#
#     # readonly_fields = ('content_object',)
#
#     def get_queryset(self, request):
#         qs = super(GenericObjectPermissionAdmin, self).get_queryset(request)
#         return qs.select_related(
#             'group', 'group__master_user',
#             'member', 'member__master_user',
#             'permission', 'permission__content_type',
#             'content_type',
#         ).prefetch_related(
#             'content_object'
#         )
#
#     def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
#         if db_field.name == 'permission':
#             qs = kwargs.get('queryset', db_field.remote_field.model.objects)
#             kwargs['queryset'] = qs.select_related('content_type')
#
#         if db_field.name == 'content_type':
#             qs = kwargs.get('queryset', db_field.remote_field.model.objects)
#             # kwargs['queryset'] = qs.order_by('app_label', 'model')
#             kwargs['queryset'] = qs.order_by('model')
#         return super(GenericObjectPermissionAdmin, self).formfield_for_foreignkey(db_field, request=request, **kwargs)
#
#     def master_user(self, obj):
#         if obj.group:
#             return obj.group.master_user
#         elif obj.member:
#             return obj.member.master_user
#         else:
#             return None
#
#             # master_user.admin_order_field = 'attribute_type__master_user'
#
#
# admin.site.register(GenericObjectPermission, GenericObjectPermissionAdmin)
