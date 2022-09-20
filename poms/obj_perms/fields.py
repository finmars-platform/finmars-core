from __future__ import unicode_literals

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from rest_framework.relations import MANY_RELATION_KWARGS

from poms.common.fields import PrimaryKeyRelatedFilteredField
from poms.obj_perms.utils import get_granted_permissions, obj_perms_filter_object_list_for_view, \
    obj_perms_filter_objects_for_view, obj_perms_prefetch, has_view_perms
from poms.users.utils import get_member_from_context


class PermissionField(serializers.SlugRelatedField):
    queryset = Permission.objects

    def __init__(self, **kwargs):
        kwargs['slug_field'] = 'codename'
        super(PermissionField, self).__init__(**kwargs)

    def get_queryset(self):
        content_type = ContentType.objects.get_for_model(self.root.Meta.model)
        qs = super(PermissionField, self).get_queryset()
        return qs.select_related('content_type').filter(content_type=content_type)


class GrantedPermissionField(serializers.ReadOnlyField):
    def get_attribute(self, instance):
        return instance

    def to_representation(self, value):
        member = get_member_from_context(self.context)
        if member:
            perms = get_granted_permissions(member, value)
            return list(perms) if perms else []
        return []


# class GrantedPermission2Field(serializers.ReadOnlyField):
#     def get_attribute(self, instance):
#         return instance
#
#     def to_representation(self, value):
#         member = get_member_from_context(self.context)
#         if member:
#             perms = get_granted_permissions2(member, value)
#             return list(perms) if perms else []
#         return []


class ManyRelatedWithObjectPermissionField(serializers.ManyRelatedField):
    def to_representation(self, iterable):
        member = get_member_from_context(self.context)
        iterable = obj_perms_filter_object_list_for_view(member, iterable)
        return super(ManyRelatedWithObjectPermissionField, self).to_representation(iterable)

    def to_internal_value(self, data):
        res = super(ManyRelatedWithObjectPermissionField, self).to_internal_value(data)
        if data is None:
            return res
        data = set(data)
        instance = self.root.instance
        member = get_member_from_context(self.context)
        if not member.is_superuser and instance:
            # add not visible for current member tag to list...
            # hidden_tags = []
            for t in obj_perms_prefetch(self.get_attribute(instance)):
                if not has_view_perms(member, t) and t.id not in data:
                    data.add(t.id)
                    res.append(t)
        return res


class PrimaryKeyRelatedFilteredWithObjectPermissionField(PrimaryKeyRelatedFilteredField):

    def __new__(cls, *args, **kwargs):
        if kwargs.pop('many', False):
            return cls.tag_many_init(*args, **kwargs)
        return super(PrimaryKeyRelatedFilteredWithObjectPermissionField, cls).__new__(cls, *args, **kwargs)

    @classmethod
    def tag_many_init(cls, *args, **kwargs):
        list_kwargs = {'child_relation': cls(*args, **kwargs)}
        for key in kwargs.keys():
            if key in MANY_RELATION_KWARGS:
                list_kwargs[key] = kwargs[key]
        return ManyRelatedWithObjectPermissionField(**list_kwargs)

    def get_queryset(self):
        queryset = super(PrimaryKeyRelatedFilteredWithObjectPermissionField, self).get_queryset()
        member = get_member_from_context(self.context)
        queryset = obj_perms_filter_objects_for_view(member, queryset)
        # queryset = ObjectPermissionFilter().simple_filter_queryset(member, queryset)
        return queryset
