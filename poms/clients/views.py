from rest_framework.decorators import action
from poms.common.views import AbstractModelViewSet
from poms.clients.serializers import ClientsViewSerializer
from poms.clients.models import Client


class ClietnsViewSet(AbstractModelViewSet):
    queryset = Client.objects.select_related(
        "master_user",
    )
    serializer_class = ClientsViewSerializer
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
    ]

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=ClientsViewSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)