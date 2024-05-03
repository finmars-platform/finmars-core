from rest_framework import serializers


class ExplorerFolderPathSerializer(serializers.Serializer):
    path = serializers.CharField(
        required=False,
        default="",
        allow_blank=True,
        allow_null=True,
    )


class ExplorerFilePathSerializer(serializers.Serializer):
    path = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
    )

    def validate_path(self, value):
        if value[-1] == "/":
            raise serializers.ValidationError("Path should not end with '/'")
        if value[0] == "/":
            raise serializers.ValidationError("Path should not start with '/'")

        return value
