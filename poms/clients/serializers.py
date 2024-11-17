from poms.common.serializers import ModelWithUserCodeSerializer
from poms.clients.models import Client
from poms.users.fields import MasterUserField


class ClientsViewSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = Client
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "notes",
        ]