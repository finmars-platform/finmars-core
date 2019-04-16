from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import smart_text

from poms.common.fields import SlugRelatedFilteredField

class ComplexImportContentTypeField(SlugRelatedFilteredField):
    queryset = ContentType.objects
    filter_backends = []

    def __init__(self, **kwargs):
        kwargs['slug_field'] = 'model'
        super(ComplexImportContentTypeField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            app_label, model = data.split('.')
            return self.get_queryset().get(app_label=app_label, model=model)
        except ObjectDoesNotExist:
            self.fail('does_not_exist', slug_name=self.slug_field, value=smart_text(data))
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, obj):
        return '%s.%s' % (obj.app_label, obj.model)
