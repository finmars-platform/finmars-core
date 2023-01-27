import os
import csv
import json
import os
import re
import traceback
from datetime import date
from tempfile import NamedTemporaryFile

from django.db import transaction
from django.utils.timezone import now
from filtration import Expression
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string

from poms.accounts.models import Account
from poms.celery_tasks.models import CeleryTask
from poms.common import formula
from poms.common.models import ProxyUser, ProxyRequest
from poms.common.storage import get_storage
from poms.common.websockets import send_websocket_message
from poms.counterparties.models import Counterparty, Responsible
from poms.currencies.models import Currency
from poms.file_reports.models import FileReport
from poms.instruments.models import Instrument, InstrumentType, DailyPricingModel, PaymentSizeDetail, Periodicity, \
    AccrualCalculationModel
from poms.integrations.models import ComplexTransactionImportScheme
from poms.portfolios.models import Portfolio
from poms.procedures.models import RequestDataFileProcedureInstance
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.system_messages.handlers import send_system_message
from poms.transaction_import.models import ProcessType, TransactionImportResult, \
    TransactionImportProcessItem, TransactionImportProcessPreprocessItem, TransactionImportBookedTransaction, \
    TransactionImportConversionItem
from poms.transaction_import.serializers import TransactionImportResultSerializer
from poms.transactions.handlers import TransactionTypeProcess
from poms.transactions.models import TransactionTypeInput
from poms.users.models import EcosystemDefault

storage = get_storage()

import logging

_l = logging.getLogger('poms.transaction_import')

props_map = {
    Account: 'account',
    Currency: 'currency',
    Instrument: 'instrument',
    InstrumentType: 'instrument_type',
    Counterparty: 'counterparty',
    Responsible: 'responsible',
    Strategy1: 'strategy1',
    Strategy2: 'strategy2',
    Strategy3: 'strategy3',
    DailyPricingModel: 'daily_pricing_model',
    PaymentSizeDetail: 'payment_size_detail',
    Portfolio: 'portfolio',
    Periodicity: 'periodicity',
    AccrualCalculationModel: 'accrual_calculation_model',
}


class TransactionImportProcess(object):

    def __init__(self, task_id, procedure_instance_id=None):

        self.task = CeleryTask.objects.get(pk=task_id)
        self.parent_task = self.task.parent

        _l.info('TransactionImportProcess.Task %s. init' % self.task)

        self.task.status = CeleryTask.STATUS_PENDING
        self.task.save()

        self.procedure_instance = None
        if procedure_instance_id:
            self.procedure_instance = RequestDataFileProcedureInstance.objects.get(id=procedure_instance_id)

            _l.info(
                'TransactionImportProcess.Task %s. init procedure_instance %s' % (self.task, self.procedure_instance))

        self.master_user = self.task.master_user
        self.member = self.task.member

        self.proxy_user = ProxyUser(self.member, self.master_user)
        self.proxy_request = ProxyRequest(self.proxy_user)

        self.scheme = ComplexTransactionImportScheme.objects.get(pk=self.task.options_object['scheme_id'])

        self.execution_context = self.task.options_object['execution_context']
        self.file_path = self.task.options_object['file_path']
        self.preprocess_file = self.task.options_object['preprocess_file']

        self.ecosystem_default = EcosystemDefault.objects.get(master_user=self.master_user)

        self.find_default_rule_scenario()

        self.result = TransactionImportResult()
        self.result.task = self.task
        self.result.scheme = self.scheme

        self.process_type = ProcessType.CSV

        self.find_process_type()

        self.file_items = []  # items from provider  (json, csv, excel)
        self.raw_items = []  # items from provider  (json, csv, excel)
        self.conversion_items = []  # items with applied converions
        self.preprocessed_items = []  # items with calculated variables applied
        self.items = []  # result items that will be passed to TransactionTypeProcess

        self.context = {
            'master_user': self.master_user,
            'member': self.member,
            'request': self.proxy_request
        }

        import_system_message_performed_by = self.member.username
        import_system_message_title = 'Transaction import (start)'

        if self.execution_context and self.execution_context["started_by"] == 'procedure':
            import_system_message_performed_by = 'System'
            import_system_message_title = 'Transaction import from broker (start)'

        send_system_message(master_user=self.master_user,
                            performed_by=import_system_message_performed_by,
                            section='import',
                            type='success',
                            title=import_system_message_title,
                            description=self.member.username + ' started import with scheme ' + self.scheme.name,
                            )

    def generate_file_report(self):

        _l.info('TransactionImportProcess.generate_file_report error_handler %s' % self.scheme.error_handler)
        _l.info(
            'TransactionImportProcess.generate_file_report missing_data_handler %s' % self.scheme.missing_data_handler)

        result = []

        result.append('Type, Transaction Import')
        result.append('Scheme, ' + self.scheme.user_code)
        result.append('Error handle, ' + self.scheme.error_handler)

        if self.result.file_name:
            result.append('Filename, ' + self.result.file_name)

        result.append('Import Rules - if object is not found, ' + self.scheme.missing_data_handler)

        success_rows_count = 0
        error_rows_count = 0
        skip_rows_count = 0

        for result_item in self.result.items:

            if result_item.status == 'error':
                error_rows_count = error_rows_count + 1

            if result_item.status == 'success':
                success_rows_count = success_rows_count + 1

            if 'skip' in result_item.status:
                skip_rows_count = skip_rows_count + 1

        result.append('Rows total, %s' % self.result.total_rows)
        result.append('Rows success import, %s' % success_rows_count)
        result.append('Rows fail import, %s' % error_rows_count)
        result.append('Rows skipped import, %s' % skip_rows_count)

        columns = ['Row Number', 'Status', 'Message']

        column_row_list = []

        for item in columns:
            column_row_list.append('"' + str(item) + '"')

        column_row = ','.join(column_row_list)

        result.append(column_row)

        for result_item in self.result.items:

            content = []

            content.append(str(result_item.row_number))
            content.append(result_item.status)

            if result_item.error_message:
                content.append(result_item.error_message)
            elif result_item.message:
                content.append(result_item.message)
            else:
                content.append('')

            content_row_list = []

            for item in content:
                content_row_list.append('"' + str(item) + '"')

            content_row = ','.join(content_row_list)

            result.append(content_row)

        result = '\n'.join(result)

        current_date_time = now().strftime("%Y-%m-%d-%H-%M")

        file_name = 'file_report_%s_task_%s.csv' % (current_date_time, self.task.id)

        file_report = FileReport()

        _l.info('TransactionImportProcess.generate_file_report uploading file')

        file_report.upload_file(file_name=file_name, text=result, master_user=self.master_user)
        file_report.master_user = self.master_user
        file_report.name = 'Transaction Import %s (Task %s).csv' % (current_date_time, self.task.id)
        file_report.file_name = file_name
        file_report.type = 'transaction_import.import'
        file_report.notes = 'System File'
        file_report.content_type = 'text/csv'

        file_report.save()

        _l.info('TransactionImportProcess.file_report %s' % file_report)
        _l.info('TransactionImportProcess.file_report %s' % file_report.file_url)

        return file_report

    def generate_json_report(self):

        serializer = TransactionImportResultSerializer(instance=self.result, context=self.context)

        result = serializer.data

        # _l.debug('self.result %s' % self.result.__dict__)

        # _l.debug('generate_json_report.result %s' % result)

        current_date_time = now().strftime("%Y-%m-%d-%H-%M")
        file_name = 'file_report_%s_task_%s.json' % (current_date_time, self.task.id)

        file_report = FileReport()

        _l.info('TransactionImportProcess.generate_json_report uploading file')

        file_report.upload_file(file_name=file_name, text=json.dumps(result, indent=4, default=str),
                                master_user=self.master_user)
        file_report.master_user = self.master_user
        file_report.name = 'Transaction Import %s (Task %s).json' % (current_date_time, self.task.id)
        file_report.file_name = file_name
        file_report.type = 'transaction_import.import'
        file_report.notes = 'System File'
        file_report.content_type = 'application/json'

        file_report.save()

        _l.info('TransactionImportProcess.json_report %s' % file_report)
        _l.info('TransactionImportProcess.json_report %s' % file_report.file_url)

        return file_report

    def find_process_type(self):

        if self.task.options_object and 'items' in self.task.options_object:
            self.process_type = ProcessType.JSON
        elif '.json' in self.file_path:
            self.process_type = ProcessType.JSON
        elif '.xlsx' in self.file_path:
            self.process_type = ProcessType.EXCEL
        elif '.csv' in self.file_path:
            self.process_type = ProcessType.CSV

        _l.info('TransactionImportProcess.Task %s. process_type %s' % (self.task, self.process_type))

    def get_default_relation(self, field):

        i = field.transaction_type_input

        model_class = i.content_type.model_class()

        key = props_map[model_class]

        v = None

        if hasattr(self.ecosystem_default, key):
            v = getattr(self.ecosystem_default, key)

        return v

    def find_default_rule_scenario(self):

        rule_scenarios = self.scheme.rule_scenarios.prefetch_related('transaction_type', 'fields',
                                                                     'fields__transaction_type_input').all()

        self.default_rule_scenario = None

        for scenario in rule_scenarios:
            if scenario.is_default_rule_scenario:
                self.default_rule_scenario = scenario

    def get_rule_value_for_item(self, item):

        try:
            return formula.safe_eval(self.scheme.rule_expr, names=item.inputs)
        except Exception as e:

            _l.info('TransactionImportProcess.Task %s. get_rule_value_for_item Exception %s' % (self.task, e))
            _l.info('TransactionImportProcess.Task %s. get_rule_value_for_item Traceback %s' % (
                self.task, traceback.format_exc()))

            return None

    def convert_value(self, item, field, value):
        i = field.transaction_type_input

        if i.value_type == TransactionTypeInput.STRING:
            return str(value)

        if i.value_type == TransactionTypeInput.SELECTOR:
            return str(value)

        elif i.value_type == TransactionTypeInput.NUMBER:
            return float(value)

        elif i.value_type == TransactionTypeInput.DATE:
            if not isinstance(value, date):
                return formula._parse_date(value)
            else:
                return value

        elif i.value_type == TransactionTypeInput.RELATION:
            model_class = i.content_type.model_class()

            v = None

            try:

                v = model_class.objects.get(master_user=self.master_user, user_code=value)

            except Exception:

                _l.error("User code %s not found for %s " % (value, field.transaction_type_input.name))

            if not v:

                if self.scheme.missing_data_handler == 'set_defaults':

                    v = self.get_default_relation(field)

                else:
                    item.status = 'error'
                    item.error_message = item.error_message + ' Can\'t find relation of ' + \
                                         '[' + field.transaction_type_input.name + ']' + '(value:' + \
                                         value + ')'

            return v

    def get_fields_for_item(self, item, rule_scenario):

        fields = {}

        for field in rule_scenario.fields.all():
            try:
                field_value = formula.safe_eval(field.value_expr, names=item.inputs,
                                                context=self.context)
                field_value = self.convert_value(item, field, field_value)
                fields[field.transaction_type_input.name] = field_value

            except Exception as e:

                item.status = 'error'
                item.error_message = item.error_message + 'Exception ' + str(e)

                _l.error('TransactionImportProcess.Task %s. get_fields_for_item %s field %s Exception %s' % (
                    self.task, item, field, e))
                _l.error('TransactionImportProcess.Task %s. get_fields_for_item %s field %s Traceback %s' % (
                    self.task, item, field, traceback.format_exc()))

        return fields

    def book(self, item, rule_scenario):

        _l.info(
            'TransactionImportProcess.Task %s. book INIT item %s rule_scenario %s' % (self.task, item, rule_scenario))

        with transaction.atomic():

            try:

                fields = self.get_fields_for_item(item, rule_scenario)

                transaction_type_process_instance = TransactionTypeProcess(
                    linked_import_task=self.task,
                    transaction_type=rule_scenario.transaction_type,
                    default_values=fields,
                    context=self.context,
                    uniqueness_reaction=self.scheme.book_uniqueness_settings,
                    member=self.member,
                    execution_context="import"
                )

                transaction_type_process_instance.process()

                if transaction_type_process_instance.uniqueness_status == 'skip':
                    item.status = 'skip'
                    item.error_message = item.error_message + 'Unique code already exist. Skip'

                if transaction_type_process_instance.uniqueness_status == 'error':
                    item.status = 'error'
                    item.error_message = item.error_message + 'Unique code already exist. Error'

                item.processed_rule_scenarios.append(rule_scenario)

                trn = TransactionImportBookedTransaction(
                    code=transaction_type_process_instance.complex_transaction.code,
                    text=transaction_type_process_instance.complex_transaction.text,
                    transaction_unique_code=transaction_type_process_instance.complex_transaction.transaction_unique_code,
                )

                item.booked_transactions.append(trn)

                item.status = 'success'
                item.message = "Transaction Booked %s" % transaction_type_process_instance.complex_transaction

                _l.info('TransactionImportProcess.Task %s. book SUCCESS item %s rule_scenario %s' % (
                    self.task, item, rule_scenario))

                self.task.update_progress(
                    {
                        'current': self.result.processed_rows,
                        'total': len(self.items),
                        'percent': round(self.result.processed_rows / (len(self.items) / 100)),
                        'description': 'Going to book %s' % (rule_scenario.transaction_type.user_code)
                    }
                )

            except Exception as e:

                item.status = 'error'
                item.error_message = item.error_message + 'Book Exception: ' + str(e)

                _l.error("TransactionImportProcess.Task %s. book Exception %s " % (self.task, e))
                _l.error("TransactionImportProcess.Task %s. book Traceback %s " % (self.task, traceback.format_exc()))

                transaction.set_rollback(True)

    def fill_with_file_items(self):

        _l.info('TransactionImportProcess.Task %s. fill_with_raw_items INIT %s' % (self.task, self.process_type))

        try:

            if self.process_type == ProcessType.JSON:
                try:
                    _l.info("Trying to get json items from task object options")
                    items = self.task.options_object['items']

                    self.result.total_rows = len(items)

                    self.file_items = items

                except Exception as e:
                    _l.info("Trying to get json items from file")

                    with storage.open(self.file_path, 'rb') as f:

                        self.file_items = json.loads(f.read())

            if self.process_type == ProcessType.CSV:

                _l.info('ProcessType.CSV self.file_path %s' % self.file_path)

                with storage.open(self.file_path, 'rb') as f:

                    with NamedTemporaryFile() as tmpf:

                        for chunk in f.chunks():
                            tmpf.write(chunk)
                        tmpf.flush()

                        # TODO check encoding (maybe should be taken from scheme)
                        with open(tmpf.name, mode='rt', encoding='utf_8_sig', errors='ignore') as cf:

                            # TODO check quotechar (maybe should be taken from scheme)
                            reader = csv.reader(cf, delimiter=self.scheme.delimiter, quotechar='"',
                                                strict=False, skipinitialspace=True)

                            column_row = None

                            for row_index, row in enumerate(reader):

                                if row_index == 0:
                                    column_row = row

                                else:

                                    file_item = {}

                                    for column_index, value in enumerate(row):
                                        key = column_row[column_index]
                                        file_item[key] = value

                                    self.file_items.append(file_item)


                            self.result.total_rows = len(self.file_items)

            if self.process_type == ProcessType.EXCEL:

                with storage.open(self.file_path, 'rb') as f:

                    with NamedTemporaryFile() as tmpf:

                        for chunk in f.chunks():
                            tmpf.write(chunk)
                        tmpf.flush()

                        os.link(tmpf.name, tmpf.name + '.xlsx')

                        _l.info('self.file_path %s' % self.file_path)
                        _l.info('tmpf.name %s' % tmpf.name)

                        wb = load_workbook(filename=tmpf.name + '.xlsx')

                        if self.scheme.spreadsheet_active_tab_name and self.scheme.spreadsheet_active_tab_name in wb.sheetnames:
                            ws = wb[self.scheme.spreadsheet_active_tab_name]
                        else:
                            ws = wb.active

                        reader = []

                        if self.scheme.spreadsheet_start_cell == 'A1':

                            for r in ws.rows:
                                reader.append([cell.value for cell in r])

                        else:

                            start_cell_row_number = int(re.search(r'\d+', self.scheme.spreadsheet_start_cell)[0])
                            start_cell_letter = self.scheme.spreadsheet_start_cell.split(str(start_cell_row_number))[0]

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

                        column_row = None

                        for row_index, row in enumerate(reader):

                            if row_index == 0:
                                column_row = row

                            else:

                                file_item = {}

                                for column_index, value in enumerate(row):
                                    key = column_row[column_index]
                                    file_item[key] = value

                                self.file_items.append(file_item)

                        self.result.total_rows = len(self.file_items)

            _l.info(
                'TransactionImportProcess.Task %s. fill_with_raw_items %s DONE items %s' % (
                    self.task, self.process_type, len(self.raw_items)))

        except Exception as e:

            _l.error('TransactionImportProcess.Task %s. fill_with_raw_items %s Exception %s' % (
                self.task, self.process_type, e))
            _l.error('TransactionImportProcess.Task %s. fill_with_raw_items %s Traceback %s' % (
                self.task, self.process_type, traceback.format_exc()))

    def fill_with_raw_items(self):

        _l.info('TransactionImportProcess.Task %s. fill_with_raw_items INIT %s' % (self.task, self.process_type))

        try:

            for file_item in self.file_items:

                item = {}

                for scheme_input in self.scheme.inputs.all():

                    try:
                        item[scheme_input.name] = file_item[scheme_input.column_name]
                    except Exception as e:
                        item[scheme_input.name] = None

                self.raw_items.append(item)
            _l.info(
                'TransactionImportProcess.Task %s. fill_with_raw_items %s DONE items %s' % (
                    self.task, self.process_type, len(self.raw_items)))

        except Exception as e:

            _l.error('TransactionImportProcess.Task %s. fill_with_raw_items %s Exception %s' % (
                self.task, self.process_type, e))
            _l.error('TransactionImportProcess.Task %s. fill_with_raw_items %s Traceback %s' % (
                self.task, self.process_type, traceback.format_exc()))

    def apply_conversion_to_raw_items(self):

        # EXECUTE CONVERSIONS ON SCHEME INPUTS

        row_number = 1
        for raw_item in self.raw_items:

            conversion_item = TransactionImportConversionItem()
            conversion_item.file_inputs = self.file_items[row_number - 1]
            conversion_item.raw_inputs = raw_item
            conversion_item.conversion_inputs = {}
            conversion_item.row_number = row_number

            for scheme_input in self.scheme.inputs.all():

                try:

                    names = raw_item

                    conversion_item.conversion_inputs[scheme_input.name] = formula.safe_eval(scheme_input.name_expr,
                                                                                             names=names,
                                                                                             context={
                                                                                                 "master_user": self.master_user,
                                                                                                 "member": self.member
                                                                                             })
                except Exception as e:

                    conversion_item.conversion_inputs[scheme_input.name] = None

            self.conversion_items.append(conversion_item)

            row_number = row_number + 1

    # We have formulas that lookup for rows
    # e.g. transaction_import.find_row
    # so it means, in first iterations we will got errors in that inputs
    def recursive_preprocess(self, deep=1, current_level=0):

        if len(self.preprocessed_items) == 0:

            row_number = 1

            for conversion_item in self.conversion_items:
                preprocess_item = TransactionImportProcessPreprocessItem()
                preprocess_item.file_inputs = conversion_item.file_inputs
                preprocess_item.raw_inputs = conversion_item.raw_inputs
                preprocess_item.conversion_inputs = conversion_item.conversion_inputs
                preprocess_item.row_number = row_number
                preprocess_item.inputs = {}

                self.preprocessed_items.append(preprocess_item)

                row_number = row_number + 1

        for preprocess_item in self.preprocessed_items:

            # CREATE SCHEME INPUTS

            for scheme_input in self.scheme.inputs.all():

                key_column_name = scheme_input.column_name

                try:

                    preprocess_item.inputs[scheme_input.name] = preprocess_item.conversion_inputs[scheme_input.name]

                except Exception as e:

                    preprocess_item.inputs[scheme_input.name] = None

                    if current_level == deep:
                        _l.error('key_column_name %s' % key_column_name)
                        _l.error('scheme_input.name %s' % scheme_input.name)
                        _l.error('preprocess_item.raw_inputs %s' % preprocess_item.conversion_inputs)
                        _l.error('TransactionImportProcess.Task %s. recursive_preprocess init input %s Exception %s' % (
                            self.task, scheme_input, e))

            # CREATE CALCULATED INPUTS

            for scheme_calculated_input in self.scheme.calculated_inputs.all():
                try:

                    names = preprocess_item.inputs

                    value = formula.safe_eval(scheme_calculated_input.name_expr, names=names,
                                              context={"master_user": self.master_user,
                                                       "member": self.member,
                                                       "transaction_import": {
                                                           "items": self.preprocessed_items
                                                       }})

                    preprocess_item.inputs[scheme_calculated_input.name] = value

                except Exception as e:

                    preprocess_item.inputs[scheme_calculated_input.name] = None

                    if current_level == deep:
                        _l.error(
                            'TransactionImportProcess.Task %s. recursive_preprocess calculated_input %s Exception %s' % (
                                self.task, scheme_calculated_input, e))
                        # _l.error(
                        #     'TransactionImportProcess.Task %s. recursive_preprocess calculated_input %s Traceback %s' % (
                        #         self.task, scheme_calculated_input, traceback.format_exc()))

        if current_level < deep:
            self.recursive_preprocess(deep, current_level + 1)

    def preprocess(self):

        _l.info('TransactionImportProcess.Task %s. preprocess INIT' % self.task)

        self.recursive_preprocess(deep=2)

        for preprocessed_item in self.preprocessed_items:
            item = TransactionImportProcessItem()
            item.row_number = preprocessed_item.row_number
            item.file_inputs = preprocessed_item.file_inputs
            item.raw_inputs = preprocessed_item.raw_inputs
            item.conversion_inputs = preprocessed_item.conversion_inputs
            item.inputs = preprocessed_item.inputs

            self.items.append(item)

        _l.info(
            'TransactionImportProcess.Task %s. preprocess DONE items %s' % (self.task, len(self.preprocessed_items)))

    def process_items(self):

        _l.info('TransactionImportProcess.Task %s. process_items INIT' % self.task)

        index = 0

        for item in self.items:

            try:

                _l.info('TransactionImportProcess.Task %s. ========= process row %s/%s ========' % (
                    self.task, str(item.row_number), str(self.result.total_rows)))

                if self.scheme.filter_expression:

                    # expr = Expression.parseString("a == 1 and b == 2")
                    expr = Expression.parseString(self.scheme.filter_expression)

                    if expr(item.result_inputs):
                        # filter passed
                        pass
                    else:

                        item.status = 'skip'
                        item.message = 'Skipped due filter'

                        _l.info(
                            'TransactionImportProcess.Task %s. Row skipped due filter %s' % (
                                self.task, str(item.row_number)))
                        continue

                rule_value = self.get_rule_value_for_item(item)

                item.processed_rule_scenarios = []
                item.booked_transactions = []

                _l.info('TransactionImportProcess.Task %s. ========= process row %s/%s ======== %s ' % (
                    self.task, str(item.row_number), str(self.result.total_rows), rule_value))

                if rule_value:

                    found = False

                    for rule_scenario in self.scheme.rule_scenarios.all():

                        selector_values = rule_scenario.selector_values.all()

                        for selector_value in selector_values:

                            if selector_value.value == rule_value:
                                found = True
                                self.book(item, rule_scenario)

                    if not found:
                        item.status = 'skip'
                        item.message = 'Selector %s does not match anything in scheme' % rule_value
                else:

                    self.book(item, self.default_rule_scenario)

                self.result.processed_rows = self.result.processed_rows + 1

                send_websocket_message(data={
                    'type': 'transaction_import_status',
                    'payload': {
                        'parent_task_id': self.task.parent_id,
                        'task_id': self.task.id,
                        'state': CeleryTask.STATUS_PENDING,
                        'processed_rows': self.result.processed_rows,
                        'total_rows': self.result.total_rows,
                        'scheme_name': self.scheme.user_code,
                        'file_name': self.result.file_name}
                }, level="member",
                    context=self.context)

                self.task.update_progress(
                    {
                        'current': self.result.processed_rows,
                        'total': len(self.items),
                        'percent': round(self.result.processed_rows / (len(self.items) / 100)),
                        'description': 'Row %s processed' % self.result.processed_rows
                    }
                )



            except Exception as e:

                item.status = 'error'
                item.message = 'Error %s' % e

                _l.error('TransactionImportProcess.Task %s.  ========= process row %s ======== Exception %s' % (
                    self.task, str(item.row_number), e))
                _l.error('TransactionImportProcess.Task %s.  ========= process row %s ======== Traceback %s' % (
                    self.task, str(item.row_number), traceback.format_exc()))

        self.result.items = self.items

        _l.info('TransactionImportProcess.Task %s. process_items DONE' % self.task)

    def get_verbose_result(self):

        booked_count = 0
        error_count = 0

        for item in self.result.items:
            if item.status == 'error':
                error_count = error_count + 1

            booked_count = booked_count + len(item.booked_transactions)

        result = 'Processed %s rows and successfully booked %s transactions. Error rows %s' % (
            len(self.items), booked_count, error_count)

        return result

    def process(self):

        try:

            self.process_items()

        except Exception as e:

            _l.error('TransactionImportProcess.Task %s. process Exception %s' % (self.task, e))
            _l.error('TransactionImportProcess.Task %s. process Traceback %s' % (self.task, traceback.format_exc()))

            self.result.error_message = 'General Import Error. Exception %s' % e

            if self.execution_context and self.execution_context["started_by"] == 'procedure':
                send_system_message(master_user=self.master_user,
                                    performed_by='System',
                                    description="Can't process file. Exception %s" % e)

        finally:

            if self.task.options_object and 'items' in self.task.options_object:
                pass
            else:
                storage.delete(self.file_path)

            send_websocket_message(data={
                'type': 'transaction_import_status',
                'payload': {
                    'parent_task_id': self.task.parent_id,
                    'task_id': self.task.id,
                    'state': CeleryTask.STATUS_DONE,
                    'processed_rows': self.result.processed_rows,
                    'total_rows': self.result.total_rows,
                    'file_name': self.result.file_name,
                    'scheme': self.scheme.id,
                    'scheme_object': {
                        'id': self.scheme.id,
                        'scheme_name': self.scheme.user_code,
                        'delimiter': self.scheme.delimiter,
                        'error_handler': self.scheme.error_handler,
                        'missing_data_handler': self.scheme.missing_data_handler
                    }}
            }, level="member",
                context=self.context)

            self.task.result_object = TransactionImportResultSerializer(instance=self.result, context=self.context).data

            self.result.reports = []

            self.result.reports.append(self.generate_file_report())
            self.result.reports.append(self.generate_json_report())

            system_message_title = 'New transactions (import from file)'
            system_message_description = 'New transactions created (Import scheme - ' + str(
                self.scheme.name) + ') - ' + str(len(self.items))

            import_system_message_title = 'Transaction import (finished)'

            system_message_performed_by = self.member.username

            if self.process_type == ProcessType.JSON:

                if self.execution_context and self.execution_context["started_by"] == 'procedure':

                    system_message_title = 'New transactions (import from broker)'
                    system_message_performed_by = 'System'

                    import_system_message_title = 'Transaction import from broker (finished)'

                    # if self.execution_context['date_from']:


                        # TODO too long, need refactor
                        # from poms.portfolios.tasks import calculate_portfolio_register_record, \
                        #     calculate_portfolio_register_price_history
                        #
                        # calculate_portfolio_register_record.apply_async(link=[
                        #     calculate_portfolio_register_price_history.s(
                        #         date_from=str(self.execution_context['date_from']))
                        # ])

            send_system_message(master_user=self.master_user,
                                performed_by=system_message_performed_by,
                                section='import',
                                type='success',
                                title="Import Finished. Prices Recalculation Required",
                                description="Please, run schedule or execute procedures to calculate portfolio prices and nav history")

        send_system_message(master_user=self.master_user,
                            performed_by=system_message_performed_by,
                            section='import',
                            type='success',
                            title=import_system_message_title,
                            attachments=[self.result.reports[0].id, self.result.reports[1].id])

        send_system_message(master_user=self.master_user,
                            performed_by=system_message_performed_by,
                            section='transactions',
                            type='success',
                            title=system_message_title,
                            description=system_message_description,
                            )

        if self.procedure_instance and self.procedure_instance.schedule_instance:
            self.procedure_instance.schedule_instance.run_next_procedure()

        self.task.add_attachment(self.result.reports[0].id)
        self.task.add_attachment(self.result.reports[1].id)

        self.task.verbose_result = self.get_verbose_result()

        self.task.status = CeleryTask.STATUS_DONE
        self.task.save()

        return self.result

    def whole_file_preprocess(self):

        if self.scheme.data_preprocess_expression:

            names = {}

            names['data'] = self.file_items

            try:

                _l.info("whole_file_preprocess  names %s" % names)

                self.file_items = formula.safe_eval(self.scheme.data_preprocess_expression, names=names, context=self.context)

                _l.info("whole_file_preprocess  self.raw_items %s" % self.raw_items)

            except Exception as e:

                _l.error("Could not execute preoprocess expression. Error %s" % e)

        _l.info("whole_file_preprocess.file_items %s" % len(self.file_items))

        return self.file_items
