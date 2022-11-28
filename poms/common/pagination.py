import logging
import sys
import time

from django.core.paginator import InvalidPage
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.settings import api_settings

_l = logging.getLogger('poms.common')


def _positive_int(integer_string, strict=False, cutoff=None):
    """
    Cast a string to a strictly positive integer.
    """
    ret = int(integer_string)
    if ret < 0 or (ret == 0 and strict):
        raise ValueError()
    if cutoff:
        ret = min(ret, cutoff)
    return ret


class PageNumberPaginationExt(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = api_settings.PAGE_SIZE * 10

    def post_paginate_queryset(self, queryset, request, view=None):

        start_time = time.time()

        page_size = request.data.get('page_size', self.page_size)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = request.data.get('page', 1)
        if page_number in self.last_page_strings:
            page_number = paginator.num_pages

        # _l.debug('post_paginate_queryset page_number %s' % page_number)
        # _l.debug('post_paginate_queryset page_size %s' % page_size)
        # _l.debug('post_paginate_queryset django_paginator_class %s' % self.django_paginator_class)

        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=str(exc)
            )
            raise NotFound(msg)

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request

        _l.debug('post_paginate_queryset before list page')

        list_page_st = time.perf_counter()

        res = list(self.page)

        _l.debug('res %s' % len(res))

        _l.debug('post_paginate_queryset list page done: %s', "{:3.3f}".format(time.perf_counter() - list_page_st))

        return res


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
