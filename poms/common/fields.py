import contextlib

from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import ISO_8601
from rest_framework.exceptions import ValidationError
from rest_framework.fields import (
    CharField,
    DateTimeField,
    FloatField,
    empty,
)
from rest_framework.relations import (
    PrimaryKeyRelatedField,
    RelatedField,
    SlugRelatedField,
)

from poms.expressions_engine import formula
from poms.iam.fields import IamProtectedRelatedField


def default_empty_list():
    return []


name_validator = RegexValidator(
    regex=r"\A[a-zA-Z0-9_]+\Z",
    message=("Invalid name. May only contain letters, digits, or underscores."),
)


class PrimaryKeyRelatedFilteredField(PrimaryKeyRelatedField):
    filter_backends = None

    def __init__(self, filter_backends=None, **kwargs):
        if filter_backends:
            self.filter_backends = filter_backends
        super().__init__(**kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = self.filter_queryset(queryset)
        return queryset

    def filter_queryset(self, queryset):
        if self.filter_backends:
            request = self.context["request"]
            for backend in self.filter_backends:
                queryset = backend().filter_queryset(request, queryset, None)
        return queryset

    def to_representation(self, value):
        try:
            if self.pk_field is not None:
                return self.pk_field.to_representation(value.pk)
            return value.pk

        except Exception:
            if type(value) == dict:
                return value["pk"]


class SlugRelatedFilteredField(SlugRelatedField):
    filter_backends = None

    def __init__(self, filter_backends=None, **kwargs):
        if filter_backends:
            self.filter_backends = filter_backends
        super().__init__(**kwargs)

    def get_queryset(self):
        queryset = super(SlugRelatedFilteredField, self).get_queryset()
        queryset = self.filter_queryset(queryset)
        return queryset

    def filter_queryset(self, queryset):
        if self.filter_backends:
            request = self.context["request"]
            for backend in self.filter_backends:
                queryset = backend().filter_queryset(request, queryset, None)
        return queryset


class UserCodeOrPrimaryKeyRelatedField(IamProtectedRelatedField):
    default_error_messages = {
        "does_not_exist": _(
            "Object with user_code or id that equals {value} does not exist."
        ),
        "invalid": _("Invalid value."),
    }

    def to_internal_value(self, value):
        queryset = self.get_queryset()
        try:
            if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
                return queryset.get(pk=int(value))
            else:
                return queryset.get(user_code=value)

        except ObjectDoesNotExist:
            self.fail("does_not_exist", value=str(value))

        except (TypeError, ValueError):
            self.fail("invalid", value=str(value))

    def to_representation(self, obj):
        return getattr(obj, "id")
        # return getattr(obj, 'user_code') # TODO someday move to user_code completely


class UserCodeField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 255
        kwargs["required"] = False
        kwargs["allow_null"] = True
        kwargs["allow_blank"] = True
        super().__init__(**kwargs)

    def to_internal_value(self, data: str) -> str:
        validated_data = super().to_internal_value(data)

        # 2025-04-23 sz discuss later
        # if validated_data and not validated_data[0].isalpha():
        #     raise ValidationError("user_code must start with a letter")

        return validated_data


class DateTimeTzAwareField(DateTimeField):
    format = "%Y-%m-%dT%H:%M:%S%z"
    input_formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        ISO_8601,
    ]

    def to_representation(self, value):
        value = timezone.localtime(value)
        return super().to_representation(value)


class ExpressionField(CharField):
    def __init__(self, **kwargs):
        kwargs["allow_null"] = kwargs.get("allow_null", False)
        kwargs["allow_blank"] = kwargs.get("allow_blank", False)
        super().__init__(**kwargs)


class Expression2Field(CharField):
    def __init__(self, **kwargs):
        kwargs["allow_null"] = kwargs.get("allow_null", False)
        kwargs["allow_blank"] = kwargs.get("allow_blank", False)
        super().__init__(**kwargs)

    def run_validation(self, data=empty):
        return super().run_validation(data)


class FloatEvalField(FloatField):
    def run_validation(self, data=empty):
        value = super().run_validation(data)
        if data is not None:
            expr = str(data)
            formula.validate(expr)
        return value

    def to_internal_value(self, data):
        with contextlib.suppress(ValidationError):
            return super().to_internal_value(data)

        if data is not None:
            try:
                expr = str(data)
                return formula.safe_eval(expr, context=self.context)
            except (formula.InvalidExpression, ArithmeticError) as e:
                raise ValidationError(_("Invalid expression.")) from e


class ContentTypeOrPrimaryKeyRelatedField(RelatedField):
    queryset = ContentType.objects

    def to_internal_value(self, data):
        try:
            if not isinstance(data, str):
                return self.queryset.get(pk=data)

            pieces = data.split(".")

            return self.queryset.get(app_label=pieces[0], model=pieces[1])
        except ObjectDoesNotExist:
            self.fail("does_not_exist", slug_name="user_code", value=str(data))
        except (TypeError, ValueError):
            self.fail("invalid")

    def to_representation(self, obj):
        return getattr(obj, "id")


class ResourceGroupsField(ArrayField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("base_field", models.CharField(max_length=1024))
        kwargs.setdefault("default", default_empty_list)
        kwargs.setdefault(
            "verbose_name",
            _("list of resource groups user_codes, to which obj belongs"),
        )
        super().__init__(*args, **kwargs)
