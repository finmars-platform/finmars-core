from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.db.models import Q
from mptt.admin import MPTTModelAdmin


class TreeModelAdmin(MPTTModelAdmin):
    mptt_level_indent = 20
    mptt_indent_field = 'name'


# class ClassifierAdmin(admin.ModelAdmin):
#     list_display = ['id', 'master_user', 'attribute_type', 'tree_id', 'level', 'parent', 'name', ]
#     list_select_related = ['attribute_type', 'attribute_type__master_user', 'parent']
#     ordering = ['attribute_type', 'tree_id', 'level', ]
#     search_fields = ['attribute_type__name', 'parent__name']
#     raw_id_fields = ['attribute_type', 'parent']
#
#     def master_user(self, obj):
#         return obj.attribute_type.master_user
#
#     master_user.admin_order_field = 'attribute_type__master_user'


# class ClassModelAdmin(TranslationAdmin):
class ClassModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_code', 'name']
    ordering = ['id']
    search_fields = ['id', 'user_code', 'name']


class PomsChangeList(ChangeList):
    def _get_default_ordering(self):
        return []


class AbstractModelAdmin(admin.ModelAdmin):
    master_user_path = None

    def get_changelist(self, request, **kwargs):
        return PomsChangeList

    def get_queryset(self, request):
        qs = super(AbstractModelAdmin, self).get_queryset(request)

        if self.master_user_path:
            master_user_id = self.get_active_master_user(request)
            if master_user_id is not None:
                if isinstance(self.master_user_path, (list, tuple)):
                    if self.master_user_path:
                        f = Q()
                        for p in self.master_user_path:
                            f |= Q(**{p: master_user_id})
                        qs = qs.filter(f)
                else:
                    qs = qs.filter(**{self.master_user_path: master_user_id})

        return qs

    @staticmethod
    def set_active_master_user(request, master_user):
        if master_user is None:
            del request.session['admin_master_user_id']
            master_user_id = None
        else:
            if isinstance(master_user, (str, int, float)):
                master_user_id = int(master_user)
            else:
                master_user_id = master_user.id
            request.session['admin_master_user_id'] = master_user_id
        return master_user_id

    @staticmethod
    def get_active_master_user(request):
        master_user_id = request.GET.get('master_user_id', None)
        if master_user_id is None:
            master_user_id = request.session.get('admin_master_user_id', None)
        else:
            master_user_id = int(master_user_id)
            if master_user_id < 0:
                del request.session['admin_master_user_id']
                master_user_id = None
            else:
                request.session['admin_master_user_id'] = master_user_id
        return master_user_id

    @staticmethod
    def get_active_master_user_object(request):
        master_user_id = AbstractModelAdmin.get_active_master_user(request)
        if master_user_id is not None:
            from poms.users.models import MasterUser
            try:
                return MasterUser.objects.get(pk=master_user_id)
            except MasterUser.DoesNotExist:
                pass
        return None
