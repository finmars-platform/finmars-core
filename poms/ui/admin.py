from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.ui.filters import LayoutContentTypeFilter
from poms.ui.models import TemplateListLayout, TemplateEditLayout, ListLayout, EditLayout, Bookmark, \
    TransactionUserFieldModel


class BaseLayoutAdmin(AbstractModelAdmin):
    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'content_type':
            qs = kwargs.get('queryset', db_field.remote_field.model.objects)
            kwargs['queryset'] = LayoutContentTypeFilter().filter_queryset(request, qs, None)
        return super(BaseLayoutAdmin, self).formfield_for_foreignkey(db_field, request=request, **kwargs)


class TransactionUserFieldModelAdmin(BaseLayoutAdmin):
    model = TransactionUserFieldModel
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'name', 'key']
    list_select_related = ['master_user']
    search_fields = ['id', 'name', 'key']
    raw_id_fields = ['master_user']


admin.site.register(TransactionUserFieldModel, TransactionUserFieldModelAdmin)


class TemplateListLayoutAdmin(BaseLayoutAdmin):
    model = TemplateListLayout
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'content_type', 'name']
    list_select_related = ['master_user', 'content_type']
    search_fields = ['id', 'name']
    raw_id_fields = ['master_user']


admin.site.register(TemplateListLayout, TemplateListLayoutAdmin)


class TemplateEditLayoutAdmin(BaseLayoutAdmin):
    model = TemplateEditLayout
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'content_type']
    list_select_related = ['master_user', 'content_type']
    search_fields = ['id']
    raw_id_fields = ['master_user']


admin.site.register(TemplateEditLayout, TemplateEditLayoutAdmin)


class ListLayoutAdmin(BaseLayoutAdmin):
    model = ListLayout
    master_user_path = 'member__master_user'
    list_display = ['id', 'master_user', 'member', 'content_type', 'name']
    list_select_related = ['member__master_user', 'member', 'content_type']
    search_fields = ['id', 'name']
    raw_id_fields = ['member']

    def master_user(self, obj):
        return obj.member.master_user

    master_user.admin_order_field = 'member__master_user'


admin.site.register(ListLayout, ListLayoutAdmin)


class EditLayoutAdmin(BaseLayoutAdmin):
    model = EditLayout
    master_user_path = 'member__master_user'
    list_display = ['id', 'master_user', 'member', 'content_type']
    list_select_related = ['member', 'content_type']
    search_fields = ['id']
    raw_id_fields = ['member']

    def master_user(self, obj):
        return obj.member.master_user

    master_user.admin_order_field = 'member__master_user'


admin.site.register(EditLayout, EditLayoutAdmin)


class BookmarkAdmin(AbstractModelAdmin):
    model = Bookmark
    master_user_path = 'member__master_user'
    list_display = ['id', 'master_user', 'member', 'tree_id', 'level', 'parent', 'name', ]
    list_select_related = ['member', 'member__master_user', 'parent']
    # ordering = ['member', 'tree_id', 'level', ]
    raw_id_fields = ['member', 'parent', 'list_layout']
    save_as = True

    def master_user(self, obj):
        return obj.member.master_user

    master_user.admin_order_field = 'member__master_user'


admin.site.register(Bookmark, BookmarkAdmin)
