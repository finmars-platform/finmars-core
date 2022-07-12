from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_str

from poms.audit.filters import ObjectHistoryContentTypeFilter
from poms.common.fields import SlugRelatedFilteredField


class ObjectHistoryContentTypeField(SlugRelatedFilteredField):
    queryset = ContentType.objects
    filter_backends = [
        ObjectHistoryContentTypeFilter
    ]

    def __init__(self, **kwargs):
        kwargs['slug_field'] = 'model'
        super(ObjectHistoryContentTypeField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            app_label, model = data.split('.')
            return self.get_queryset().get(app_label=app_label, model=model)
        except ObjectHistoryContentTypeField:
            self.fail('does_not_exist', slug_name=self.slug_field, value=force_str(data))
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, obj):
        return '%s.%s' % (obj.app_label, obj.model)
