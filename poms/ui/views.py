import django_filters
from django_filters.fields import Lookup
from rest_framework.filters import FilterSet

from poms.common.filters import NoOpFilter, CharFilter
from poms.common.views import AbstractModelViewSet
from poms.ui.models import TemplateListLayout, TemplateEditLayout, ListLayout, EditLayout, Bookmark, Configuration
from poms.ui.serializers import TemplateListLayoutSerializer, ListLayoutSerializer, TemplateEditLayoutSerializer, \
    EditLayoutSerializer, BookmarkSerializer, ConfigurationSerializer
from poms.users.filters import OwnerByMasterUserFilter, OwnerByMemberFilter
from poms.users.permissions import SuperUserOnly


class LayoutContentTypeFilter(django_filters.CharFilter):
    def filter(self, qs, value):
        if isinstance(value, Lookup):
            lookup = str(value.lookup_type)
            value = value.value
        else:
            lookup = self.lookup_expr
        if value in ([], (), {}, None, ''):
            return qs
        if self.distinct:
            qs = qs.distinct()
        try:
            app_label, model = value.split('.', maxsplit=1)
        except ValueError:
            # skip on invalid value
            app_label, model = '', ''
        qs = self.get_method(qs)(**{
            'content_type__app_label': app_label,
            'content_type__model__%s' % lookup: model,
        })
        return qs


class TemplateListLayoutFilterSet(FilterSet):
    id = NoOpFilter()
    is_default = django_filters.BooleanFilter()
    name = CharFilter()
    content_type = LayoutContentTypeFilter()

    class Meta:
        model = TemplateListLayout
        fields = []


class TemplateListLayoutViewSet(AbstractModelViewSet):
    queryset = TemplateListLayout.objects.select_related(
        'master_user',
        'content_type'
    )
    serializer_class = TemplateListLayoutSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = TemplateListLayoutFilterSet
    permission_classes = AbstractModelViewSet.permission_classes + [
        SuperUserOnly,
    ]
    ordering_fields = [
        'content_type', 'name', 'is_default',
    ]


class TemplateEditLayoutFilterSet(FilterSet):
    id = NoOpFilter()
    content_type = LayoutContentTypeFilter()

    class Meta:
        model = TemplateEditLayout
        fields = []


class TemplateEditLayoutViewSet(AbstractModelViewSet):
    queryset = TemplateEditLayout.objects.select_related(
        'master_user',
        'content_type'
    )
    serializer_class = TemplateEditLayoutSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        SuperUserOnly,
    ]
    filter_class = TemplateEditLayoutFilterSet
    ordering_fields = [
        'content_type', 'name',
    ]


class ListLayoutFilterSet(FilterSet):
    id = NoOpFilter()
    is_default = django_filters.BooleanFilter()
    name = CharFilter()
    content_type = LayoutContentTypeFilter()

    class Meta:
        model = ListLayout
        fields = []


class ListLayoutViewSet(AbstractModelViewSet):
    queryset = ListLayout.objects.select_related(
        'member',
        'content_type'
    )
    serializer_class = ListLayoutSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMemberFilter,
    ]
    filter_class = ListLayoutFilterSet
    ordering_fields = [
        'content_type', 'name', 'is_default'
    ]


class EditLayoutFilterSet(FilterSet):
    id = NoOpFilter()
    content_type = LayoutContentTypeFilter()

    class Meta:
        model = EditLayout
        fields = []


class EditLayoutViewSet(AbstractModelViewSet):
    queryset = EditLayout.objects.select_related(
        'member',
        'content_type'
    )
    serializer_class = EditLayoutSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMemberFilter,
    ]
    filter_class = EditLayoutFilterSet
    ordering_fields = [
        'content_type',
    ]


class BookmarkFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = Bookmark
        fields = []


class BookmarkViewSet(AbstractModelViewSet):
    queryset = Bookmark.objects.prefetch_related(
        'member',
        'list_layout',
        'list_layout__content_type',
        'parent',
        'children',
    ).filter(parent__isnull=True)
    serializer_class = BookmarkSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMemberFilter,
    ]
    filter_class = BookmarkFilterSet
    ordering_fields = [
        'name',
        'position',
    ]


class ConfigurationFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = Configuration
        fields = []


class ConfigurationViewSet(AbstractModelViewSet):
    queryset = Configuration.objects.prefetch_related(
        'master_user',
    )
    serializer_class = ConfigurationSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = ConfigurationFilterSet
    ordering_fields = [
        'name',
    ]
