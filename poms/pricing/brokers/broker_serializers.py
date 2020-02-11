from rest_framework import serializers


class StandardProtocolValueSerializer(serializers.Serializer):
    date = serializers.DateField()
    value = serializers.CharField()


class StandardProtocolFieldSerializer(serializers.Serializer):

    code = serializers.CharField(max_length=255)
    parameters = serializers.ListField(child=serializers.CharField(max_length=255))
    values = StandardProtocolValueSerializer(many=True)


class StandardProtocolItemSerializer(serializers.Serializer):

    reference = serializers.CharField(max_length=255)
    parameters = serializers.ListField(child=serializers.CharField(max_length=255))
    fields = StandardProtocolFieldSerializer(many=True)


class StandardProtocolSerializer(serializers.Serializer):

    date_from = serializers.DateField()
    date_to = serializers.DateField()

    items = StandardProtocolItemSerializer(many=True)


class DataRequestSerializer(serializers.Serializer):

    procedure = serializers.IntegerField()

    data = StandardProtocolSerializer()
