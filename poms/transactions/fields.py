import json
import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import ReadOnlyField
from rest_framework.relations import RelatedField

from poms.common.fields import (
    SlugRelatedFilteredField,
    UserCodeOrPrimaryKeyRelatedField,
)
from poms.transactions.filters import TransactionTypeInputContentTypeFilter
from poms.transactions.models import (
    TransactionType,
    TransactionTypeGroup,
    TransactionTypeInput,
)
from poms.users.filters import OwnerByMasterUserFilter

_l = logging.getLogger("poms.transactions")


class TransactionTypeGroupField(UserCodeOrPrimaryKeyRelatedField):
    queryset = TransactionTypeGroup.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]

    def to_internal_value(self, value):
        queryset = self.get_queryset()
        try:
            if isinstance(value, str):
                return queryset.get(user_code=value).user_code
            else:
                return queryset.get(pk=value).user_code
        except Exception:
            return value
        # except ObjectDoesNotExist:
        #     self.fail("does_not_exist", value=str(data))
        # except (TypeError, ValueError):
        #     self.fail("invalid")

    def to_representation(self, obj):
        try:
            queryset = self.get_queryset()

            return queryset.get(user_code=obj).id

        except Exception:
            # TODO on frontend do case that user_code instead of id
            return obj


class TransactionTypeField(UserCodeOrPrimaryKeyRelatedField):
    queryset = TransactionType.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class TransactionTypeInputField(RelatedField):
    default_error_messages = {
        "does_not_exist": _("Object with user_code or id that equals {value} does not exist."),
        "invalid": _("Invalid value."),
    }

    queryset = TransactionTypeInput.objects

    def get_queryset(self):
        return super().get_queryset()

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        try:
            if isinstance(data, str):
                return queryset.get(name=data)
            else:
                return queryset.get(pk=data)
        except ObjectDoesNotExist:
            self.fail("does_not_exist", slug_name="name", value=str(data))
        except (TypeError, ValueError):
            self.fail("invalid")

    def to_representation(self, obj):
        return obj.id


class TransactionTypeInputContentTypeField(SlugRelatedFilteredField):
    queryset = ContentType.objects
    filter_backends = [TransactionTypeInputContentTypeFilter]

    def __init__(self, **kwargs):
        kwargs["slug_field"] = "model"
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            app_label, model = data.split(".")

            return ContentType.objects.all().get(app_label=app_label, model=model)

        except ObjectDoesNotExist:
            self.fail("does_not_exist", slug_name=self.slug_field, value=force_str(data))
        except (TypeError, ValueError):
            self.fail("invalid")

    def to_representation(self, obj):
        return f"{obj.app_label}.{obj.model}"


class ReadOnlyContentTypeField(ReadOnlyField):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_representation(self, obj):
        return f"{obj.app_label}.{obj.model}"


class CharOrJSONField(serializers.CharField):
    def to_representation(self, value):
        # Try to parse string to JSON
        if isinstance(value, str):
            try:
                val = json.loads(value)
                # _l.info("CharOrJSONField to_representation %s" % val)
                return val
            except json.JSONDecodeError:
                pass
        return value

    def to_internal_value(self, data):
        # Accept dicts and convert to JSON string
        if isinstance(data, dict):
            return json.dumps(data)
        return super().to_internal_value(data)
