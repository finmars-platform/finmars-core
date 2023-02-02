from __future__ import unicode_literals

from rest_framework import permissions
from rest_framework.views import APIView

from poms.audit import history


class HistoricalModelMixin(APIView):
    pass
    # TODO DEPRECATED OR REQUIRE REFACTOR
    # def dispatch(self, request, *args, **kwargs):
    #     if request.method.upper() in permissions.SAFE_METHODS:
    #         return super(HistoricalModelMixin, self).dispatch(request, *args, **kwargs)
    #     with history.enable():
    #         return super(HistoricalModelMixin, self).dispatch(request, *args, **kwargs)
    #
    # @history.enable
    # def perform_create(self, serializer):
    #     history.set_flag_addition()
    #     super(HistoricalModelMixin, self).perform_create(serializer)
    #     history.set_actor_content_object(serializer.instance)
    #
    # @history.enable
    # def perform_update(self, serializer):
    #     history.set_flag_change()
    #     history.set_actor_content_object(serializer.instance)
    #     super(HistoricalModelMixin, self).perform_update(serializer)
    #
    # @history.enable
    # def perform_destroy(self, instance):
    #     history.set_flag_deletion()
    #     history.set_actor_content_object(instance)
    #     super(HistoricalModelMixin, self).perform_destroy(instance)
