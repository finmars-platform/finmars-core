from rest_framework import routers

from poms.schedules import views

router = routers.DefaultRouter()
router.register(
    "schedules/schedule",
    views.ScheduleViewSet,
    "schedule",
)
