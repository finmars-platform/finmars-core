from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import force_str

from poms.common.fields import PrimaryKeyRelatedFilteredField, SlugRelatedFilteredField
from poms.ui.filters import LayoutContentTypeFilter
from poms.ui.models import EditLayout, ListLayout
from poms.users.filters import OwnerByMemberFilter


class LayoutContentTypeField(SlugRelatedFilteredField):
    queryset = ContentType.objects
    filter_backends = [LayoutContentTypeFilter]

    def __init__(self, **kwargs):
        kwargs["slug_field"] = "model"
        super(LayoutContentTypeField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            app_label, model = data.split(".")
            return ContentType.objects.get(app_label=app_label, model=model)
        except ObjectDoesNotExist:
            self.fail(
                "does_not_exist", slug_name=self.slug_field, value=force_str(data)
            )
        except (TypeError, ValueError):
            self.fail("invalid")

    def to_representation(self, obj):
        return "%s.%s" % (obj.app_label, obj.model)


class ListLayoutField(PrimaryKeyRelatedFilteredField):
    queryset = ListLayout.objects
    filter_backends = (OwnerByMemberFilter,)


class EditLayoutField(PrimaryKeyRelatedFilteredField):
    queryset = EditLayout.objects
    filter_backends = (OwnerByMemberFilter,)
