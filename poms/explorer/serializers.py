from rest_framework import serializers

from poms.explorer.utils import has_slash


class ExplorerFolderPathSerializer(serializers.Serializer):
    path = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate_path(self, value):
        if not value:
            return ""

        if has_slash(value):
            raise serializers.ValidationError("Path should not start or end with '/'")

        return value


class ExplorerFilePathSerializer(serializers.Serializer):
    path = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
    )

    def validate_path(self, value):
        if has_slash(value):
            raise serializers.ValidationError("Path should not start or end with '/'")

        return value
