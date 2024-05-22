from rest_framework import serializers

from poms.explorer.utils import has_slash


class BasePathSerializer(serializers.Serializer):
    path = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
    )

    def validate_path(self, value):
        if not value:
            return ""

        if has_slash(value):
            raise serializers.ValidationError("Path should not start or end with '/'")

        return value


class FolderPathSerializer(BasePathSerializer):
    path = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default="",
    )


class FilePathSerializer(BasePathSerializer):
    pass


TRUTHY_VALUES = {"true", "1", "yes"}


class DeletePathSerializer(BasePathSerializer):
    is_dir = serializers.CharField(
        default="false",
        required=False,
        allow_null=True,
    )

    def validate_is_dir(self, value) -> bool:
        return bool(value and (value.lower() in TRUTHY_VALUES))

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
    )

    def validate(self, attrs):
        storage = self.context["storage"]
        space_code = self.context["space_code"]

        target_directory_path = attrs['target_directory_path']
        if has_slash(target_directory_path):
            raise serializers.ValidationError(
                "'target_directory_path' should not start or end with '/'"
            )
        new_target_directory_path = f"{space_code}/{target_directory_path}"
        if storage and not storage.exists(new_target_directory_path):
            raise serializers.ValidationError(
                f"target folder '{target_directory_path}' does not exist"
            )

        updated_items = []
        for item in attrs["items"]:
            if has_slash(item):
                raise serializers.ValidationError(
                    f"item {item} should not start or end with '/'"
                )
            if target_directory_path in item:
                raise serializers.ValidationError(
                    f"item {item} should not be part of the target directory"
                )
            item = f"{space_code}/{item}"
            if storage and not storage.exists(item):
                raise serializers.ValidationError(f"item {item} does not exist")

            updated_items.append(item)

        attrs["target_directory_path"] = new_target_directory_path
        attrs["items"] = updated_items
        return attrs


class ZipFilesSerializer(serializers.Serializer):
    paths = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
    )

    def validate(self, attrs):
        for path in attrs["paths"]:
            if has_slash(path):
                raise serializers.ValidationError(
                    f"path {path} should not start or end with '/'"
                )

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
