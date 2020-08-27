from poms.common.serializers import ModelWithTimeStampSerializer
from poms.procedures.models import RequestDataFileProcedure
from poms.users.fields import MasterUserField


class RequestDataFileProcedureSerializer(ModelWithTimeStampSerializer):

    master_user = MasterUserField()

    class Meta:
        model = RequestDataFileProcedure
        fields = [
            'id', 'master_user', 'name', 'user_code', 'notes',
            'provider', 'scheme_name'
        ]
