from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters import MultipleChoiceFilter
from rest_framework.filters import BaseFilterBackend


class NotificationFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        queryset = queryset.filter(
            recipient=request.user
        ).filter(
            Q(recipient_member__isnull=True) | Q(recipient_member=request.user.member)
        )
        if request.GET.get('all') in ['1', 'true', 'yes']:
            return queryset
        else:
            return queryset.filter(read_date__isnull=True)


def notification_content_type_choices():
    queryset = ContentType.objects.all().order_by('app_label', 'model')
    for c in queryset:
        if c.model_class():
            yield '%s.%s' % (c.app_label, c.model), c.model_class()._meta.verbose_name


class NotificationContentTypeMultipleChoiceFilter(MultipleChoiceFilter):
    def __init__(self, *args, **kwargs):
        # queryset = ContentType.objects.all().order_by('app_label', 'model').filter(
        #     pk__in=get_history_model_content_type_list())
        # kwargs['choices'] = lambda: [('%s.%s' % (c.app_label, c.model), c.model_class()._meta.verbose_name)
        #                      for c in queryset]
        kwargs['choices'] = notification_content_type_choices
        super(NotificationContentTypeMultipleChoiceFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        value = value or tuple()
        cvalue = []
        for v in value:
            ctype = v.split('.')
            ctype = ContentType.objects.get_by_natural_key(*ctype)
            cvalue.append(ctype.id)
        return super(NotificationContentTypeMultipleChoiceFilter, self).filter(qs, cvalue)
