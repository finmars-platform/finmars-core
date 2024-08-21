import mimetypes
import os.path
import re

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.common.storage import pretty_size
from poms.explorer.models import (
    DIR_SUFFIX,
    MAX_NAME_LENGTH,
    MAX_PATH_LENGTH,
    AccessLevel,
    FinmarsDirectory,
    FinmarsFile,
)
from poms.explorer.policy_handlers import get_or_create_storage_access_policy
from poms.explorer.utils import is_true_value, path_is_file
from poms.iam.models import AccessPolicy
from poms.instruments.models import Instrument
from poms.users.models import MasterUser, Member

forbidden_symbols_in_path = r'[:*?"<>|;&]'
bad_path_regex = re.compile(forbidden_symbols_in_path)

"""
 Path (a string in the DB), should be a valid UNIX style path which has no: 
 forbidden symbols, two and more adjusted '/' ( like //, /// etc ). 
 Path should end with file name (without '/' at the end) or with '/*' for directories.
 Root path contains '<space-code>/', it's the first directory available for a user.
 Path should be no longer than 2048 characters.
"""


class BasePathSerializer(serializers.Serializer):
    path = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
    )

    @staticmethod
    def validate_path(path: str):
        return path.strip("/") if path else ""


class DirectoryPathSerializer(BasePathSerializer):
    path = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default=DIR_SUFFIX,
    )


class FilePathSerializer(BasePathSerializer):
    pass


class DeletePathSerializer(BasePathSerializer):
    is_dir = serializers.CharField(
        default="false",
        required=False,
        allow_null=True,
    )

    @staticmethod
    def validate_is_dir(value) -> bool:
        return is_true_value(value)

    def validate_path(self, value):
        if not value:
            raise serializers.ValidationError("Path required")

        if value == "/":
            raise serializers.ValidationError("Path '/' is not allowed")

        if ".system" in value:
            raise serializers.ValidationError("Path '.system' is not allowed")

        return value


class MoveSerializer(serializers.Serializer):
    target_directory_path = serializers.CharField(required=True, allow_blank=False)
    paths = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        required=True,
    )

    def validate(self, attrs):
        storage = self.context["storage"]
        space_code = self.context["space_code"]

        target_directory_path = attrs["target_directory_path"].strip("/")
        new_target_directory_path = f"{space_code}/{target_directory_path}/"
        if not storage.dir_exists(new_target_directory_path):
            raise serializers.ValidationError(
                f"target directory '{new_target_directory_path}' does not exist"
            )

        updated_paths = []
        for path in attrs["paths"]:
            path = path.strip("/")

            directory_path = os.path.dirname(path)
            if target_directory_path == directory_path:
                raise serializers.ValidationError(
                    f"path {path} belongs to target directory path"
                )

            path = f"{space_code}/{path}"
            dir_path = f"{path}/"
            if storage.dir_exists(dir_path):
                # this is a directory
                path = f"{path}/"

            updated_paths.append(path)

        attrs["target_directory_path"] = new_target_directory_path
        attrs["paths"] = updated_paths
        return attrs


class ZipFilesSerializer(serializers.Serializer):
    paths = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
    )

    def validate(self, attrs):
        for path in attrs["paths"]:
            path = path.strip("/")

        return attrs


class ResponseSerializer(serializers.Serializer):
    status = serializers.CharField(required=True)
    path = serializers.CharField(required=False)
    details = serializers.CharField(required=False)
    files = serializers.ListField(
        required=False,
        child=serializers.CharField(),
    )
    results = serializers.ListField(
        required=False,
        child=serializers.DictField(),
    )


class TaskResponseSerializer(serializers.Serializer):
    status = serializers.CharField(required=True)
    task_id = serializers.CharField(required=True)


class UnZipSerializer(serializers.Serializer):
    target_directory_path = serializers.CharField(required=True, allow_blank=False)
    file_path = serializers.CharField(required=True, allow_blank=False)

    def validate_target_directory_path(self, value):
        storage = self.context["storage"]
        space_code = self.context["space_code"]

        target_directory_path = value.strip("/")
        new_target_directory_path = f"{space_code}/{target_directory_path}/"
        if not storage.dir_exists(new_target_directory_path):
            raise serializers.ValidationError(
                f"target folder '{target_directory_path}' does not exist"
            )
        return new_target_directory_path

    def validate_file_path(self, value):
        storage = self.context["storage"]
        space_code = self.context["space_code"]

        value = value.strip("/")

        if not value.endswith(".zip"):
            raise serializers.ValidationError(
                f"file {value} should be a zip file, with '.zip' extension"
            )

        new_file_path = f"{space_code}/{value}"
        if not path_is_file(storage, new_file_path):
            raise serializers.ValidationError(f"item {new_file_path} is not a file")

        return new_file_path


class SearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinmarsFile
        fields = "__all__"

    def to_representation(self, instance: FinmarsFile) -> dict:
        name = instance.name
        size = instance.size
        mime_type, _ = mimetypes.guess_type(name)
        return {
            "type": "file",
            "mime_type": mime_type,
            "name": name,
            "created_at": instance.created_at,
            "modified_at": instance.modified_at,
            "file_path": instance.path,
            "size": size,
            "size_pretty": pretty_size(size),
        }


class QuerySearchSerializer(serializers.Serializer):
    query = serializers.CharField(allow_null=True, required=False, allow_blank=True)


class InstrumentMicroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = [
            "id",
            "user_code",
        ]


class FinmarsFileSerializer(serializers.ModelSerializer):
    instruments = InstrumentMicroSerializer(many=True, read_only=True)
    name = serializers.SerializerMethodField()
    extension = serializers.SerializerMethodField()

    class Meta:
        model = FinmarsFile
        fields = [
            "id",
            "path",
            "size",
            "name",
            "extension",
            "created_at",
            "modified_at",
            "instruments",
        ]

    @staticmethod
    def get_name(obj: FinmarsFile) -> str:
        return obj.name

    @staticmethod
    def get_extension(obj: FinmarsFile) -> str:
        return obj.extension

    @staticmethod
    def validate_path(path: str) -> str:
        if bad_path_regex.search(path):
            raise ValidationError(detail=f"Invalid path {path}", code="path")
        return path.rstrip("/")

    @staticmethod
    def validate_size(size: int) -> int:
        if size < 0:
            raise ValidationError(detail=f"Invalid size {size}", code="size")

        return size


class AccessPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPolicy
        fields = "__all__"


class StorageObjectAccessPolicySerializer(serializers.Serializer):
    path = serializers.CharField(allow_blank=False, max_length=MAX_PATH_LENGTH)
    access = serializers.CharField(allow_blank=False, max_length=10)
    username = serializers.CharField(allow_blank=False, max_length=MAX_NAME_LENGTH)

    @staticmethod
    def validate_path(value: str) -> str:
        path = value.removesuffix(DIR_SUFFIX)
        if bad_path_regex.search(path):
            raise ValidationError(detail=f"Invalid path {value}", code="path")
        return value

    @staticmethod
    def validate_access(value: str) -> str:
        AccessLevel.validate_level(value)
        return value

    def validate_username(self, value: str) -> str:
        realm_code = self.context["realm_code"]
        space_code = self.context["space_code"]
        master_user = MasterUser.objects.filter(space_code=space_code).first()
        if not master_user:
            raise ValidationError(
                detail=f"MasterUser not found for {realm_code}/{space_code}",
                code="master_user",
            )
        member = Member.objects.filter(master_user=master_user, username=value).first()
        if not master_user:
            raise ValidationError(
                detail=f"Member with username {value} not found in {realm_code}/{space_code}",
                code="username",
            )
        return member

    def validate(self, attrs: dict) -> dict:
        path = attrs["path"]
        if path.endswith(DIR_SUFFIX):
            storage_object = FinmarsDirectory.objects.filter(path=path).first()
        else:
            storage_object = FinmarsFile.objects.filter(path=path).first()

        if not storage_object:
            raise ValidationError(
                detail=f"Storage object {path} was not found",
                code="path",
            )

        attrs["storage_object"] = storage_object
        return attrs

    def set_access_policy(self) -> AccessPolicy:
        storage_object = self.validated_data["storage_object"]
        access = self.validated_data["access"]
        member = self.validated_data["username"]
        return get_or_create_storage_access_policy(storage_object, member, access)
