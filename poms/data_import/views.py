import io
import csv
import json
from dateutil.parser import parse
from django.db import IntegrityError
from django.db.models.base import ModelBase
from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework.status import HTTP_201_CREATED, HTTP_500_INTERNAL_SERVER_ERROR
from poms.common.formula import safe_eval, ExpressionSyntaxError
from poms.obj_attrs.models import GenericAttributeType, GenericAttribute
from poms.users.models import Member
from poms.integrations.models import CounterpartyMapping, AccountMapping, ResponsibleMapping
from .serializers import DataImportSerializer, DataImportSchemaSerializer, DataImportSchemaFieldsSerializer, \
    DataImportSchemaModelsSerializer, DataImportSchemaMatchingSerializer, DataImportContentTypeSerializer
from .models import DataImport, DataImportSchema, DataImportSchemaFields, DataImportSchemaMatching
from .options import PUBLIC_FIELDS
from .utils import split_csv_str


class DataImportViewSet(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser,)
    queryset = DataImport.objects.all()
    serializer_class = DataImportSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        status = HTTP_201_CREATED
        response_data = []
        self.perform_create(serializer)
        f = csv.DictReader(io.TextIOWrapper(request.data['files'].file))
        schema = DataImportSchema.objects.get(pk=request.data['schema'])
        fields = schema.dataimportschemafields_set.all()
        matchings_fields = DataImportSchemaMatching.objects.filter(schema=schema)
        data = {}
        raw_data = {}
        for row in f:
            values = split_csv_str(row.values())
            if values:
                try:
                    dict_row = {}
                    for field in fields:
                        raw_data[field.source] = values[field.num]
                        if isinstance(values[field.num], str):
                            dict_row[field.source] = '"' + values[field.num] + '"'
                        else:
                            dict_row[field.source] = values[field.num]
                    for matching_field in matchings_fields:
                        if dict_row.get(matching_field.expression):
                            data[matching_field.model_field] = raw_data.get(matching_field.expression)
                        else:
                            expr = matching_field.expression.format(**dict_row)
                            data[matching_field.model_field] = safe_eval(expr)
                    if data:
                        master_user_id = Member.objects.get(user=self.request.user).master_user.id
                        accepted_data = {}
                        relation_data = {}
                        accepted_data['master_user_id'] = master_user_id
                        for key in PUBLIC_FIELDS[schema.model.model]:
                            accepted_data[key] = data.get(key)
                        for k, v in accepted_data.copy().items():
                            if isinstance(k, ModelBase):
                                del accepted_data[k]
                                try:
                                    if k._meta.model_name == 'counterparty':
                                        mapping_model = CounterpartyMapping
                                    elif k._meta.model_name == 'responsible':
                                        mapping_model = ResponsibleMapping
                                    elif k._meta.model_name == 'account':
                                        mapping_model = AccountMapping
                                    else:
                                        raise KeyError
                                    relation_data[k._meta.verbose_name_plural] = mapping_model.objects.filter(value=raw_data[k._meta.model_name.capitalize()])[0].content_object
                                except (KeyError, IndexError):
                                    continue
                            else:
                                accepted_data[k] = v
                        additional_keys = []
                        for item in data.keys():
                            if item not in accepted_data.keys() and len(item.split(':')) == 1:
                                additional_keys.append(item)

                        o, _ = schema.model.model_class().objects.get_or_create(**accepted_data)
                        for r in relation_data.keys():
                            getattr(o, str(r)).add(relation_data[r])
                        for additional_key in additional_keys:
                            attr_type = GenericAttributeType.objects.filter(user_code=additional_key).first()
                            attribute = GenericAttribute(content_object=o, attribute_type=attr_type)
                            if attr_type:
                                if attr_type.value_type == 40:
                                    attribute.value_date = str(data[additional_key])
                                elif attr_type.value_type == 10:
                                    attribute.value_string = data[additional_key]
                                elif attr_type.value_type == 20:
                                    attribute.value_float = float(data[additional_key])
                                else:
                                    pass
                                attribute.save()
                except Exception as e:
                    response_data.append({'error': e.__str__(), 'row': json.dumps(raw_data)})
                    if int(request.data.get('error_handling')[0]):
                        continue
                    else:
                        return Response(response_data, status=HTTP_500_INTERNAL_SERVER_ERROR)
        headers = self.get_success_headers(serializer.data)
        return Response(response_data, status=status, headers=headers)


class DataImportSchemaViewSet(viewsets.ModelViewSet):
    queryset = DataImportSchema.objects.all()
    serializer_class = DataImportSchemaSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'model',)


class DataImportSchemaFieldsViewSet(viewsets.ModelViewSet):
    queryset = DataImportSchemaFields.objects.all()
    serializer_class = DataImportSchemaFieldsSerializer
    filter_backends = (DjangoFilterBackend,)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).filter(
            schema_id=self.request.query_params.get('schema_id'))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        schema, created = DataImportSchema.objects.update_or_create(name=request.data.get('schema_name'),
                                                        defaults={'model_id': int(request.data.get('schema_model'))})
        field_list = request.data.get('field_list')
        if field_list:
            for i in field_list:
                serializer = self.get_serializer(data=i)
                # serializer.instance = self.queryset.get(id=i['id'])
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
        if request.data.get('matching_list'):
            for m in request.data['matching_list']:
                if m.get('expression'):
                    o, _ = DataImportSchemaMatching.objects.update_or_create(schema=schema,
                                                                             model_field=m['model_field'],
                                                                             defaults={
                                                                                 'expression': m['expression']
                                                                             })
        return Response(status=HTTP_201_CREATED)


class DataImportSchemaModelsViewSet(viewsets.ModelViewSet):
    queryset = ContentType.objects.filter(model__in=[
        'accounttype',
        'counterparty',
        'currency',
        'instrument',
        'portfolio',
        'pricingpolicy',
        'responsible',
        'strategy1',
        'strategy2',
        'strategy3',

    ])
    serializer_class = DataImportSchemaModelsSerializer

    @detail_route(methods=['get'])
    def fields(self, request, pk=None):
        obj = self.get_object()
        base_fields = list(map(lambda f: {'model_field': f, 'expression': ''}, PUBLIC_FIELDS[obj.model]))
        master_user = Member.objects.get(user=self.request.user).master_user
        all_attr_fields = GenericAttributeType.objects.filter(master_user=master_user, content_type=obj)
        additional_fields = []
        for attr_fields in all_attr_fields:
            additional_fields.append({'model_field': attr_fields.name, 'expression': ''})
        return Response({'results': base_fields + additional_fields})


class DataImportSchemaMatchingViewSet(viewsets.ModelViewSet):
    queryset = DataImportSchemaMatching.objects.all()
    serializer_class = DataImportSchemaMatchingSerializer
    filter_backends = (DjangoFilterBackend,)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).filter(schema_id=self.request.query_params.get('schema_id'))
        serializer = self.get_serializer(queryset, many=True)
        schema = DataImportSchema.objects.get(pk=self.request.query_params.get('schema_id'))
        base_fields = list(map(lambda f: {'model_field': f if isinstance(f, str) else f._meta.model_name, 'expression': '', 'related': False if isinstance(f, str) else True}, PUBLIC_FIELDS[schema.model.name]))
        master_user = Member.objects.get(user=self.request.user).master_user
        all_attr_fields = GenericAttributeType.objects.filter(master_user=master_user, content_type=schema.model)
        additional_fields = []
        for attr_fields in all_attr_fields:
            additional_fields.append({'model_field': attr_fields.name, 'expression': '', 'related': False})
        all_fields = base_fields + additional_fields
        for f in serializer.data:
            if f['expression']:
                for i, item in enumerate(all_fields):
                    if f['model_field'].split(':')[0] == item['model_field']:
                        f['related'] = item['related']
                        all_fields[i] = f
        return Response(all_fields)


class ContentTypeViewSet(viewsets.ModelViewSet):
    queryset = ContentType.objects.filter(app_label__in=[
        'accounts', 'counterparties', 'currencies', 'instruments', 'portfolios', 'strategies'
    ])
    serializer_class = DataImportContentTypeSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'model',)


    @detail_route(methods=['get'])
    def fields(self, request, pk=None):
        obj = self.get_object()
        model = obj.model_class()
        return Response({'results': [f.name for f in model._meta.fields]})
