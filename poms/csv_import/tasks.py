from celery import shared_task, chord, current_task
from django.contrib.auth.models import Permission
from django.db import IntegrityError
from django.utils.timezone import now

from poms.common.formula import safe_eval, ExpressionEvalError
from poms.common.utils import date_now
from poms.file_reports.models import FileReport
from poms.obj_perms.models import GenericObjectPermission

from poms.users.models import EcosystemDefault, Group
from django.apps import apps

from poms.integrations.models import CounterpartyMapping, AccountMapping, ResponsibleMapping, PortfolioMapping, \
    PortfolioClassifierMapping, AccountClassifierMapping, ResponsibleClassifierMapping, CounterpartyClassifierMapping, \
    PricingPolicyMapping, InstrumentMapping, CurrencyMapping, InstrumentTypeMapping, PaymentSizeDetailMapping, \
    DailyPricingModelMapping, PriceDownloadSchemeMapping, InstrumentClassifierMapping, AccountTypeMapping, \
    PriceDownloadScheme, Task, PricingConditionMapping

from poms.portfolios.models import Portfolio
from poms.currencies.models import Currency
from poms.instruments.models import PricingPolicy, Instrument, InstrumentType, DailyPricingModel, PaymentSizeDetail, \
    PricingCondition
from poms.counterparties.models import Counterparty, Responsible
from poms.accounts.models import Account, AccountType

from poms.obj_attrs.models import GenericAttributeType, GenericAttribute, GenericClassifier
from poms.common import formula
from django.core.exceptions import ValidationError as CoreValidationError
from rest_framework.exceptions import ValidationError

from .filters import SchemeContentTypeFilter
from .models import CsvDataImport, CsvImportScheme
from .serializers import CsvDataImportSerializer, CsvImportSchemeSerializer

from django.utils.translation import ugettext
from logging import getLogger

_l = getLogger('poms.csv_import')

from datetime import date, datetime

from io import StringIO
import csv


from storages.backends.sftpstorage import SFTPStorage
SFS = SFTPStorage()

from tempfile import NamedTemporaryFile



def generate_file_report(instance, master_user, type, name):
    _l.debug('instance %s' % instance)

    columns = ['Row number']

    columns = columns + instance.stats[0]['error_data']['columns']['imported_columns']
    columns = columns + instance.stats[0]['error_data']['columns']['data_matching']

    columns.append('Error Message')
    columns.append('Reaction')

    rows_content = []

    _l.info(instance.stats)

    for errorRow in instance.stats:

        _l.info('errorRow %s' % errorRow)

        localResult = []

        localResult.append(errorRow['original_row_index'])

        localResult = localResult + errorRow['error_data']['data']['imported_columns']
        localResult = localResult + errorRow['error_data']['data']['data_matching']

        localResult.append(str(errorRow['error_message']))
        localResult.append(str(errorRow['error_reaction']))

        localResultWrapper = []

        for item in localResult:

            localResultWrapper.append('"' + str(item) + '"')

        rows_content.append(localResultWrapper)

    columnRow = ','.join(columns)

    result = []

    result.append('Type, ' + 'Transaction Import')
    result.append('Error handle, ' + instance.error_handler)
    # result.append('Filename, ' + instance.file.name)
    result.append('Mode, ' + instance.mode)
    result.append('Import Rules - if object is not found, ' + instance.missing_data_handler)
    # result.push('Entity, ' + vm.scheme.content_type)

    result.append('Rows total, ' + str(instance.total_rows - 1))

    rowsSuccessTotal = 0
    rowsSkippedCount = 0
    rowsFailedCount = 0

    # rowsSkippedCount = instance.stats.filter(function (item) {
    # return item.error_reaction === 'Skipped';
    # }).length
    #
    #  rowsFailedCount = instance.stats.filter(function (item) {
    # return item.error_reaction !== 'Skipped';
    # }).length

    for item in instance.stats:
        if item['error_reaction'] == 'Skipped':
            rowsSkippedCount = rowsSkippedCount + 1

    for item in instance.stats:
        if item['error_reaction'] != 'Skipped':
            rowsFailedCount = rowsFailedCount + 1

    if instance.error_handler == 'break':

        index = instance.stats[0]['original_row_index']

        rowsSuccessTotal = index - 1  # get row before error
        rowsSuccessTotal = rowsSuccessTotal - 1  # exclude headers

    else:
        rowsSuccessTotal = instance.total_rows - 1 - rowsFailedCount - rowsSkippedCount

    if rowsSuccessTotal < 0:
        rowsSuccessTotal = 0

    result.append('Rows success import, ' + str(rowsSuccessTotal))
    result.append('Rows omitted, ' + str(rowsSkippedCount))
    result.append('Rows fail import, ' + str(rowsFailedCount))

    result.append('\n')
    result.append(columnRow)

    for contentRow in rows_content:
        contentRowStr = list(map(str, contentRow))

        # _l.debug('contentRowStr %s ' % contentRowStr)

        result.append(','.join(contentRowStr))

    # _l.debug('result %s ' % result)

    result = '\n'.join(result)

    current_date_time = now().strftime("%Y-%m-%d-%H-%M")

    file_name = 'file_report_%s.csv' % current_date_time

    file_report = FileReport()

    _l.debug('generate_file_report uploading file ')

    file_report.upload_file(file_name=file_name, text=result, master_user=master_user)
    file_report.master_user = master_user
    file_report.name = "%s %s" % (name, current_date_time)
    file_report.file_name = file_name
    file_report.type = type
    file_report.notes = 'System File'

    file_report.save()

    _l.debug('file_report %s' % file_report)
    _l.debug('file_report %s' % file_report.file_url)

    return file_report.pk


def get_row_data(row, csv_fields):
    csv_row_dict = {}

    for csv_field in csv_fields:

        if csv_field.column - 1 < len(row):
            row_value = row[csv_field.column - 1]

            csv_row_dict[csv_field.name] = row_value

        else:

            csv_row_dict[csv_field.name] = ''

    return csv_row_dict


def get_row_data_converted(row, csv_fields, csv_row_dict_raw, context, conversion_errors):
    csv_row_dict = {}

    for csv_field in csv_fields:

        if csv_field.column - 1 < len(row):

            try:

                executed_expression = safe_eval(csv_field.name_expr, names=csv_row_dict_raw, context=context)

                csv_row_dict[csv_field.name] = executed_expression

            except (ExpressionEvalError, TypeError, Exception, KeyError):

                csv_row_dict[csv_field.name] = ugettext('Invalid expression')

                error = {
                    'name': csv_field.name,
                    'value': ugettext('Invalid expression')
                }

                conversion_errors.append(error)

        else:

            csv_row_dict[csv_field.name] = ''

    return csv_row_dict


def get_field_type(field):
    if field.system_property_key is not None:
        return 'system_attribute'
    else:
        return 'dynamic_attribute'


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

            _l.info('result %s' % result)

            if 'user_code' in result:
                item_result = Model.objects.get(master_user_id=result['master_user'], user_code=result['user_code'])

        except Model.DoesNotExist:

            item_result = None

    return item_result


def process_csv_file(master_user,
                     scheme,
                     file,
                     error_handler,
                     missing_data_handler,
                     classifier_handler,
                     context,
                     task_instance,
                     update_state,
                     mode,
                     process_result_handler, member):

    csv_fields = scheme.csv_fields.all()
    entity_fields = scheme.entity_fields.all()

    errors = []
    results = []

    row_index = 0

    delimiter = task_instance.delimiter.encode('utf-8').decode('unicode_escape')

    reader = csv.reader(file, delimiter=delimiter, quotechar=task_instance.quotechar,
                        strict=False, skipinitialspace=True)

    for row_index, row in enumerate(reader):

        if row_index != 0:

            instance = {}
            instance['_row_index'] = row_index
            instance['_row'] = row

            if scheme.content_type.model != 'pricehistory' and scheme.content_type.model != 'currencyhistory':
                instance['master_user'] = master_user
                instance['attributes'] = []

            inputs_error = []
            executed_expressions = []

            csv_row_dict_raw = {}

            error_row = {
                'level': 'info',
                'error_message': '',
                'original_row_index': row_index,
                'inputs': csv_row_dict_raw,
                'original_row': row,
                'error_data': {
                    'columns': {
                        'imported_columns': [],
                        'converted_imported_columns': [],
                        'data_matching': []
                    },
                    'data': {
                        'imported_columns': [],
                        'converted_imported_columns': [],
                        'data_matching': []
                    }
                },
                'error_reaction': 'Success'
            }

            csv_row_dict_raw = get_row_data(row, csv_fields)

            executed_filter_expression = True

            if scheme.filter_expr:

                try:
                    executed_filter_expression = safe_eval(scheme.filter_expr, names=csv_row_dict_raw, context={})
                except (ExpressionEvalError, TypeError, Exception, KeyError):

                    _l.info('Filter expression error')

                    return

            if executed_filter_expression:

                error_row['inputs'] = csv_row_dict_raw

                for key, value in csv_row_dict_raw.items():
                    error_row['error_data']['columns']['imported_columns'].append(key)
                    error_row['error_data']['data']['imported_columns'].append(value)

                conversion_errors = []

                csv_row_dict = get_row_data_converted(row, csv_fields, csv_row_dict_raw, {}, conversion_errors)

                # _l.info('csv_row_dict %s' % csv_row_dict)

                for key, value in csv_row_dict.items():
                    error_row['error_data']['columns']['converted_imported_columns'].append(
                        key + ': Conversion Expression')
                    error_row['error_data']['data']['converted_imported_columns'].append(value)

                if len(conversion_errors) > 0:

                    inputs_messages = []

                    for input_error in inputs_error:
                        message = '[{0}] (Imported column conversion expression, value: "{1}")'.format(
                            input_error['field'].name, input_error['reason'])

                        inputs_messages.append(message)

                    error_row['error_message'] = error_row['error_message'] + '\n' + '\n' + ugettext(
                        'Can\'t process fields: %(messages)s') % {
                                                     'messages': ', '.join(str(m) for m in inputs_messages)
                                                 }

                    if error_handler == 'break':
                        error_row['error_reaction'] = 'Break import'
                        error_row['level'] = 'error'
                        errors.append(error_row)

                        return results, errors
                    else:
                        error_row['level'] = 'error'
                        error_row['error_reaction'] = 'Continue import'

                mapping_map = {
                    'counterparties': CounterpartyMapping,
                    'responsibles': ResponsibleMapping,
                    'accounts': AccountMapping,
                    'portfolios': PortfolioMapping,
                    'pricing_policy': PricingPolicyMapping,
                    'instrument': InstrumentMapping,
                    'instrument_type': InstrumentTypeMapping,
                    'type': AccountTypeMapping,
                    'price_download_scheme': PriceDownloadSchemeMapping,
                    'daily_pricing_model': DailyPricingModelMapping,
                    'payment_size_detail': PaymentSizeDetailMapping,
                    'pricing_condition': PricingConditionMapping,
                    'currency': CurrencyMapping,
                    'pricing_currency': CurrencyMapping,
                    'accrued_currency': CurrencyMapping
                }

                relation_map = {
                    'counterparties': Counterparty,
                    'responsibles': Responsible,
                    'accounts': Account,
                    'portfolios': Portfolio,
                    'pricing_policy': PricingPolicy,
                    'instrument': Instrument,
                    'instrument_type': InstrumentType,
                    'type': AccountType,
                    'currency': Currency,
                    'pricing_currency': Currency,
                    'accrued_currency': Currency
                }

                classifier_mapping_map = {
                    'portfolio': PortfolioClassifierMapping,
                    'instrument': InstrumentClassifierMapping,
                    'account': AccountClassifierMapping,
                    'responsible': ResponsibleClassifierMapping,
                    'counterparty': CounterpartyClassifierMapping
                }

                instance_property_to_default_ecosystem_property = {
                    'pricing_currency': 'currency',
                    'accrued_currency': 'currency',
                    'type': 'account_type'
                }

                for entity_field in entity_fields:

                    key = entity_field.system_property_key

                    if entity_field.expression != '':

                        error_row['error_data']['columns']['data_matching'].append(entity_field.name)

                        if get_field_type(entity_field) == 'system_attribute':

                            executed_expression = None

                            # _l.info('entity_field.expression %s' % entity_field.expression)
                            # _l.info('csv_row_dict %s' % csv_row_dict)

                            try:
                                # context=self.report.context
                                executed_expression = safe_eval(entity_field.expression, names=csv_row_dict,
                                                                context={})

                                executed_expressions.append(executed_expression)

                                # _l.info('executed_expression %s ' % executed_expression)

                                if key in mapping_map:

                                    try:

                                        instance[key] = mapping_map[key].objects.get(master_user=master_user,
                                                                                     value=executed_expression).content_object

                                    except (mapping_map[key].DoesNotExist, KeyError):

                                        try:

                                            _l.info('Lookup by user code %s' % executed_expression)

                                            if key == 'price_download_scheme':
                                                instance[key] = PriceDownloadScheme.objects.get(master_user=master_user,
                                                                                              scheme_name=executed_expression)

                                            elif key == 'daily_pricing_model':
                                                instance[key] = DailyPricingModel.objects.get(
                                                    system_code=executed_expression)

                                            elif key == 'pricing_condition':
                                                instance[key] = PricingCondition.objects.get(
                                                    system_code=executed_expression)

                                            elif key == 'payment_size_detail':

                                                instance[key] = PaymentSizeDetail.objects.get(
                                                    system_code=executed_expression)

                                            else:

                                                instance[key] = relation_map[key].objects.get(master_user=master_user,
                                                                                              user_code=executed_expression)

                                        except (relation_map[key].DoesNotExist, KeyError):

                                            if missing_data_handler == 'set_defaults':

                                                ecosystem_default = EcosystemDefault.objects.get(
                                                    master_user=master_user)

                                                eco_key = key

                                                if key in instance_property_to_default_ecosystem_property:
                                                    eco_key = instance_property_to_default_ecosystem_property[key]

                                                if hasattr(ecosystem_default, eco_key):
                                                    instance[key] = getattr(ecosystem_default, eco_key)
                                                else:
                                                    _l.info("Can't set default value for %s" % key)
                                            else:

                                                inputs_error.append(
                                                    {"field": entity_field,
                                                     "reason": "Relation does not exists"}
                                                )

                                                # inputs_error.append(entity_field)

                                                _l.debug('Mapping for key does not exist', key)
                                                _l.debug('Expression', executed_expression)


                                else:

                                    # _l.info('key %s' % key)

                                    if key == 'user_code':

                                        if len(executed_expression) <= 25:

                                            instance[key] = executed_expression

                                        else:

                                            inputs_error.append(
                                                {"field": entity_field,
                                                 "reason": "The imported User Code is too large. It should be limited with 25 symbols."}
                                            )

                                    else:

                                        instance[key] = executed_expression

                                    # _l.info('date instance[key] %s' % instance[key])

                                    # if key == 'date':
                                    #
                                    #     try:
                                    #
                                    #         instance[key] = formula._parse_date(instance[key])
                                    #
                                    #         _l.info('date instance[key] %s' % instance[key])
                                    #
                                    #     except (ExpressionEvalError, TypeError):
                                    #
                                    #         inputs_error.append(
                                    #             {"field": entity_field,
                                    #              "reason": "Invalid Expression"}
                                    #         )


                            except (ExpressionEvalError, TypeError, Exception, KeyError):

                                if missing_data_handler == 'set_defaults':

                                    _l.info('ExpressionEvalError Settings Default %s' % ExpressionEvalError)

                                    ecosystem_default = EcosystemDefault.objects.get(
                                        master_user=master_user)

                                    eco_key = key

                                    if key in instance_property_to_default_ecosystem_property:
                                        eco_key = instance_property_to_default_ecosystem_property[key]

                                    if hasattr(ecosystem_default, eco_key):
                                        instance[key] = getattr(ecosystem_default, eco_key)
                                    else:
                                        _l.info("Can't set default value for %s" % key)

                                else:

                                    _l.info('ExpressionEvalError Appending Error %s' % ExpressionEvalError)

                                    inputs_error.append(
                                        {"field": entity_field,
                                         "reason": "Invalid Expression"}
                                    )

                                    executed_expressions.append(ugettext('Invalid expression'))

                            # _l.info('executed_expression %s' % executed_expression)

                        if get_field_type(entity_field) == 'dynamic_attribute':

                            executed_attr = {}
                            executed_attr['dynamic_attribute_id'] = entity_field.dynamic_attribute_id

                            executed_expression = None

                            try:
                                # context=self.report.context
                                executed_expression = safe_eval(entity_field.expression, names=csv_row_dict,
                                                                context={})

                                executed_expressions.append(executed_expression)

                            except (ExpressionEvalError, TypeError, Exception, KeyError):

                                # inputs_error.append(entity_field)
                                inputs_error.append(
                                    {"field": entity_field,
                                     "reason": "Invalid Expression"}
                                )

                                executed_expressions.append(ugettext('Invalid expression'))

                            attr_type = GenericAttributeType.objects.get(pk=executed_attr['dynamic_attribute_id'])

                            if attr_type.value_type == 30:

                                if scheme.content_type.model in classifier_mapping_map:

                                    try:
                                        executed_attr['executed_expression'] = classifier_mapping_map[
                                            scheme.content_type.model].objects.get(
                                            master_user=master_user,
                                            value=executed_expression, attribute_type=attr_type).content_object

                                    except (classifier_mapping_map[scheme.content_type.model].DoesNotExist, KeyError):

                                        try:

                                            # _l.info('Lookup by name in classifier')

                                            executed_attr['executed_expression'] = GenericClassifier.objects.get(
                                                attribute_type=attr_type, name=executed_expression)

                                        except (GenericClassifier.DoesNotExist, KeyError):

                                            if classifier_handler == 'append':

                                                classifier_obj = GenericClassifier.objects.create(
                                                    attribute_type=attr_type,
                                                    name=executed_expression)

                                                executed_attr['executed_expression'] = classifier_obj

                                            else:

                                                executed_attr['executed_expression'] = None

                                                # inputs_error.append(entity_field)
                                                #
                                                # _l.info('%s classifier mapping  does not exist' % scheme.content_type.model)
                                                # _l.info('expresion: %s ' % executed_expression)

                            else:

                                executed_attr['executed_expression'] = executed_expression

                            instance['attributes'].append(executed_attr)

                error_row['error_data']['data']['data_matching'] = executed_expressions

                if inputs_error:

                    inputs_messages = []

                    for input_error in inputs_error:
                        message = '[{0}] ({1})'.format(input_error['field'].name, input_error['reason'])

                        inputs_messages.append(message)

                    error_row['level'] = 'error'
                    error_row['error_message'] = error_row['error_message'] + '\n' + '\n' + ugettext(
                        'Can\'t process fields: %(inputs)s') % {
                                                     'inputs': ', '.join(str(m) for m in inputs_messages)}

                    error_row['error_reaction'] = 'Continue import'

                    if error_handler == 'break':
                        error_row['level'] = 'error'
                        error_row['error_reaction'] = 'Break import'
                        errors.append(error_row)

                        return results, errors

                    errors.append(error_row)

                else:

                    # error_row['error_reaction'] = 'Success'

                    instance, error_row = process_result_handler(instance, error_row, scheme, error_handler, mode,
                                                                 member, master_user)

                    results.append(instance)
                    errors.append(error_row)

                    if error_handler == 'break' and error_row['level'] == 'error':
                        error_row['error_reaction'] = 'Break import'
                        return results, errors

            else:

                error_row['level'] = 'info'
                error_row['error_message'] = 'Row was skipped'
                error_row['error_reaction'] = 'Skipped'
                errors.append(error_row)

        row_index = row_index + 1

        task_instance.processed_rows = row_index

        # _l.info('task_instance.processed_rows: %s', task_instance.processed_rows)

        update_state(task_id=task_instance.task_id, state=Task.STATUS_PENDING,
                     meta={'processed_rows': task_instance.processed_rows,
                           'total_rows': task_instance.total_rows, 'scheme_name': scheme.scheme_name,
                           'file_name': task_instance.filename})

    return results, errors


class ValidateHandler:

    def create_simple_instance(self, scheme, result):

        Model = apps.get_model(app_label=scheme.content_type.app_label, model_name=scheme.content_type.model)

        result_without_many_to_many = {}

        many_to_many_fields = ['counterparties', 'responsibles', 'accounts', 'portfolios']
        system_fields = ['_row_index', '_row']

        for key, value in result.items():

            if key != 'attributes':

                if key not in many_to_many_fields and key not in system_fields:
                    result_without_many_to_many[key] = value

        try:
            instance = Model(**result_without_many_to_many)
        except (ValidationError, IntegrityError):

            _l.info("Validation error create simple instance %s" % result)

            instance = None

        return instance

    def attributes_full_clean(self, instance, attributes):

        for result_attr in attributes:

            attr_type = GenericAttributeType.objects.get(pk=result_attr['dynamic_attribute_id'])

            if attr_type:

                attribute = GenericAttribute(content_object=instance, attribute_type=attr_type)

                # _l.info('result_attr', result_attr)
                # _l.info('attribute', attribute)

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

                attribute.object_id = 1  # To pass object id check

                attribute.full_clean()

    def instance_full_clean(self, scheme, result, error_handler, error_row):

        try:

            instance = self.create_simple_instance(scheme, result)

            if instance:

                # self.fill_with_relation_attributes(instance, result)
                if scheme.content_type.model != 'pricehistory' and scheme.content_type.model != 'currencyhistory':
                    self.attributes_full_clean(instance, result['attributes'])

                instance.full_clean()

        except CoreValidationError as e:

            error_row['error_reaction'] = 'Continue import'
            error_row['level'] = 'error'
            error_row['error_message'] = error_row['error_message'] + ugettext(
                'Validation error %(error)s ') % {
                                             'error': e
                                         },

    def instance_overwrite_full_clean(self, scheme, result, item, error_handler, error_row):

        # _l.info('Overwrite item %s' % item)

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

        except CoreValidationError as e:

            error_row['error_reaction'] = 'Continue import'
            error_row['level'] = 'error'
            error_row['error_message'] = error_row['error_message'] + ugettext(
                'Validation error %(error)s ') % {
                                             'error': e
                                         }

            if error_handler == 'break':
                error_row['error_reaction'] = 'Break import'

    def full_clean_result(self, result_item, error_row, scheme, error_handler, mode, member, master_user):

        item = get_item(scheme, result_item)

        if mode == 'overwrite' and item:

            self.instance_overwrite_full_clean(scheme, result_item, item, error_handler, error_row)

        elif mode == 'overwrite' and not item:

            self.instance_full_clean(scheme, result_item, error_handler, error_row)

        elif mode == 'skip' and not item:

            self.instance_full_clean(scheme, result_item, error_handler, error_row)

        elif mode == 'skip' and item:

            error_row['level'] = 'error'
            error_row['error_reaction'] = 'Skipped'
            error_row['error_message'] = error_row['error_message'] + str(ugettext(
                'Entry already exists '))

        return result_item, error_row

    def _row_count(self, file, instance):

        delimiter = instance.delimiter.encode('utf-8').decode('unicode_escape')

        reader = csv.reader(file, delimiter=delimiter, quotechar=instance.quotechar,
                            strict=False, skipinitialspace=True)

        row_index = 0

        for row_index, row in enumerate(reader):
            pass
        return row_index

    def process(self, instance, update_state):

        _l.info('ValidateHandler.process: initialized')

        scheme_id = instance.scheme.id
        error_handler = instance.error_handler
        missing_data_handler = instance.missing_data_handler
        classifier_handler = instance.classifier_handler
        delimiter = instance.delimiter
        mode = instance.mode
        master_user = instance.master_user
        member = instance.member

        scheme = CsvImportScheme.objects.get(pk=scheme_id)

        try:
            with SFS.open(instance.file_path, 'rb') as f:
                with NamedTemporaryFile() as tmpf:
                    _l.info('tmpf')
                    _l.info(tmpf)

                    for chunk in f.chunks():
                        tmpf.write(chunk)
                    tmpf.flush()

                    with open(tmpf.name, mode='rt', encoding=instance.encoding, errors='ignore') as cfr:
                        instance.total_rows = self._row_count(cfr, instance)
                        update_state(task_id=instance.task_id, state=Task.STATUS_PENDING,
                                     meta={'total_rows': instance.total_rows, 'scheme_name': instance.scheme.scheme_name, 'file_name': instance.filename})

                    with open(tmpf.name, mode='rt', encoding=instance.encoding, errors='ignore') as cf:

                        context = {}

                        results, process_errors = process_csv_file(master_user, scheme, cf, error_handler, missing_data_handler,
                                                                   classifier_handler,
                                                                   context, instance, update_state, mode, self.full_clean_result, member)

                        _l.info('ValidateHandler.process_csv_file: finished')
                        _l.info('ValidateHandler.process_csv_file process_errors %s: ' % len(process_errors))

                        instance.imported = len(results)
                        instance.stats = process_errors
        except Exception as e:

            _l.info(e)
            _l.info('Can\'t process file', exc_info=True)
            instance.error_message = ugettext("Invalid file format or file already deleted.")
        finally:
            # import_file_storage.delete(instance.file_path)
            SFS.delete(instance.file_path)

        if instance.stats and len(instance.stats):
            instance.stats_file_report = generate_file_report(instance, master_user, 'csv_import.validate',
                                                              'Simple Data Import Validation')

        return instance


@shared_task(name='csv_import.data_csv_file_import_validate', bind=True)
def data_csv_file_import_validate(self, instance):
    handler = ValidateHandler()

    setattr(instance, 'task_id', current_task.request.id)

    handler.process(instance, self.update_state)

    return instance


class ImportHandler:

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

        try:
            instance = Model.objects.create(**result_without_many_to_many)
        except (ValidationError, IntegrityError):
            instance = None

        return instance

    def add_permissions(self, instance, scheme, member, master_user):

        groups = Group.objects.filter(master_user=master_user)

        _l.debug('Add permissions for %s' % instance)

        _l.debug('len groups for %s' % len(list(groups)))
        _l.debug('len member groups for %s' % member.groups.all())

        for group in groups:

            permission_table = group.permission_table

            if permission_table and 'data' in permission_table:

                table = None

                for item in permission_table['data']:
                    if item['content_type'] == scheme.content_type.app_label + '.' + scheme.content_type.model:
                        table = item['data']

                _l.debug('content_type %s' % scheme.content_type.app_label + '.' + scheme.content_type.model)
                _l.debug('table %s' % table)

                if table:

                    manage_codename = 'manage_' + scheme.content_type.model
                    change_codename = 'change_' + scheme.content_type.model
                    view_codename = 'view_' + scheme.content_type.model

                    manage_permission = Permission.objects.get(content_type=scheme.content_type,
                                                               codename=manage_codename)
                    change_permission = Permission.objects.get(content_type=scheme.content_type,
                                                               codename=change_codename)
                    view_permission = Permission.objects.get(content_type=scheme.content_type, codename=view_codename)

                    for member_group in member.groups.all():

                        if member_group.id == group.id:

                            if 'creator_manage' in table and table['creator_manage']:
                                perm = GenericObjectPermission.objects.update_or_create(object_id=instance.id,
                                                                                        content_type=scheme.content_type,
                                                                                        group=group,
                                                                                        permission=manage_permission)

                            if 'creator_change' in table and table['creator_change']:
                                perm = GenericObjectPermission.objects.update_or_create(object_id=instance.id,
                                                                                        content_type=scheme.content_type,
                                                                                        group=group,
                                                                                        permission=change_permission)

                            if 'creator_view' in table and table['creator_view']:
                                perm = GenericObjectPermission.objects.update_or_create(object_id=instance.id,
                                                                                        content_type=scheme.content_type,
                                                                                        group=group,
                                                                                        permission=view_permission)
                        else:

                            if 'other_manage' in table and table['other_manage']:
                                perm = GenericObjectPermission.objects.update_or_create(object_id=instance.id,
                                                                                        content_type=scheme.content_type,
                                                                                        group=group,
                                                                                        permission=manage_permission)
                            if 'other_change' in table and table['other_change']:
                                perm = GenericObjectPermission.objects.update_or_create(object_id=instance.id,
                                                                                        content_type=scheme.content_type,
                                                                                        group=group,
                                                                                        permission=change_permission)
                            if 'other_view' in table and table['other_view']:
                                perm = GenericObjectPermission.objects.update_or_create(object_id=instance.id,
                                                                                        content_type=scheme.content_type,
                                                                                        group=group,
                                                                                        permission=view_permission)

    def is_inherit_rights(self, scheme, member):

        result = False

        if scheme.content_type.model == 'account' or scheme.content_type.model == 'instrument':

            for group in member.groups.all():

                permission_table = group.permission_table

                if permission_table and 'data' in permission_table:

                    table = None

                    for item in permission_table['data']:
                        if item['content_type'] == scheme.content_type.app_label + '.' + scheme.content_type.model:
                            table = item['data']

                    if table:

                        if table['inherit_rights']:
                            result = True

        return result

    def add_inherited_permissions(self, instance, scheme, member, master_user):

        _l.debug('add_inherited_permissions')

        if scheme.content_type.model == 'account':

            if instance.type:
                for perm in instance.type.object_permissions.all():
                    type_codename = perm.permission.codename.split('_')[0]
                    account_perm = Permission.objects.get(codename=type_codename + '_' + 'account')

                    GenericObjectPermission.objects.create(group=perm.group, object_id=instance.id,
                                                           content_type=scheme.content_type,
                                                           permission=account_perm)

        if scheme.content_type.model == 'instrument':
            if instance.instrument_type:
                for perm in instance.instrument_type.object_permissions.all():
                    type_codename = perm.permission.codename.split('_')[0]
                    account_perm = Permission.objects.get(codename=type_codename + '_' + 'instrument')

                    GenericObjectPermission.objects.create(group=perm.group, object_id=instance.id,
                                                           content_type=scheme.content_type,
                                                           permission=account_perm)

    def save_instance(self, scheme, result, error_handler, error_row, member, master_user):

        try:

            instance = self.create_simple_instance(scheme, result)

            _l.info('ImportHandler save_instance %s ' % instance)

            if instance:

                self.fill_with_relation_attributes(instance, result)
                if scheme.content_type.model != 'pricehistory' and scheme.content_type.model != 'currencyhistory':
                    self.fill_with_dynamic_attributes(instance, result['attributes'])
                    self.add_permissions(instance, scheme, member, master_user)

                    if self.is_inherit_rights(scheme, member):
                        self.add_inherited_permissions(instance, scheme, member, master_user)

                instance.save()

        except ValidationError as e:

            error_row['error_reaction'] = 'Continue import'
            error_row['level'] = 'error'
            error_row['error_message'] = error_row['error_message'] + ugettext(
                'Validation error %(error)s ') % {
                                             'error': e
                                         }

    def overwrite_instance(self, scheme, result, item, error_handler, error_row, member, master_user):

        # _l.info('Overwrite item %s' % item)

        _l.info('ImportHandler overwrite_instance %s ' % item)

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
                self.add_permissions(item, scheme, member, master_user)

            item.save()

        except ValidationError as e:

            error_row['error_reaction'] = 'Continue import'
            error_row['level'] = 'error'
            error_row['error_message'] = error_row['error_message'] + str(ugettext(
                'Validation error %(error)s ') % {
                                                                              'error': e
                                                                          })

    def import_result(self, result_item, error_row, scheme, error_handler, mode, member, master_user):

        # _l.info('ImportHandler.result_item %s' % result_item)

        item = get_item(scheme, result_item)

        if mode == 'overwrite' and item:

            # _l.info('Overwrite instance')

            self.overwrite_instance(scheme, result_item, item, error_handler, error_row, member, master_user)

        elif mode == 'overwrite' and not item:

            _l.info('Create instance')

            self.save_instance(scheme, result_item, error_handler, error_row, member, master_user)

        elif mode == 'skip' and not item:

            _l.info('Create instance')

            self.save_instance(scheme, result_item, error_handler, error_row, member, master_user)

        elif mode == 'skip' and item:

            # _l.info('Skip instance %s')

            error_row['level'] = 'error'
            error_row['error_message'] = error_row['error_message'] + error_row[
                'error_message']

        return result_item, error_row

    def _row_count(self, file, instance):

        delimiter = instance.delimiter.encode('utf-8').decode('unicode_escape')

        reader = csv.reader(file, delimiter=delimiter, quotechar=instance.quotechar,
                            strict=False, skipinitialspace=True)

        row_index = 0

        for row_index, row in enumerate(reader):
            pass
        return row_index

    def process(self, instance, update_state):

        _l.info('ImportHandler.process: initialized')

        scheme_id = instance.scheme.id
        error_handler = instance.error_handler
        missing_data_handler = instance.missing_data_handler
        classifier_handler = instance.classifier_handler
        delimiter = instance.delimiter
        mode = instance.mode
        master_user = instance.master_user
        member = instance.member

        _l.info('ImportHandler.mode %s' % mode)

        scheme = CsvImportScheme.objects.get(pk=scheme_id)

        try:
            with SFS.open(instance.file_path, 'rb') as f:
                with NamedTemporaryFile() as tmpf:
                    _l.info('tmpf')
                    _l.info(tmpf)

                    for chunk in f.chunks():
                        tmpf.write(chunk)
                    tmpf.flush()

                    with open(tmpf.name, mode='rt', encoding=instance.encoding, errors='ignore') as cfr:
                        instance.total_rows = self._row_count(cfr, instance)
                        update_state(task_id=instance.task_id, state=Task.STATUS_PENDING,
                                          meta={'total_rows': instance.total_rows, 'scheme_name': instance.scheme.scheme_name, 'file_name': instance.filename})

                    with open(tmpf.name, mode='rt', encoding=instance.encoding, errors='ignore') as cf:

                        context = {}

                        results, process_errors = process_csv_file(master_user, scheme, cf, error_handler, missing_data_handler,
                                                                   classifier_handler,
                                                                   context, instance, update_state, mode, self.import_result, member)

                        _l.info('ImportHandler.process_csv_file: finished')
                        _l.info('ImportHandler.process_csv_file process_errors %s: ' % len(process_errors))

                        instance.imported = len(results)
                        instance.stats = process_errors
        except Exception as e:

            _l.info(e)
            _l.info('Can\'t process file', exc_info=True)
            instance.error_message = ugettext("Invalid file format or file already deleted.")
        finally:
            # import_file_storage.delete(instance.file_path)
            SFS.delete(instance.file_path)

        if instance.stats and len(instance.stats):
            instance.stats_file_report = generate_file_report(instance, master_user, 'csv_import.import',
                                                              'Simple Data Import')

        return instance


@shared_task(name='csv_import.data_csv_file_import', bind=True)
def data_csv_file_import(self, instance):
    handler = ImportHandler()

    setattr(instance, 'task_id', current_task.request.id)

    handler.process(instance, self.update_state)

    return instance
