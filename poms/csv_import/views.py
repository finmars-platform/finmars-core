from rest_framework.exceptions import ValidationError

from .models import Scheme, CsvDataImport
from .serializers import SchemeSerializer, CsvDataImportSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser
from django.apps import apps

from poms.users.models import Member

from poms.common.formula import safe_eval, ExpressionSyntaxError
from poms.integrations.models import CounterpartyMapping, AccountMapping, ResponsibleMapping, PortfolioMapping

from poms.obj_attrs.models import GenericAttributeType, GenericAttribute

import io
import csv


class SchemeViewSet(viewsets.ModelViewSet):
    queryset = Scheme.objects.all()
    serializer_class = SchemeSerializer

    def create(self, request, *args, **kwargs):
        serializer = SchemeSerializer(data=request.data)

        if serializer.is_valid(raise_exception=ValueError):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CsvDataImportViewSet(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser,)
    queryset = CsvDataImport.objects.all()
    serializer_class = CsvDataImportSerializer
    http_method_names = ['get', 'post', 'head']

    def get_row_data(self, row, csv_fields):

        csv_row_dict = {}

        for csv_field in csv_fields:
            row_value = row[csv_field.column]

            csv_row_dict[csv_field.value] = row_value

        return csv_row_dict

    def get_results(self, request, scheme, entity_fields, csv_fields, reader, error_handler):

        errors = []
        results = []

        row_number = 0

        for row in reader:

            if row_number != 0:

                # try:

                print('scheme.content_type.model %s' % scheme.content_type.model)

                csv_row_dict = self.get_row_data(row, csv_fields)

                instance = {}
                instance['master_user'] = Member.objects.get(user=request.user).master_user
                instance['attributes'] = []

                for entity_field in entity_fields:

                    key = entity_field.system_property_key

                    if key is not None:

                        if entity_field.expression != '':

                            if key == 'counterparties':
                                instance[key] = CounterpartyMapping.objects.get(
                                    value=csv_row_dict[entity_field.expression]).content_object
                            elif key == 'responsibles':
                                instance[key] = ResponsibleMapping.objects.get(
                                    value=csv_row_dict[entity_field.expression]).content_object
                            elif key == 'accounts':
                                instance[key] = AccountMapping.objects.get(
                                    value=csv_row_dict[entity_field.expression]).content_object
                            elif key == 'portfolios':
                                instance[key] = PortfolioMapping.objects.get(
                                    value=csv_row_dict[entity_field.expression]).content_object
                            else:
                                instance[key] = safe_eval(entity_field.expression,
                                                          names=csv_row_dict)
                    else:

                        executed_attr = {}
                        executed_attr['dynamic_attribute_id'] = entity_field.dynamic_attribute_id
                        executed_attr['executed_expression'] = safe_eval(entity_field.expression,
                                                                         names=csv_row_dict)

                        instance['attributes'].append(executed_attr)

                if instance['user_code'] == '':
                    instance['user_code'] = instance['name']

                results.append(instance)

                # except:
                #
                #     instance['master_user'] = None
                #
                #     errors.append({"line": row_number, 'instance': instance})
                #
                #     if error_handler == 'break':
                #         break

            row_number = row_number + 1

        return results, errors

    def create(self, request, *args, **kwargs):

        scheme_id = request.data['scheme']
        error_handler = request.data['error_handler']

        scheme = Scheme.objects.get(pk=scheme_id)

        if 'file' not in request.data:
            raise ValidationError('File is not set')

        file = request.data['file'].read().decode('utf-8')

        io_string = io.StringIO(file)
        reader = csv.reader(io_string, delimiter=';')

        csv_fields = scheme.csv_fields.all()
        entity_fields = scheme.entity_fields.all()

        Model = apps.get_model(app_label=scheme.content_type.app_label, model_name=scheme.content_type.model)

        results, errors = self.get_results(request, scheme, entity_fields, csv_fields, reader, error_handler)

        for result in results:

            # try:

            result_without_many_to_many = {}

            many_to_many_fields = ['counterparties', 'responsibles', 'accounts', 'portfolios']

            for key, value in result.items():

                print('key %s' % key)

                if key != 'attributes':

                    if key not in many_to_many_fields:
                        result_without_many_to_many[key] = value

            print('result_without_many_to_many %s ' % result_without_many_to_many)

            instance = Model.objects.create(**result_without_many_to_many)

            print('saved result %s' % instance)

            for key, value in result.items():

                if key == 'counterparties':
                    getattr(instance, key, False).add(result[key])
                elif key == 'responsibles':
                    getattr(instance, key, False).add(result[key])
                elif key == 'accounts':
                    getattr(instance, key, False).add(result[key])
                elif key == 'portfolios':
                    getattr(instance, key, False).add(result[key])

            print('result %s' % result['attributes'])

            for result_attr in result['attributes']:

                print('attr', result_attr)

                attr_type = GenericAttributeType.objects.get(pk=result_attr['dynamic_attribute_id'])

                print('attr_type %s' % attr_type)

                print(repr(instance))

                attribute = GenericAttribute(content_object=instance, attribute_type=attr_type)

                if attr_type:
                    if attr_type.value_type == 40:
                        attribute.value_date = result_attr['executed_expression']
                    elif attr_type.value_type == 10:
                        attribute.value_string = result_attr['executed_expression']
                    elif attr_type.value_type == 20:
                        attribute.value_float = result_attr['executed_expression']
                    else:
                        pass

                print('attribute %s' % attribute)

                attribute.save()

            instance.save()

            # except:
            #
            #     result['master_user'] = None
            #
            #     errors.append({"line": row_number + 1, 'instance': result})  # we skipped first row in csv, so +1
            #
            #     if error_handler == 'break':
            #         break

        if len(errors):
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(request.data, status=status.HTTP_201_CREATED)
