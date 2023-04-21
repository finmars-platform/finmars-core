import os
import shutil

from rest_framework import serializers

from poms.common.storage import get_storage
from poms.configuration.models import Configuration
from poms_app import settings

storage = get_storage()

import logging

_l = logging.getLogger('poms.configuration')


class ConfigurationSerializer(serializers.ModelSerializer):
    manifest = serializers.JSONField(allow_null=True, required=False)

    class Meta:
        model = Configuration
        fields = (
            'id', 'configuration_code', 'name', 'short_name', 'description', 'version', 'from_marketplace',
            'is_package', 'manifest')


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
                                 'configurations/%s' % file_name)

        shutil.copyfile(file.temporary_file_path(), file_path)
        # storage.save(file_path, file)

        _l.info("Save file to %s" % file_path)

        return ConfigurationImport(file_path=file_path, file_name=file_name)
