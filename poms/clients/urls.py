from rest_framework import routers
import poms.clients.views as clients


router = routers.DefaultRouter()

router.register(
    r"client",
    clients.ClientsViewSet,
    "client",
)