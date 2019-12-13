from celery import shared_task, chord

import csv
import logging

from poms.common import formula
from poms.integrations.models import Task
from poms.integrations.storage import import_file_storage
from tempfile import NamedTemporaryFile
from django.utils.translation import ugettext
from django.db import transaction
from poms.common.utils import date_now

from poms.reconciliation.models import ReconciliationNewBankFileField, ReconciliationBankFileField
from poms.reconciliation.serializers import ReconciliationNewBankFileFieldSerializer, \
    ReconciliationBankFileFieldSerializer

_l = logging.getLogger('poms.reconciliation')


@shared_task(name='reconciliation.process_bank_file_for_reconcile', bind=True)
def process_bank_file_for_reconcile(self, instance):
    _l.info('complex_transaction_file_import: %s', instance)

    instance.processed_rows = 0

    scheme = instance.scheme
    scheme_inputs = list(scheme.inputs.all())

    recon_scenarios = list(scheme.recon_scenarios.all())

    _now = date_now()

    def _process_csv_file(file):

        instance.processed_rows = 0

        delimiter = instance.delimiter.encode('utf-8').decode('unicode_escape')

        reader = csv.reader(file, delimiter=delimiter, quotechar=instance.quotechar,
                            strict=False, skipinitialspace=True)

        instance.results = []

        for row_index, row in enumerate(reader):

            _l.info('process row: %s -> %s', row_index, row)
            if (row_index == 0 and instance.skip_first_line) or not row:
                _l.info('skip first row')
                continue

            inputs_raw = {}
            inputs = {}
            inputs_error = []
            inputs_conversion_error = []

            error_rows = {
                'level': 'info',
                'error_message': '',
                'original_row_index': row_index,
                'original_row': row,
                'error_data': {
                    'columns': {
                        'imported_columns': [],
                        'converted_imported_columns': [],
                        'transaction_type_selector': [],
                        'executed_input_expressions': []
                    },
                    'data': {
                        'imported_columns': [],
                        'converted_imported_columns': [],
                        'transaction_type_selector': [],
                        'executed_input_expressions': []
                    }
                },
                'error_reaction': "Success"
            }

            matched_selector = False

            for i in scheme_inputs:

                error_rows['error_data']['columns']['imported_columns'].append(i.name)

                try:
                    inputs_raw[i.name] = row[i.column - 1]
                    error_rows['error_data']['data']['imported_columns'].append(row[i.column - 1])
                except:
                    _l.info('can\'t process input: %s|%s', i.name, i.column, exc_info=True)
                    error_rows['error_data']['data']['imported_columns'].append(ugettext('Invalid expression'))
                    inputs_error.append(i)

            if inputs_error:

                error_rows['level'] = 'error'

                error_rows['error_message'] = error_rows['error_message'] + str(
                    ugettext('Can\'t process fields: %(inputs)s') % {
                        'inputs': ', '.join('[' + i.name + '] (Can\'t find input)' for i in inputs_error)
                    })
                instance.error_rows.append(error_rows)
                if instance.break_on_error:
                    error_rows['error_reaction'] = 'Break'
                    instance.error_row_index = row_index
                    instance.error_rows.append(error_rows)
                    return
                else:
                    error_rows['error_reaction'] = 'Continue import'
                    continue

            for i in scheme_inputs:

                error_rows['error_data']['columns']['converted_imported_columns'].append(
                    i.name + ': Conversion Expression ' + '(' + i.name_expr + ')')

                try:
                    inputs[i.name] = formula.safe_eval(i.name_expr, names=inputs_raw)
                    error_rows['error_data']['data']['converted_imported_columns'].append(row[i.column - 1])
                except:
                    _l.info('can\'t process conversion input: %s|%s', i.name, i.column, exc_info=True)
                    error_rows['error_data']['data']['converted_imported_columns'].append(
                        ugettext('Invalid expression'))
                    inputs_conversion_error.append(i)

            if inputs_conversion_error:

                error_rows['level'] = 'error'

                error_rows['error_message'] = error_rows['error_message'] + str(
                    ugettext('Can\'t process fields: %(inputs)s') % {
                        'inputs': ', '.join(
                            '[' + i.name + '] (Imported column conversion expression, value; "' + i.name_exp + '")' for
                            i in inputs_conversion_error)
                    })
                instance.error_rows.append(error_rows)
                if instance.break_on_error:
                    error_rows['error_reaction'] = 'Break'
                    instance.error_row_index = row_index
                    instance.error_rows.append(error_rows)
                    return
                else:
                    error_rows['error_reaction'] = 'Continue import'
                    continue

            try:
                selector_value = formula.safe_eval(scheme.rule_expr, names=inputs)
            except:

                error_rows['level'] = 'error'

                _l.info('can\'t process selector value expression', exc_info=True)
                error_rows['error_message'] = error_rows['error_message'] + '\n' + '\n' + str(ugettext(
                    'Can\'t eval rule expression'))
                instance.error_rows.append(error_rows)
                if instance.break_on_error:
                    instance.error_row_index = row_index
                    instance.error_rows.append(error_rows)
                    return
                else:
                    continue
            _l.info('selector_value value: %s', selector_value)

            matched_selector = False
            processed_scenarios = 0

            for scheme_recon in recon_scenarios:

                matched_selector = False

                selector_values = scheme_recon.selector_values.all()

                for item in selector_values:

                    if item.value == selector_value:
                        matched_selector = True

                if matched_selector:

                    processed_scenarios = processed_scenarios + 1

                    result_row = {}

                    for i in scheme_inputs:
                        result_row[i.name] = row[i.column - 1]

                    result_row['fields'] = []

                    fields = {}
                    fields_error = []
                    for field in scheme_recon.fields.all():

                        new_bank_file_field = ReconciliationNewBankFileField(master_user=instance.master_user)

                        new_bank_file_field.reference_name = field.reference_name
                        new_bank_file_field.description = field.description
                        new_bank_file_field.file_name = instance.filename
                        new_bank_file_field.import_scheme_name = instance.scheme.scheme_name

                        try:
                            new_bank_file_field.source_id = formula.safe_eval(scheme_recon.line_reference_id,
                                                                              names=inputs)
                        except formula.InvalidExpression:
                            new_bank_file_field.value_string = '<InvalidExpression>'

                        try:
                            new_bank_file_field.reference_date = formula.safe_eval(scheme_recon.reference_date,
                                                                                   names=inputs)
                        except formula.InvalidExpression:
                            new_bank_file_field.reference_date = _now

                        if field.value_string:
                            try:
                                new_bank_file_field.value_string = formula.safe_eval(field.value_string, names=inputs)
                            except formula.InvalidExpression:
                                new_bank_file_field.value_string = '<InvalidExpression>'
                        if field.value_float:
                            try:
                                new_bank_file_field.value_float = formula.safe_eval(field.value_float, names=inputs)
                            except formula.InvalidExpression:
                                pass

                        if field.value_date:
                            try:
                                new_bank_file_field.value_date = formula.safe_eval(field.value_date, names=inputs)
                            except formula.InvalidExpression:
                                pass

                        new_bank_file_field.save()

                        try:

                            existed_bank_file_field = ReconciliationBankFileField.objects.get(
                                master_user=instance.master_user,
                                source_id=new_bank_file_field.source_id,
                                reference_name=new_bank_file_field.reference_name,
                                import_scheme_name=new_bank_file_field.import_scheme_name)

                            serializer = ReconciliationBankFileFieldSerializer(existed_bank_file_field)

                        except ReconciliationBankFileField.DoesNotExist:

                            serializer = ReconciliationNewBankFileFieldSerializer(new_bank_file_field)



                        result_row['fields'].append(serializer.data)

                        try:
                            result_row['source_id'] = formula.safe_eval(scheme_recon.line_reference_id, names=inputs)
                        except formula.InvalidExpression:
                            result_row['source_id'] = '<InvalidExpression>'

                    instance.processed_rows = instance.processed_rows + 1

                    self.update_state(task_id=instance.task_id, state=Task.STATUS_PENDING,
                                      meta={'processed_rows': instance.processed_rows,
                                            'total_rows': instance.total_rows,
                                            'scheme_name': instance.scheme.scheme_name, 'file_name': instance.filename})

                    instance.results.append(result_row)

            if processed_scenarios == 0:
                error_rows['level'] = 'error'

                if instance.break_on_error:
                    instance.error_row_index = row_index
                    error_rows['error_reaction'] = 'Break'
                    instance.error_rows.append(error_rows)
                    return
                else:
                    error_rows['error_reaction'] = 'Continue import'

            instance.error_rows.append(error_rows)

    def _row_count(file):

        delimiter = instance.delimiter.encode('utf-8').decode('unicode_escape')

        reader = csv.reader(file, delimiter=delimiter, quotechar=instance.quotechar,
                            strict=False, skipinitialspace=True)

        row_index = 0

        for row_index, row in enumerate(reader):
            pass
        return row_index

    instance.error_rows = []
    try:
        with import_file_storage.open(instance.file_path, 'rb') as f:
            with NamedTemporaryFile() as tmpf:
                _l.info('tmpf')
                _l.info(tmpf)

                for chunk in f.chunks():
                    tmpf.write(chunk)
                tmpf.flush()
                with open(tmpf.name, mode='rt', encoding=instance.encoding, errors='ignore') as cfr:
                    instance.total_rows = _row_count(cfr)
                    self.update_state(task_id=instance.task_id, state=Task.STATUS_PENDING,
                                      meta={'total_rows': instance.total_rows,
                                            'scheme_name': instance.scheme.scheme_name, 'file_name': instance.filename})
                    # instance.save()
                with open(tmpf.name, mode='rt', encoding=instance.encoding, errors='ignore') as cf:
                    _process_csv_file(cf)

    except:
        _l.info('Can\'t process file', exc_info=True)
        instance.error_message = ugettext("Invalid file format or file already deleted.")
    finally:
        import_file_storage.delete(instance.file_path)

    instance.error = bool(instance.error_message) or (instance.error_row_index is not None) or bool(instance.error_rows)

    return instance
