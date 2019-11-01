import django_filters
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

from poms.common.filters import ModelExtMultipleChoiceFilter
from poms.obj_perms.models import GenericObjectPermission
from poms.obj_perms.utils import obj_perms_filter_objects, get_all_perms
from poms.users.models import Member, Group


class AllFakeFilter(django_filters.Filter):
    field_class = forms.ChoiceField

    def __init__(self, *args, **kwargs):
        kwargs['choices'] = (
            (0, '0: Granted only'),
            (1, '1: Show all'),
        )
        super(AllFakeFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        return qs


class ObjectPermissionBackend(BaseFilterBackend):
    codename_set = ['view_%(model_name)s', 'change_%(model_name)s', 'manage_%(model_name)s', 'view_%(model_name)s_show_parameters', 'view_%(model_name)s_hide_parameters']

    def get_codename_set(self, model_cls):
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }
        return {perm % kwargs for perm in self.codename_set}

    def filter_queryset(self, request, queryset, view):

        # print('ObjectPermissionBackend.filter_queryset %s' % view.action)

        if view and view.action == 'retrieve':
            # any object can'be loaded even if not permission
            # result must be filtered in the serializer
            # return obj_perms_prefetch(queryset)
            return queryset

        return obj_perms_filter_objects(request.user.member, self.get_codename_set(queryset.model), queryset,
                                        prefetch=False)


class ObjectPermissionMemberFilter(ModelExtMultipleChoiceFilter):
    model = Member
    field_name = 'username'
    master_user_path = 'master_user'

    def __init__(self, *args, **kwargs):
        self.object_permission_model = kwargs.pop('object_permission_model')
        super(ObjectPermissionMemberFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        value = value or ()
        if self.is_noop(qs, value):
            return qs
        if not value:
            return qs
        value = set(value)

        # qs = qs.filter(self.get_user_filter_q(value) | self.get_group_filter_q(value))
        qs = qs.filter(self.get_permission_filter(value))

        if self.distinct:
            return qs.distinct()
        return qs

    # def get_user_filter_q(self, value):
    #     user_lookup_name, user_obj_perms_model = get_user_obj_perms_model(self.object_permission_model)
    #     return Q(pk__in=user_obj_perms_model.objects.filter(member__in=value).values_list(
    #         'content_object__id', flat=True))
    #
    # def get_group_filter_q(self, value):
    #     group_lookup_name, group_obj_perms_model = get_group_obj_perms_model(self.object_permission_model)
    #     return Q(pk__in=group_obj_perms_model.objects.filter(group__members__in=value).values_list(
    #         'content_object__id', flat=True))

    def get_permission_filter(self, value):
        ctype = ContentType.objects.get_for_model(self.object_permission_model)
        return Q(
            pk__in=GenericObjectPermission.objects.filter(
                content_type=ctype, permission__content_type=ctype,
            ).filter(
                Q(member__in=value) | Q(group__members__in=value)
            ).values_list('object_id', flat=True)
        )


class ObjectPermissionGroupFilter(ModelExtMultipleChoiceFilter):
    model = Group
    field_name = 'name'
    master_user_path = 'master_user'

    def __init__(self, *args, **kwargs):
        self.object_permission_model = kwargs.pop('object_permission_model')
        super(ObjectPermissionGroupFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        value = value or ()
        if self.is_noop(qs, value):
            return qs
        if not value:
            return qs
        value = set(value)

        # qs = qs.filter(self.get_user_filter_q(value) | self.get_group_filter_q(value))
        qs = qs.filter(self.get_permission_filter(value))

        if self.distinct:
            return qs.distinct()
        return qs

    # def get_user_filter_q(self, value):
    #     user_lookup_name, user_obj_perms_model = get_user_obj_perms_model(self.object_permission_model)
    #     return Q(pk__in=user_obj_perms_model.objects.filter(member__groups__in=value).values_list(
    #         'content_object__id', flat=True))
    #
    # def get_group_filter_q(self, value):
    #     group_lookup_name, group_obj_perms_model = get_group_obj_perms_model(self.object_permission_model)
    #     return Q(pk__in=group_obj_perms_model.objects.filter(group__in=value).values_list(
    #         'content_object__id', flat=True))

    def get_permission_filter(self, value):
        ctype = ContentType.objects.get_for_model(self.object_permission_model)
        return Q(
            pk__in=GenericObjectPermission.objects.filter(
                content_type=ctype, permission__content_type=ctype,
            ).filter(
                Q(member__groups__in=value) | Q(group__in=value)
            ).values_list('object_id', flat=True)
        )


class ObjectPermissionPermissionFilter(django_filters.MultipleChoiceFilter):
    def __init__(self, *args, **kwargs):
        self.object_permission_model = kwargs.pop('object_permission_model')
        kwargs['choices'] = [(p, p) for p in get_all_perms(self.object_permission_model)]
        super(ObjectPermissionPermissionFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        value = value or ()
        if self.is_noop(qs, value):
            return qs
        if not value:
            return qs
        value = set(value)

        # qs = qs.filter(self.get_user_filter_q(value) | self.get_group_filter_q(value))
        qs = qs.filter(self.get_permission_filter(value))

        ctype = ContentType.objects.get_for_model(self.object_permission_model)
        qs = qs.filter(
            pk__in=GenericObjectPermission.objects.filter(
                content_type=ctype, permission__content_type=ctype,
                permission__codename__in=value
            ).values_list('object_id', flat=True)
        )
        if self.distinct:
            return qs.distinct()
        return qs

    # def get_user_filter_q(self, value):
    #     user_lookup_name, user_obj_perms_model = get_user_obj_perms_model(self.object_permission_model)
    #     return Q(pk__in=user_obj_perms_model.objects.filter(permission__codename__in=value).values_list(
    #         'content_object__id', flat=True))
    #
    # def get_group_filter_q(self, value):
    #     group_lookup_name, group_obj_perms_model = get_group_obj_perms_model(self.object_permission_model)
    #     return Q(pk__in=group_obj_perms_model.objects.filter(permission__codename__in=value).values_list(
    #         'content_object__id', flat=True))

    def get_permission_filter(self, value):
        ctype = ContentType.objects.get_for_model(self.object_permission_model)
        return Q(
            pk__in=GenericObjectPermission.objects.filter(
                content_type=ctype, permission__content_type=ctype,
                permission__codename__in=value
            ).values_list('object_id', flat=True)
        )
