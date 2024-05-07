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


class MoveSerializer(serializers.Serializer):
    target_directory_path = serializers.CharField(required=True, allow_blank=False)
    items = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
    )

    def validate(self, attrs):
        target_directory_path = attrs["target_directory_path"]
        if has_slash(target_directory_path):
            raise serializers.ValidationError(
                "'target_directory_path' should not start or end with '/'"
            )

        items = attrs["items"]
        for item in items:
            if has_slash(item):
                raise serializers.ValidationError(
                    f"item {item} should not start or end with '/'"
                )
            if target_directory_path in item:
                raise serializers.ValidationError(
                    f"item {item} should not be part of the target directory"
                )

        return attrs
