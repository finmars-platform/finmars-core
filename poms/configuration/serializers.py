from rest_framework import serializers

from poms.configuration.models import Configuration


class ConfigurationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Configuration
        fields = ('id', 'configuration_code', 'name', 'short_name', 'notes', 'version')