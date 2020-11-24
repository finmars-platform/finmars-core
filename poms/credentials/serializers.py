from poms.common.serializers import ModelWithTimeStampSerializer
from poms.credentials.models import Credentials
from poms.users.fields import MasterUserField
from rest_framework import serializers

from storages.backends.sftpstorage import SFTPStorage
SFS = SFTPStorage()

class CredentialsSerializer(ModelWithTimeStampSerializer):

    master_user = MasterUserField()
    path_to_public_key = serializers.FileField(required=False, allow_null=True, allow_empty_file=False, write_only=True)
    path_to_private_key = serializers.FileField(required=False, allow_null=True, allow_empty_file=False, write_only=True)

    class Meta:
        model = Credentials
        fields = [
            'id', 'master_user', 'name', 'user_code', 'type',
            'provider', 'username', 'password',
            'public_key', 'path_to_public_key',
            'private_key', 'path_to_private_key'
        ]

    def create(self, validated_data):

        path_to_public_key = validated_data.pop('path_to_private_key', None)
        path_to_private_key = validated_data.pop('path_to_private_key', None)

        credentials = Credentials.objects.create(**validated_data)

        if path_to_public_key:
            file_path = '%s/data_providers/%s/%s' % (credentials.master_user.token, credentials.provider.user_code, path_to_public_key.name)

            SFS.save(file_path, path_to_public_key)
            credentials.path_to_public_key = file_path

        if path_to_private_key:
            file_path = '%s/data_providers/%s/%s' % (credentials.master_user.token, credentials.provider.user_code, path_to_private_key.name)

            SFS.save(file_path, path_to_private_key)
            credentials.path_to_private_key = file_path

        credentials.save()


        return credentials

    def update(self, credentials, validated_data):

        path_to_public_key = validated_data.pop('path_to_private_key', None)
        path_to_private_key = validated_data.pop('path_to_private_key', None)

        credentials.name = validated_data.get('name', credentials.name)
        credentials.user_code = validated_data.get('user_code', credentials.user_code)
        credentials.type = validated_data.get('type', credentials.type)
        credentials.provider = validated_data.get('provider', credentials.provider)
        credentials.username = validated_data.get('username', credentials.username)
        credentials.password = validated_data.get('password', credentials.password)
        credentials.public_key = validated_data.get('password', credentials.public_key)
        credentials.private_key = validated_data.get('private_key', credentials.private_key)

        if path_to_public_key:
            file_path = '%s/data_providers/%s/%s' % (credentials.master_user.token, credentials.provider.user_code, path_to_public_key.name)

            SFS.save(file_path, path_to_public_key)
            credentials.path_to_public_key = file_path

        if path_to_private_key:
            file_path = '%s/data_providers/%s/%s' % (credentials.master_user.token, credentials.provider.user_code, path_to_private_key.name)

            SFS.save(file_path, path_to_private_key)
            credentials.path_to_private_key = file_path

        credentials.save()

        return credentials
