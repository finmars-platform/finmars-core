from poms.clients.models import Client
from poms.common.fields import PrimaryKeyRelatedFilteredField


class ClientField(PrimaryKeyRelatedFilteredField):
    queryset = Client.objects
