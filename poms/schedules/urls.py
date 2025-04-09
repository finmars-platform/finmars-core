from rest_framework import routers

from poms.schedules import views

router = routers.DefaultRouter()
router.register(
    "schedule",
    views.ScheduleViewSet,
    "schedule",
)
