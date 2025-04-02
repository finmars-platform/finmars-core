from rest_framework import routers

import poms.clients.views as clients

router = routers.DefaultRouter()

router.register(
    "client",
    clients.ClientsViewSet,
    "client",
)
router.register(
    "client-secret",
    clients.ClientSecretsViewSet,
    "clientsecrets",
)
