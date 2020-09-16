from poms.common.serializers import ModelWithTimeStampSerializer
from poms.procedures.models import RequestDataFileProcedure
from poms.users.fields import MasterUserField
from rest_framework import serializers

class RequestDataFileProcedureSerializer(ModelWithTimeStampSerializer):

    master_user = MasterUserField()

    class Meta:
        model = RequestDataFileProcedure
        fields = [
            'id', 'master_user', 'name', 'user_code', 'notes',
            'provider', 'scheme_name'
        ]


class RunRequestDataFileProcedureSerializer(serializers.Serializer):
    def __init__(self, **kwargs):
        kwargs['context'] = context = kwargs.get('context', {}) or {}
        super(RunRequestDataFileProcedureSerializer, self).__init__(**kwargs)
        context['instance'] = self.instance

        self.fields['procedure'] = serializers.PrimaryKeyRelatedField(read_only=True)
