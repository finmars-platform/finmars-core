import logging

from rest_framework.filters import BaseFilterBackend

from finmars_iam.utils import filter_queryset_with_access_policies

_l = logging.getLogger('finmars_iam')


class ObjectPermissionBackend(BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):

        # _l.info('ObjectPermissionBackend.filter_queryset.request %s' % request)

        result = filter_queryset_with_access_policies(request.user, queryset)

        # _l.info('ObjectPermissionBackend.filter_queryset after access filter: %s' % result.count())

        return result
