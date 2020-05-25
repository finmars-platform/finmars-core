from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from poms.common.serializers import ModelWithTimeStampSerializer
from poms.complex_import.models import ComplexImportScheme, ComplexImport, ComplexImportSchemeAction, \
    ComplexImportSchemeActionCsvImport, ComplexImportSchemeActionTransactionImport
from poms.csv_import.fields import CsvImportSchemeField
from poms.integrations.fields import ComplexTransactionImportSchemeRestField

from poms.users.fields import MasterUserField

from rest_framework.fields import empty


class ComplexImportSchemeActionCsvImportSerializer(serializers.ModelSerializer):
    csv_import_scheme = CsvImportSchemeField(required=False, allow_null=True)

    class Meta:
        model = ComplexImportSchemeActionCsvImport
        fields = (
            'csv_import_scheme', 'mode', 'missing_data_handler', 'error_handler', 'classifier_handler', 'notes')


class ComplexImportSchemeActionTransactionImportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplexImportSchemeActionTransactionImport
        fields = ('complex_transaction_import_scheme', 'missing_data_handler', 'error_handler', 'notes')


class ComplexImportSchemeActionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    skip = serializers.BooleanField(required=False)

    complex_transaction_import_scheme = ComplexImportSchemeActionTransactionImportSerializer(
        source='compleximportschemeactiontransactionimport',
        required=False,
        allow_null=True)
    csv_import_scheme = ComplexImportSchemeActionCsvImportSerializer(
        source='compleximportschemeactioncsvimport',
        required=False, allow_null=True)

    class Meta:
        model = ComplexImportSchemeAction
        fields = (
            'id', 'action_notes', 'order', 'skip', 'csv_import_scheme', 'complex_transaction_import_scheme')


class ComplexImportSchemeSerializer(ModelWithTimeStampSerializer):
    master_user = MasterUserField()

    actions = ComplexImportSchemeActionSerializer(required=False, many=True, read_only=False)

    class Meta:
        model = ComplexImportScheme
        fields = ('id', 'master_user', 'scheme_name', 'actions')

    def create(self, validated_data):
        actions = validated_data.pop('actions', None)
        instance = super(ComplexImportSchemeSerializer, self).create(validated_data)
        self.save_actions(instance, actions)
        return instance

    def update(self, instance, validated_data):

        actions = validated_data.pop('actions', empty)
        instance = super(ComplexImportSchemeSerializer, self).update(instance, validated_data)

        if actions is not empty:
            actions = self.save_actions(instance, actions)
        if actions is not empty:
            instance.actions.exclude(id__in=[a.id for a in actions]).delete()
        return instance

    def save_actions_csv_import_scheme(self, instance, actions, existed_actions, actions_data):

        for order, action_data in enumerate(actions_data):
            pk = action_data.pop('id', None)
            action = existed_actions.get(pk, None)

            action_csv_import_scheme_data = action_data.get('csv_import_scheme',
                                                            action_data.get('compleximportschemeactioncsvimport'))
            if action_csv_import_scheme_data:

                action_csv_import_scheme = None
                if action:
                    try:
                        action_csv_import_scheme = action.compleximportschemeactioncsvimport
                    except ObjectDoesNotExist:
                        pass
                if action_csv_import_scheme is None:
                    action_csv_import_scheme = ComplexImportSchemeActionCsvImport(complex_import_scheme=instance)

                action_csv_import_scheme.order = order

                action_csv_import_scheme.action_notes = action_data.get('action_notes',
                                                                        action_csv_import_scheme.action_notes)

                action_csv_import_scheme.skip = action_data.get('skip',
                                                                                action_csv_import_scheme.skip)


                for attr, value in action_csv_import_scheme_data.items():
                    setattr(action_csv_import_scheme, attr, value)

                action_csv_import_scheme.save()
                actions[order] = action_csv_import_scheme

    def save_actions_complex_transaction_import_scheme(self, instance, actions, existed_actions, actions_data):

        for order, action_data in enumerate(actions_data):
            pk = action_data.pop('id', None)
            action = existed_actions.get(pk, None)

            action_complex_transaction_import_scheme_data = action_data.get('complex_transaction_import_scheme',
                                                                            action_data.get(
                                                                                'compleximportschemeactiontransactionimport'))
            if action_complex_transaction_import_scheme_data:

                action_complex_transaction_import_scheme = None
                if action:
                    try:
                        action_complex_transaction_import_scheme = action.compleximportschemeactiontransactionimport
                    except ObjectDoesNotExist:
                        pass
                if action_complex_transaction_import_scheme is None:
                    action_complex_transaction_import_scheme = ComplexImportSchemeActionTransactionImport(
                        complex_import_scheme=instance)

                action_complex_transaction_import_scheme.order = order

                action_complex_transaction_import_scheme.action_notes = action_data.get('action_notes',
                                                                                        action_complex_transaction_import_scheme.action_notes)

                action_complex_transaction_import_scheme.skip = action_data.get('skip',
                                                                                        action_complex_transaction_import_scheme.skip)

                for attr, value in action_complex_transaction_import_scheme_data.items():
                    setattr(action_complex_transaction_import_scheme, attr, value)

                action_complex_transaction_import_scheme.save()
                actions[order] = action_complex_transaction_import_scheme

    def save_actions(self, instance, actions_data):
        actions_qs = instance.actions.select_related(
            'compleximportschemeactioncsvimport',
            'compleximportschemeactiontransactionimport', ).order_by('order', 'id')
        existed_actions = {a.id: a for a in actions_qs}

        actions = [None for a in actions_data]

        self.save_actions_csv_import_scheme(instance, actions, existed_actions, actions_data)

        self.save_actions_complex_transaction_import_scheme(instance, actions, existed_actions, actions_data)

        return actions


class ComplexImportSerializer(serializers.ModelSerializer):
    file = serializers.FileField()

    class Meta:
        model = ComplexImport

        fields = ('file', 'complex_import_scheme')
