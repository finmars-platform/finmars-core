from rest_framework.exceptions import ValidationError

from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.filters import FilterSet
from django.apps import apps

from poms.currencies.models import CurrencyHistory
from poms.instruments.models import PriceHistory
from poms.integrations.storage import import_file_storage
from django.utils import timezone
import uuid

from poms.common.views import AbstractModelViewSet
from poms.portfolios.models import Portfolio
from poms.users.models import Member
from poms.common import formula
from poms.common.formula import safe_eval, ExpressionSyntaxError, ExpressionEvalError

from poms.integrations.models import CounterpartyMapping, AccountMapping, ResponsibleMapping, PortfolioMapping, \
    PortfolioClassifierMapping, AccountClassifierMapping, ResponsibleClassifierMapping, CounterpartyClassifierMapping, \
    PricingPolicyMapping, InstrumentMapping, CurrencyMapping

from poms.obj_attrs.models import GenericAttributeType, GenericAttribute, GenericClassifier

from django.utils.translation import ugettext

import io
import csv

from .filters import SchemeContentTypeFilter
from .models import Scheme, CsvDataImport
from .serializers import SchemeSerializer, CsvDataImportSerializer

from logging import getLogger

_l = getLogger('poms.csv_import')


class SchemeFilterSet(FilterSet):
    content_type = SchemeContentTypeFilter(name='content_type')

    class Meta:
        model = Scheme
        fields = []


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')


class SchemeViewSet(AbstractModelViewSet):
    queryset = Scheme.objects.select_related(
        'master_user',
    )
    serializer_class = SchemeSerializer
    filter_class = SchemeFilterSet

    # def create(self, request, *args, **kwargs):
    #
    #     request.data['master_user'] = request.user
    #
    #     serializer = SchemeSerializer(data=request.data, context={'user': request.user})
    #
    #     if serializer.is_valid(raise_exception=ValueError):
    #         serializer.save()
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)
    #
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CsvDataImportViewSet(AbstractModelViewSet):
    parser_classes = (MultiPartParser,)
    queryset = CsvDataImport.objects.select_related(
        'master_user',
    )
    serializer_class = CsvDataImportSerializer
    http_method_names = ['get', 'post', 'head']

    def get_row_data(self, row, csv_fields):

        csv_row_dict = {}

        for csv_field in csv_fields:

            if csv_field.column < len(row):
                row_value = row[csv_field.column]

                csv_row_dict[csv_field.value] = row_value

        return csv_row_dict

    def get_field_type(self, field):

        if field.system_property_key is not None:
            return 'system_attribute'
        else:
            return 'dynamic_attribute'

    def process_csv_file(self, master_user, scheme, rows, error_handler):

        csv_fields = scheme.csv_fields.all()
        entity_fields = scheme.entity_fields.all()

        errors = []
        results = []

        row_index = 0

        for row in rows:

            if row_index != 0:

                csv_row_dict = self.get_row_data(row, csv_fields)

                instance = {}
                instance['_row_index'] = row_index
                instance['_row'] = row

                if scheme.content_type.model != 'pricehistory' and scheme.content_type.model != 'currencyhistory':
                    instance['master_user'] = master_user
                    instance['attributes'] = []

                print("model %s" % scheme.content_type.model)
                print("instance %s" % instance)

                inputs_error = []
                error_row = {
                    'error_message': None,
                    'original_row_index': row_index,
                    'original_row': row,
                }

                for entity_field in entity_fields:

                    key = entity_field.system_property_key

                    if self.get_field_type(entity_field) == 'system_attribute':

                        if entity_field.expression != '':

                            if key == 'counterparties':

                                try:
                                    instance[key] = CounterpartyMapping.objects.get(
                                        value=csv_row_dict[entity_field.expression]).content_object

                                except (CounterpartyMapping.DoesNotExist, KeyError):

                                    inputs_error.append(entity_field)

                                    _l.debug('CounterpartyMapping %s does not exist', entity_field.expression)

                            elif key == 'responsibles':

                                try:
                                    instance[key] = ResponsibleMapping.objects.get(
                                        value=csv_row_dict[entity_field.expression]).content_object

                                except (ResponsibleMapping.DoesNotExist, KeyError):

                                    inputs_error.append(entity_field)

                                    _l.debug('ResponsibleMapping %s does not exist', entity_field.expression)

                            elif key == 'accounts':

                                try:
                                    instance[key] = AccountMapping.objects.get(
                                        value=csv_row_dict[entity_field.expression]).content_object

                                except (AccountMapping.DoesNotExist, KeyError):

                                    inputs_error.append(entity_field)

                                    _l.debug('AccountMapping %s does not exist', entity_field.expression)

                            elif key == 'portfolios':

                                try:
                                    instance[key] = PortfolioMapping.objects.get(
                                        value=csv_row_dict[entity_field.expression]).content_object

                                except (PortfolioMapping.DoesNotExist, KeyError):

                                    inputs_error.append(entity_field)

                                    _l.debug('PortfolioMapping %s does not exist', entity_field.expression)

                            elif key == 'pricing_policy':

                                try:
                                    instance[key] = PricingPolicyMapping.objects.get(
                                        value=csv_row_dict[entity_field.expression]).content_object

                                except (PricingPolicyMapping.DoesNotExist, KeyError):

                                    inputs_error.append(entity_field)

                                    _l.debug('PricingPolicyMapping %s does not exist', entity_field.expression)

                            elif key == 'instrument':

                                try:
                                    instance[key] = InstrumentMapping.objects.get(
                                        value=csv_row_dict[entity_field.expression]).content_object

                                except (InstrumentMapping.DoesNotExist, KeyError):

                                    inputs_error.append(entity_field)

                                    _l.debug('InstrumentMapping %s does not exist', entity_field.expression)

                            elif key == 'currency':

                                try:
                                    instance[key] = CurrencyMapping.objects.get(
                                        value=csv_row_dict[entity_field.expression]).content_object

                                except (CurrencyMapping.DoesNotExist, KeyError):

                                    inputs_error.append(entity_field)

                                    _l.debug('CurrencyMapping %s does not exist', entity_field.expression)

                            else:

                                try:

                                    instance[key] = safe_eval(entity_field.expression, names=csv_row_dict)

                                    if key == 'date':

                                        try:

                                            instance[key] = formula._parse_date(instance[key])

                                        except (ExpressionEvalError, TypeError):

                                            inputs_error.append(entity_field)


                                except (ExpressionEvalError, TypeError, Exception, KeyError):

                                    inputs_error.append(entity_field)

                                    # _l.debug('Can not evaluate system attribute % expression ', entity_field.expression)

                    if self.get_field_type(entity_field) == 'dynamic_attribute':

                        executed_attr = {}
                        executed_attr['dynamic_attribute_id'] = entity_field.dynamic_attribute_id

                        try:

                            attr_type = GenericAttributeType.objects.get(pk=executed_attr['dynamic_attribute_id'])

                            if attr_type.value_type == 40:

                                executed_attr['executed_expression'] = safe_eval(entity_field.expression,
                                                                                 names=csv_row_dict)
                                try:

                                    formula._parse_date(executed_attr['executed_expression'])

                                except (ExpressionEvalError, TypeError):

                                    inputs_error.append(entity_field)

                            if attr_type.value_type == 20:

                                executed_attr['executed_expression'] = safe_eval(entity_field.expression,
                                                                                 names=csv_row_dict)
                                try:

                                    formula._float(executed_attr['executed_expression'])

                                except (ExpressionEvalError, TypeError):

                                    inputs_error.append(entity_field)

                            if attr_type.value_type == 10:
                                executed_attr['executed_expression'] = safe_eval(entity_field.expression,
                                                                                 names=csv_row_dict)

                            if attr_type.value_type == 30:

                                if scheme.content_type.model == 'portfolio':

                                    try:
                                        executed_attr['executed_expression'] = PortfolioClassifierMapping.objects.get(
                                            value=csv_row_dict[entity_field.expression]).content_object

                                    except (PortfolioClassifierMapping.DoesNotExist, KeyError):

                                        inputs_error.append(entity_field)

                                        _l.debug('PortfolioClassifierMapping %s does not exist',
                                                 entity_field.expression)

                                if scheme.content_type.model == 'account':

                                    try:
                                        executed_attr['executed_expression'] = AccountClassifierMapping.objects.get(
                                            value=csv_row_dict[entity_field.expression]).content_object

                                    except (AccountClassifierMapping.DoesNotExist, KeyError):

                                        inputs_error.append(entity_field)

                                        _l.debug('AccountClassifierMapping %s does not exist', entity_field.expression)

                                if scheme.content_type.model == 'responsible':

                                    try:
                                        executed_attr['executed_expression'] = ResponsibleClassifierMapping.objects.get(
                                            value=csv_row_dict[entity_field.expression]).content_object

                                    except (ResponsibleClassifierMapping.DoesNotExist, KeyError):

                                        inputs_error.append(entity_field)

                                        _l.debug('ResponsibleClassifierMapping %s does not exist',
                                                 entity_field.expression)

                                if scheme.content_type.model == 'counterparty':

                                    try:
                                        executed_attr[
                                            'executed_expression'] = CounterpartyClassifierMapping.objects.get(
                                            value=csv_row_dict[entity_field.expression]).content_object

                                    except (CounterpartyClassifierMapping.DoesNotExist, KeyError):

                                        inputs_error.append(entity_field)

                                        _l.debug('CounterpartyClassifierMapping %s does not exist',
                                                 entity_field.expression)


                        except (ExpressionEvalError, TypeError, Exception):

                            inputs_error.append(entity_field)

                            # _l.debug('Can not evaluate dynamic attribute % expression ', entity_field.expression)

                        instance['attributes'].append(executed_attr)

                if inputs_error:

                    error_row['error_message'] = ugettext('Can\'t process field: %(inputs)s') % {
                        'inputs': ', '.join(i.name for i in inputs_error)
                    }

                    errors.append(error_row)

                    if error_handler == 'break':
                        return results, errors

                else:

                    # if (hasattr(instance, 'user_code') and instance['user_code'] == ''):
                    #     instance['user_code'] = instance['name']

                    results.append(instance)

            row_index = row_index + 1

        return results, errors

    def fill_with_dynamic_attributes(self, instance, attributes):

        for result_attr in attributes:

            attr_type = GenericAttributeType.objects.get(pk=result_attr['dynamic_attribute_id'])

            if attr_type:

                attribute = GenericAttribute(content_object=instance, attribute_type=attr_type)

                if attr_type.value_type == 10:
                    attribute.value_string = str(result_attr['executed_expression'])
                elif attr_type.value_type == 20:
                    attribute.value_float = float(result_attr['executed_expression'])
                elif attr_type.value_type == 30:

                    attribute.classifier = result_attr['executed_expression']

                    print('attribute', attribute)

                elif attr_type.value_type == 40:
                    attribute.value_date = formula._parse_date(result_attr['executed_expression'])
                else:
                    pass

                attribute.save()

    def fill_with_relation_attributes(self, instance, result):

        for key, value in result.items():

            if key == 'counterparties':
                getattr(instance, key, False).add(result[key])
            elif key == 'responsibles':
                getattr(instance, key, False).add(result[key])
            elif key == 'accounts':
                getattr(instance, key, False).add(result[key])
            elif key == 'portfolios':
                getattr(instance, key, False).add(result[key])

    def create_simple_instance(self, scheme, result):

        Model = apps.get_model(app_label=scheme.content_type.app_label, model_name=scheme.content_type.model)

        result_without_many_to_many = {}

        many_to_many_fields = ['counterparties', 'responsibles', 'accounts', 'portfolios']
        system_fields = ['_row_index', '_row']

        for key, value in result.items():

            if key != 'attributes':

                if key not in many_to_many_fields and key not in system_fields:
                    result_without_many_to_many[key] = value

        instance = Model.objects.create(**result_without_many_to_many)

        return instance

    def save_instance(self, scheme, result, process_errors, error_handler):

        try:

            instance = self.create_simple_instance(scheme, result)

            self.fill_with_relation_attributes(instance, result)
            if scheme.content_type.model != 'pricehistory' and scheme.content_type.model != 'currencyhistory':
                self.fill_with_dynamic_attributes(instance, result['attributes'])

            instance.save()
        except ValidationError as e:

            error_row = {
                'error_message': ugettext('Validation error %(error)s ') % {
                    'error': e
                },
                'original_row_index': result['_row_index'],
                'original_row': result['_row'],
            }

            process_errors.append(error_row)

            if error_handler == 'break':
                return process_errors

    def import_results(self, scheme, error_handler, results, process_errors):

        Model = apps.get_model(app_label=scheme.content_type.app_label, model_name=scheme.content_type.model)

        for result in results:

            print('scheme.content_type.model %s' % scheme.content_type.model)
            print('result %s' % result)

            if scheme.content_type.model == 'pricehistory':

                try:

                    Model.objects.get(instrument=result['instrument'], pricing_policy=result['pricing_policy'],
                                      date=result['date'])

                    error_row = {
                        'error_message': ugettext('Entry already exists ') % {
                            'instrument': result['instrument'],
                            'pricing_policy': result['pricing_policy'],
                            'date': result['date']
                        },
                        'original_row_index': result['_row_index'],
                        'original_row': result['_row'],
                    }

                    process_errors.append(error_row)

                    if error_handler == 'break':
                        return process_errors

                except Model.DoesNotExist:

                    self.save_instance(scheme, result, process_errors, error_handler)

            elif scheme.content_type.model == 'currencyhistory':

                try:

                    Model.objects.get(currency=result['currency'], pricing_policy=result['pricing_policy'],
                                      date=result['date'])

                    error_row = {
                        'error_message': ugettext('Entry already exists ') % {
                            'currency': result['currency'],
                            'pricing_policy': result['pricing_policy'],
                            'date': result['date']
                        },
                        'original_row_index': result['_row_index'],
                        'original_row': result['_row'],
                    }

                    process_errors.append(error_row)

                    if error_handler == 'break':
                        return process_errors

                except Model.DoesNotExist:

                    self.save_instance(scheme, result, process_errors, error_handler)

            else:

                try:

                    Model.objects.get(master_user_id=result['master_user'], user_code=result['user_code'])

                    error_row = {
                        'error_message': ugettext('Entry with user code %(user_code)s already exists ') % {
                            'user_code': result['user_code']
                        },
                        'original_row_index': result['_row_index'],
                        'original_row': result['_row'],
                    }

                    process_errors.append(error_row)

                    if error_handler == 'break':
                        return process_errors

                except Model.DoesNotExist:
                    self.save_instance(scheme, result, process_errors, error_handler)

        return process_errors

    def create(self, request, *args, **kwargs):

        scheme_id = request.data['scheme']
        error_handler = request.data['error_handler']

        scheme = Scheme.objects.get(pk=scheme_id)

        if 'file' not in request.data:
            raise ValidationError('File is not set')

        if not request.data['file'].name.endswith('.csv'):
            raise ValidationError('File is not csv format')

        csv_contents = request.data['file'].read().decode('utf-8-sig')
        rows = csv_contents.splitlines()

        print('rows len %s' % len(rows))

        rows = map(lambda x: x.split(','), rows)

        master_user = self.request.user.master_user

        results, process_errors = self.process_csv_file(master_user, scheme, rows, error_handler)

        if error_handler == 'break' and len(process_errors) != 0:
            return Response({
                "imported": len(results),
                "errors": process_errors
            }, status=status.HTTP_202_ACCEPTED)

        process_errors = self.import_results(scheme, error_handler, results, process_errors)

        return Response({
            "imported": len(results),
            "errors": process_errors
        }, status=status.HTTP_202_ACCEPTED)
