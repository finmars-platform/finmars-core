from rest_framework import routers
from . import views
from django.urls import path, include

router = routers.DefaultRouter()

router.register(
    r"system-notifications",
    views.NotificationViewSet,
    basename="system-notification",
)
router.register(
    r"subscriptions",
    views.SubscriptionViewSet,
    basename="subscription",
)
router.register(
    r"channels",
    views.ChannelViewSet,
    basename="channel",
)

router.register(r"categories", views.CategoryViewSet, basename="category")

router.register(r"statuses", views.CurrentStatusViewSet, basename="status")

# app_name = 'system_messages'

urlpatterns = [
    path("", include(router.urls)),
]
