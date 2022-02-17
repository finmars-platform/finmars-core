import re
import uuid
import hashlib

from celery import shared_task, chord, current_task
from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.timezone import now
from openpyxl.utils import column_index_from_string

from poms.common.crypto.AESCipher import AESCipher
from poms.common.crypto.RSACipher import RSACipher
from poms.common.formula import safe_eval, ExpressionEvalError
from poms.common.utils import date_now
from poms.file_reports.models import FileReport
from poms.obj_perms.models import GenericObjectPermission
from poms.pricing.models import InstrumentPricingPolicy
from poms.system_messages.handlers import send_system_message

from poms.users.models import EcosystemDefault, Group
from django.apps import apps
from django.contrib.contenttypes.models import ContentType

from poms.integrations.models import CounterpartyMapping, AccountMapping, ResponsibleMapping, PortfolioMapping, \
    PortfolioClassifierMapping, AccountClassifierMapping, ResponsibleClassifierMapping, CounterpartyClassifierMapping, \
    PricingPolicyMapping, InstrumentMapping, CurrencyMapping, InstrumentTypeMapping, PaymentSizeDetailMapping, \
    DailyPricingModelMapping, InstrumentClassifierMapping, AccountTypeMapping, \
    Task, PricingConditionMapping, TransactionFileResult

from poms.portfolios.models import Portfolio
from poms.currencies.models import Currency
from poms.instruments.models import PricingPolicy, Instrument, InstrumentType, DailyPricingModel, PaymentSizeDetail, \
    PricingCondition, AccrualCalculationModel, Periodicity
from poms.counterparties.models import Counterparty, Responsible
from poms.accounts.models import Account, AccountType

from poms.obj_attrs.models import GenericAttributeType, GenericAttribute, GenericClassifier
from poms.common import formula
from django.core.exceptions import ValidationError as CoreValidationError
from rest_framework.exceptions import ValidationError

from .filters import SchemeContentTypeFilter
from .models import CsvDataImport, CsvImportScheme
from .serializers import CsvDataImportSerializer, CsvImportSchemeSerializer, CsvDataFileImport

from django.utils.translation import ugettext
from logging import getLogger
from openpyxl import load_workbook

from ..common.websockets import send_websocket_message

import traceback


_l = getLogger('poms.csv_import')

from datetime import date, datetime

from io import StringIO
import csv

from storages.backends.sftpstorage import SFTPStorage

SFS = SFTPStorage()

from tempfile import NamedTemporaryFile


class ProxyUser(object):

    def __init__(self, member, master_user):
        self.member = member
        self.master_user = master_user


class ProxyRequest(object):

    def __init__(self, user):
        self.user = user


def generate_file_report(instance, master_user, type, name):
    columns = ['Row number']

    columns = columns + instance.stats[0]['error_data']['columns']['imported_columns']
    columns = columns + instance.stats[0]['error_data']['columns']['data_matching']

    columns.append('Error Message')
    columns.append('Reaction')

    rows_content = []

    for errorRow in instance.stats:

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
        if item['error_reaction'] != 'Skipped' and item['error_reaction'] != 'Success':
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

        result.append(','.join(contentRowStr))

    result = '\n'.join(result)

    current_date_time = now().strftime("%Y-%m-%d-%H-%M")

    file_name = 'file_report_%s.csv' % current_date_time

    file_report = FileReport()

    file_report.upload_file(file_name=file_name, text=result, master_user=master_user)
    file_report.master_user = master_user
    file_report.name = "%s %s" % (name, current_date_time)
    file_report.file_name = file_name
    file_report.type = type
    file_report.notes = 'System File'

    file_report.save()

    return file_report.pk


def generate_file_report_simple(instance, type, name):
    try:
        columns = ['Row number']

        columns.append('Message')

        rows_content = []

        for errorRow in instance.items:

            if errorRow['original_row_index'] != 0:

                localResult = []

                localResult.append(errorRow['original_row_index'])

                if errorRow['error_message']:
                    localResult.append(str(errorRow['error_message']))
                else:
                    localResult.append('OK')

                localResultWrapper = []

                for item in localResult:
                    localResultWrapper.append('"' + str(item) + '"')

                rows_content.append(localResultWrapper)

        columnRow = ','.join(columns)

        result = []

        result.append('Type, ' + type)
        # result.append('Filename, ' + instance.file.name)
        result.append('Mode, ' + instance.mode)
        # result.append('Import Rules - if object is not found, ' + instance.missing_data_handler)
        # result.push('Entity, ' + vm.scheme.content_type)

        result.append('Rows total, ' + str(instance.total_rows))

        rowsSuccessTotal = 0
        rowsSkippedCount = 0
        rowsFailedCount = 0

        # result.append('Rows success import, ' + str(rowsSuccessTotal))
        # result.append('Rows omitted, ' + str(rowsSkippedCount))
        # result.append('Rows fail import, ' + str(rowsFailedCount))

        result.append('\n')
        result.append(columnRow)

        for contentRow in rows_content:
            contentRowStr = list(map(str, contentRow))

            result.append(','.join(contentRowStr))

        result = '\n'.join(result)

        current_date_time = now().strftime("%Y-%m-%d-%H-%M")

        file_name = 'Unified Instrument Import %s.csv' % current_date_time

        file_report = FileReport()

        file_report.upload_file(file_name=file_name, text=result, master_user=instance.master_user)
        file_report.master_user = instance.master_user
        file_report.name = "%s %s" % (name, current_date_time)
        file_report.file_name = file_name
        file_report.type = type
        file_report.notes = 'System File'

        file_report.save()

        return file_report.pk
    except Exception as e:
        _l.info("Generate file error occured %s" % e)
        _l.info(traceback.format_exc())
        return None


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
        except Exception as e:

            # _l.debug('get_item pricehistory exception %s' % e)

            item_result = None


    elif scheme.content_type.model == 'currencyhistory':

        try:

            item_result = Model.objects.get(currency=result['currency'], pricing_policy=result['pricing_policy'],
                                            date=result['date'])

        except Exception as e:

            traceback.format_exc()

            # _l.debug('get_item currencyhistory exception %s' % e)

            item_result = None

    else:

        try:

            if 'user_code' in result:
                item_result = Model.objects.get(master_user_id=result['master_user'], user_code=result['user_code'])

        except Exception as e:

            # _l.debug('get_item entity exception %s' % e)

            item_result = None

    return item_result


def update_row_with_calculated_data(csv_row_dict, inputs, calculated_inputs):
    for i in calculated_inputs:

        try:
            value = formula.safe_eval(i.name_expr, names=inputs)
            csv_row_dict[i.name] = value

        except Exception:
            _l.debug('can\'t process calculated input: %s|%s', i.name, i.column, exc_info=True)
            csv_row_dict[i.name] = None

    return csv_row_dict


def process_csv_file(master_user,
                     scheme,
                     original_file,
                     file,
                     error_handler,
                     missing_data_handler,
                     classifier_handler,
                     context,
                     task_instance,
                     update_state,
                     mode,
                     process_result_handler,
                     member,
                     execution_context=None):
    csv_fields = scheme.csv_fields.all()
    entity_fields = scheme.entity_fields.all()
    calculated_inputs = list(scheme.calculated_inputs.all())

    errors = []
    results = []

    reader = []

    processed_row_index = 0

    delimiter = task_instance.delimiter.encode('utf-8').decode('unicode_escape')

    if '.csv' in task_instance.filename or (execution_context and execution_context["started_by"] == 'procedure'):

        reader = csv.reader(file, delimiter=delimiter, quotechar=task_instance.quotechar,
                            strict=False, skipinitialspace=True)

    elif '.xlsx' in task_instance.filename:
        _l.info('trying to parse excel %s ' % task_instance.filename)


        wb = load_workbook(filename=original_file)

        ws = wb.active

        _l.info('ws %s' % ws)

        reader = []

        if task_instance.scheme.spreadsheet_start_cell == 'A1':

            for r in ws.rows:
                reader.append([cell.value for cell in r])

        else:

            start_cell_row_number = int(re.search(r'\d+', task_instance.scheme.spreadsheet_start_cell)[0])
            start_cell_letter = task_instance.scheme.spreadsheet_start_cell.split(str(start_cell_row_number))[0]

            start_cell_column_number = column_index_from_string(start_cell_letter)


            row_number = 1

            for r in ws.rows:

                row_values = []

                if row_number >= start_cell_row_number:

                    for cell in r:


                        if cell.column >= start_cell_column_number:
                            row_values.append(cell.value)

                    reader.append(row_values)

                row_number = row_number + 1


        _l.info('reader %s' % reader)

    for row_index, row in enumerate(reader):

        if row_index != 0:

            try:

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

                try:
                    csv_row_dict_raw = get_row_data(row, csv_fields)
                except Exception as e:
                    raise Exception("Can't get row data")

                executed_filter_expression = True

                if scheme.filter_expr:

                    try:
                        executed_filter_expression = safe_eval(scheme.filter_expr, names=csv_row_dict_raw, context={})
                    except (ExpressionEvalError, TypeError, Exception, KeyError):
                        raise Exception("Can evaluate filter expression")

                if executed_filter_expression:

                    error_row['inputs'] = csv_row_dict_raw

                    for key, value in csv_row_dict_raw.items():
                        error_row['error_data']['columns']['imported_columns'].append(key)
                        error_row['error_data']['data']['imported_columns'].append(value)

                    conversion_errors = []

                    csv_row_dict = get_row_data_converted(row, csv_fields, csv_row_dict_raw, {}, conversion_errors)

                    csv_row_dict = update_row_with_calculated_data(csv_row_dict, csv_fields, calculated_inputs)

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

                    excluded_fields = ['price_download_scheme', 'daily_pricing_model']

                    for entity_field in entity_fields:

                        key = entity_field.system_property_key

                        if entity_field.expression != '' and key not in excluded_fields:

                            error_row['error_data']['columns']['data_matching'].append(entity_field.name)

                            if get_field_type(entity_field) == 'system_attribute':

                                executed_expression = None

                                try:
                                    # context=self.report.context

                                    if entity_field.use_default and scheme.content_type.model == 'instrument':
                                        instance[key] = None # will be set from instrument type
                                    else:

                                        executed_expression = safe_eval(entity_field.expression, names=csv_row_dict,
                                                                        context={})

                                        executed_expressions.append(executed_expression)

                                        if key in mapping_map:

                                            try:

                                                instance[key] = mapping_map[key].objects.get(master_user=master_user,
                                                                                             value=executed_expression).content_object

                                            except (mapping_map[key].DoesNotExist, KeyError):

                                                try:

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
                                                            _l.debug("Can't set default value for %s" % key)
                                                    else:

                                                        inputs_error.append(
                                                            {"field": entity_field,
                                                             "reason": "Relation does not exists"}
                                                        )

                                        else:

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

                                except (ExpressionEvalError, TypeError, Exception, KeyError):

                                    if missing_data_handler == 'set_defaults':

                                        ecosystem_default = EcosystemDefault.objects.get(
                                            master_user=master_user)

                                        eco_key = key

                                        if key in instance_property_to_default_ecosystem_property:
                                            eco_key = instance_property_to_default_ecosystem_property[key]

                                        if hasattr(ecosystem_default, eco_key):
                                            instance[key] = getattr(ecosystem_default, eco_key)
                                        else:
                                            _l.debug("Can't set default value for %s" % key)

                                    else:

                                        _l.debug('ExpressionEvalError Appending Error %s key %s' % (
                                            ExpressionEvalError, key))

                                        instance[key] = None

                                        inputs_error.append(
                                            {"field": entity_field,
                                             "reason": "Invalid Expression"}
                                        )

                                        executed_expressions.append(ugettext('Invalid expression'))

                                # _l.debug('executed_expression %s' % executed_expression)

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

                                        except (
                                                classifier_mapping_map[scheme.content_type.model].DoesNotExist,
                                                KeyError):

                                            try:

                                                # _l.debug('Lookup by name in classifier')

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
                                                    # _l.debug('%s classifier mapping  does not exist' % scheme.content_type.model)
                                                    # _l.debug('expresion: %s ' % executed_expression)

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

                    else:

                        try:

                            instance, error_row = process_result_handler(instance, error_row, scheme, error_handler,
                                                                         mode,
                                                                         member, master_user)

                            results.append(instance)

                        except Exception as e:

                            _l.info('Result processing error %s ' % e)

                            traceback.format_exc()

                            raise Exception("Result processing error")

                else:

                    error_row['level'] = 'info'
                    error_row['error_message'] = 'Row was skipped'
                    error_row['error_reaction'] = 'Skipped'

            except Exception as e:

                error_row['error_message'] = error_row['error_message'] + ugettext(
                    'Unhandled Error. %s' % e)

            finally:

                if row_index != 0:  # skip header from counting
                    processed_row_index = processed_row_index + 1

                errors.append(error_row)

                task_instance.processed_rows = processed_row_index

                _l.debug('task_instance.processed_rows: %s', task_instance.processed_rows)

                send_websocket_message(data={
                    'type': 'simple_import_status',
                    'payload': {'task_id': task_instance.task_id,
                                'state': Task.STATUS_PENDING,
                                'processed_rows': task_instance.processed_rows,
                                'total_rows': task_instance.total_rows,
                                'user_code': scheme.user_code,
                                'file_name': task_instance.filename}
                }, level="member",
                    context={"master_user": master_user, "member": member})

                # Deprecated
                update_state(task_id=task_instance.task_id, state=Task.STATUS_PENDING,
                             meta={'processed_rows': task_instance.processed_rows,
                                   'total_rows': task_instance.total_rows, 'user_code': scheme.user_code,
                                   'file_name': task_instance.filename})

                if error_handler == 'break' and error_row['level'] == 'error':
                    error_row['error_reaction'] = 'Break import'

                    return results, errors

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
            instance = None

        return instance

    def attributes_full_clean(self, instance, attributes, error_handler, error_row):

        attr_type_user_code = 'Unknown'

        for result_attr in attributes:

            attr_type_user_code = 'Unknown'

            try:

                attr_type = GenericAttributeType.objects.get(pk=result_attr['dynamic_attribute_id'])

                attr_type_user_code = attr_type.user_code

                if attr_type:

                    attribute = GenericAttribute(content_object=instance, attribute_type=attr_type)

                    # _l.debug('result_attr', result_attr)
                    # _l.debug('attribute', attribute)

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

            except Exception as e:

                # _l.info("e %s" % e)

                error_row['error_reaction'] = 'Continue import'
                error_row['level'] = 'error'
                error_row['error_message'] = error_row['error_message'] + ugettext(
                    'Validation error %(error)s ') % {
                                                 'error': 'Cannot create attribute Attribute type %s, value %s' % (attr_type_user_code, result_attr['executed_expression'])
                                             }

    def instance_full_clean(self, scheme, result, error_handler, error_row):

        try:

            instance = self.create_simple_instance(scheme, result)

            if instance:

                # self.fill_with_relation_attributes(instance, result)
                if scheme.content_type.model != 'pricehistory' and scheme.content_type.model != 'currencyhistory':
                    self.attributes_full_clean(instance, result['attributes'], error_handler, error_row)

                instance.full_clean()

        except CoreValidationError as e:
            
            _l.info('instance_full_clean  e %s' % e)

            error_row['error_reaction'] = 'Continue import'
            error_row['level'] = 'error'
            error_row['error_message'] = error_row['error_message'] + ugettext(
                'Validation error %(error)s ') % {
                                             'error': 'Cannot create instance'
                                         }

    def instance_overwrite_full_clean(self, scheme, result, item, error_handler, error_row):

        # _l.debug('Overwrite item %s' % item)

        try:

            many_to_many_fields = ['counterparties', 'responsibles', 'accounts', 'portfolios']
            system_fields = ['_row_index', '_row']

            for key, value in result.items():

                if key != 'attributes':

                    if key not in many_to_many_fields and key not in system_fields:
                        setattr(item, key, value)

            # TODO import attribute validation later
            # self.fill_with_relation_attributes(item, result)
            # if scheme.content_type.model != 'pricehistory' and scheme.content_type.model != 'currencyhistory':
            #     self.attributes_full_clean(item, result['attributes'], error_handler, error_row)

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

        _l.debug('ValidateHandler.process: initialized')

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
                    for chunk in f.chunks():
                        tmpf.write(chunk)
                    tmpf.flush()

                    if '.csv' in instance.filename:

                        with open(tmpf.name, mode='rt', encoding=instance.encoding, errors='ignore') as cfr:
                            instance.total_rows = self._row_count(cfr, instance)
                            update_state(task_id=instance.task_id, state=Task.STATUS_PENDING,
                                         meta={'total_rows': instance.total_rows,
                                               'user_code': instance.scheme.user_code, 'file_name': instance.filename})

                    elif '.xlsx' in instance.filename:

                        wb = load_workbook(filename=f)

                        ws = wb.active

                        _l.info('ws %s' % ws)

                        reader = []

                        row_index = 0

                        for r in ws.rows:
                            row_index = row_index + 1

                        instance.total_rows = row_index

                        update_state(task_id=instance.task_id, state=Task.STATUS_PENDING,
                                     meta={'total_rows': instance.total_rows,
                                           'user_code': instance.scheme.user_code, 'file_name': instance.filename})


                    with open(tmpf.name, mode='rt', encoding=instance.encoding, errors='ignore') as cf:
                        context = {}

                        results, process_errors = process_csv_file(master_user, scheme, f, cf, error_handler,
                                                                   missing_data_handler,
                                                                   classifier_handler,
                                                                   context, instance, update_state, mode,
                                                                   self.full_clean_result, member)

                        _l.debug('ValidateHandler.process_csv_file: finished')
                        _l.debug('ValidateHandler.process_csv_file process_errors %s: ' % len(process_errors))

                        instance.imported = len(results)
                        instance.stats = process_errors
        except Exception as e:

            _l.debug(e)
            _l.debug('Can\'t process file', exc_info=True)
            instance.error_message = ugettext("Invalid file format or file already deleted.")
        finally:
            # import_file_storage.delete(instance.file_path)
            SFS.delete(instance.file_path)

        if instance.stats and len(instance.stats):
            instance.stats_file_report = generate_file_report(instance, master_user, 'csv_import.validate',
                                                              'Simple Data Import Validation')

            send_websocket_message(data={
                'type': 'simple_import_status',
                'payload': {'task_id': instance.task_id,
                            'state': Task.STATUS_DONE,
                            'processed_rows': instance.processed_rows,
                            'total_rows': instance.total_rows,
                            'file_name': instance.filename,
                            'stats': instance.stats,
                            'stats_file_report': instance.stats_file_report,
                            'scheme': scheme.id,
                            'scheme_object': {
                                'id': scheme.id,
                                'user_code': scheme.user_code,
                                'classifier_handler': scheme.classifier_handler,
                                'delimiter': scheme.delimiter,
                                'error_handler': scheme.error_handler,
                                'missing_data_handler': scheme.missing_data_handler,
                                'mode': scheme.mode,
                            }}
            }, level="member",
                context={"master_user": master_user, "member": member})

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

    def create_simple_instance(self, scheme, result, error_row):

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
        except (ValidationError, IntegrityError, ValueError) as e:

            _l.info('create_simple_instance %s' % e)

            instance = None


            error_row['error_reaction'] = 'Continue import'
            error_row['level'] = 'error'
            error_row['error_message'] = error_row['error_message'] + ugettext(
                'Cannot create simple instance %(error)s ') % {
                                             'error': e}

        return instance

    def add_permissions(self, instance, scheme, member, master_user):

        groups = Group.objects.filter(master_user=master_user)

        _l.debug('len groups for %s' % len(list(groups)))

        for group in groups:

            permission_table = group.permission_table

            if permission_table and 'data' in permission_table:

                table = None

                for item in permission_table['data']:
                    if item['content_type'] == scheme.content_type.app_label + '.' + scheme.content_type.model:
                        table = item['data']

                _l.debug('content_type %s' % scheme.content_type.app_label + '.' + scheme.content_type.model)
                # _l.debug('table %s' % table)

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

    def add_instrument_type_pricing_policies(self, instance, scheme, member, master_user):

        _l.debug("Add Pricing Policies instrument_type %s" % instance.instrument_type)

        if instance.instrument_type:

            InstrumentPricingPolicy.objects.filter(instrument=instance).delete()

            for pp_item in instance.instrument_type.pricing_policies.all():
                item = InstrumentPricingPolicy()

                item.instrument = instance
                item.pricing_policy = pp_item.pricing_policy
                item.pricing_scheme = pp_item.pricing_scheme
                item.notes = pp_item.notes
                item.default_value = pp_item.default_value
                item.attribute_key = pp_item.attribute_key
                item.json_data = pp_item.json_data

                item.save()

    def save_instance(self, scheme, result, error_handler, error_row, member, master_user):

        try:

            instance = self.create_simple_instance(scheme, result, error_row)

            if instance:

                self.fill_with_relation_attributes(instance, result)
                if scheme.content_type.model != 'pricehistory' and scheme.content_type.model != 'currencyhistory':
                    self.fill_with_dynamic_attributes(instance, result['attributes'])
                    self.add_permissions(instance, scheme, member, master_user)

                    if self.is_inherit_rights(scheme, member):
                        self.add_inherited_permissions(instance, scheme, member, master_user)

                if scheme.content_type.model == 'instrument':
                    self.add_instrument_type_pricing_policies(instance, scheme, member, master_user)

                instance.save()

        except Exception as e:

            _l.info("save_instance Exception %s" % e)

            error_row['error_reaction'] = 'Continue import'
            error_row['level'] = 'error'
            error_row['error_message'] = error_row['error_message'] + ugettext(
                'Validation error %(error)s ') % {
                                             'error': e
                                         }

    def overwrite_instance(self, scheme, result, item, error_handler, error_row, member, master_user):

        # _l.debug('Overwrite item %s' % item)

        # _l.debug('ImportHandler overwrite_instance %s ' % item)

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

            if scheme.content_type.model == 'instrument':
                self.add_instrument_type_pricing_policies(item, scheme, member, master_user)

            item.save()

        except ValidationError as e:

            error_row['error_reaction'] = 'Continue import'
            error_row['level'] = 'error'
            error_row['error_message'] = error_row['error_message'] + str(ugettext(
                'Validation error %(error)s ') % {
                                                                              'error': e
                                                                          })

    def import_result(self, result_item, error_row, scheme, error_handler, mode, member, master_user):

        # _l.debug('ImportHandler.result_item %s' % result_item)

        item = get_item(scheme, result_item)

        if mode == 'overwrite' and item:

            # _l.debug('Overwrite instance')

            self.overwrite_instance(scheme, result_item, item, error_handler, error_row, member, master_user)

        elif mode == 'overwrite' and not item:

            _l.debug('Create instance')

            self.save_instance(scheme, result_item, error_handler, error_row, member, master_user)

        elif mode == 'skip' and not item:

            _l.debug('Create instance')

            self.save_instance(scheme, result_item, error_handler, error_row, member, master_user)

        elif mode == 'skip' and item:

            # _l.debug('Skip instance %s')

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

        # return plain index, -1 row because of ignoring csv header row

        return row_index

    def process(self, instance, update_state, execution_context=None):

        _l.debug('ImportHandler.process: initialized')

        scheme_id = instance.scheme.id
        error_handler = instance.error_handler
        missing_data_handler = instance.missing_data_handler
        classifier_handler = instance.classifier_handler
        delimiter = instance.delimiter
        mode = instance.mode
        master_user = instance.master_user
        member = instance.member

        _l.debug('ImportHandler.mode %s' % mode)

        scheme = CsvImportScheme.objects.get(pk=scheme_id)

        try:
            with SFS.open(instance.file_path, 'rb') as f:

                with NamedTemporaryFile() as tmpf:
                    for chunk in f.chunks():
                        tmpf.write(chunk)
                    tmpf.flush()

                    if '.csv' in instance.filename or (execution_context and execution_context["started_by"] == 'procedure'):

                        with open(tmpf.name, mode='rt', encoding=instance.encoding, errors='ignore') as cfr:
                            instance.total_rows = self._row_count(cfr, instance)
                            update_state(task_id=instance.task_id, state=Task.STATUS_PENDING,
                                         meta={'total_rows': instance.total_rows,
                                               'user_code': instance.scheme.user_code, 'file_name': instance.filename})

                    elif '.xlsx' in instance.filename:

                        wb = load_workbook(filename=f)

                        ws = wb.active

                        _l.info('ws %s' % ws)

                        reader = []

                        row_index = 0

                        for r in ws.rows:
                            row_index = row_index + 1

                        instance.total_rows = row_index

                        update_state(task_id=instance.task_id, state=Task.STATUS_PENDING,
                                     meta={'total_rows': instance.total_rows,
                                           'user_code': instance.scheme.user_code, 'file_name': instance.filename})



                    with open(tmpf.name, mode='rt', encoding=instance.encoding, errors='ignore') as cf:
                        context = {}

                        results, process_errors = process_csv_file(master_user, scheme, f, cf, error_handler,
                                                                   missing_data_handler,
                                                                   classifier_handler,
                                                                   context, instance, update_state, mode,
                                                                   self.import_result, member, execution_context)

                        _l.debug('ImportHandler.process_csv_file: finished')
                        _l.debug('ImportHandler.process_csv_file process_errors %s: ' % len(process_errors))

                        instance.imported = len(results)
                        instance.stats = process_errors
        except Exception as e:

            _l.debug(e)
            _l.debug('Can\'t process file', exc_info=True)
            instance.error_message = ugettext("Invalid file format or file already deleted.")
        finally:
            # import_file_storage.delete(instance.file_path)
            SFS.delete(instance.file_path)

        if instance.stats and len(instance.stats):
            instance.stats_file_report = generate_file_report(instance, master_user, 'csv_import.import',
                                                              'Simple Data Import')

            send_websocket_message(data={
                'type': 'simple_import_status',
                'payload': {'task_id': instance.task_id,
                            'state': Task.STATUS_DONE,
                            'processed_rows': instance.processed_rows,
                            'total_rows': instance.total_rows,
                            'file_name': instance.filename,
                            'stats': instance.stats,
                            'stats_file_report': instance.stats_file_report,
                            'scheme': scheme.id,
                            'scheme_object': {
                                'id': scheme.id,
                                'user_code': scheme.user_code,
                                'classifier_handler': scheme.classifier_handler,
                                'delimiter': scheme.delimiter,
                                'error_handler': scheme.error_handler,
                                'missing_data_handler': scheme.missing_data_handler,
                                'mode': scheme.mode,
                            }}
            }, level="member",
                context={"master_user": master_user, "member": member})

            send_websocket_message(data={'type': "simple_message",
                                         'payload': {
                                             'message': "Member %s imported data with Simple Import Service" % member.username
                                         }
                                         }, level="master_user", context={"master_user": master_user, "member": member})

            if execution_context and execution_context["started_by"] == 'procedure':
                send_system_message(master_user=instance.master_user,
                                    source="Simple Import Service",
                                    text="Import Finished",
                                    file_report_id=instance.stats_file_report)
            else:
                send_system_message(master_user=instance.master_user,
                                    source="Simple Import Service",
                                    text="User %s Import Finished" % member.username,
                                    file_report_id=instance.stats_file_report)

        return instance


@shared_task(name='csv_import.data_csv_file_import', bind=True)
def data_csv_file_import(self, instance, execution_context=None):

    try:

        _l.info('data_csv_file_import %s' % instance)

        handler = ImportHandler()

        setattr(instance, 'task_id', current_task.request.id)

        handler.process(instance, self.update_state, execution_context)

        return instance

    except Exception as e:

        traceback.format_exc()

        _l.debug('data_csv_file_import decryption error %s' % e)


@shared_task(name='csv_import.data_csv_file_import_by_procedure', bind=True)
def data_csv_file_import_by_procedure(self, procedure_instance_id, transaction_file_result_id):

    with transaction.atomic():

        from poms.integrations.serializers import ComplexTransactionCsvFileImport
        from poms.procedures.models import RequestDataFileProcedureInstance

        procedure_instance = RequestDataFileProcedureInstance.objects.get(id=procedure_instance_id)
        transaction_file_result = TransactionFileResult.objects.get(id=transaction_file_result_id)

        try:

            _l.debug(
                'data_csv_file_import_by_procedure looking for scheme_user_code %s ' % procedure_instance.procedure.scheme_user_code)

            scheme = CsvImportScheme.objects.get(master_user=procedure_instance.master_user,
                                                 user_code=procedure_instance.procedure.scheme_user_code)

            text = "Data File Procedure %s. File is received, start data import" % (
                procedure_instance.procedure.user_code)

            send_system_message(master_user=procedure_instance.master_user,
                                source="Data File Procedure Service",
                                text=text)

            with SFS.open(transaction_file_result.file_path, 'rb') as f:

                try:

                    encrypted_text = f.read()

                    rsa_cipher = RSACipher()

                    aes_key = None

                    try:
                        aes_key = rsa_cipher.decrypt(procedure_instance.private_key, procedure_instance.symmetric_key)
                    except Exception as e:
                        _l.debug('data_csv_file_import_by_procedure AES Key decryption error %s' % e)

                    aes_cipher = AESCipher(aes_key)

                    decrypt_text = None

                    try:
                        decrypt_text = aes_cipher.decrypt(encrypted_text)
                    except Exception as e:
                        _l.debug('data_csv_file_import_by_procedure Text decryption error %s' % e)

                    _l.debug('data_csv_file_import_by_procedure file decrypted')

                    _l.debug('Size of decrypted text: %s' % len(decrypt_text))

                    with NamedTemporaryFile() as tmpf:

                        tmpf.write(decrypt_text.encode('utf-8'))
                        tmpf.flush()

                        file_name = '%s-%s' % (timezone.now().strftime('%Y%m%d%H%M%S'), uuid.uuid4().hex)
                        file_path = '%s/data_files/%s.dat' % (procedure_instance.master_user.token, file_name)

                        SFS.save(file_path, tmpf)

                        _l.debug('data_csv_file_import_by_procedure tmp file filled')

                        instance = CsvDataFileImport(scheme=scheme,
                                                     file_path=file_path,
                                                     filename=transaction_file_result.file_path,
                                                     member=procedure_instance.member,
                                                     master_user=procedure_instance.master_user,
                                                     delimiter=scheme.delimiter,
                                                     error_handler=scheme.error_handler,
                                                     mode=scheme.mode,
                                                     classifier_handler=scheme.classifier_handler,
                                                     missing_data_handler=scheme.missing_data_handler)

                        _l.debug('data_csv_file_import_by_procedure instance: %s' % instance)

                        current_date_time = now().strftime("%Y-%m-%d-%H-%M")

                        file_name = '%s-%s' % (timezone.now().strftime('%Y%m%d%H%M%S'), uuid.uuid4().hex)
                        file_name_hash = hashlib.md5(file_name.encode('utf-8')).hexdigest()

                        file_report = FileReport()

                        file_report.upload_file(
                            file_name='Data Procedure %s (%s).csv' % (current_date_time, file_name_hash),
                            text=decrypt_text, master_user=procedure_instance.master_user)
                        file_report.master_user = procedure_instance.master_user
                        file_report.name = "'Data Import File. Procedure ' %s %s" % (
                            procedure_instance.id, current_date_time)
                        file_report.file_name = 'Data Procedure %s (%s).csv' % (current_date_time, file_name_hash)
                        file_report.type = 'csv_import.import'
                        file_report.notes = 'Data Import File. Procedure %s' % procedure_instance.id

                        file_report.save()

                        _l.debug('file_report %s' % file_report)

                        text = "Data File Procedure %s. File is received. Start Import" % (
                            procedure_instance.procedure.user_code)

                        send_system_message(master_user=procedure_instance.master_user,
                                            source="Data File Procedure Service",
                                            text=text,
                                            file_report_id=file_report.id)

                        transaction.on_commit(
                            lambda: data_csv_file_import.apply_async(
                                kwargs={'instance': instance, 'execution_context': {'started_by': 'procedure'}}))


                except Exception as e:

                    traceback.format_exc()

                    _l.debug('data_csv_file_import_by_procedure decryption error %s' % e)

        except CsvImportScheme.DoesNotExist:

            text = "Data File Procedure %s. Can't import file, Import scheme %s is not found" % (
                procedure_instance.procedure.user_code, procedure_instance.procedure.user_code)

            send_system_message(master_user=procedure_instance.master_user,
                                source="Data File Procedure Service",
                                text=text)

            _l.debug(
                'data_csv_file_import_by_procedure scheme %s not found' % procedure_instance.procedure.user_code)

            procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
            procedure_instance.save()


def set_defaults_from_instrument_type(instrument_object, instrument_type):

    try:
        # Set system attributes

        if instrument_type.payment_size_detail:
            instrument_object['payment_size_detail'] = instrument_type.payment_size_detail.id
        else:
            instrument_object['payment_size_detail'] = None

        if instrument_type.accrued_currency:
            instrument_object['accrued_currency'] = instrument_type.accrued_currency.id
        else:
            instrument_object['accrued_currency'] = None

        instrument_object['default_price'] = instrument_type.default_price
        instrument_object['maturity_date'] = instrument_type.maturity_date
        instrument_object['maturity_price'] = instrument_type.maturity_price

        instrument_object['accrued_multiplier'] = instrument_type.accrued_multiplier
        instrument_object['default_accrued'] = instrument_type.default_accrued

        if instrument_type.exposure_calculation_model:
            instrument_object['exposure_calculation_model'] = instrument_type.exposure_calculation_model.id
        else:
            instrument_object['exposure_calculation_model'] = None

        instrument_object['long_underlying_instrument'] = instrument_type.long_underlying_instrument
        instrument_object['underlying_long_multiplier'] = instrument_type.underlying_long_multiplier

        instrument_object['short_underlying_instrument'] = instrument_type.short_underlying_instrument
        instrument_object['underlying_short_multiplier'] = instrument_type.underlying_short_multiplier

        instrument_object['long_underlying_exposure'] = instrument_type.long_underlying_exposure
        instrument_object['short_underlying_exposure'] = instrument_type.short_underlying_exposure

        instrument_object['co_directional_exposure_currency'] = instrument_type.co_directional_exposure_currency
        instrument_object['counter_directional_exposure_currency'] = instrument_type.counter_directional_exposure_currency

        # Set attributes
        instrument_object['attributes'] = []

        for attribute in instrument_type.instrument_attributes.all():

            attribute_type = GenericAttributeType.objects.get(master_user=self.instrument_type.master_user, user_code=attribute.attribute_type_user_code)

            attr = {
                'attribute_type': attribute_type.id
            }

            if attribute.value_type == 10:
                attr['value_string'] = attribute.value_string

            if attribute.value_type == 20:
                attr['value_float'] = attribute.value_float

            if attribute.value_type == 30:
                try:
                    attr['classifier'] = GenericClassifier.objects.get(attribute_type=attribute.attribute_type,
                                                           name=attribute.value_classifier).id
                except Exception as e:
                    attr['classifier'] = None

            if attribute.value_type == 40:
                attr['value_date'] = attribute.value_date

            instrument_object['attributes'].append(attr)

        # Set Event Schedules

        instrument_object['event_schedules'] = []

        for instrument_type_event in instrument_type.events.all():

            event_schedule = {
                # 'name': instrument_type_event.name,
                'event_class': instrument_type_event.data['event_class']
            }

            for item in instrument_type_event.data['items']:

                # TODO add check for value type
                if 'default_value' in item:
                    event_schedule[item['key']] = item['default_value']

            if 'items2' in instrument_type_event.data:

                for item in instrument_type_event.data['items2']:
                    if 'default_value' in item:
                        event_schedule[item['key']] = item['default_value']

            #
            event_schedule['is_auto_generated'] = True
            event_schedule['actions'] = []

            for instrument_type_action in instrument_type_event.data['actions']:
                action = {}
                action['transaction_type'] = instrument_type_action[
                    'transaction_type']  # TODO check if here user code instead of id
                action['text'] = instrument_type_action['text']
                action['is_sent_to_pending'] = instrument_type_action['is_sent_to_pending']
                action['is_book_automatic'] = instrument_type_action['is_book_automatic']

                event_schedule['actions'].append(action)

            instrument_object['event_schedules'].append(event_schedule)

        # Set Accruals

        instrument_object['accrual_calculation_schedules'] = []

        for instrument_type_accrual in instrument_type.accruals.all():

            accrual = {

            }

            for item in instrument_type_accrual.data['items']:

                # TODO add check for value type
                if 'default_value' in item:
                    accrual[item['key']] = item['default_value']


            instrument_object['accrual_calculation_schedules'].append(accrual)

        return instrument_object

    except Exception as e:
        _l.info('set_defaults_from_instrument_type e %s' % e)
        _l.info(traceback.format_exc())

        raise Exception("Instrument Type is not configured correctly %s" % e)


def set_events_for_instrument(instrument_object, data_object, instrument_type_obj):
    instrument_type = instrument_type_obj.user_code.lower()

    maturity = None

    if 'maturity' in data_object:
        maturity = data_object['maturity']

    if 'maturity_date' in data_object:
        maturity = data_object['maturity_date']

    if maturity:

        if instrument_type in ['bonds', 'convertible_bonds', 'index_linked_bonds', 'short_term_notes']:

            if len(instrument_object['event_schedules']):
                # C
                coupon_event = instrument_object['event_schedules'][0]

                # coupon_event['periodicity'] = data_object['periodicity']

                if 'first_coupon_date' in data_object:
                    coupon_event['effective_date'] = data_object['first_coupon_date']


                coupon_event['final_date'] = maturity

                # M
                expiration_event = instrument_object['event_schedules'][1]

                expiration_event['effective_date'] = maturity
                expiration_event['final_date'] = maturity

        if instrument_type in ['bond_futures', 'fx_forwards', 'forwards', 'futures', 'commodity_futures',
                               'call_options', 'etfs', 'funds',
                               'index_futures', 'index_options', 'put_options', 'tbills', 'warrants']:
            # M
            expiration_event = instrument_object['event_schedules'][0]

            expiration_event['effective_date'] = maturity
            expiration_event['final_date'] = maturity


def set_accruals_for_instrument(instrument_object, data_object, instrument_type_obj):
    # instrument_type = data_object['instrument_type']

    instrument_type = instrument_type_obj.user_code.lower()

    if instrument_type in ['bonds']:

        if len(instrument_object['accrual_calculation_schedules']):
            accrual = instrument_object['accrual_calculation_schedules'][0]

            accrual['effective_date'] = data_object['first_coupon_date']
            accrual['accrual_end_date'] = data_object['maturity']
            # accrual['accrual_size'] = data_object['accrual_size']
            # accrual['periodicity'] = data_object['periodicity']
            # accrual['periodicity_n'] = data_object['periodicity_n']


def handler_instrument_object(source_data, instrument_type, master_user, ecosystem_default, attribute_types):

    object_data = {}
    object_data = source_data.copy()

    object_data['instrument_type'] = instrument_type.id


    set_defaults_from_instrument_type(object_data, instrument_type)

    _l.info("Settings defaults for instrument done")

    try:
        object_data['pricing_currency'] = Currency.objects.get(master_user=master_user,
                                                               user_code=source_data['pricing_currency']).id
    except Exception as e:

        object_data['pricing_currency'] = ecosystem_default.currency.id

    # try:
    #     object_data['accrued_currency'] = Currency.objects.get(master_user=master_user,
    #                                                            user_code=source_data['accrued_currency']).id
    # except Exception as e:
    # 
    #     object_data['accrued_currency'] = ecosystem_default.currency.id

    object_data['accrued_currency'] = object_data['pricing_currency']
    object_data['co_directional_exposure_currency'] = object_data['pricing_currency']
    object_data['counter_directional_exposure_currency'] = object_data['pricing_currency']

    try:
        object_data['payment_size_detail'] = PaymentSizeDetail.objects.get(
            user_code=source_data['payment_size_detail']).id
    except Exception as e:

        object_data['payment_size_detail'] = ecosystem_default.payment_size_detail.id

    try:
        object_data['pricing_condition'] = PricingCondition.objects.get(
            user_code=source_data['pricing_condition']).id
    except Exception as e:

        object_data['pricing_condition'] = ecosystem_default.pricing_condition.id



    if 'maturity' in source_data and source_data['maturity'] != '':
        object_data['maturity_date'] = source_data['maturity']

    elif  'maturity_date' in source_data and source_data['maturity_date'] != '':

        if source_data['maturity_date'] == 'null' or source_data['maturity_date'] == '9999-00-00':
            object_data['maturity_date'] = '2999-01-01'
        else:
            object_data['maturity_date'] = source_data['maturity_date']
    else:
        object_data['maturity_date'] = '2999-01-01'

    object_data['attributes'] = []

    for attribute_type in attribute_types:

        lower_user_code = attribute_type.user_code.lower()

        if lower_user_code in source_data:

            attribute = {
                'attribute_type': attribute_type.id,
            }

            if attribute_type.value_type == 10:
                attribute['value_string'] = source_data[lower_user_code]

            if attribute_type.value_type == 20:
                attribute['value_float'] = source_data[lower_user_code]

            if attribute_type.value_type == 30:

                try:

                    classifier = GenericClassifier.objects.get(attribute_type=attribute_type,
                                                               name=source_data[lower_user_code])

                    attribute['classifier'] = classifier.id

                except Exception as e:
                    attribute['classifier'] = None

            if attribute_type.value_type == 40:
                attribute['value_date'] = source_data[lower_user_code]

            object_data['attributes'].append(attribute)

    _l.info("Settings attributes for instrument done")

    object_data['master_user'] = master_user.id
    object_data['manual_pricing_formulas'] = []
    # object_data['accrual_calculation_schedules'] = []
    # object_data['event_schedules'] = []
    object_data['factor_schedules'] = []


    set_events_for_instrument(object_data, source_data, instrument_type)
    _l.info("Settings events for instrument done")

    _l.info('source_data %s' % source_data)

    if 'accrual_calculation_schedules':
        if len(source_data['accrual_calculation_schedules']):

            if len(object_data['event_schedules']):
                # C
                coupon_event = object_data['event_schedules'][0]

                if 'first_payment_date' in source_data['accrual_calculation_schedules'][0]:
                    coupon_event['effective_date'] = source_data['accrual_calculation_schedules'][0]['first_payment_date']

    if 'accrual_calculation_schedules' in source_data:

        if len(source_data['accrual_calculation_schedules']):

            _l.info("Setting up accrual schedules. Init")

            if len(object_data['accrual_calculation_schedules']):

                _l.info("Setting up accrual schedules. Overwrite Existing")

                accrual = object_data['accrual_calculation_schedules'][0]

                if 'accrual_start_date' in source_data['accrual_calculation_schedules'][0]:
                    accrual['accrual_start_date'] = source_data['accrual_calculation_schedules'][0]['accrual_start_date']

                if 'first_payment_date' in source_data['accrual_calculation_schedules'][0]:
                    accrual['first_payment_date'] = source_data['accrual_calculation_schedules'][0]['first_payment_date']

                try:
                    accrual['accrual_size'] = float(source_data['accrual_calculation_schedules'][0]['accrual_size'])
                except Exception as e:
                    accrual['accrual_size'] = 0

                try:
                    accrual['periodicity_n'] = int(source_data['accrual_calculation_schedules'][0]['periodicity_n'])

                    if accrual['periodicity_n'] == 1:
                        accrual['periodicity'] = Periodicity.ANNUALLY

                    if accrual['periodicity_n'] == 2:
                        accrual['periodicity'] = Periodicity.SEMI_ANNUALLY

                    if accrual['periodicity_n'] == 4:
                        accrual['periodicity'] = Periodicity.QUARTERLY

                    if accrual['periodicity_n'] == 6:
                        accrual['periodicity'] = Periodicity.BIMONTHLY

                    if accrual['periodicity_n'] == 12:
                        accrual['periodicity'] = Periodicity.MONTHLY

                    _l.info('periodicity %s' % accrual['periodicity'])

                except Exception as e:
                    accrual['periodicity_n'] = 0

            else:

                _l.info("Setting up accrual schedules. Creating new")

                accrual = {}

                accrual['accrual_calculation_model'] = AccrualCalculationModel.ACT_365
                accrual['periodicity'] = Periodicity.ANNUALLY


                if 'accrual_start_date' in source_data['accrual_calculation_schedules'][0]:
                    accrual['accrual_start_date'] = source_data['accrual_calculation_schedules'][0]['accrual_start_date']

                if 'first_payment_date' in source_data['accrual_calculation_schedules'][0]:
                    accrual['first_payment_date'] = source_data['accrual_calculation_schedules'][0]['first_payment_date']

                try:
                    accrual['accrual_size'] = float(source_data['accrual_calculation_schedules'][0]['accrual_size'])
                except Exception as e:
                    accrual['accrual_size'] = 0

                try:
                    accrual['periodicity_n'] = int(source_data['accrual_calculation_schedules'][0]['periodicity_n'])

                    if accrual['periodicity_n'] == 1:
                        accrual['periodicity'] = Periodicity.ANNUALLY

                    if accrual['periodicity_n'] == 2:
                        accrual['periodicity'] = Periodicity.SEMI_ANNUALLY

                    if accrual['periodicity_n'] == 4:
                        accrual['periodicity'] = Periodicity.QUARTERLY

                    if accrual['periodicity_n'] == 6:
                        accrual['periodicity'] = Periodicity.BIMONTHLY

                    if accrual['periodicity_n'] == 12:
                        accrual['periodicity'] = Periodicity.MONTHLY

                    _l.info('periodicity %s' % accrual['periodicity'])

                except Exception as e:
                    accrual['periodicity_n'] = 0


                object_data['accrual_calculation_schedules'].append(accrual)
    else:
        set_accruals_for_instrument(object_data, source_data, instrument_type)

    if 'name' not in object_data and 'user_code' in object_data:
        object_data['name'] = object_data['user_code']

    if 'short_name' not in object_data and 'user_code' in object_data:
        object_data['short_name'] = object_data['user_code']

    return object_data



class UnifiedImportHandler():

    def __init__(self, instance, update_state, execution_context):
        self.instance = instance
        self.update_state = update_state
        self.execution_context = execution_context

    def get_row_data(self, row, first_row):
        csv_row_dict = {}

        index = 0
        for col in first_row:
            col_name = col.lower().replace(" ", "_")

            csv_row_dict[col_name] = row[index]

            index = index + 1

        return csv_row_dict

    def _row_count(self, file, instance):

        delimiter = instance.delimiter.encode('utf-8').decode('unicode_escape')

        reader = csv.reader(file, delimiter=delimiter, quotechar=instance.quotechar,
                            strict=False, skipinitialspace=True)

        row_index = 0

        for row_index, row in enumerate(reader):
            pass

        # return plain index, -1 row because of ignoring csv header row

        return row_index

    def process_row(self, first_row, row, item, context):

        from poms.instruments.serializers import InstrumentSerializer


        try:

            row_as_dict = self.get_row_data(row, first_row)

            item['row_as_dict'] = row_as_dict

            row_data = {}
            row_data = row_as_dict  # tmp

            instrument_type = None

            # _l.info('row_data %s' % row_data)

            skip = False

            try:

                instrument_type = InstrumentType.objects.get(master_user=self.instance.master_user,
                                                             user_code=row_as_dict['instrument_type'])


            except Exception as e:

                item['error_message'] = 'Instrument Type Does not Find'

                skip = True

            if skip == False:

                row_data = handler_instrument_object(row_as_dict, instrument_type, self.instance.master_user, self.ecosystem_default, self.attribute_types)

                if self.instance.mode == 'skip':

                    serializer = InstrumentSerializer(data=row_data, context=context)

                    is_valid = serializer.is_valid()

                    item['row_data'] = row_data

                    if is_valid:
                        serializer.save()
                    else:
                        item['error_message'] = serializer.errors

                if self.instance.mode == 'overwrite':

                    instrument = None

                    try:
                        instrument = Instrument.objects.get(user_code=row_data['user_code'],
                                                            master_user=self.instance.master_user)
                    except Instrument.DoesNotExist:
                        instrument = None

                    serializer = InstrumentSerializer(data=row_data, context=context, instance=instrument)

                    is_valid = serializer.is_valid()

                    item['row_data'] = row_data

                    if is_valid:
                        serializer.save()
                    else:
                        item['error_message'] = serializer.errors

        except Exception as e:

            _l.info("Error %s" % e)
            _l.info(traceback.format_exc())

            item['error_message'] = 'Unhandled error in row processing. Exception %s' % str(e)

        finally:

            self.instance.processed_rows = item['original_row_index']

            send_websocket_message(data={
                'type': 'simple_import_status',
                'payload': {'task_id': self.instance.task_id,
                            'state': Task.STATUS_PENDING,
                            'processed_rows': self.instance.processed_rows,
                            'total_rows': self.instance.total_rows,
                            'file_name': self.instance.filename}
            }, level="member",
                context={"master_user": self.instance.master_user, "member": self.instance.member})

    def unified_process_csv_file(self, file):

        _l.info('unified_process_csv_file mode %s' % self.instance.mode)

        errors = []
        results = []

        delimiter = self.instance.delimiter.encode('utf-8').decode('unicode_escape')

        reader = csv.reader(file, delimiter=delimiter, quotechar=self.instance.quotechar,
                            strict=False, skipinitialspace=True)

        first_row = None

        proxy_user = ProxyUser(self.instance.member, self.instance.master_user)
        proxy_request = ProxyRequest(proxy_user)

        context = {'master_user': self.instance.master_user,
                   'request': proxy_request}

        instrument_content_type = ContentType.objects.get(app_label="instruments", model='instrument')

        self.ecosystem_default = EcosystemDefault.objects.get(master_user=self.instance.master_user)
        self.attribute_types = GenericAttributeType.objects.filter(master_user=self.instance.master_user,
                                                                   content_type=instrument_content_type)

        items = []

        for row_index, row in enumerate(reader):

            item = {
                'original_row_index': row_index,
                'error_message': ''
            }

            if row_index == 0:
                first_row = row
            else:

                self.process_row(first_row, row, item, context)

            items.append(item)

        return items

    def process(self):

        _l.debug('UnifiedImportHandler.process: initialized')

        mode = self.instance.mode
        master_user = self.instance.master_user
        member = self.instance.member

        _l.debug('UnifiedImportHandler.mode %s' % mode)

        try:
            with SFS.open(self.instance.file_path, 'rb') as f:
                with NamedTemporaryFile() as tmpf:
                    for chunk in f.chunks():
                        tmpf.write(chunk)
                    tmpf.flush()

                    with open(tmpf.name, mode='rt', encoding=self.instance.encoding, errors='ignore') as cfr:
                        self.instance.total_rows = self._row_count(cfr, self.instance)
                        self.update_state(task_id=self.instance.task_id, state=Task.STATUS_PENDING,
                                          meta={'total_rows': self.instance.total_rows,
                                                'file_name': self.instance.filename})

                    with open(tmpf.name, mode='rt', encoding=self.instance.encoding, errors='ignore') as cf:
                        context = {}

                        items = self.unified_process_csv_file(cf)

                        _l.debug('UnifiedImportHandler.process_csv_file: finished')

                        self.instance.items = items
        except Exception as e:

            _l.debug(e)
            _l.debug('Can\'t process file', exc_info=True)
            self.instance.error_message = ugettext("Invalid file format or file already deleted.")
        finally:
            # import_file_storage.delete(instance.file_path)
            SFS.delete(self.instance.file_path)

        _l.info("Import here? %s" % len(self.instance.items))

        if self.instance.items and len(self.instance.items):

            self.instance.stats_file_report = generate_file_report_simple(self.instance, 'csv_import.unified_import',
                                                                          'Unified Data Import')

            _l.info('self.instance.stats_file_report %s' % self.instance.stats_file_report)

            send_websocket_message(data={
                'type': 'simple_import_status',
                'payload': {'task_id': self.instance.task_id,
                            'state': Task.STATUS_DONE,
                            'processed_rows': self.instance.processed_rows,
                            'total_rows': self.instance.total_rows,
                            'file_name': self.instance.filename,
                            'stats': self.instance.stats,
                            'stats_file_report': self.instance.stats_file_report
                            }
            }, level="member",
                context={"master_user": master_user, "member": member})

            send_websocket_message(data={'type': "simple_message",
                                         'payload': {
                                             'message': "Member %s imported data with Simple Import Service" % member.username
                                         }
                                         }, level="master_user", context={"master_user": master_user, "member": member})

            if self.execution_context and self.execution_context["started_by"] == 'procedure':
                send_system_message(master_user=self.instance.master_user,
                                    source="Unified Simple Import Service",
                                    text="Import Finished",
                                    file_report_id=self.instance.stats_file_report)
            else:
                send_system_message(master_user=self.instance.master_user,
                                    source="Unified  Simple Import Service",
                                    text="User %s Import Finished" % member.username,
                                    file_report_id=self.instance.stats_file_report)

        return self.instance


@shared_task(name='csv_import.unified_data_csv_file_import', bind=True)
def unified_data_csv_file_import(self, instance, execution_context=None):
    handler = UnifiedImportHandler(instance, self.update_state, execution_context)

    setattr(instance, 'task_id', current_task.request.id)

    handler.process()

    return instance
