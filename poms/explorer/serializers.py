import mimetypes
import os.path
import re

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.common.storage import pretty_size
from poms.explorer.models import FinmarsFile
from poms.explorer.utils import check_is_true, path_is_file
from poms.instruments.models import Instrument


class BasePathSerializer(serializers.Serializer):
    path = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
    )

    @staticmethod
    def validate_path(path: str):
        return path.strip("/") if path else ""


class FolderPathSerializer(BasePathSerializer):
    path = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default="",
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


forbidden_symbols_in_name = r'[/\\:*?"<>|;&]'
bad_name_regex = re.compile(forbidden_symbols_in_name)

forbidden_symbols_in_path = r'[:*?"<>|;&]'
bad_path_regex = re.compile(forbidden_symbols_in_path)


class InstrumentMicroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = [
            "id",
            "user_code",
        ]


class FinmarsFileSerializer(serializers.ModelSerializer):
    instruments = InstrumentMicroSerializer(many=True, read_only=True)

    class Meta:
        model = FinmarsFile
        fields = "__all__"

    @staticmethod
    def validate_path(path: str) -> str:
        if bad_path_regex.search(path):
            raise ValidationError(detail=f"Invalid path {path}", code="path")

        return path

    @staticmethod
    def validate_name(name: str) -> str:
        if bad_name_regex.search(name):
            raise ValidationError(detail=f"Invalid name {name}", code="name")

        return name

    @staticmethod
    def validate_size(size: int) -> int:
        if size < 1:
            raise ValidationError(detail=f"Invalid size {size}", code="size")

        return size
