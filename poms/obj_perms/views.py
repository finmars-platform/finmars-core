from logging import getLogger

from rest_framework.decorators import list_route
from rest_framework.response import Response

from poms.common.views import AbstractModelViewSet, AbstractEvGroupViewSet
from poms.obj_perms.filters import ObjectPermissionBackend
from poms.obj_perms.permissions import PomsObjectPermission
from poms.obj_perms.utils import obj_perms_prefetch

_l = getLogger('poms.obj_perms')


class AbstractWithObjectPermissionViewSet(AbstractModelViewSet):
    # TODO: remove bulk_objects_permissions_serializer_class
    # bulk_objects_permissions_serializer_class = None
    filter_backends = AbstractModelViewSet.filter_backends + [
        ObjectPermissionBackend,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsObjectPermission,
    ]
    # prefetch_permissions_for = []

    # def filter_queryset(self, queryset):
    #     queryset = super(AbstractWithObjectPermissionViewSet, self).filter_queryset(queryset)
    #     if hasattr(self, 'prefetch_permissions_for'):
    #         queryset = obj_perms_prefetch(queryset, lookups_related=self.prefetch_permissions_for)
    #     return queryset

    # def get_serializer_class(self):
    #     # if self.action == 'objects_permissions':
    #     #     return self.bulk_objects_permissions_serializer_class
    #     return super(AbstractWithObjectPermissionViewSet, self).get_serializer_class()

    # def get_serializer(self, *args, **kwargs):
    #     return super(AbstractWithObjectPermissionViewSet, self).get_serializer(*args, **kwargs)

    # @list_route(methods=['POST'], url_path='objects-permissions')
    # def objects_permissions(self, request):
    #     serializer = self.get_serializer(data=request.data)
    #     # serializer.Meta.model = self.serializer_class.Meta.model
    #     serializer.is_valid(raise_exception=True)
    #     serializer.save()
    #     return Response(serializer.data)


class AbstractEvGroupWithObjectPermissionViewSet(AbstractEvGroupViewSet):
    filter_backends = AbstractModelViewSet.filter_backends + [
        ObjectPermissionBackend,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsObjectPermission,
    ]
