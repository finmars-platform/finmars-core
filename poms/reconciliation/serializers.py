from rest_framework import serializers

from poms.common.fields import ExpressionField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.integrations.fields import ComplexTransactionImportSchemeRestField
from poms.integrations.serializers import ComplexTransactionImportSchemeSerializer
from poms.reconciliation.models import ReconciliationNewBankFileField, ReconciliationComplexTransactionField, \
    ReconciliationBankFileField, TransactionTypeReconField
from poms.users.fields import MasterUserField, HiddenMemberField

from poms.integrations.storage import import_file_storage

from django.utils.translation import ugettext, ugettext_lazy
from django.utils import timezone

import uuid


class TransactionTypeReconFieldSerializer(serializers.ModelSerializer):
    value_string = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True,
                                   allow_null=True, default='')
    value_float = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True,
                                  allow_null=True, default='')
    value_date = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True,
                                 allow_null=True, default='')

    class Meta:
        model = TransactionTypeReconField
        fields = ['id', 'reference_name', 'description', 'value_string', 'value_float', 'value_date']


class ReconciliationComplexTransactionFieldSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)

    class Meta:
        model = ReconciliationComplexTransactionField
        fields = (
            'id', 'master_user', 'complex_transaction', 'description', 'value_string', 'value_float', 'value_date',
            'is_canceled',
            'status', 'reference_name')


class ReconciliationBankFileFieldSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    type = serializers.SerializerMethodField()

    class Meta:
        model = ReconciliationBankFileField
        fields = (
            'id', 'master_user', 'source_id',
            'description',
            'value_string', 'value_float', 'value_date',
            'is_canceled',
            'status',
            'file_name', 'import_scheme_name',
            'reference_date', 'reference_name',
            'type')

    def get_type(self, obj):
        return 'existing'


class ReconciliationNewBankFileFieldSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    type = serializers.SerializerMethodField()

    class Meta:
        model = ReconciliationNewBankFileField
        fields = (
            'id', 'master_user', 'source_id',
            'description',
            'value_string', 'value_float', 'value_date',
            'is_canceled',
            'file_name', 'import_scheme_name',
            'reference_date', 'reference_name',
            'type')

    def get_type(self, obj):
        return 'new'


class ProcessBankFileForReconcile:
    def __init__(self, task_id=None, task_status=None, master_user=None, member=None,
                 scheme=None, file_path=None, skip_first_line=None, delimiter=None, quotechar=None, encoding=None,
                 error_handling=None, missing_data_handler=None, error=None, error_message=None, error_row_index=None,
                 error_rows=None, results=None,
                 total_rows=None, processed_rows=None, filename=None):
        self.task_id = task_id
        self.task_status = task_status

        self.filename = filename

        self.master_user = master_user
        self.member = member

        self.scheme = scheme
        self.file_path = file_path
        self.skip_first_line = bool(skip_first_line)
        self.delimiter = delimiter or ','
        self.quotechar = quotechar or '"'
        self.encoding = encoding or 'utf-8'

        self.error_handling = error_handling or 'continue'
        self.missing_data_handler = missing_data_handler or 'throw_error'
        self.error = error
        self.error_message = error_message
        self.error_row_index = error_row_index
        self.error_rows = error_rows
        self.total_rows = total_rows
        self.processed_rows = processed_rows

        self.results = results

    def __str__(self):
        return '%s-%s:%s' % (getattr(self.master_user, 'id', None), getattr(self.member, 'id', None), self.file_path)

    @property
    def break_on_error(self):
        return self.error_handling == 'break'

    @property
    def continue_on_error(self):
        return self.error_handling == 'continue'


class ProcessBankFileForReconcileSerializer(serializers.Serializer):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    master_user = MasterUserField()
    member = HiddenMemberField()

    scheme = ComplexTransactionImportSchemeRestField(required=False)
    file = serializers.FileField(required=False, allow_null=True)
    skip_first_line = serializers.BooleanField(required=False, default=True)
    delimiter = serializers.CharField(max_length=2, required=False, initial=',', default=',')
    quotechar = serializers.CharField(max_length=1, required=False, initial='"', default='"')
    encoding = serializers.CharField(max_length=20, required=False, initial='utf-8', default='utf-8')

    error_handling = serializers.ChoiceField(
        choices=[('break', 'Break on first error'), ('continue', 'Try continue')],
        required=False, initial='continue', default='continue'
    )

    missing_data_handler = serializers.ChoiceField(
        choices=[('throw_error', 'Treat as Error'), ('set_defaults', 'Replace with Default Value')],
        required=False, initial='throw_error', default='throw_error'
    )

    error = serializers.ReadOnlyField()
    error_message = serializers.ReadOnlyField()
    error_row_index = serializers.ReadOnlyField()
    error_rows = serializers.ReadOnlyField()
    processed_rows = serializers.ReadOnlyField()
    total_rows = serializers.ReadOnlyField()
    results = serializers.ReadOnlyField()

    scheme_object = ComplexTransactionImportSchemeSerializer(source='scheme', read_only=True)

    def create(self, validated_data):

        filetmp = file = validated_data.get('file', None)

        print('filetmp %s' % filetmp)

        filename = None
        if filetmp:
            filename = filetmp.name

            print('filename %s' % filename)

            validated_data['filename'] = filename

        if validated_data.get('task_id', None):
            validated_data.pop('file', None)
        else:
            file = validated_data.pop('file', None)
            if file:
                master_user = validated_data['master_user']
                file_name = '%s-%s' % (timezone.now().strftime('%Y%m%d%H%M%S'), uuid.uuid4().hex)
                file_path = self._get_path(master_user, file_name)
                import_file_storage.save(file_path, file)
                validated_data['file_path'] = file_path
            else:
                raise serializers.ValidationError({'file': ugettext('Required field.')})
        return ProcessBankFileForReconcile(**validated_data)

    def _get_path(self, owner, file_name):
        return '%s/%s.dat' % (owner.pk, file_name)
