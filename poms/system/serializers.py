
from rest_framework import serializers

from poms.system.models import EcosystemConfiguration


class EcosystemConfigurationSerializer(serializers.ModelSerializer):

    data = serializers.JSONField(allow_null=False)

    class Meta:

        model = EcosystemConfiguration
        fields = ('id', 'name', 'description', 'data')
