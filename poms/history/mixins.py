from __future__ import unicode_literals

import logging

from django.contrib.contenttypes.models import ContentType
from rest_framework.views import APIView

from poms.history.models import HistoricalRecord

_l = logging.getLogger('poms.history')


class HistoryMixin(APIView):

    def save_change_in_history(self, serializer):

        try:

            _l.info('save_change_in_history.serializer.validated_data %s' % serializer.validated_data)

            user_code = None

            if serializer.data.get('transaction_unique_code', None):
                user_code = serializer.data['transaction_unique_code']
            elif serializer.data.get('code', None):
                user_code = serializer.data['code']
            elif serializer.data.get('user_code', None):
                user_code = serializer.data['user_code']

            if user_code:

                HistoricalRecord.objects.create(
                    master_user=self.request.user.master_user,
                    member=self.request.user.member,
                    data=serializer.data,
                    user_code=serializer.data['user_code'],
                    content_type=ContentType.objects.get_for_model(serializer.Meta.model)
                )
            else:
                _l.error("Could not save history unique code is not defined. Content Type %s" % (
                    str(ContentType.objects.get_for_model(serializer.Meta.model))))

        except Exception as e:
            _l.error("Could not save history %s" % e)

    def dispatch(self, request, *args, **kwargs):
        return super(HistoryMixin, self).dispatch(request, *args, **kwargs)

    def perform_create(self, serializer):

        super(HistoryMixin, self).perform_create(serializer)

        self.save_change_in_history(serializer)

    def perform_update(self, serializer):

        super(HistoryMixin, self).perform_update(serializer)

        self.save_change_in_history(serializer)

    def perform_destroy(self, instance):
        # TODO what do with history on delete?
        super(HistoryMixin, self).perform_destroy(instance)
