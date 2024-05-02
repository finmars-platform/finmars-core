from rest_framework import serializers


class ExplorerSerializer(serializers.Serializer):
    path = serializers.CharField(required=True, allow_blank=False, allow_null=False)

    def validate_path(self, value):
        if value[-1] == "/":
            raise serializers.ValidationError("Path should not end with a slash")

        return value
