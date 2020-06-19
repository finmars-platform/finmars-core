import django_filters
from django_filters.fields import Lookup
from django_filters.rest_framework import FilterSet

from poms.common.filters import NoOpFilter, CharFilter
from poms.common.views import AbstractModelViewSet, AbstractReadOnlyModelViewSet
from poms.ui.models import ListLayout, EditLayout, Bookmark, Configuration, \
    ConfigurationExportLayout, TransactionUserFieldModel, InstrumentUserFieldModel, PortalInterfaceAccessModel, \
    DashboardLayout, TemplateLayout, ContextMenuLayout, EntityTooltip
from poms.ui.serializers import ListLayoutSerializer, \
    EditLayoutSerializer, BookmarkSerializer, ConfigurationSerializer, ConfigurationExportLayoutSerializer, \
    TransactionUserFieldSerializer, InstrumentUserFieldSerializer, PortalInterfaceAccessModelSerializer, \
    DashboardLayoutSerializer, TemplateLayoutSerializer, ContextMenuLayoutSerializer, EntityTooltipSerializer
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


class PortalInterfaceAccessViewSet(AbstractReadOnlyModelViewSet):
    queryset = PortalInterfaceAccessModel.objects
    serializer_class = PortalInterfaceAccessModelSerializer
    pagination_class = None


class TransactionUserFieldViewSet(AbstractModelViewSet):
    queryset = TransactionUserFieldModel.objects.select_related(
        'master_user',
    )
    serializer_class = TransactionUserFieldSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]


class TemplateLayoutFilterSet(FilterSet):
    id = NoOpFilter()

    content_type = LayoutContentTypeFilter()

    class Meta:
        model = EntityTooltip
        fields = []


class EntityTooltipViewSet(AbstractModelViewSet):
    queryset = EntityTooltip.objects.select_related(
        'master_user',
    )
    serializer_class = EntityTooltipSerializer
    filter_class = TemplateLayoutFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]


class InstrumentUserFieldViewSet(AbstractModelViewSet):
    queryset = InstrumentUserFieldModel.objects.select_related(
        'master_user',
    )
    serializer_class = InstrumentUserFieldSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]


class TemplateLayoutFilterSet(FilterSet):
    id = NoOpFilter()
    is_default = django_filters.BooleanFilter()
    name = CharFilter()
    type = CharFilter()

    class Meta:
        model = TemplateLayout
        fields = []


class TemplateLayoutViewSet(AbstractModelViewSet):
    queryset = TemplateLayout.objects.select_related(
        'member',
    )
    serializer_class = TemplateLayoutSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMemberFilter,
    ]
    filter_class = TemplateLayoutFilterSet
    ordering_fields = [
     'name', 'is_default',
    ]


class ContextMenuLayoutFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()

    class Meta:
        model = ContextMenuLayout
        fields = []


class ContextMenuLayoutViewSet(AbstractModelViewSet):
    queryset = ContextMenuLayout.objects
    serializer_class = ContextMenuLayoutSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMemberFilter,
    ]
    filter_class = ContextMenuLayoutFilterSet
    permission_classes = AbstractModelViewSet.permission_classes + [
        SuperUserOnly,
    ]
    ordering_fields = [
        'type', 'name',
    ]

class ListLayoutFilterSet(FilterSet):
    id = NoOpFilter()
    is_default = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
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


class DashboardLayoutFilterSet(FilterSet):
    id = NoOpFilter()
    is_default = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    name = CharFilter()

    class Meta:
        model = DashboardLayout
        fields = []


class DashboardLayoutViewSet(AbstractModelViewSet):
    queryset = DashboardLayout.objects.select_related(
        'member'
    )
    serializer_class = DashboardLayoutSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMemberFilter,
    ]
    filter_class = DashboardLayoutFilterSet
    ordering_fields = ['name', 'is_default'
    ]


class ConfigurationExportLayoutFilterSet(FilterSet):
    id = NoOpFilter()
    is_default = django_filters.BooleanFilter()
    name = CharFilter()

    class Meta:
        model = ConfigurationExportLayout
        fields = []


class ConfigurationExportLayoutViewSet(AbstractModelViewSet):
    queryset = ConfigurationExportLayout.objects.select_related(
        'member',
    )
    serializer_class = ConfigurationExportLayoutSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMemberFilter,
    ]
    filter_class = ConfigurationExportLayoutFilterSet
    ordering_fields = [
        'name', 'is_default'
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
