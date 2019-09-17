from __future__ import unicode_literals

from django_filters.rest_framework import FilterSet

from poms.common.filters import CharFilter, NoOpFilter
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionGroupFilter, \
    ObjectPermissionPermissionFilter
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet
from poms.tags.filters import TagContentTypeFilter
from poms.tags.models import Tag
from poms.tags.serializers import TagSerializer
from poms.users.filters import OwnerByMasterUserFilter


class TagFilterSet(FilterSet):
    id = NoOpFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    content_type = TagContentTypeFilter(field_name='content_types')
    member = ObjectPermissionMemberFilter(object_permission_model=Tag)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Tag)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Tag)

    class Meta:
        model = Tag
        fields = []


class TagViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Tag.objects.prefetch_related(
        'content_types',
        *get_permissions_prefetch_lookups((None, Tag))
    )
    serializer_class = TagSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = TagFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]
