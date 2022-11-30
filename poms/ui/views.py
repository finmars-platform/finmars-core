import django_filters
from django_filters.fields import Lookup
from django_filters.rest_framework import FilterSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from poms.common.filters import NoOpFilter, CharFilter, CharExactFilter
from poms.common.mixins import DestroySystemicModelMixin
from poms.common.views import AbstractModelViewSet, AbstractReadOnlyModelViewSet
from poms.ui.models import ListLayout, EditLayout, Bookmark, Configuration, \
    ConfigurationExportLayout, TransactionUserFieldModel, InstrumentUserFieldModel, PortalInterfaceAccessModel, \
    DashboardLayout, TemplateLayout, ContextMenuLayout, EntityTooltip, ColorPalette, CrossEntityAttributeExtension, \
    ColumnSortData
from poms.ui.serializers import ListLayoutSerializer, \
    EditLayoutSerializer, BookmarkSerializer, ConfigurationSerializer, ConfigurationExportLayoutSerializer, \
    TransactionUserFieldSerializer, InstrumentUserFieldSerializer, PortalInterfaceAccessModelSerializer, \
    DashboardLayoutSerializer, TemplateLayoutSerializer, ContextMenuLayoutSerializer, EntityTooltipSerializer, \
    ColorPaletteSerializer, ListLayoutLightSerializer, DashboardLayoutLightSerializer, \
    CrossEntityAttributeExtensionSerializer, ColumnSortDataSerializer
from poms.users.filters import OwnerByMasterUserFilter, OwnerByMemberFilter


class LayoutContentTypeFilter(django_filters.CharFilter):
    def filter(self, qs, value):

        print("hello? %s" % value)

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


class ColorPaletteFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()
    user_code = CharFilter()

    class Meta:
        model = ColorPalette
        fields = []


class ColorPaletteViewSet(AbstractModelViewSet):
    queryset = ColorPalette.objects.select_related(
        'master_user',
    )
    serializer_class = ColorPaletteSerializer
    filter_class = ColorPaletteFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]


class EntityTooltipFilterSet(FilterSet):
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
    filter_class = EntityTooltipFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]


class CrossEntityAttributeExtensionFilterSet(FilterSet):
    id = NoOpFilter()

    content_type = LayoutContentTypeFilter()

    class Meta:
        model = CrossEntityAttributeExtension
        fields = []


class CrossEntityAttributeExtensionViewSet(AbstractModelViewSet):
    queryset = CrossEntityAttributeExtension.objects.select_related(
        'master_user',
    )
    serializer_class = CrossEntityAttributeExtensionSerializer
    filter_class = CrossEntityAttributeExtensionFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]


class ColumnSortDataFilterSet(FilterSet):
    id = NoOpFilter()

    name = CharFilter()
    user_code = CharFilter()
    column_key = CharFilter()

    is_common = django_filters.BooleanFilter()

    class Meta:
        model = ColumnSortData
        fields = []


class ColumnSortDataViewSet(AbstractModelViewSet):
    queryset = ColumnSortData.objects.select_related(
        'member',
    )
    serializer_class = ColumnSortDataSerializer
    filter_class = ColumnSortDataFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMemberFilter,
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
    user_code = CharFilter()
    type = CharFilter()

    class Meta:
        model = ContextMenuLayout
        fields = []


class ContextMenuLayoutViewSet(AbstractModelViewSet):
    queryset = ContextMenuLayout.objects.select_related(
        'member'
    )
    serializer_class = ContextMenuLayoutSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMemberFilter,
    ]
    filter_class = ContextMenuLayoutFilterSet

    @action(detail=True, methods=['get'], url_path='ping')
    def ping(self, request, pk=None):
        layout = self.get_object()

        return Response({
            "id": layout.id,
            "modified": layout.modified,
            "is_default": layout.is_default
        })


class ListLayoutFilterSet(FilterSet):
    id = NoOpFilter()
    is_default = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    name = CharFilter()
    # user_code = CharFilter()
    user_code = CharExactFilter()
    content_type = LayoutContentTypeFilter()

    class Meta:
        model = ListLayout
        fields = ['content_type', 'name']


class ListLayoutViewSet(AbstractModelViewSet, DestroySystemicModelMixin):
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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='ping')
    def ping(self, request, pk=None):
        layout = self.get_object()

        return Response({
            "id": layout.id,
            "modified": layout.modified,
            "is_default": layout.is_default
        })


class ListLayoutLightViewSet(AbstractModelViewSet):
    queryset = ListLayout.objects.select_related(
        'member',
        'content_type'
    )
    serializer_class = ListLayoutLightSerializer
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

    @action(detail=True, methods=['get'], url_path='ping')
    def ping(self, request, pk=None):
        layout = self.get_object()

        return Response({
            "id": layout.id,
            "modified": layout.modified,
            "is_default": layout.is_default
        })


class DashboardLayoutLightViewSet(AbstractModelViewSet):
    queryset = DashboardLayout.objects.select_related(
        'member'
    )
    serializer_class = DashboardLayoutLightSerializer
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

    @action(detail=True, methods=['get'], url_path='ping')
    def ping(self, request, pk=None):
        layout = self.get_object()

        return Response({
            "id": layout.id,
            "modified": layout.modified,
            "is_default": layout.is_default
        })


class EditLayoutFilterSet(FilterSet):
    id = NoOpFilter()
    content_type = LayoutContentTypeFilter()
    is_default = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    name = CharFilter()
    user_code = CharFilter()

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

    @action(detail=True, methods=['get'], url_path='ping')
    def ping(self, request, pk=None):
        layout = self.get_object()

        return Response({
            "id": layout.id,
            "modified": layout.modified,
            "is_default": layout.is_default
        })


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
