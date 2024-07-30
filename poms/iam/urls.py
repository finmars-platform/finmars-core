from rest_framework import routers

import poms.iam.views as iam

router = routers.DefaultRouter()
router.register(
    "role",
    iam.RoleViewSet,
    "role",
)
router.register(
    "group",
    iam.GroupViewSet,
    "group",
)
router.register(
    "access-policy",
    iam.AccessPolicyViewSet,
    "accessPolicy",
)
