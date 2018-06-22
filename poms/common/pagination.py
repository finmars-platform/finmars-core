import sys

from rest_framework.pagination import PageNumberPagination
from rest_framework.settings import api_settings


class PageNumberPaginationExt(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = api_settings.PAGE_SIZE * 10


class BigPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = sys.maxsize
    page_size = sys.maxsize


class CustomPaginationMixin(object):

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination
        is disabled.
        """
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(
            queryset, self.request, view=self)

    def get_paginated_response(self, data):
        """
        Return a paginated style `Response` object for the given
        output data.
        """
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)