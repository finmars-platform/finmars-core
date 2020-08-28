from poms.common.serializers import ModelWithTimeStampSerializer
from poms.credentials.models import Credentials
from poms.users.fields import MasterUserField


class CredentialsSerializer(ModelWithTimeStampSerializer):

    master_user = MasterUserField()

    class Meta:
        model = Credentials
        fields = [
            'id', 'master_user', 'name', 'user_code', 'type',
            'provider', 'username', 'password', 'key'
        ]
