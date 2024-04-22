from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.models import ContentType

from poms.common.admin import AbstractModelAdmin
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier, GenericAttribute, GenericAttributeTypeOption



# class AbstractAttributeTypeAdmin(admin.ModelAdmin):
#     list_display = ['id', 'master_user', 'user_code', 'name', 'value_type', ]
#     list_select_related = ['master_user', ]
#     ordering = ['master_user', 'user_code']
#     list_filter = ['value_type']
#     search_fields = ['id', 'name']
#     raw_id_fields = ['master_user']
#     save_as = True
#
#
# class AbstractAttributeTypeClassifierInline(admin.TabularInline):
#     extra = 0
#     fields = ['id', 'name', 'parent']
#     raw_id_fields = ['parent']
#     readonly_fields = ['id']
#     # formfield_overrides = {
#     #     models.TextField: {'widget': widgets.AdminTextInputWidget},
#     # }
#     model = AbstractClassifier
#
#     def __init__(self, parent_model, *args, **kwargs):
#         # _, self.model = get_rel_model(parent_model, 'attribute_type', MPTTModel)
#         self.model = parent_model._meta.get_field('classifiers').related_model
#         super(AbstractAttributeTypeClassifierInline, self).__init__(parent_model, *args, **kwargs)
#
#
# class AbstractAttributeTypeOptionInline(admin.TabularInline):
#     extra = 0
#     fields = ['member', 'is_hidden', ]
#     raw_id_fields = ['member']
#     model = AbstractAttributeTypeOption
#
#     def __init__(self, parent_model, *args, **kwargs):
#         self.model = parent_model._meta.get_field('options').related_model
#         super(AbstractAttributeTypeOptionInline, self).__init__(parent_model, *args, **kwargs)
#
#
# class AbstractAttributeTypeOptionAdmin(admin.ModelAdmin):
#     extra = 0
#     list_display = ['id', 'member', 'attribute_type', 'is_hidden']
#     fields = ['member', 'attribute_type', 'is_hidden']
#     raw_id_fields = ['member']
#
#
# class AbstractAttributeInline(admin.TabularInline):
#     extra = 0
#     fields = ['attribute_type', 'value_string', 'value_float', 'value_date', 'classifier']
#     raw_id_fields = ['attribute_type', 'classifier']
#     model = AbstractAttribute
#
#     def __init__(self, parent_model, *args, **kwargs):
#         self.model = parent_model._meta.get_field('attributes').related_model
#         super(AbstractAttributeInline, self).__init__(parent_model, *args, **kwargs)
#

class GenericAttributeTypeOptionInline(admin.TabularInline):
    model = GenericAttributeTypeOption
    extra = 0
    raw_id_fields = ['member']


class GenericAttributeTypeAdmin(AbstractModelAdmin):
    model = GenericAttributeType
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'content_type', 'value_type', 'user_code']
    list_select_related = ['content_type', 'content_type']
    list_filter = ['value_type', 'content_type']
    search_fields = ['id', 'user_code']
    raw_id_fields = ['master_user', 'content_type']
    inlines = [
        GenericAttributeTypeOptionInline,
    ]
    save_as = True


admin.site.register(GenericAttributeType, GenericAttributeTypeAdmin)


class GenericClassifierAdmin(AbstractModelAdmin):
    model = GenericClassifier
    master_user_path = 'attribute_type__master_user'
    list_display = ['id', 'master_user', 'attribute_type', 'content_type', 'tree_id', 'level', 'parent',
                    'name', ]
    list_select_related = ['attribute_type', 'attribute_type__master_user', 'attribute_type__content_type', 'parent']
    search_fields = ['attribute_type__id', 'attribute_type__user_code', ]
    raw_id_fields = ['attribute_type', 'parent']
    save_as = True

    def master_user(self, obj):
        return obj.attribute_type.master_user

    master_user.admin_order_field = 'attribute_type__master_user'

    def content_type(self, obj):
        return obj.attribute_type.content_type

    content_type.admin_order_field = 'attribute_type__content_type'


admin.site.register(GenericClassifier, GenericClassifierAdmin)


class GenericAttributeAdmin(AbstractModelAdmin):
    model = GenericAttribute
    master_user_path = 'attribute_type__master_user'
    list_display = ['id', 'master_user', 'attribute_type', 'content_type', 'object_id',
                    'content_object', 'value_string', 'value_float', 'value_date', 'classifier', ]
    list_select_related = ['content_type', 'attribute_type', 'attribute_type__master_user',
                           'attribute_type__content_type', 'classifier']
    list_filter = ['content_type']
    search_fields = ['attribute_type__id', 'attribute_type__user_code', ]
    raw_id_fields = ['attribute_type', 'content_type', 'classifier']
    save_as = True

    def get_queryset(self, request):
        qs = super(GenericAttributeAdmin, self).get_queryset(request)
        return qs.prefetch_related('content_object')

    def master_user(self, obj):
        return obj.attribute_type.master_user

    master_user.admin_order_field = 'attribute_type__master_user'

    def attribute_type__content_type(self, obj):
        return obj.attribute_type.content_type


admin.site.register(GenericAttribute, GenericAttributeAdmin)


class GenericAttributeInline(GenericTabularInline):
    model = GenericAttribute
    raw_id_fields = ['attribute_type', 'classifier']
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'attribute_type':
            qs = kwargs.get('queryset', db_field.remote_field.model.objects)
            # TODO beware of cached values for get_for_model, refactor
            kwargs['queryset'] = qs.select_related('content_type').filter(
                content_type=ContentType.objects.get_for_model(self.parent_model)
            )
        return super(GenericAttributeInline, self).formfield_for_foreignkey(db_field, request=request, **kwargs)
