from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.translation import gettext_lazy
from rest_framework import ISO_8601
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField, DateTimeField, FloatField, empty, RegexField
from rest_framework.relations import PrimaryKeyRelatedField, SlugRelatedField, RelatedField
from django.contrib.contenttypes.models import ContentType
from poms.common import formula
from poms.iam.fields import IamProtectedRelatedField


class PrimaryKeyRelatedFilteredField(PrimaryKeyRelatedField):
    filter_backends = None

    def __init__(self, filter_backends=None, **kwargs):
        if filter_backends:
            self.filter_backends = filter_backends
        super(PrimaryKeyRelatedFilteredField, self).__init__(**kwargs)

    def get_queryset(self):
        queryset = super(PrimaryKeyRelatedFilteredField, self).get_queryset()
        queryset = self.filter_queryset(queryset)
        return queryset

    def filter_queryset(self, queryset):
        if self.filter_backends:
            request = self.context['request']
            for backend in self.filter_backends:
                queryset = backend().filter_queryset(request, queryset, None)
        return queryset

    def to_representation(self, value):

        try:

            if self.pk_field is not None:
                return self.pk_field.to_representation(value.pk)
            return value.pk

        except Exception as e:

            if type(value) == dict:
                return value['pk']


class SlugRelatedFilteredField(SlugRelatedField):
    filter_backends = None

    def __init__(self, filter_backends=None, **kwargs):
        if filter_backends:
            self.filter_backends = filter_backends
        super(SlugRelatedFilteredField, self).__init__(**kwargs)

    def get_queryset(self):
        queryset = super(SlugRelatedFilteredField, self).get_queryset()
        queryset = self.filter_queryset(queryset)
        return queryset

    def filter_queryset(self, queryset):
        if self.filter_backends:
            request = self.context['request']
            for backend in self.filter_backends:
                queryset = backend().filter_queryset(request, queryset, None)
        return queryset


# Thats cool
class UserCodeOrPrimaryKeyRelatedField(IamProtectedRelatedField):

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        try:
            if isinstance(data, str):
                return queryset.get(user_code=data)
            else:
                return queryset.get(pk=data)
        except ObjectDoesNotExist:
            self.fail('does_not_exist', slug_name='user_code', value=str(data))
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, obj):
        return getattr(obj, 'id')


class UserCodeField(CharField):
    def __init__(self, *args, **kwargs):
        # kwargs['max_length'] = 25
        kwargs['max_length'] = 255
        kwargs['required'] = False
        kwargs['allow_null'] = True
        kwargs['allow_blank'] = True
        super(UserCodeField, self).__init__(**kwargs)


class DateTimeTzAwareField(DateTimeField):
    format = '%Y-%m-%dT%H:%M:%S%z'
    # format = None
    input_formats = ['%Y-%m-%dT%H:%M:%S%z', ISO_8601, ]

    def to_representation(self, value):
        value = timezone.localtime(value)
        return super(DateTimeTzAwareField, self).to_representation(value)


class ExpressionField(CharField):
    def __init__(self, **kwargs):
        kwargs['allow_null'] = kwargs.get('allow_null', False)
        kwargs['allow_blank'] = kwargs.get('allow_blank', False)
        super(ExpressionField, self).__init__(**kwargs)

    # def run_validation(self, data=empty):
    #     value = super(ExpressionField, self).run_validation(data)
    #     if value and value != empty:
    #         formula.validate(value)
    #     return value


class Expression2Field(CharField):
    def __init__(self, **kwargs):
        kwargs['allow_null'] = kwargs.get('allow_null', False)
        kwargs['allow_blank'] = kwargs.get('allow_blank', False)
        super(Expression2Field, self).__init__(**kwargs)

    def run_validation(self, data=empty):
        value = super(Expression2Field, self).run_validation(data)
        # if value and value != empty:
        #     formula.validate(value)
        return value


class FloatEvalField(FloatField):
    def __init__(self, **kwargs):
        # kwargs['allow_null'] = kwargs.get('allow_null', False)
        # kwargs['allow_blank'] = kwargs.get('allow_blank', False)
        super(FloatEvalField, self).__init__(**kwargs)

    def run_validation(self, data=empty):
        value = super(FloatEvalField, self).run_validation(data)
        if data is not None:
            expr = str(data)
            formula.validate(expr)
            # try:
            #     formula.try_parse(data)
            # except formula.InvalidExpression as e:
            #     raise ValidationError('Invalid expression: %s' % e)
        return value

    def to_internal_value(self, data):
        try:
            return super(FloatEvalField, self).to_internal_value(data)
        except ValidationError:
            pass
        if data is not None:
            try:
                expr = str(data)
                return formula.safe_eval(expr, context=self.context)
            except (formula.InvalidExpression, ArithmeticError):
                raise ValidationError(gettext_lazy('Invalid expression.'))


class ISINField(RegexField):
    REGEX = '\S+ \S+'

    def __init__(self, **kwargs):
        super(ISINField, self).__init__(ISINField.REGEX, **kwargs)

    def to_representation(self, value):
        if isinstance(value, (tuple, list)):
            return ' '.join(value)
        else:
            return str(value)

            # def to_internal_value(self, data):
            #     data = super(ISINField, self).to_internal_value(data)
            #     if data is not None:
            #         return data.split(maxsplit=1)
            #     return None


class ContentTypeOrPrimaryKeyRelatedField(RelatedField):

    queryset = ContentType.objects

    def to_internal_value(self, data):

        try:
            if isinstance(data, str):

                pieces = data.split('.')

                return self.queryset.get(app_label=pieces[0], model=pieces[1])
            else:
                return self.queryset.get(pk=data)
        except ObjectDoesNotExist:
            self.fail('does_not_exist', slug_name='user_code', value=str(data))
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, obj):
        return getattr(obj, 'id')
