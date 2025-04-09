from rest_framework import routers

from poms.celery_tasks import views

router = routers.DefaultRouter()

router.register(
    "task",
    views.CeleryTaskViewSet,
    "CeleryTask",
)
router.register(
    "worker",
    views.CeleryWorkerViewSet,
    "CeleryWorker",
)
router.register(
    "stats",
    views.CeleryStatsViewSet,
    "CeleryStats",
)
