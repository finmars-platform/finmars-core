from rest_framework.filters import BaseFilterBackend
from rest_framework.relations import (
    PrimaryKeyRelatedField,
    SlugRelatedField,
    RelatedField,
)

from poms.common.fields import (
    PrimaryKeyRelatedFilteredField,
    UserCodeOrPrimaryKeyRelatedField,
)
from poms.obj_attrs.filters import OwnerByAttributeTypeFilter
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier
from poms.users.filters import OwnerByMasterUserFilter
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist


class GenericAttributeTypeField(UserCodeOrPrimaryKeyRelatedField):
    queryset = GenericAttributeType.objects.all()
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class GenericClassifierPermissionBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        attribute_type_model = queryset.model._meta.get_field(
            "attribute_type"
        ).related_model
        attribute_type_qs = attribute_type_model.objects.all()
        queryset = queryset.filter(attribute_type__in=attribute_type_qs)
        return queryset


class GenericClassifierField(RelatedField):
    queryset = GenericClassifier.objects
    filter_backends = [
        OwnerByAttributeTypeFilter,
        # GenericClassifierPermissionBackend,
    ]

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        try:
            if isinstance(data, str):
                return queryset.filter(name=data)[
                    0
                ]  # TODO thats strange, investigate and refactor
            else:
                return queryset.get(pk=data)
        except ObjectDoesNotExist:
            self.fail("does_not_exist", slug_name="name", value=str(data))
        except (TypeError, ValueError):
            self.fail("invalid")

    def to_representation(self, obj):
        return getattr(obj, "id")
