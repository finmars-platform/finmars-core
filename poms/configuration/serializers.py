import os
import shutil

from rest_framework import serializers

from poms.common.storage import get_storage
from poms.configuration.models import Configuration, NewMemberSetupConfiguration
from poms_app import settings

storage = get_storage()

import logging

_l = logging.getLogger('poms.configuration')


class ConfigurationSerializer(serializers.ModelSerializer):
    manifest = serializers.JSONField(allow_null=True, required=False)

    class Meta:
        model = Configuration
        fields = (
            'id', 'configuration_code', 'name', 'short_name', 'description', 'version', 'is_from_marketplace',
            'is_package', 'manifest', 'is_primary')


class ConfigurationImport:
    def __init__(self, file_path=None, file_name=None):
        self.file_path = file_path
        self.file_name = file_name


class ConfigurationImportSerializer(serializers.Serializer):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    file = serializers.FileField(required=False, allow_null=True)

    def create(self, validated_data):
        file = validated_data.pop('file', None)

        file_name = file.name

        # file_path = '%s/public/configurations/%s' % (settings.BASE_API_URL, file_name)
        file_path = os.path.join(settings.BASE_DIR,
                                 'public/import-configurations/%s' % file_name)

        # if not os.path.exists(os.path.join(settings.BASE_DIR, 'configurations/')):
        #     os.makedirs(os.path.join(settings.BASE_DIR, 'configurations/'), exist_ok=True)
        #
        # shutil.copyfile(file.temporary_file_path(), file_path)
        # storage.save(file_path, file)

        storage.save(file_path, file)

        _l.info("Save file to %s" % file_path)

        return ConfigurationImport(file_path=file_path, file_name=file_name)


class NewMemberSetupConfigurationSerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = NewMemberSetupConfiguration
        fields = (
            'id',
            'name', 'notes',
            'user_code', 'configuration_code',
            'target_configuration_code',
            'target_configuration_version',
            'target_configuration_is_package',

            'file_url',
            'file_name',

            'file'
        )

    def create(self, validated_data):

        file = validated_data.pop('file', None)

        if file:
            file_path = settings.BASE_API_URL + '/.system/new-member-setup-configurations/%s' % file.name

            storage.save(file_path, file)
            validated_data['file_url'] = file_path
            validated_data['file_name'] = file.name

        return NewMemberSetupConfiguration.objects.create(**validated_data)

    def update(self, instance, validated_data):

        file = validated_data.pop('file', None)

        if file:
            file_path = settings.BASE_API_URL + '/.system/new-member-setup-configurations/%s' % file.name

            storage.save(file_path, file)
            validated_data['file_url'] = file_path
            validated_data['file_name'] = file.name

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        return instance
