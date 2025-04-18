from rest_framework import routers

import poms.users.views as users

router = routers.DefaultRouter()

router.register(
    r"ping",
    users.PingViewSet,
    "ping",
)
router.register(
    r"user",
    users.UserViewSet,
    'user'
)
router.register(
    r"master-user",
    users.MasterUserViewSet,
    'masteruser'
)
router.register(  # Deprecated at all, no light-method needed
    r"master-user-light",
    users.MasterUserLightViewSet,
    "masteruserlight",
)
router.register(
    r"member",
    users.MemberViewSet,
    "member",
)
router.register(
    r"ecosystem-default",
    users.EcosystemDefaultViewSet,
    "ecosystemdefault",
)
router.register(
    r"usercode-prefix",
    users.UsercodePrefixViewSet,
    "usercodeprefix",
)

# router.register(r'group', users.GroupViewSet)
# router.register(
#     r"group",
#     iam.GroupViewSet,
# )
# router.register(
#     r"language",
#     api.LanguageViewSet,
#     "language",
# )
# router.register(
#     r"timezone",
#     api.TimezoneViewSet,
#     "timezone",
# )
