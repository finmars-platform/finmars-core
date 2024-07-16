import mimetypes
import os.path
import re
from pathlib import Path

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.common.storage import pretty_size
from poms.explorer.models import (
    DIR,
    FILE,
    FULL,
    MAX_NAME_LENGTH,
    MAX_PATH_LENGTH,
    READ,
    FinmarsDirectory,
    FinmarsFile,
)
from poms.explorer.policy_handlers import upsert_storage_obj_access_policy
from poms.explorer.utils import check_is_true, path_is_file
from poms.iam.models import AccessPolicy
from poms.instruments.models import Instrument
from poms.users.models import MasterUser, Member


forbidden_symbols_in_path = r'[:*?"<>|;&]'
bad_path_regex = re.compile(forbidden_symbols_in_path)


class BasePathSerializer(serializers.Serializer):
    path = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
    )

    def validate_path(self, value: str) -> str:
        if bad_path_regex.search(value):
            raise ValidationError(detail=f"Invalid path {value}", code="path")

        path = str(Path(value))
        # TODO: check if path exists and has policy
        return path


class DirectoryPathSerializer(BasePathSerializer):
    pass


class FilePathSerializer(BasePathSerializer):
    def validate_path(self, value: str) -> str:
        path = super().validate_path(value)
        parent = Path(path).parent
        # TODO: check if parent exists and has policy
        path = str(str)
        return path


class DeletePathSerializer(BasePathSerializer):
    is_dir = serializers.CharField(
        default="false",
        required=False,
        allow_null=True,
    )

    @staticmethod
    def validate_is_dir(value) -> bool:
        return check_is_true(value)

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
    items = serializers.ListField(
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

        updated_items = []
        for path in attrs["items"]:
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

            updated_items.append(path)

        attrs["target_directory_path"] = new_target_directory_path
        attrs["items"] = updated_items
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

    def to_representation(self, instance: FinmarsFile) -> dict:
        name = instance.name
        size = instance.size
        mime_type, _ = mimetypes.guess_type(name)
        return {
            "type": "file",
            "mime_type": mime_type,
            "name": name,
            "created": instance.created,
            "modified": instance.modified,
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
            "created",
            "modified",
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
        path = path.rstrip("/")
        return path

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
    object_type = serializers.CharField(allow_blank=False, max_length=10)
    policy = serializers.CharField(allow_blank=False, max_length=10)
    username = serializers.CharField(allow_blank=False, max_length=MAX_NAME_LENGTH)

    @staticmethod
    def validate_path(value: str) -> str:
        if bad_path_regex.search(value):
            raise ValidationError(detail=f"Invalid path {value}", code="path")
        return value

    @staticmethod
    def validate_object_type(value: str) -> str:
        if value not in {DIR, FILE}:
            raise ValidationError(detail=f"Invalid object type {value}", code="object")
        return value

    @staticmethod
    def validate_policy(value: str) -> str:
        if value not in {READ, FULL}:
            raise ValidationError(detail=f"Invalid policy {value}", code="policy")
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
        object_type = attrs["object_type"]
        if object_type == DIR:
            storage_object = FinmarsDirectory.objects.filter(path=path).first()
        else:
            storage_object = FinmarsFile.objects.filter(path=path).first()

        if storage_object is None:
            raise ValidationError(
                detail=f"Storage object {path} of type {object_type} not found",
                code="path",
            )

        attrs["storage_object"] = storage_object
        return attrs

    def set_access_policy(self):
        storage_object = self.validated_data["storage_object"]
        policy = self.validated_data["policy"]
        member = self.validated_data["username"]
        return upsert_storage_obj_access_policy(storage_object, member, policy)
