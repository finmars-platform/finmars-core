from __future__ import unicode_literals

from functools import update_wrapper

from django import forms
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import ugettext_lazy

from poms.common.admin import AbstractModelAdmin
from poms.instruments.models import EventScheduleConfig
from poms.integrations.models import PricingAutomatedSchedule
from poms.users.models import MasterUser, UserProfile, Member, Group, TIMEZONE_CHOICES, FakeSequence, \
    InviteToMasterUser, EcosystemDefault


# from django.contrib.sessions.models import Session
# class SessionAdmin(ModelAdmin):
#     def _session_data(self, obj):
#         return obj.get_decoded()
#     list_display = ['session_key', '_session_data', 'expire_date']
# admin.site.register(Session, SessionAdmin)

class MemberInline(admin.TabularInline):
    model = Member
    extra = 0
    raw_id_fields = ['user', 'groups', ]


class PricingAutomatedScheduleInline(admin.StackedInline):
    model = PricingAutomatedSchedule
    can_delete = False
    # readonly_fields = ['latest_running', 'latest_task']


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
        PricingAutomatedScheduleInline,
        EventScheduleConfigInline,
        MemberInline,
    ]
    list_display = ['id', 'name', 'set_activate_link']
    list_filter = (MasterUserIsActiveFilter,)
    search_fields = ['id', 'name']
    raw_id_fields = [
        'system_currency', 'currency', 'account_type', 'account', 'counterparty_group', 'counterparty',
        'responsible_group', 'responsible', 'instrument_type', 'instrument', 'portfolio',
        'strategy1_group', 'strategy1_subgroup', 'strategy1',
        'strategy2_group', 'strategy2_subgroup', 'strategy2',
        'strategy3_group', 'strategy3_subgroup', 'strategy3',
        'thread_group', 'transaction_type_group', 'mismatch_portfolio', 'mismatch_account',
    ]

    actions = [
        'generate_events', 'clone_data',
        'patch_currencies', 'patch_currencies_with_overwrites',
        'patch_bloomberg_currency_mappings', 'patch_bloomberg_currency_mappings_with_overwrites',
    ]

    def get_queryset(self, request):
        from django.contrib.admin.options import IS_POPUP_VAR
        if IS_POPUP_VAR in request.GET:
            self.master_user_path = 'id'
        else:
            self.master_user_path = None
        qs = super(MasterUserAdmin, self).get_queryset(request)
        qs = qs.annotate(id_check=F('id') - self.get_active_master_user(request))
        return qs

    def save_model(self, request, obj, form, change):
        super(MasterUserAdmin, self).save_model(request, obj, form, change)

        if not change:
            obj.create_defaults()

    def clone_data(self, request, queryset):
        from poms.users.cloner import FullDataCloner
        for mu in queryset:
            cloner = FullDataCloner(mu)
            cloner.clone()

    clone_data.short_description = ugettext_lazy("Clone selected master users")

    def generate_events(self, request, queryset):
        from poms.instruments.tasks import generate_events
        generate_events.apply_async(kwargs={'master_users': [mu.pk for mu in queryset]})

    generate_events.short_description = ugettext_lazy("Generate and check events")

    def patch_currencies(self, request, queryset):
        for mu in queryset:
            mu.patch_currencies()

    patch_currencies.short_description = ugettext_lazy("Patch currencies")

    def patch_currencies_with_overwrites(self, request, queryset):
        for mu in queryset:
            mu.patch_currencies(True, True)

    patch_currencies_with_overwrites.short_description = ugettext_lazy(
        "Patch currencies (and overwrite names and reference_for_pricing)")

    def patch_bloomberg_currency_mappings(self, request, queryset):
        for mu in queryset:
            mu.patch_bloomberg_currency_mappings()

    patch_bloomberg_currency_mappings.short_description = ugettext_lazy("Patch bloomberg mapping")

    def patch_bloomberg_currency_mappings_with_overwrites(self, request, queryset):
        for mu in queryset:
            mu.patch_bloomberg_currency_mappings(True)

    patch_bloomberg_currency_mappings_with_overwrites.short_description = ugettext_lazy(
        "Patch bloomberg mapping (and overwrite value)")

    def set_activate_link(self, obj):
        if getattr(obj, 'id_check', 1) == 0:
            return '<a href="%s">Unset</a>' % (
                reverse("admin:users_masteruser_clearactive", args=(obj.id,))
            )
        else:
            return '<a href="%s">Set</a>' % (
                reverse("admin:users_masteruser_setactive", args=(obj.id,))
            )

    set_activate_link.allow_tags = True
    set_activate_link.short_description = 'Is Active'

    def get_urls(self):
        urls = super(MasterUserAdmin, self).get_urls()

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.model_name

        urls = [
                   url(r'^(.+)/set_active/$', wrap(self.set_active_view), name='%s_%s_setactive' % info),
                   url(r'^(.+)/clear_active/$', wrap(self.clear_active_view), name='%s_%s_clearactive' % info),
               ] + urls
        return urls

    def set_active_view(self, request, object_id, form_url='', extra_context=None):
        self.set_active_master_user(request, object_id)
        self.message_user(request, ugettext_lazy("Active master user successful set."))
        if 'HTTP_REFERER' in request.META:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        else:
            return HttpResponseRedirect(redirect_to=reverse("admin:users_masteruser_changelist"))

    def clear_active_view(self, request, object_id, form_url='', extra_context=None):
        self.set_active_master_user(request, None)
        self.message_user(request, ugettext_lazy("Active master user successful unset."))
        if 'HTTP_REFERER' in request.META:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        else:
            return HttpResponseRedirect(redirect_to=reverse("admin:users_masteruser_changelist"))


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
    list_display = ['id', 'master_user', 'user', 'is_deleted', 'is_owner', 'is_admin']
    list_select_related = ['master_user', 'user']
    list_filter = ['is_deleted', 'is_owner', 'is_admin']
    raw_id_fields = ['master_user', 'user', 'groups']

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
        fields = ['language', 'timezone']


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


class GroupAdmin(AbstractModelAdmin):
    model = Group
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'name', ]
    list_select_related = ['master_user']
    raw_id_fields = ['master_user']

    # def formfield_for_manytomany(self, db_field, request=None, **kwargs):
    #     if db_field.name == 'permissions':
    #         qs = kwargs.get('queryset', db_field.remote_field.model.objects)
    #         kwargs['queryset'] = qs.select_related('content_type')
    #     return super(GroupAdmin, self).formfield_for_manytomany(db_field, request=request, **kwargs)


admin.site.register(Group, GroupAdmin)


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


class InviteToMasterUserAdmin(AbstractModelAdmin):
    model = InviteToMasterUser
    list_display = ['id', 'user', 'from_member', 'status', 'master_user' ]
    list_select_related = ['user', 'from_member', 'master_user']
    list_filter = ['status', ]
    raw_id_fields = ['user', ]


admin.site.register(InviteToMasterUser, InviteToMasterUserAdmin)
