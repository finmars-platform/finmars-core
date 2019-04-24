from rest_framework.exceptions import ValidationError

from rest_framework.response import Response
from rest_framework import status

from rest_framework.parsers import MultiPartParser
from rest_framework.filters import FilterSet
from django.apps import apps

from poms.common.views import AbstractModelViewSet
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet

from poms.users.filters import OwnerByMasterUserFilter

from poms.common import formula
from poms.common.formula import safe_eval, ExpressionEvalError

from poms.integrations.models import CounterpartyMapping, AccountMapping, ResponsibleMapping, PortfolioMapping, \
    PortfolioClassifierMapping, AccountClassifierMapping, ResponsibleClassifierMapping, CounterpartyClassifierMapping, \
    PricingPolicyMapping, InstrumentMapping, CurrencyMapping, InstrumentTypeMapping, PaymentSizeDetailMapping, \
    DailyPricingModelMapping, PriceDownloadSchemeMapping, InstrumentClassifierMapping, AccountTypeMapping

from poms.obj_attrs.models import GenericAttributeType, GenericAttribute

from django.utils.translation import ugettext

from .filters import SchemeContentTypeFilter
from .models import CsvDataImport, CsvImportScheme
from .serializers import CsvDataImportSerializer, CsvImportSchemeSerializer

from logging import getLogger

_l = getLogger('poms.csv_import')


class SchemeFilterSet(FilterSet):
    content_type = SchemeContentTypeFilter(name='content_type')

    class Meta:
        model = CsvImportScheme
        fields = []


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')


class SchemeViewSet(AbstractModelViewSet):
    queryset = CsvImportScheme.objects.select_related(
        'master_user',
    )
    serializer_class = CsvImportSchemeSerializer
    filter_class = SchemeFilterSet
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]


def get_row_data(row, csv_fields):
    csv_row_dict = {}

    for csv_field in csv_fields:

        if csv_field.column < len(row):
            row_value = row[csv_field.column]

            csv_row_dict[csv_field.name] = row_value

    return csv_row_dict


def get_field_type(field):
    if field.system_property_key is not None:
        return 'system_attribute'
    else:
        return 'dynamic_attribute'


def process_csv_file(master_user, scheme, rows, error_handler, context):
    csv_fields = scheme.csv_fields.all()
    entity_fields = scheme.entity_fields.all()

    errors = []
    results = []

    row_index = 0

    for row in rows:

        if row_index != 0:

            csv_row_dict = get_row_data(row, csv_fields)

            instance = {}
            instance['_row_index'] = row_index
            instance['_row'] = row

            if scheme.content_type.model != 'pricehistory' and scheme.content_type.model != 'currencyhistory':
                instance['master_user'] = master_user
                instance['attributes'] = []

            # print("model %s" % scheme.content_type.model)
            # print("instance %s" % instance)

            inputs_error = []
            error_row = {
                'error_message': None,
                'original_row_index': row_index,
                'original_row': row,
            }

            for entity_field in entity_fields:

                key = entity_field.system_property_key

                if get_field_type(entity_field) == 'system_attribute':

                    if entity_field.expression != '':

                        executed_expression = None

                        try:
                            # context=self.report.context
                            executed_expression = safe_eval(entity_field.expression, names=csv_row_dict,
                                                            context=context)

                        except (ExpressionEvalError, TypeError, Exception, KeyError):

                            inputs_error.append(entity_field)

                        # print('executed_expression %s' % executed_expression)

                        if key == 'counterparties':

                            try:
                                instance[key] = CounterpartyMapping.objects.get(master_user=master_user,
                                                                                value=executed_expression).content_object

                            except (CounterpartyMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                _l.debug('CounterpartyMapping %s does not exist', entity_field.expression)

                        elif key == 'responsibles':

                            try:
                                instance[key] = ResponsibleMapping.objects.get(master_user=master_user,
                                                                               value=executed_expression).content_object

                            except (ResponsibleMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                _l.debug('ResponsibleMapping %s does not exist', entity_field.expression)

                        elif key == 'accounts':

                            try:
                                instance[key] = AccountMapping.objects.get(master_user=master_user,
                                                                           value=executed_expression).content_object

                            except (AccountMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                _l.debug('AccountMapping %s does not exist', entity_field.expression)

                        elif key == 'portfolios':

                            try:
                                instance[key] = PortfolioMapping.objects.get(master_user=master_user,
                                                                             value=executed_expression).content_object

                            except (PortfolioMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                _l.debug('PortfolioMapping %s does not exist', entity_field.expression)

                        elif key == 'pricing_policy':

                            try:
                                instance[key] = PricingPolicyMapping.objects.get(master_user=master_user,
                                                                                 value=executed_expression).content_object

                            except (PricingPolicyMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                _l.debug('PricingPolicyMapping %s does not exist', entity_field.expression)

                        elif key == 'instrument':

                            try:
                                instance[key] = InstrumentMapping.objects.get(master_user=master_user,
                                                                              value=executed_expression).content_object

                            except (InstrumentMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                _l.debug('InstrumentMapping %s does not exist', entity_field.expression)

                        elif key == 'instrument_type':

                            try:
                                instance[key] = InstrumentTypeMapping.objects.get(master_user=master_user,
                                                                                  value=executed_expression).content_object

                            except (InstrumentTypeMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                _l.debug('InstrumentTypeMapping %s does not exist  ', entity_field.expression)

                        elif key == 'type':

                            try:
                                instance[key] = AccountTypeMapping.objects.get(master_user=master_user,
                                                                               value=executed_expression).content_object

                            except (AccountTypeMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                _l.debug('AccountTypeMapping %s does not exist  ', entity_field.expression)

                        elif key == 'price_download_scheme':

                            try:
                                instance[key] = PriceDownloadSchemeMapping.objects.get(master_user=master_user,
                                                                                       value=executed_expression).content_object

                            except (PriceDownloadSchemeMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                _l.debug('PriceDownloadSchemeMapping %s does not exist', entity_field.expression)

                        elif key == 'daily_pricing_model':

                            try:
                                instance[key] = DailyPricingModelMapping.objects.get(master_user=master_user,
                                                                                     value=executed_expression).content_object

                            except (DailyPricingModelMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                _l.debug('DailyPricingModelMapping %s does not exist', entity_field.expression)

                        elif key == 'payment_size_detail':

                            try:
                                instance[key] = PaymentSizeDetailMapping.objects.get(master_user=master_user,
                                                                                     value=executed_expression).content_object

                            except (PaymentSizeDetailMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                _l.debug('PaymentSizeDetailMapping %s does not exist', entity_field.expression)

                        elif key == 'currency':

                            try:
                                instance[key] = CurrencyMapping.objects.get(master_user=master_user,
                                                                            value=executed_expression).content_object

                            except (CurrencyMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                _l.debug('CurrencyMapping %s does not exist', entity_field.expression)

                        elif key == 'pricing_currency':

                            try:
                                instance[key] = CurrencyMapping.objects.get(master_user=master_user,
                                                                            value=executed_expression).content_object

                            except (CurrencyMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                _l.debug('CurrencyMapping %s does not exist', entity_field.expression)

                        elif key == 'accrued_currency':

                            try:
                                instance[key] = CurrencyMapping.objects.get(master_user=master_user,
                                                                            value=executed_expression).content_object

                            except (CurrencyMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                _l.debug('CurrencyMapping %s does not exist', entity_field.expression)

                        else:

                            instance[key] = executed_expression

                            if key == 'date':

                                try:

                                    instance[key] = formula._parse_date(instance[key])

                                except (ExpressionEvalError, TypeError):

                                    inputs_error.append(entity_field)

                        # _l.debug('Can not evaluate system attribute % expression ', entity_field.expression)

                if get_field_type(entity_field) == 'dynamic_attribute':

                    executed_attr = {}
                    executed_attr['dynamic_attribute_id'] = entity_field.dynamic_attribute_id

                    executed_expression = None

                    try:
                        # context=self.report.context
                        executed_expression = safe_eval(entity_field.expression, names=csv_row_dict,
                                                        context=context)

                    except (ExpressionEvalError, TypeError, Exception, KeyError):

                        inputs_error.append(entity_field)

                    attr_type = GenericAttributeType.objects.get(pk=executed_attr['dynamic_attribute_id'])

                    if attr_type.value_type == 30:

                        if scheme.content_type.model == 'portfolio':

                            try:
                                executed_attr['executed_expression'] = PortfolioClassifierMapping.objects.get(
                                    master_user=master_user,
                                    value=executed_expression, attribute_type=attr_type).content_object

                            except (PortfolioClassifierMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                print('PortfolioClassifierMapping %s does not exist' %
                                      executed_expression)

                        if scheme.content_type.model == 'instrument':

                            try:
                                executed_attr['executed_expression'] = InstrumentClassifierMapping.objects.get(
                                    master_user=master_user,
                                    value=executed_expression, attribute_type=attr_type).content_object

                            except (InstrumentClassifierMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                print('InstrumentClassifierMapping %s does not exist' %
                                      executed_expression)

                        if scheme.content_type.model == 'account':

                            try:

                                executed_attr['executed_expression'] = AccountClassifierMapping.objects.get(
                                    master_user=master_user,
                                    value=executed_expression,
                                    attribute_type=attr_type).content_object

                            except (AccountClassifierMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                print('AccountClassifierMapping %s does not exist' % executed_expression)

                        if scheme.content_type.model == 'responsible':

                            try:
                                executed_attr['executed_expression'] = ResponsibleClassifierMapping.objects.get(
                                    master_user=master_user,
                                    value=executed_expression, attribute_type=attr_type).content_object

                            except (ResponsibleClassifierMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                print('ResponsibleClassifierMapping %s does not exist' %
                                      executed_expression)

                        if scheme.content_type.model == 'counterparty':

                            try:
                                executed_attr[
                                    'executed_expression'] = CounterpartyClassifierMapping.objects.get(
                                    master_user=master_user,
                                    value=executed_expression, attribute_type=attr_type).content_object

                            except (CounterpartyClassifierMapping.DoesNotExist, KeyError):

                                inputs_error.append(entity_field)

                                print('CounterpartyClassifierMapping %s does not exist' %
                                      executed_expression)

                    else:

                        executed_attr['executed_expression'] = executed_expression

                    instance['attributes'].append(executed_attr)

            if inputs_error:

                print('inputs_error')
                print(inputs_error)

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


def get_item(scheme, result):
    Model = apps.get_model(app_label=scheme.content_type.app_label, model_name=scheme.content_type.model)

    item_result = None

    if scheme.content_type.model == 'pricehistory':

        try:

            item_result = Model.objects.get(instrument=result['instrument'],
                                            pricing_policy=result['pricing_policy'],
                                            date=result['date'])
        except Model.DoesNotExist:

            item_result = None


    elif scheme.content_type.model == 'currencyhistory':

        try:

            item_result = Model.objects.get(currency=result['currency'], pricing_policy=result['pricing_policy'],
                                            date=result['date'])

        except Model.DoesNotExist:

            item_result = None

    else:

        try:

            item_result = Model.objects.get(master_user_id=result['master_user'], user_code=result['user_code'])

        except Model.DoesNotExist:

            item_result = None

    return item_result


class CsvDataImportValidateViewSet(AbstractModelViewSet):
    parser_classes = (MultiPartParser,)
    queryset = CsvDataImport.objects.select_related(
        'master_user',
    )
    serializer_class = CsvDataImportSerializer
    http_method_names = ['get', 'post', 'head']

    def create_simple_instance(self, scheme, result):

        Model = apps.get_model(app_label=scheme.content_type.app_label, model_name=scheme.content_type.model)

        result_without_many_to_many = {}

        many_to_many_fields = ['counterparties', 'responsibles', 'accounts', 'portfolios']
        system_fields = ['_row_index', '_row']

        for key, value in result.items():

            if key != 'attributes':

                if key not in many_to_many_fields and key not in system_fields:
                    result_without_many_to_many[key] = value

        instance = Model(**result_without_many_to_many)

        return instance

    def attributes_full_clean(self, instance, attributes):

        for result_attr in attributes:

            attr_type = GenericAttributeType.objects.get(pk=result_attr['dynamic_attribute_id'])

            if attr_type:

                attribute = GenericAttribute(content_object=instance, attribute_type=attr_type)

                print('result_attr', result_attr)
                print('attribute', attribute)

                if attr_type.value_type == 10:
                    attribute.value_string = str(result_attr['executed_expression'])
                elif attr_type.value_type == 20:
                    attribute.value_float = float(result_attr['executed_expression'])
                elif attr_type.value_type == 30:

                    attribute.classifier = result_attr['executed_expression']

                elif attr_type.value_type == 40:
                    attribute.value_date = formula._parse_date(result_attr['executed_expression'])
                else:
                    pass

                attribute.object_id = 1 # To pass object id check

                attribute.full_clean()

    def instance_full_clean(self, scheme, result, process_errors, error_handler):

        try:

            instance = self.create_simple_instance(scheme, result)

            # self.fill_with_relation_attributes(instance, result)
            if scheme.content_type.model != 'pricehistory' and scheme.content_type.model != 'currencyhistory':
                self.attributes_full_clean(instance, result['attributes'])

            instance.full_clean()

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

    def instance_overwrite_full_clean(self, scheme, result, item, process_errors, error_handler):

        print('Overwrite item %s' % item)

        try:

            many_to_many_fields = ['counterparties', 'responsibles', 'accounts', 'portfolios']
            system_fields = ['_row_index', '_row']

            for key, value in result.items():

                if key != 'attributes':

                    if key not in many_to_many_fields and key not in system_fields:
                        setattr(item, key, value)

            # self.fill_with_relation_attributes(item, result)
            if scheme.content_type.model != 'pricehistory' and scheme.content_type.model != 'currencyhistory':
                self.attributes_full_clean(item, result['attributes'])

            item.full_clean()

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

    def full_clean_results(self, scheme, error_handler, mode, results, process_errors):

        for result in results:

            item = get_item(scheme, result)

            if mode == 'overwrite' and item:

                self.instance_overwrite_full_clean(scheme, result, item, process_errors, error_handler)

            elif mode == 'overwrite' and not item:

                self.instance_full_clean(scheme, result, process_errors, error_handler)

            elif mode == 'skip' and not item:

                self.instance_full_clean(scheme, result, process_errors, error_handler)

            elif mode == 'skip' and item:

                error_row = {
                    'error_message': ugettext('Entry already exists '),
                    'original_row_index': result['_row_index'],
                    'original_row': result['_row'],
                }

                process_errors.append(error_row)

                if error_handler == 'break':
                    return process_errors

        return process_errors

    def create(self, request, *args, **kwargs):

        scheme_id = request.data['scheme']
        error_handler = request.data['error_handler']
        delimiter = request.data['delimiter']
        mode = request.data['mode']

        scheme = CsvImportScheme.objects.get(pk=scheme_id)

        if 'file' not in request.data:
            raise ValidationError('File is not set')

        if not request.data['file'].name.endswith('.csv'):
            raise ValidationError('File is not csv format')

        csv_contents = request.data['file'].read().decode('utf-8-sig')
        rows = csv_contents.splitlines()

        delimiter = delimiter.encode('utf-8').decode('unicode_escape')

        rows = list(map(lambda x: x.split(delimiter), rows))

        rows_total = len(rows)

        master_user = self.request.user.master_user

        context = super(CsvDataImportValidateViewSet, self).get_serializer_context()

        results, process_errors = process_csv_file(master_user, scheme, rows, error_handler, context)

        if error_handler == 'break' and len(process_errors) != 0:
            return Response({
                "imported": len(results),
                "total": rows_total,
                "errors": process_errors
            }, status=status.HTTP_202_ACCEPTED)

        process_errors = self.full_clean_results(scheme, error_handler, mode, results, process_errors)

        return Response({
            "imported": len(results),
            "total": rows_total,
            "errors": process_errors
        }, status=status.HTTP_202_ACCEPTED)


class CsvDataImportViewSet(AbstractModelViewSet):
    parser_classes = (MultiPartParser,)
    queryset = CsvDataImport.objects.select_related(
        'master_user',
    )
    serializer_class = CsvDataImportSerializer
    http_method_names = ['get', 'post', 'head']

    def delete_dynamic_attributes(self, instance, attributes):

        for result_attr in attributes:

            attr_type = GenericAttributeType.objects.get(pk=result_attr['dynamic_attribute_id'])

            if attr_type:
                attribute = GenericAttribute.objects.filter(object_id=instance.pk, attribute_type=attr_type)

                attribute.delete()

    def fill_with_dynamic_attributes(self, instance, attributes):

        for result_attr in attributes:

            attr_type = GenericAttributeType.objects.get(pk=result_attr['dynamic_attribute_id'])

            if attr_type:

                attribute = GenericAttribute(content_object=instance, attribute_type=attr_type)

                print('result_attr', result_attr)
                print('attribute', attribute)

                if attr_type.value_type == 10:
                    attribute.value_string = str(result_attr['executed_expression'])
                elif attr_type.value_type == 20:
                    attribute.value_float = float(result_attr['executed_expression'])
                elif attr_type.value_type == 30:

                    attribute.classifier = result_attr['executed_expression']

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

    def overwrite_instance(self, scheme, result, item, process_errors, error_handler):

        print('Overwrite item %s' % item)

        try:

            many_to_many_fields = ['counterparties', 'responsibles', 'accounts', 'portfolios']
            system_fields = ['_row_index', '_row']

            for key, value in result.items():

                if key != 'attributes':

                    if key not in many_to_many_fields and key not in system_fields:
                        setattr(item, key, value)

            self.fill_with_relation_attributes(item, result)
            if scheme.content_type.model != 'pricehistory' and scheme.content_type.model != 'currencyhistory':
                self.delete_dynamic_attributes(item, result['attributes'])
                self.fill_with_dynamic_attributes(item, result['attributes'])

            item.save()

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

    def import_results(self, scheme, error_handler, mode, results, process_errors):

        for result in results:

            item = get_item(scheme, result)

            if mode == 'overwrite' and item:

                self.overwrite_instance(scheme, result, item, process_errors, error_handler)

            elif mode == 'overwrite' and not item:

                self.save_instance(scheme, result, process_errors, error_handler)

            elif mode == 'skip' and not item:

                self.save_instance(scheme, result, process_errors, error_handler)

            elif mode == 'skip' and item:

                error_row = {
                    'error_message': ugettext('Entry already exists '),
                    'original_row_index': result['_row_index'],
                    'original_row': result['_row'],
                }

                process_errors.append(error_row)

                if error_handler == 'break':
                    return process_errors

        return process_errors

    def create(self, request, *args, **kwargs):

        scheme_id = request.data['scheme']
        error_handler = request.data['error_handler']
        delimiter = request.data['delimiter']
        mode = request.data['mode']

        scheme = CsvImportScheme.objects.get(pk=scheme_id)

        if 'file' not in request.data:
            raise ValidationError('File is not set')

        if not request.data['file'].name.endswith('.csv'):
            raise ValidationError('File is not csv format')

        csv_contents = request.data['file'].read().decode('utf-8-sig')
        rows = csv_contents.splitlines()

        delimiter = delimiter.encode('utf-8').decode('unicode_escape')

        rows = list(map(lambda x: x.split(delimiter), rows))

        rows_total = len(rows)

        master_user = self.request.user.master_user

        context = super(CsvDataImportViewSet, self).get_serializer_context()

        results, process_errors = process_csv_file(master_user, scheme, rows, error_handler, context)

        if error_handler == 'break' and len(process_errors) != 0:
            return Response({
                "imported": len(results),
                "total": rows_total,
                "errors": process_errors
            }, status=status.HTTP_202_ACCEPTED)

        process_errors = self.import_results(scheme, error_handler, mode, results, process_errors)

        return Response({
            "imported": len(results),
            "total": rows_total,
            "errors": process_errors
        }, status=status.HTTP_202_ACCEPTED)
