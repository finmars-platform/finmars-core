import traceback

from django.utils.translation import gettext_lazy
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.common import formula
from poms.common.fields import ExpressionField, Expression2Field

import logging
_l = logging.getLogger('poms.api')

class Language(object):
    def __init__(self, code='', name=''):
        self.code = code
        self.name = name

    def __str__(self):
        return '{}: {}'.format(self.code, self.name)


class LanguageSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=2)
    name = serializers.CharField(max_length=50)

    def create(self, validated_data):
        return Language(**validated_data)

    def update(self, instance, validated_data):
        instance.code = validated_data.get('code', instance.code)
        instance.name = validated_data.get('name', instance.name)
        return instance


class Timezone(object):
    def __init__(self, code='', name='', offset=0):
        self.code = code
        self.name = name
        self.offset = offset

    def __str__(self):
        return '{}: {}'.format(self.code, self.name)


class TimezoneSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=2)
    name = serializers.CharField(max_length=50)

    def create(self, validated_data):
        return Timezone(**validated_data)

    def update(self, instance, validated_data):
        instance.code = validated_data.get('code', instance.code)
        instance.name = validated_data.get('name', instance.name)
        return instance


class ExpressionSerializer(serializers.Serializer):
    expression = ExpressionField(required=True, style={'base_template': 'textarea.html'})
    names1 = serializers.DictField(required=False, allow_null=True, help_text='Raw names as JSON object')
    # names2 = ExpressionField(required=False, allow_null=True, help_text='Names as expression',
    #                          style={'base_template': 'textarea.html'})
    names = serializers.ReadOnlyField()
    is_eval = serializers.BooleanField()
    result = serializers.ReadOnlyField()
    # help_raw = serializers.SerializerMethodField()
    # help = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super(ExpressionSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request', None)
        if request and request.query_params.get('help', '1') == '0':
            self.fields.pop('help_raw')
            self.fields.pop('help')

    def validate(self, attrs):
        is_eval = attrs.get('is_eval', False)
        if is_eval:
            expression = attrs['expression']
            names1 = attrs.get('names1', None)
            names2 = attrs.get('names2', None)
            if names2:
                try:
                    names2 = formula.safe_eval(names2, context=self.context)
                except formula.InvalidExpression as e:
                    raise ValidationError({'names2': gettext_lazy('Invalid expression.')})
            names = {}
            if names1:
                names.update(names1)
            if names2:
                names.update(names2)
            attrs['names'] = names
            try:
                attrs['result'] = formula.safe_eval(expression, names, context=self.context)
            except formula.InvalidExpression as e:
                _l.error("Manual expression error %s" % e)
                _l.error("Manual expression traceback %s" % traceback.format_exc())
                raise ValidationError({'expression': gettext_lazy('Invalid expression.'), "error_message": str(e)})
        return attrs

    def get_help(self, obj):
        return formula.HELP

    def get_help_raw(self, obj):
        return formula.HELP.split('\n')
