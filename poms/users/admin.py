from __future__ import unicode_literals

from functools import update_wrapper

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from django.http import HttpResponseRedirect
from django.urls import re_path
from django.urls import reverse
from django.utils.translation import gettext_lazy

from poms.common.admin import AbstractModelAdmin
from poms.instruments.models import EventScheduleConfig
from poms.users.models import MasterUser, UserProfile, Member, TIMEZONE_CHOICES, FakeSequence, \
     EcosystemDefault, OtpToken


# from django.contrib.sessions.models import Session
# class SessionAdmin(ModelAdmin):
#     def _session_data(self, obj):
#         return obj.get_decoded()
#     list_display = ['session_key', '_session_data', 'expire_date']
# admin.site.register(Session, SessionAdmin)

class MemberInline(admin.TabularInline):
    model = Member
    extra = 0
    raw_id_fields = ['user']


class EventScheduleConfigInline(admin.StackedInline):
    model = EventScheduleConfig
    can_delete = False


class MasterUserIsActiveFilter(admin.SimpleListFilter):
    title = 'Is active'
    parameter_name = 'admin_is_active'

    def lookups(self, request, model_admin):
        return (
            # (None, 'All'),
            ('1', 'Yes'),
            ('0', 'No'),
        )

    def queryset(self, request, queryset):
        master_user_id = AbstractModelAdmin.get_active_master_user(request)
        if master_user_id is not None:
            if self.value() == '0':
                return queryset.exclude(id=master_user_id)
            if self.value() == '1':
                return queryset.filter(id=master_user_id)
        return queryset


class MasterUserAdmin(AbstractModelAdmin):
    model = MasterUser
    master_user_path = 'id'
    inlines = [
        MemberInline,
    ]
    list_display = ['id', 'name']
    list_filter = (MasterUserIsActiveFilter,)
    search_fields = ['id', 'name']
    raw_id_fields = [
    ]


admin.site.register(MasterUser, MasterUserAdmin)


class EcosystemDefaultAdmin(AbstractModelAdmin):
    model = EcosystemDefault
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'currency', 'account_type', 'account', 'counterparty_group', 'counterparty',
                    'responsible_group', 'responsible', 'portfolio', 'instrument_type', 'instrument',
                    'transaction_type']
    list_select_related = ['master_user', ]
    raw_id_fields = ['master_user', ]


admin.site.register(EcosystemDefault, EcosystemDefaultAdmin)


class MemberAdmin(AbstractModelAdmin):
    model = Member
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'username', 'user', 'is_deleted', 'is_owner', 'is_admin']
    list_select_related = ['master_user', 'user']
    list_filter = ['is_deleted', 'is_owner', 'is_admin']
    raw_id_fields = ['master_user', 'user', ]

    # def formfield_for_manytomany(self, db_field, request=None, **kwargs):
    #     if db_field.name == 'permissions':
    #         qs = kwargs.get('queryset', db_field.remote_field.model.objects)
    #         kwargs['queryset'] = qs.select_related('content_type')
    #     return super(MemberAdmin, self).formfield_for_manytomany(db_field, request=request, **kwargs)


admin.site.register(Member, MemberAdmin)


class UserProfileForm(forms.ModelForm):
    language = forms.ChoiceField(choices=settings.LANGUAGES, initial=settings.LANGUAGE_CODE)
    timezone = forms.ChoiceField(choices=TIMEZONE_CHOICES)

    class Meta:
        model = UserProfile
        fields = ['language', 'timezone', 'two_factor_verification', 'active_master_user', 'user_unique_id']


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    form = UserProfileForm
    can_delete = False


class UserWithProfileAdmin(UserAdmin):
    inlines = [UserProfileInline]

    def get_inline_instances(self, request, obj=None):
        if obj:
            return super(UserWithProfileAdmin, self).get_inline_instances(request, obj=obj)
        else:
            return []


admin.site.unregister(User)
admin.site.register(User, UserWithProfileAdmin)


class PermissionAdmin(admin.ModelAdmin):
    model = Permission
    list_display = ['id', '_app_label', '_model', 'codename']
    list_select_related = ['content_type']
    ordering = ['content_type__app_label', 'content_type__model', 'codename']
    search_fields = ['content_type__app_label', 'content_type__model', 'codename']
    readonly_fields = ['content_type', 'codename']
    list_per_page = 2000

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _app_label(self, obj):
        return obj.content_type.app_label

    _app_label.admin_order_field = 'content_type__app_label'

    def _model(self, obj):
        return obj.content_type.model

    _model.admin_order_field = 'content_type__model'


admin.site.register(Permission, PermissionAdmin)


class ContentTypeAdmin(admin.ModelAdmin):
    model = ContentType
    list_display = ['id', 'app_label', 'model', 'name']
    ordering = ['app_label', 'model']
    readonly_fields = ['app_label', 'model']
    search_fields = ['app_label', 'model']
    list_per_page = 2000

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(ContentType, ContentTypeAdmin)


class OtpTokenAdmin(AbstractModelAdmin):
    model = OtpToken
    list_display = ['id', 'user', 'name', ]
    raw_id_fields = ['user']


admin.site.register(OtpToken, OtpTokenAdmin)


class FakeSequenceAdmin(AbstractModelAdmin):
    model = FakeSequence
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'name', 'value']
    list_select_related = ['master_user']
    raw_id_fields = ['master_user']
    readonly_fields = ['master_user', 'name', 'value']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(FakeSequence, FakeSequenceAdmin)


